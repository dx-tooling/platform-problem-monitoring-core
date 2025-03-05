#!/usr/bin/env python3
"""Download logstash documents from Elasticsearch."""

import argparse
import datetime
import json
import sys
import time
from pathlib import Path

import requests

from platform_problem_monitoring_core.utils import load_json, logger, save_json


def _add_time_range_to_query(query_data: dict, start_date_time: str, current_date_time: str) -> dict:
    """
    Add time range filter to the Elasticsearch query.
    
    Args:
        query_data: Original query data
        start_date_time: Start date and time in ISO format
        current_date_time: Current date and time in ISO format
        
    Returns:
        Updated query data with time range filter
    """
    if "query" in query_data:
        if "bool" in query_data["query"]:
            if "filter" not in query_data["query"]["bool"]:
                query_data["query"]["bool"]["filter"] = []
            
            # Add time range filter
            query_data["query"]["bool"]["filter"].append({
                "range": {
                    "@timestamp": {
                        "gte": start_date_time,
                        "lte": current_date_time
                    }
                }
            })
        else:
            # If there's no bool query, create one
            original_query = query_data["query"]
            query_data["query"] = {
                "bool": {
                    "must": [original_query],
                    "filter": [{
                        "range": {
                            "@timestamp": {
                                "gte": start_date_time,
                                "lte": current_date_time
                            }
                        }
                    }]
                }
            }
    else:
        # If there's no query at all, create a simple one
        query_data["query"] = {
            "bool": {
                "filter": [{
                    "range": {
                        "@timestamp": {
                            "gte": start_date_time,
                            "lte": current_date_time
                        }
                    }
                }]
            }
        }
    
    return query_data


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
        start_date_time = (datetime.datetime.now(datetime.UTC) - datetime.timedelta(days=1)).isoformat()
        logger.info(f"Using default start date and time: {start_date_time}")
        return start_date_time


def _save_current_date_time(current_date_time_file: str, current_date_time: str) -> None:
    """
    Save current date and time to file for the next run.
    
    Args:
        current_date_time_file: Path to store the current date and time
        current_date_time: Current date and time in ISO format
    """
    with Path(current_date_time_file).open("w") as f:
        f.write(current_date_time)


def _verify_elasticsearch_connection(elasticsearch_url: str) -> None:
    """
    Verify Elasticsearch server is available.
    
    Args:
        elasticsearch_url: Elasticsearch server URL
        
    Raises:
        Exception: If the server is not available
    """
    # Do a simple request first to verify the server is available
    response = requests.get(elasticsearch_url)
    if response.status_code != 200:
        error_msg = f"Failed to connect to Elasticsearch: HTTP {response.status_code}"
        logger.error(error_msg)
        raise Exception(error_msg)
    
    server_info = response.json()
    es_version = server_info.get("version", {}).get("number", "unknown")
    logger.info(f"Connected to Elasticsearch version: {es_version}")


def _download_documents_with_pagination(elasticsearch_url: str, query_data: dict) -> list:
    """
    Download documents from Elasticsearch using pagination.
    
    Args:
        elasticsearch_url: Elasticsearch server URL
        query_data: Query to execute
        
    Returns:
        List of downloaded documents
    """
    documents = []
    page_size = 1000  # Number of documents per page
    scroll_id = None
    scroll_timeout = "5m"  # Keep the search context alive for 5 minutes
    headers = {"Content-Type": "application/json"}
    
    # Initial search
    search_url = f"{elasticsearch_url.rstrip('/')}/logstash-*/_search"
    search_params = {"scroll": scroll_timeout, "size": page_size}
    
    search_response = requests.post(
        search_url,
        params=search_params,
        headers=headers,
        json=query_data
    )
    
    if search_response.status_code != 200:
        error_msg = f"Search request failed: HTTP {search_response.status_code}, {search_response.text}"
        logger.error(error_msg)
        raise Exception(error_msg)
    
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
    
    try:
        while scroll_id and len(hits) > 0:
            page += 1
            # Use the scroll API directly
            scroll_url = f"{elasticsearch_url.rstrip('/')}/_search/scroll"
            scroll_data = {
                "scroll": scroll_timeout,
                "scroll_id": scroll_id
            }
            
            scroll_response = requests.post(
                scroll_url,
                headers=headers,
                json=scroll_data
            )
            
            if scroll_response.status_code != 200:
                logger.error(f"Scroll request failed: HTTP {scroll_response.status_code}, {scroll_response.text}")
                break
            
            response = scroll_response.json()
            scroll_id = response.get("_scroll_id")
            hits = response.get("hits", {}).get("hits", [])
            
            if hits:
                documents.extend(hits)
                logger.info(f"Downloaded {len(hits)} documents (page {page})")
                
                # Add a small delay to avoid overwhelming the Elasticsearch server
                time.sleep(0.1)
    finally:
        # Clear the scroll context to free up resources
        if scroll_id:
            try:
                clear_scroll_url = f"{elasticsearch_url.rstrip('/')}/_search/scroll"
                clear_scroll_data = {"scroll_id": [scroll_id]}
                
                requests.delete(
                    clear_scroll_url,
                    headers=headers,
                    json=clear_scroll_data
                )
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
    """
    logger.info("Downloading logstash documents")
    logger.info(f"Elasticsearch URL: {elasticsearch_url}")
    logger.info(f"Query file: {query_file}")
    logger.info(f"Start date and time file: {start_date_time_file}")
    logger.info(f"Output file: {output_file}")
    logger.info(f"Current date and time file: {current_date_time_file}")
    
    try:
        # Load the Lucene query
        query_data = load_json(query_file)
        logger.info(f"Loaded query: {json.dumps(query_data, indent=2)}")
        
        # Read the start date and time
        start_date_time = _get_start_date_time(start_date_time_file)
        
        # Get the current date and time
        # Using timezone-aware approach to address deprecation warning
        current_date_time = datetime.datetime.now(datetime.UTC).isoformat()
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
    
    except Exception as e:
        logger.error(f"Error downloading documents: {str(e)}")
        raise


def main() -> None:
    """Execute the script when run directly."""
    parser = argparse.ArgumentParser(description="Download logstash documents from Elasticsearch")
    parser.add_argument("--elasticsearch-url", required=True, help="Elasticsearch server URL")
    parser.add_argument("--query-file", required=True, help="Path to the Lucene query file")
    parser.add_argument("--start-date-time-file", required=True, help="Path to the file containing the start date and time")
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
