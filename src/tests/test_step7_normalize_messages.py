#!/usr/bin/env python3
"""Unit tests for step7_normalize_messages.py."""

import json
import tempfile
from pathlib import Path
from typing import Any, Dict, List

import pytest

from platform_problem_monitoring_core.step7_normalize_messages import normalize_messages


class TestStep7NormalizeMessages:
    """Tests for the normalize_messages function."""

    @pytest.fixture
    def sample_extracted_data(self) -> List[Dict[str, Any]]:
        """Provide sample extracted data for testing."""
        return [
            {
                "id": "test-id-1",
                "index": "logstash-test-index-1",
                "message": (
                    "Error occurred at 2025-03-05T10:57:14.135052+00:00 in file "
                    "/opt/website/prod/backend-app/src/App/Controller.php"
                ),
            },
            {
                "id": "test-id-2",
                "index": "logstash-test-index-2",
                "message": "User 133d8fdf-5a47-11eb-9edb-0685f7490bd8 logged in from IP 10.0.11.128",
            },
            {
                "id": "test-id-3",
                "index": "logstash-test-index-3",
                "message": 'Request from session_id="cpnfegs3qjho575ua7dk1o533o" failed with status code 400',
            },
        ]

    @pytest.fixture
    def extracted_fields_path(self) -> str:
        """Provide the path to the extracted_fields.jsonl fixture."""
        return "src/tests/fixtures/extracted_fields.jsonl"

    def test_normalize_messages_with_sample_data(self, sample_extracted_data: List[Dict[str, Any]]) -> None:
        """Test normalize_messages with a small sample of data."""
        # Create temporary files for input and output
        with tempfile.NamedTemporaryFile(mode="w+", delete=False) as input_file, tempfile.NamedTemporaryFile(
            mode="w+", delete=False
        ) as output_file:

            # Write sample data to input file (one JSON object per line)
            for doc in sample_extracted_data:
                input_file.write(json.dumps(doc) + "\n")
            input_file.flush()

            input_path = Path(input_file.name)
            output_path = Path(output_file.name)

            try:
                # Run the normalize_messages function
                normalize_messages(str(input_path), str(output_path))

                # Read and verify the output
                with output_path.open("r") as f:
                    output_content = f.read()
                    normalized_data = json.loads(output_content)

                # Verify the structure of the output
                assert "patterns" in normalized_data
                assert isinstance(normalized_data["patterns"], list)

                # Should have patterns for our sample data
                assert len(normalized_data["patterns"]) > 0

                # Check that each pattern has the expected fields
                for pattern in normalized_data["patterns"]:
                    assert "cluster_id" in pattern
                    assert "count" in pattern
                    assert "pattern" in pattern
                    assert "sample_doc_references" in pattern

                # Check for masking in patterns
                patterns_text = " ".join([p["pattern"] for p in normalized_data["patterns"]])
                # Check that sensitive information is masked
                assert "2025-03-05T10:57:14.135052+00:00" not in patterns_text
                assert "TIMESTAMP" in patterns_text or "timestamp" in patterns_text.lower()
                assert "133d8fdf-5a47-11eb-9edb-0685f7490bd8" not in patterns_text
                assert "UUID" in patterns_text or "uuid" in patterns_text.lower()
                assert "10.0.11.128" not in patterns_text
                assert "IP" in patterns_text or "ip" in patterns_text.lower()

            finally:
                # Clean up temporary files
                Path(input_file.name).unlink(missing_ok=True)
                Path(output_file.name).unlink(missing_ok=True)

    def test_normalize_messages_with_fixture(self, extracted_fields_path: str) -> None:
        """Test normalize_messages with the extracted_fields.jsonl fixture."""
        # Create a temporary file for output
        with tempfile.NamedTemporaryFile(mode="w+", delete=False) as output_file:
            output_path = Path(output_file.name)

            try:
                # Run the normalize_messages function
                normalize_messages(extracted_fields_path, str(output_path))

                # Read and verify the output
                with output_path.open("r") as f:
                    output_content = f.read()
                    normalized_data = json.loads(output_content)

                # Verify the structure of the output
                assert "patterns" in normalized_data
                assert isinstance(normalized_data["patterns"], list)
                assert len(normalized_data["patterns"]) > 0

                # Check that each pattern has the expected fields
                for pattern in normalized_data["patterns"]:
                    assert "cluster_id" in pattern
                    assert "count" in pattern
                    assert "pattern" in pattern
                    assert "sample_doc_references" in pattern

                # Verify that at least some patterns have multiple occurrences
                assert any(pattern["count"] > 1 for pattern in normalized_data["patterns"])

            finally:
                # Clean up temporary file
                Path(output_file.name).unlink(missing_ok=True)

    def test_normalize_messages_with_missing_file(self) -> None:
        """Test normalize_messages with a non-existent input file."""
        # Create a temporary file for output
        with tempfile.NamedTemporaryFile(mode="w+", delete=False) as output_file:
            output_path = Path(output_file.name)

            try:
                # Try to run normalize_messages with a non-existent input file
                with pytest.raises(FileNotFoundError):
                    normalize_messages("non_existent_file.jsonl", str(output_path))
            finally:
                # Clean up temporary file
                Path(output_file.name).unlink(missing_ok=True)

    def test_normalize_messages_with_invalid_json(self) -> None:
        """Test normalize_messages with invalid JSON input."""
        # Create temporary files for input and output
        with tempfile.NamedTemporaryFile(mode="w+", delete=False) as input_file, tempfile.NamedTemporaryFile(
            mode="w+", delete=False
        ) as output_file:

            # Write invalid JSON to input file
            input_file.write("{invalid json")
            input_file.flush()

            input_path = Path(input_file.name)
            output_path = Path(output_file.name)

            try:
                # The function logs a warning but doesn't raise an exception for invalid JSON
                normalize_messages(str(input_path), str(output_path))

                # Verify that the output file exists and contains valid JSON
                with output_path.open("r") as f:
                    output_content = f.read()
                    normalized_data = json.loads(output_content)

                # Should have an empty patterns list since no valid input was processed
                assert "patterns" in normalized_data
                assert isinstance(normalized_data["patterns"], list)
                assert len(normalized_data["patterns"]) == 0

            finally:
                # Clean up temporary files
                Path(input_file.name).unlink(missing_ok=True)
                Path(output_file.name).unlink(missing_ok=True)
