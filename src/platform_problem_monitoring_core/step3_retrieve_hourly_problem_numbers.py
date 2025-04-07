#!/usr/bin/env python3
"""Retrieve number of problem logstash documents per hour."""

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


def _generate_hour_ranges(hours_back: int) -> List[Dict[str, str]]:
    """
    Generate a list of hour ranges going back from now.

    Args:
        hours_back: Number of hours to go back in time

    Returns:
        List of dictionaries containing start and end times for each hour
    """
    now = datetime.datetime.now(timezone.utc)
    ranges = []

    for i in range(hours_back - 1, -1, -1):  # Go from oldest to newest
        end_time = now - datetime.timedelta(hours=i)
        start_time = end_time - datetime.timedelta(hours=1)
        ranges.append({"start": start_time.isoformat(), "end": end_time.isoformat()})

    return ranges


def _add_time_range_to_query(query_data: Dict[str, Any], start_time: str, end_time: str) -> Dict[str, Any]:
    """
    Add time range filter to the Elasticsearch query.

    Args:
        query_data: Original query data
        start_time: Start time in ISO format
        end_time: End time in ISO format

    Returns:
        Updated query data with time range filter
    """
    # Create a deep copy to avoid modifying the original
    query_copy: Dict[str, Any] = json.loads(json.dumps(query_data))

    if "query" in query_copy:
        if "bool" in query_copy["query"]:
            if "filter" not in query_copy["query"]["bool"]:
                query_copy["query"]["bool"]["filter"] = []

            # Add time range filter
            query_copy["query"]["bool"]["filter"].append({"range": {"@timestamp": {"gte": start_time, "lt": end_time}}})
        else:
            # If there's no bool query, create one
            original_query = query_copy["query"]
            query_copy["query"] = {
                "bool": {
                    "must": [original_query],
                    "filter": [{"range": {"@timestamp": {"gte": start_time, "lt": end_time}}}],
                }
            }
    else:
        # If there's no query at all, create a simple one
        query_copy["query"] = {"bool": {"filter": [{"range": {"@timestamp": {"gte": start_time, "lt": end_time}}}]}}

    return query_copy


def _query_elasticsearch_for_hour(
    elasticsearch_url: str,
    query_data: Dict[str, Any],
    start_time: str,
    end_time: str,
    max_retries: int = 3,
    timeout: int = 30,
) -> int:
    """
    Query Elasticsearch for the number of documents in a specific hour.

    Args:
        elasticsearch_url: Elasticsearch server URL
        query_data: Query to execute
        start_time: Start time in ISO format
        end_time: End time in ISO format
        max_retries: Maximum number of connection retry attempts
        timeout: Connection timeout in seconds

    Returns:
        Number of matching documents

    Raises:
        RequestsConnectionError: If unable to connect to Elasticsearch
        HTTPError: If Elasticsearch returns an error response
        Timeout: If the connection times out
    """
    # Add time range to query
    query_with_time = _add_time_range_to_query(json.loads(json.dumps(query_data)), start_time, end_time)

    # Create the search URL
    search_url = f"{elasticsearch_url.rstrip('/')}/logstash-*/_count"
    headers = {"Content-Type": "application/json"}

    retry_count = 0
    last_error = None

    while retry_count < max_retries:
        try:
            # Execute the query
            response = requests.post(search_url, headers=headers, json=query_with_time, timeout=timeout)
            response.raise_for_status()

            # Extract the count from the response
            result = response.json()
            count: int = result.get("count", 0)
            return count

        except (RequestsConnectionError, HTTPError, Timeout) as e:
            last_error = e
            retry_count += 1
            logger.warning(f"Query attempt {retry_count} failed for range {start_time} to {end_time}: {str(e)}")

            if retry_count < max_retries:
                # Exponential backoff: 1s, 2s, 4s, etc.
                wait_time = 2 ** (retry_count - 1)
                logger.info(f"Retrying in {wait_time} seconds...")
                time.sleep(wait_time)

    # If we get here, all retries failed
    error_msg = f"Failed to query Elasticsearch after {max_retries} attempts: {str(last_error)}"
    logger.error(error_msg)
    raise RequestsConnectionError(error_msg) from last_error


def retrieve_hourly_problem_numbers(elasticsearch_url: str, query_file: str, hours_back: int, output_file: str) -> None:
    """
    Retrieve number of problem logstash documents per hour.

    Args:
        elasticsearch_url: Elasticsearch server URL
        query_file: Path to the Lucene query file
        hours_back: Number of hours to go back in time
        output_file: Path to store the hourly numbers

    Raises:
        FileNotFoundError: If the query file cannot be found
        json.JSONDecodeError: If the query file contains invalid JSON
        RequestsConnectionError: If unable to connect to Elasticsearch
        HTTPError: If Elasticsearch returns an error response
        OSError: If unable to write to the output file
    """
    logger.info("Retrieving hourly problem numbers")
    logger.info(f"Elasticsearch URL: {elasticsearch_url}")
    logger.info(f"Query file: {query_file}")
    logger.info(f"Hours back: {hours_back}")
    logger.info(f"Output file: {output_file}")

    # Load the Lucene query
    query_data = load_json(query_file)
    logger.info(f"Loaded query: {json.dumps(query_data, indent=2)}")

    # Generate hour ranges
    hour_ranges = _generate_hour_ranges(hours_back)
    logger.info(f"Generated {len(hour_ranges)} hour ranges")

    # Query Elasticsearch for each hour range
    results = []
    for hour_range in hour_ranges:
        start_time = hour_range["start"]
        end_time = hour_range["end"]

        try:
            count = _query_elasticsearch_for_hour(elasticsearch_url, query_data, start_time, end_time)
            results.append({"start_time": start_time, "end_time": end_time, "count": count})
            logger.info(f"Hour {start_time} to {end_time}: {count} documents")
        except Exception as e:
            logger.error(f"Error querying hour range {start_time} to {end_time}: {str(e)}")
            raise

    # Ensure the output directory exists
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Save results to output file
    save_json(results, output_file)
    logger.info(f"Results saved to {output_file}")


def main() -> None:
    """Execute the script when run directly."""
    parser = argparse.ArgumentParser(description="Retrieve number of problem logstash documents per hour")
    parser.add_argument("--elasticsearch-url", required=True, help="Elasticsearch server URL")
    parser.add_argument("--query-file", required=True, help="Path to the Lucene query file")
    parser.add_argument("--hours-back", type=int, default=24, help="Number of hours to go back in time")
    parser.add_argument("--output-file", required=True, help="Path to store the hourly numbers")

    args = parser.parse_args()

    try:
        retrieve_hourly_problem_numbers(args.elasticsearch_url, args.query_file, args.hours_back, args.output_file)
        sys.exit(0)
    except Exception as e:
        logger.error(f"Error retrieving hourly problem numbers: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
