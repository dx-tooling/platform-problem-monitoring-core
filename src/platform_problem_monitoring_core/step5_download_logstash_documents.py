#!/usr/bin/env python3
"""Download logstash documents from Elasticsearch."""

import argparse
import datetime
import json
import sys
import time
from datetime import timezone
from pathlib import Path
from typing import Any, Dict, List

import requests
from requests.exceptions import ConnectionError as RequestsConnectionError
from requests.exceptions import HTTPError, Timeout

from platform_problem_monitoring_core.utils import load_json, logger, save_json


def _add_time_range_to_query(
    query_data: Dict[str, Any], start_date_time: str, current_date_time: str
) -> Dict[str, Any]:
    """
    Add time range filter to the Elasticsearch query.

    Args:
        query_data: Original query data
        start_date_time: Start date and time in ISO format
        current_date_time: Current date and time in ISO format

    Returns:
        Updated query data with time range filter
    """
    # Create a deep copy of the query to avoid modifying the original
    query_copy: Dict[str, Any] = json.loads(json.dumps(query_data))

    if "query" in query_copy:
        if "bool" in query_copy["query"]:
            if "filter" not in query_copy["query"]["bool"]:
                query_copy["query"]["bool"]["filter"] = []

            # Add time range filter
            query_copy["query"]["bool"]["filter"].append(
                {"range": {"@timestamp": {"gte": start_date_time, "lte": current_date_time}}}
            )
        else:
            # If there's no bool query, create one
            original_query = query_copy["query"]
            query_copy["query"] = {
                "bool": {
                    "must": [original_query],
                    "filter": [{"range": {"@timestamp": {"gte": start_date_time, "lte": current_date_time}}}],
                }
            }
    else:
        # If there's no query at all, create a simple one
        query_copy["query"] = {
            "bool": {"filter": [{"range": {"@timestamp": {"gte": start_date_time, "lte": current_date_time}}}]}
        }

    return query_copy


def _get_start_date_time(start_date_time_file: str) -> str:
    """
    Read start date and time from file or use default.

    Args:
        start_date_time_file: Path to the file containing the start date and time

    Returns:
        Start date and time in ISO format
    """
    try:
        with Path(start_date_time_file).open("r") as f:
            start_date_time = f.read().strip()
            logger.info(f"Start date and time: {start_date_time}")
            return start_date_time
    except FileNotFoundError:
        logger.warning(f"Start date and time file not found: {start_date_time_file}")
        # Default to 24 hours ago if file not found
        # Using timezone-aware approach to address deprecation warning
        start_date_time = (datetime.datetime.now(timezone.utc) - datetime.timedelta(days=1)).isoformat()
        logger.info(f"Using default start date and time: {start_date_time}")
        return start_date_time


def _save_current_date_time(current_date_time_file: str, current_date_time: str) -> None:
    """
    Save current date and time to file for the next run.

    Args:
        current_date_time_file: Path to store the current date and time
        current_date_time: Current date and time in ISO format

    Raises:
        OSError: If unable to write to the file
    """
    try:
        with Path(current_date_time_file).open("w") as f:
            f.write(current_date_time)
    except (OSError, IOError) as e:
        logger.error(f"Failed to save current date and time to {current_date_time_file}: {e}")
        raise


def _verify_elasticsearch_connection(elasticsearch_url: str, max_retries: int = 3, timeout: int = 30) -> None:
    """
    Verify Elasticsearch server is available.

    Args:
        elasticsearch_url: Elasticsearch server URL
        max_retries: Maximum number of connection retry attempts
        timeout: Connection timeout in seconds

    Raises:
        ConnectionError: If unable to connect to the server after retries
        HTTPError: If the server returns an error response
        Timeout: If the connection times out
    """
    retry_count = 0
    last_error = None

    while retry_count < max_retries:
        try:
            # Do a simple request first to verify the server is available
            response = requests.get(elasticsearch_url, timeout=timeout)
            response.raise_for_status()  # Raise exception for 4XX/5XX responses

            server_info = response.json()
            es_version = server_info.get("version", {}).get("number", "unknown")
            logger.info(f"Connected to Elasticsearch version: {es_version}")
            return

        except (RequestsConnectionError, HTTPError, Timeout) as e:
            last_error = e
            retry_count += 1
            logger.warning(f"Connection attempt {retry_count} failed: {str(e)}")

            if retry_count < max_retries:
                # Exponential backoff: 1s, 2s, 4s, etc.
                wait_time = 2 ** (retry_count - 1)
                logger.info(f"Retrying in {wait_time} seconds...")
                time.sleep(wait_time)

    # If we get here, all retries failed
    error_msg = f"Failed to connect to Elasticsearch after {max_retries} attempts: {str(last_error)}"
    logger.error(error_msg)
    raise RequestsConnectionError(error_msg)


