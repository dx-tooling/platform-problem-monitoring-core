#!/usr/bin/env python3
"""Unit tests for step6_extract_fields.py."""

import json
import tempfile
from pathlib import Path
from typing import Any, Dict, List

import pytest

from platform_problem_monitoring_core.step6_extract_fields import extract_fields


class TestStep6ExtractFields:
    """Tests for the extract_fields function."""

    @pytest.fixture
    def logstash_documents_path(self) -> str:
        """Return the path to the logstash_documents.json fixture."""
        return str(Path(__file__).parent / "fixtures" / "logstash_documents.json")

    @pytest.fixture
    def sample_logstash_data(self) -> List[Dict[str, Any]]:
        """Create a small sample of logstash data for testing."""
        return [
            {"_index": "logstash-test-index-1", "_id": "test-id-1", "_source": {"message": "Test message 1"}},
            {"_index": "logstash-test-index-2", "_id": "test-id-2", "_source": {"message": "Test message 2"}},
            {
                "_index": "logstash-test-index-3",
                "_id": "test-id-3",
                "_source": {
                    # Missing message field
                },
            },
        ]

    def test_extract_fields_with_sample_data(self, sample_logstash_data: List[Dict[str, Any]]) -> None:
        """Test extract_fields with a small sample of data."""
        # Create temporary files for input and output
        with tempfile.NamedTemporaryFile(mode="w+", delete=False) as input_file, tempfile.NamedTemporaryFile(
            mode="w+", delete=False
        ) as output_file:

            # Write sample data to input file
            json.dump(sample_logstash_data, input_file)
            input_file.flush()

            input_path = Path(input_file.name)
            output_path = Path(output_file.name)

            try:
                # Run the extract_fields function
                extract_fields(str(input_path), str(output_path))

                # Read and verify the output
                with output_path.open("r") as f:
                    lines = f.readlines()

                # Should have 2 lines (one document has no message)
                assert len(lines) == 2

                # Verify the content of each line
                extracted1 = json.loads(lines[0])
                assert extracted1["index"] == "logstash-test-index-1"
                assert extracted1["id"] == "test-id-1"
                assert extracted1["message"] == "Test message 1"

                extracted2 = json.loads(lines[1])
                assert extracted2["index"] == "logstash-test-index-2"
                assert extracted2["id"] == "test-id-2"
                assert extracted2["message"] == "Test message 2"
            finally:
                # Clean up temporary files
                input_path.unlink()
                output_path.unlink()

    def test_extract_fields_with_fixture(self, logstash_documents_path: str) -> None:
        """Test extract_fields with the logstash_documents.json fixture."""
        # Create a temporary file for output
        with tempfile.NamedTemporaryFile(mode="w+", delete=False) as output_file:
            output_path = Path(output_file.name)

            try:
                # Run the extract_fields function
                extract_fields(logstash_documents_path, str(output_path))

                # Read and verify the output
                with output_path.open("r") as f:
                    lines = f.readlines()

                # Verify we have output lines
                assert len(lines) > 0

                # Verify the structure of the first line
                first_extracted = json.loads(lines[0])
                assert "index" in first_extracted
                assert "id" in first_extracted
                assert "message" in first_extracted

                # Verify all lines are valid JSON
                for line in lines:
                    extracted = json.loads(line)
                    assert isinstance(extracted, dict)
                    assert "index" in extracted
                    assert "id" in extracted
                    assert "message" in extracted
                    assert extracted["message"]  # Message should not be empty
            finally:
                # Clean up temporary file
                output_path.unlink()

    def test_extract_fields_with_missing_file(self) -> None:
        """Test extract_fields with a non-existent input file."""
        with tempfile.NamedTemporaryFile(mode="w+", delete=False) as output_file:
            output_path = Path(output_file.name)

            try:
                # Try to run extract_fields with a non-existent input file
                with pytest.raises(FileNotFoundError):
                    extract_fields("non_existent_file.json", str(output_path))
            finally:
                # Clean up temporary file
                output_path.unlink()

    def test_extract_fields_with_invalid_json(self) -> None:
        """Test extract_fields with invalid JSON input."""
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
                # Try to run extract_fields with invalid JSON
                with pytest.raises(json.JSONDecodeError):
                    extract_fields(str(input_path), str(output_path))
            finally:
                # Clean up temporary files
                input_path.unlink()
                output_path.unlink()
