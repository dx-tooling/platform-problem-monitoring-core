#!/usr/bin/env python3
"""Unit tests for step4a_check_high_priority_alerts.py."""

import json
import tempfile
from pathlib import Path
from typing import Any, Dict, List

import pytest
import responses
from requests.exceptions import RequestException

from platform_problem_monitoring_core.step4a_check_high_priority_alerts import (
    HighPriorityAlert,
    HighPriorityMessage,
    _add_message_to_query,
    _add_time_range_to_query,
    _parse_high_priority_messages,
    _query_elasticsearch_for_message_count,
    check_high_priority_alerts,
)


class TestStep4aCheckHighPriorityAlerts:
    """Tests for the check_high_priority_alerts function and related functions."""

    @pytest.fixture
    def high_priority_file_path(self) -> str:
        """Create a temporary file with high priority message definitions."""
        with tempfile.NamedTemporaryFile(mode="w+", delete=False) as temp_file:
            temp_file.write("5, Google Captcha Error\n")
            temp_file.write("10, Database connection failed\n")
            temp_file.write("0, Critical security breach\n")
            temp_file.write("# Comment line\n")
            temp_file.write("invalid line\n")
            temp_file.flush()
            return temp_file.name

    @pytest.fixture
    def query_file_path(self) -> str:
        """Create a temporary file with a base Elasticsearch query."""
        with tempfile.NamedTemporaryFile(mode="w+", delete=False) as temp_file:
            query = {
                "query": {
                    "bool": {
                        "should": [
                            {"match": {"message": "error"}},
                            {"match": {"message": "failure"}},
                        ],
                        "minimum_should_match": 1,
                    }
                }
            }
            json.dump(query, temp_file)
            temp_file.flush()
            return temp_file.name

    @pytest.fixture
    def hourly_data_file_path(self) -> str:
        """Create a temporary file with hourly data."""
        with tempfile.NamedTemporaryFile(mode="w+", delete=False) as temp_file:
            hourly_data = [
                {"start_time": "2023-01-01T00:00:00Z", "end_time": "2023-01-01T01:00:00Z", "count": 10},
                {"start_time": "2023-01-01T01:00:00Z", "end_time": "2023-01-01T02:00:00Z", "count": 15},
            ]
            json.dump(hourly_data, temp_file)
            temp_file.flush()
            return temp_file.name

    def test_parse_high_priority_messages(self, high_priority_file_path: str) -> None:
        """Test parsing high priority messages from a file."""
        # Act
        messages = _parse_high_priority_messages(high_priority_file_path)

        # Assert
        assert len(messages) == 3
        assert messages[0] == HighPriorityMessage(threshold=5, message="Google Captcha Error")
        assert messages[1] == HighPriorityMessage(threshold=10, message="Database connection failed")
        assert messages[2] == HighPriorityMessage(threshold=0, message="Critical security breach")

    def test_parse_high_priority_messages_file_not_found(self) -> None:
        """Test parsing high priority messages when file doesn't exist."""
        # Act
        messages = _parse_high_priority_messages("nonexistent_file.txt")

        # Assert
        assert len(messages) == 0

    def test_add_message_to_query(self) -> None:
        """Test adding a message search to a query."""
        # Arrange
        query = {"query": {"match_all": {}}}
        message = "test message"

        # Act
        result = _add_message_to_query(query, message)

        # Assert
        assert "query" in result
        assert "bool" in result["query"]
        assert "must" in result["query"]["bool"]
        assert {"match_phrase": {"message": message}} in result["query"]["bool"]["must"]

    def test_add_message_to_existing_bool_query(self) -> None:
        """Test adding a message search to an existing bool query."""
        # Arrange
        query = {
            "query": {
                "bool": {
                    "should": [{"match": {"field": "value"}}],
                    "must_not": [{"match": {"field": "exclude"}}],
                }
            }
        }
        message = "test message"

        # Act
        result = _add_message_to_query(query, message)

        # Assert
        assert "must" in result["query"]["bool"]
        assert {"match_phrase": {"message": message}} in result["query"]["bool"]["must"]
        # Original parts should be preserved
        assert "should" in result["query"]["bool"]
        assert "must_not" in result["query"]["bool"]

    def test_add_time_range_to_query(self) -> None:
        """Test adding a time range filter to a query."""
        # Arrange
        query = {"query": {"match_all": {}}}
        start_time = "2023-01-01T00:00:00Z"
        end_time = "2023-01-01T01:00:00Z"

        # Act
        result = _add_time_range_to_query(query, start_time, end_time)

        # Assert
        assert "query" in result
        assert "bool" in result["query"]
        assert "filter" in result["query"]["bool"]

        time_range = {"range": {"@timestamp": {"gte": start_time, "lt": end_time}}}
        assert time_range in result["query"]["bool"]["filter"]

    @responses.activate
    def test_query_elasticsearch_for_message_count(self) -> None:
        """Test querying Elasticsearch for a message count."""
        # Arrange
        elasticsearch_url = "http://localhost:9200"
        query_data = {"query": {"match_all": {}}}
        message = "test message"
        start_time = "2023-01-01T00:00:00Z"
        end_time = "2023-01-01T01:00:00Z"

        responses.add(
            responses.POST,
            f"{elasticsearch_url}/logstash-*/_count",
            json={"count": 42},
            status=200,
        )

        # Act
        count = _query_elasticsearch_for_message_count(elasticsearch_url, query_data, message, start_time, end_time)

        # Assert
        assert count == 42
        assert len(responses.calls) == 1

        # Verify the request body
        request_body = json.loads(responses.calls[0].request.body)
        assert "query" in request_body
        assert "bool" in request_body["query"]
        assert "must" in request_body["query"]["bool"]
        assert "filter" in request_body["query"]["bool"]

    @responses.activate
    def test_query_elasticsearch_error_handling(self) -> None:
        """Test error handling when querying Elasticsearch."""
        # Arrange
        elasticsearch_url = "http://localhost:9200"
        query_data = {"query": {"match_all": {}}}
        message = "test message"
        start_time = "2023-01-01T00:00:00Z"
        end_time = "2023-01-01T01:00:00Z"

        responses.add(
            responses.POST,
            f"{elasticsearch_url}/logstash-*/_count",
            body=RequestException("Connection error"),
        )

        # Act
        count = _query_elasticsearch_for_message_count(elasticsearch_url, query_data, message, start_time, end_time)

        # Assert
        assert count == 0  # Should return 0 on error

    @responses.activate
    def test_check_high_priority_alerts(
        self, high_priority_file_path: str, query_file_path: str, hourly_data_file_path: str
    ) -> None:
        """Test the complete high priority alerts check process."""
        # Arrange
        elasticsearch_url = "http://localhost:9200"
        output_file_path = tempfile.mktemp()

        # Mock Elasticsearch responses
        responses.add(
            responses.POST,
            f"{elasticsearch_url}/logstash-*/_count",
            json={"count": 10},  # Above threshold for first message
            status=200,
        )

        responses.add(
            responses.POST,
            f"{elasticsearch_url}/logstash-*/_count",
            json={"count": 5},  # Below threshold for second message
            status=200,
        )

        responses.add(
            responses.POST,
            f"{elasticsearch_url}/logstash-*/_count",
            json={"count": 5},  # Above threshold for third message (threshold is 0)
            status=200,
        )

        # Act
        check_high_priority_alerts(
            elasticsearch_url,
            query_file_path,
            high_priority_file_path,
            hourly_data_file_path,
            output_file_path,
        )

        # Assert
        # Check that the output file exists and contains the expected alerts
        with open(output_file_path, "r") as f:
            result = json.load(f)

        assert "alerts" in result
        alerts = result["alerts"]
        assert len(alerts) == 2  # Only two messages should exceed their thresholds

        # Check first alert
        assert alerts[0]["message"] == "Google Captcha Error"
        assert alerts[0]["threshold"] == 5
        assert alerts[0]["actual_count"] == 10
        assert alerts[0]["percentage_above_threshold"] == 100.0  # (10-5)/5 * 100

        # Check second alert
        assert alerts[1]["message"] == "Critical security breach"
        assert alerts[1]["threshold"] == 0
        assert alerts[1]["actual_count"] == 5
        assert alerts[1]["percentage_above_threshold"] == 100.0  # Special case for threshold=0

        # Clean up
        Path(output_file_path).unlink(missing_ok=True)

    def test_check_high_priority_alerts_no_messages(
        self, query_file_path: str, hourly_data_file_path: str
    ) -> None:
        """Test the alerts check when there are no high priority messages defined."""
        # Arrange
        elasticsearch_url = "http://localhost:9200"
        empty_file_path = tempfile.mktemp()
        output_file_path = tempfile.mktemp()

        try:
            # Create an empty high priority file
            Path(empty_file_path).touch()

            # Act
            check_high_priority_alerts(
                elasticsearch_url,
                query_file_path,
                empty_file_path,
                hourly_data_file_path,
                output_file_path,
            )

            # Assert
            with open(output_file_path, "r") as f:
                result = json.load(f)

            assert "alerts" in result
            assert len(result["alerts"]) == 0

        finally:
            # Clean up
            Path(empty_file_path).unlink(missing_ok=True)
            Path(output_file_path).unlink(missing_ok=True)

    def test_check_high_priority_alerts_empty_hourly_data(
        self, high_priority_file_path: str, query_file_path: str
    ) -> None:
        """Test the alerts check when hourly data is empty."""
        # Arrange
        elasticsearch_url = "http://localhost:9200"
        empty_hourly_data_path = tempfile.mktemp()
        output_file_path = tempfile.mktemp()

        try:
            # Create an empty hourly data file
            with open(empty_hourly_data_path, "w") as f:
                json.dump([], f)

            # Act
            check_high_priority_alerts(
                elasticsearch_url,
                query_file_path,
                high_priority_file_path,
                empty_hourly_data_path,
                output_file_path,
            )

            # Assert
            with open(output_file_path, "r") as f:
                result = json.load(f)

            assert "alerts" in result
            assert len(result["alerts"]) == 0

        finally:
            # Clean up
            Path(empty_hourly_data_path).unlink(missing_ok=True)
            Path(output_file_path).unlink(missing_ok=True)
