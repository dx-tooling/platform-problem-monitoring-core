#!/usr/bin/env python3
"""Check for high priority alerts that exceed defined thresholds."""

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List, NamedTuple

import requests

from platform_problem_monitoring_core.utils import ensure_dir_exists, load_json, logger, save_json


class HighPriorityMessage(NamedTuple):
    """Represents a high priority message definition."""

    threshold: int
    message: str


class HighPriorityAlert(NamedTuple):
    """Represents a high priority alert that has been triggered."""

    message: str
    threshold: int
    actual_count: int
    percentage_above_threshold: float


def _parse_high_priority_messages(file_path: str) -> List[HighPriorityMessage]:
    """
    Parse the high priority messages file.

    Args:
        file_path: Path to the high priority messages file

    Returns:
        List of HighPriorityMessage objects
    """
    if not Path(file_path).exists():
        logger.warning(f"High priority messages file not found: {file_path}")
        return []

    high_priority_messages = []
    with Path(file_path).open("r") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            try:
                threshold_str, message = line.split(",", 1)
                threshold = int(threshold_str.strip())
                message = message.strip()
                high_priority_messages.append(HighPriorityMessage(threshold=threshold, message=message))
                logger.debug(f"Parsed high priority message: threshold={threshold}, message={message}")
            except ValueError as e:
                logger.warning(f"Invalid line in high priority messages file: {line}, error: {e}")
                continue

    logger.info(f"Parsed {len(high_priority_messages)} high priority messages")
    return high_priority_messages


def _add_message_to_query(query_data: dict, message: str) -> dict:
    """
    Add message search criteria to the Elasticsearch query.

    Args:
        query_data: Original query data
        message: Message to search for

    Returns:
        Updated query data with message search
    """
    query_copy = json.loads(json.dumps(query_data))  # Deep copy

    if "query" in query_copy:
        if "bool" in query_copy["query"]:
            # Add message match to any existing bool query
            if "must" not in query_copy["query"]["bool"]:
                query_copy["query"]["bool"]["must"] = []

            query_copy["query"]["bool"]["must"].append({"match_phrase": {"message": message}})
        else:
            # If there's a query but no bool, wrap it in a bool
            original_query = query_copy["query"]
            query_copy["query"] = {
                "bool": {
                    "must": [
                        original_query,
                        {"match_phrase": {"message": message}}
                    ]
                }
            }
    else:
        # If there's no query, create a simple one
        query_copy["query"] = {
            "bool": {
                "must": [{"match_phrase": {"message": message}}]
            }
        }

    return query_copy


def _add_time_range_to_query(query_data: dict, start_time: str, end_time: str) -> dict:
    """
    Add time range filter to the Elasticsearch query.

    Args:
        query_data: Original query data
        start_time: Start time in ISO format
        end_time: End time in ISO format

    Returns:
        Updated query data with time range filter
    """
    query_copy = json.loads(json.dumps(query_data))  # Deep copy

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


def _query_elasticsearch_for_message_count(
    elasticsearch_url: str, query_data: dict, message: str, start_time: str, end_time: str
) -> int:
    """
    Query Elasticsearch for the count of a specific message in a time range.

    Args:
        elasticsearch_url: Elasticsearch server URL
        query_data: Base query data
        message: Message to search for
        start_time: Start time in ISO format
        end_time: End time in ISO format

    Returns:
        Number of matching documents
    """
    # Add message search to query
    query_with_message = _add_message_to_query(query_data, message)

    # Add time range to query
    query_with_time = _add_time_range_to_query(query_with_message, start_time, end_time)

    # Create the search URL
    search_url = f"{elasticsearch_url.rstrip('/')}/logstash-*/_count"
    headers = {"Content-Type": "application/json"}

    try:
        # Execute the query
        response = requests.post(search_url, headers=headers, json=query_with_time, timeout=30)
        response.raise_for_status()

        # Extract the count from the response
        result = response.json()
        count: int = result.get("count", 0)
        return count

    except requests.exceptions.RequestException as e:
        logger.error(f"Error querying Elasticsearch for message '{message}': {str(e)}")
        # Return 0 on error to avoid failing the entire process
        return 0