def _download_documents_with_pagination(
    elasticsearch_url: str, query_data: Dict[str, Any], timeout: int = 30
) -> List[Dict[str, Any]]:
    """
    Download documents from Elasticsearch using pagination.

    Args:
        elasticsearch_url: Elasticsearch server URL
        query_data: Query to execute
        timeout: Connection timeout in seconds

    Returns:
        List of downloaded documents

    Raises:
        ConnectionError: If unable to connect to the server
        HTTPError: If the server returns an error response
        Timeout: If the connection times out
    """
    documents: List[Dict[str, Any]] = []
    page_size = 1000  # Number of documents per page
    scroll_id = None
    scroll_timeout = "5m"  # Keep the search context alive for 5 minutes
    headers = {"Content-Type": "application/json"}

    # Initial search
    search_url = f"{elasticsearch_url.rstrip('/')}/logstash-*/_search"
    search_params: Dict[str, str] = {"scroll": scroll_timeout, "size": str(page_size)}

    try:
        search_response = requests.post(
            search_url, params=search_params, headers=headers, json=query_data, timeout=timeout
        )
        search_response.raise_for_status()  # Raise exception for 4XX/5XX responses

        # Process the first batch of results
        response = search_response.json()
        scroll_id = response.get("_scroll_id")
        hits = response.get("hits", {}).get("hits", [])
        total_docs = response.get("hits", {}).get("total", {}).get("value", 0)

        logger.info(f"Found {total_docs} documents matching the query")

        # Process the first page of results
        documents.extend(hits)
        logger.info(f"Downloaded {len(hits)} documents (page 1)")

        # Continue scrolling until all documents are retrieved
        page = 1

        while scroll_id and len(hits) > 0:
            page += 1
            try:
                # Use the scroll API directly
                scroll_url = f"{elasticsearch_url.rstrip('/')}/_search/scroll"
                scroll_data = {"scroll": scroll_timeout, "scroll_id": scroll_id}

                scroll_response = requests.post(scroll_url, headers=headers, json=scroll_data, timeout=timeout)
                scroll_response.raise_for_status()

                response = scroll_response.json()
                scroll_id = response.get("_scroll_id")
                hits = response.get("hits", {}).get("hits", [])

                if hits:
                    documents.extend(hits)
                    logger.info(f"Downloaded {len(hits)} documents (page {page})")

                    # Add a small delay to avoid overwhelming the Elasticsearch server
                    time.sleep(0.1)
            except (RequestsConnectionError, HTTPError, Timeout) as e:
                logger.error(f"Error during scroll operation on page {page}: {str(e)}")
                # Continue with documents retrieved so far
                break

    except (RequestsConnectionError, HTTPError, Timeout) as e:
        logger.error(f"Error during initial search: {str(e)}")
        raise
    finally:
        # Clear the scroll context to free up resources
        if scroll_id:
            try:
                clear_scroll_url = f"{elasticsearch_url.rstrip('/')}/_search/scroll"
                clear_scroll_data = {"scroll_id": [scroll_id]}

                requests.delete(clear_scroll_url, headers=headers, json=clear_scroll_data, timeout=timeout)
            except Exception as e:
                logger.warning(f"Failed to clear scroll context: {str(e)}")

    return documents


def download_logstash_documents(
    elasticsearch_url: str,
    query_file: str,
    start_date_time_file: str,
    output_file: str,
    current_date_time_file: str,
) -> None:
    """
    Download logstash documents from Elasticsearch.

    Args:
        elasticsearch_url: Elasticsearch server URL
        query_file: Path to the Lucene query file
        start_date_time_file: Path to the file containing the start date and time
        output_file: Path to store the downloaded logstash documents
        current_date_time_file: Path to store the current date and time

    Raises:
        FileNotFoundError: If any of the required files cannot be found
        RequestsConnectionError: If unable to connect to Elasticsearch
        JSONDecodeError: If the query file contains invalid JSON
        OSError: If unable to write output files
    """
    logger.info("Downloading logstash documents")
    logger.info(f"Elasticsearch URL: {elasticsearch_url}")
    logger.info(f"Query file: {query_file}")
    logger.info(f"Start date and time file: {start_date_time_file}")
    logger.info(f"Output file: {output_file}")
    logger.info(f"Current date and time file: {current_date_time_file}")

    # Load the Lucene query
    query_data = load_json(query_file)
    logger.info(f"Loaded query: {json.dumps(query_data, indent=2)}")

    # Read the start date and time
    start_date_time = _get_start_date_time(start_date_time_file)

    # Get the current date and time
    # Using timezone-aware approach to address deprecation warning
    current_date_time = datetime.datetime.now(timezone.utc).isoformat()
    logger.info(f"Current date and time: {current_date_time}")

    # Save the current date and time for the next run
    _save_current_date_time(current_date_time_file, current_date_time)

    # Connect to Elasticsearch - first check if the server is reachable
    _verify_elasticsearch_connection(elasticsearch_url)

    # Add time range to the query
    query_data = _add_time_range_to_query(query_data, start_date_time, current_date_time)
    logger.info(f"Modified query with time range: {json.dumps(query_data, indent=2)}")

    # Download documents using pagination
    documents = _download_documents_with_pagination(elasticsearch_url, query_data)

    logger.info(f"Downloaded a total of {len(documents)} documents")

    # Save the documents to the output file
    save_json(documents, output_file)
    logger.info(f"Saved documents to {output_file}")

    logger.info("Logstash documents downloaded successfully")


def main() -> None:
    """Execute the script when run directly."""
    parser = argparse.ArgumentParser(description="Download logstash documents from Elasticsearch")
    parser.add_argument("--elasticsearch-url", required=True, help="Elasticsearch server URL")
    parser.add_argument("--query-file", required=True, help="Path to the Lucene query file")
    parser.add_argument(
        "--start-date-time-file",
        required=True,
        help="Path to the file containing the start date and time",
    )
    parser.add_argument("--output-file", required=True, help="Path to store the downloaded logstash documents")
    parser.add_argument("--current-date-time-file", required=True, help="Path to store the current date and time")

    args = parser.parse_args()

    try:
        download_logstash_documents(
            args.elasticsearch_url,
            args.query_file,
            args.start_date_time_file,
            args.output_file,
            args.current_date_time_file,
        )
        sys.exit(0)
    except Exception as e:
        logger.error(f"Error downloading logstash documents: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