def check_high_priority_alerts(
    elasticsearch_url: str,
    query_file: str,
    high_priority_file: str,
    hourly_data_file: str,
    output_file: str,
) -> None:
    """
    Check for high priority alerts that exceed defined thresholds.

    Args:
        elasticsearch_url: Elasticsearch server URL
        query_file: Path to the base Elasticsearch query file
        high_priority_file: Path to the high priority messages file
        hourly_data_file: Path to the hourly data file (for time range)
        output_file: Path to store the high priority alerts
    """
    logger.info("Checking for high priority alerts")
    logger.info(f"Elasticsearch URL: {elasticsearch_url}")
    logger.info(f"Query file: {query_file}")
    logger.info(f"High priority file: {high_priority_file}")
    logger.info(f"Hourly data file: {hourly_data_file}")
    logger.info(f"Output file: {output_file}")

    try:
        # Load the base query
        query_data = load_json(query_file)

        # Parse high priority messages
        high_priority_messages = _parse_high_priority_messages(high_priority_file)

        if not high_priority_messages:
            logger.info("No high priority messages defined, skipping checks")
            save_json({"alerts": []}, output_file)
            return

        # Load hourly data to get the time range
        hourly_data = load_json(hourly_data_file)

        if not hourly_data:
            logger.warning("Hourly data file is empty, cannot determine time range")
            save_json({"alerts": []}, output_file)
            return

        # Get the start and end times from the hourly data
        start_time = hourly_data[0]["start_time"]
        end_time = hourly_data[-1]["end_time"]

        logger.info(f"Using time range: {start_time} to {end_time}")

        # Check each high priority message
        alerts = []
        for hp_message in high_priority_messages:
            logger.info(f"Checking high priority message: {hp_message.message} (threshold: {hp_message.threshold})")

            count = _query_elasticsearch_for_message_count(
                elasticsearch_url, query_data, hp_message.message, start_time, end_time
            )

            logger.info(f"Found {count} occurrences of message: {hp_message.message}")

            # If count exceeds threshold, add to alerts
            if count > hp_message.threshold:
                percentage_above = ((count - hp_message.threshold) / hp_message.threshold * 100) if hp_message.threshold > 0 else 100
                alert = HighPriorityAlert(
                    message=hp_message.message,
                    threshold=hp_message.threshold,
                    actual_count=count,
                    percentage_above_threshold=percentage_above
                )
                alerts.append(alert._asdict())  # Convert to dict for JSON serialization
                logger.info(f"Alert triggered: {hp_message.message} ({count} > {hp_message.threshold})")

        # Save alerts to output file
        result = {"alerts": alerts}
        save_json(result, output_file)

        logger.info(f"Found {len(alerts)} high priority alerts")
        logger.info(f"Results saved to {output_file}")

    except FileNotFoundError as e:
        logger.error(f"File not found: {str(e)}")
        raise
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Error checking high priority alerts: {str(e)}")
        raise


def main() -> None:
    """Execute the script when run directly."""
    parser = argparse.ArgumentParser(description="Check for high priority alerts that exceed defined thresholds")
    parser.add_argument("--elasticsearch-url", required=True, help="Elasticsearch server URL")
    parser.add_argument("--query-file", required=True, help="Path to the base Elasticsearch query file")
    parser.add_argument("--high-priority-file", required=True, help="Path to the high priority messages file")
    parser.add_argument("--hourly-data-file", required=True, help="Path to the hourly data file (for time range)")
    parser.add_argument("--output-file", required=True, help="Path to store the high priority alerts")

    args = parser.parse_args()

    try:
        check_high_priority_alerts(
            args.elasticsearch_url,
            args.query_file,
            args.high_priority_file,
            args.hourly_data_file,
            args.output_file,
        )
        sys.exit(0)
    except Exception as e:
        logger.error(f"Error checking high priority alerts: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
