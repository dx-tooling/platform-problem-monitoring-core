#!/usr/bin/env python3
"""Tests for the compare_normalizations function."""

import json
import tempfile
from pathlib import Path
from typing import Any, Dict

import pytest

from platform_problem_monitoring_core.step8_compare_normalizations import (
    PatternDict,
    _find_decreased_patterns,
    _find_disappeared_patterns,
    _find_increased_patterns,
    _find_new_patterns,
    compare_normalizations,
    get_count,
)


class TestStep8CompareNormalizations:
    """Test suite for the compare_normalizations module."""

    @pytest.fixture
    def current_normalization_path(self) -> str:
        """Provide the path to the current_normalization_results.json fixture."""
        return "src/tests/fixtures/current_normalization_results.json"

    @pytest.fixture
    def previous_normalization_path(self) -> str:
        """Provide the path to the previous_normalization_results.json fixture."""
        return "src/tests/fixtures/previous_normalization_results.json"

    @pytest.fixture
    def comparison_results_path(self) -> str:
        """Provide the path to the comparison_results.json fixture."""
        return "src/tests/fixtures/comparison_results.json"

    @pytest.fixture
    def sample_current_data(self) -> Dict[str, Any]:
        """Create a small sample of current normalization data for testing."""
        return {
            "patterns": [
                {
                    "cluster_id": 1,
                    "count": 10,
                    "pattern": "Error message 1",
                    "first_seen": "index1:id1",
                    "last_seen": "index1:id2",
                    "sample_log_lines": [],
                    "sample_doc_references": ["index1:id1", "index1:id2"],
                },
                {
                    "cluster_id": 2,
                    "count": 5,
                    "pattern": "Error message 2",
                    "first_seen": "index2:id1",
                    "last_seen": "index2:id2",
                    "sample_log_lines": [],
                    "sample_doc_references": ["index2:id1", "index2:id2"],
                },
                {
                    "cluster_id": 3,
                    "count": 8,
                    "pattern": "Error message 3",
                    "first_seen": "index3:id1",
                    "last_seen": "index3:id2",
                    "sample_log_lines": [],
                    "sample_doc_references": ["index3:id1", "index3:id2"],
                },
            ]
        }

    @pytest.fixture
    def sample_previous_data(self) -> Dict[str, Any]:
        """Create a small sample of previous normalization data for testing."""
        return {
            "patterns": [
                {
                    "cluster_id": 1,
                    "count": 5,
                    "pattern": "Error message 1",
                    "first_seen": "index1:id1",
                    "last_seen": "index1:id2",
                    "sample_log_lines": [],
                    "sample_doc_references": ["index1:id1", "index1:id2"],
                },
                {
                    "cluster_id": 2,
                    "count": 10,
                    "pattern": "Error message 2",
                    "first_seen": "index2:id1",
                    "last_seen": "index2:id2",
                    "sample_log_lines": [],
                    "sample_doc_references": ["index2:id1", "index2:id2"],
                },
                {
                    "cluster_id": 4,
                    "count": 3,
                    "pattern": "Error message 4",
                    "first_seen": "index4:id1",
                    "last_seen": "index4:id2",
                    "sample_log_lines": [],
                    "sample_doc_references": ["index4:id1", "index4:id2"],
                },
            ]
        }

    def test_get_count(self) -> None:
        """Test the get_count function."""
        pattern: PatternDict = {
            "cluster_id": "1",
            "count": 10,
            "pattern": "test pattern",
            "first_seen": "index:id1",
            "last_seen": "index:id2",
            "sample_log_lines": [],
            "sample_doc_references": [],
        }
        assert get_count(pattern) == 10

    def test_find_new_patterns(self, sample_current_data: Dict[str, Any], sample_previous_data: Dict[str, Any]) -> None:
        """Test the _find_new_patterns function."""
        new_patterns = _find_new_patterns(sample_current_data, sample_previous_data)

        # Should find "Error message 3" as new
        assert len(new_patterns) == 1
        assert new_patterns[0]["pattern"] == "Error message 3"
        assert new_patterns[0]["count"] == 8

    def test_find_disappeared_patterns(
        self, sample_current_data: Dict[str, Any], sample_previous_data: Dict[str, Any]
    ) -> None:
        """Test the _find_disappeared_patterns function."""
        disappeared_patterns = _find_disappeared_patterns(sample_current_data, sample_previous_data)

        # Should find "Error message 4" as disappeared
        assert len(disappeared_patterns) == 1
        assert disappeared_patterns[0]["pattern"] == "Error message 4"
        assert disappeared_patterns[0]["count"] == 3

    def test_find_increased_patterns(
        self, sample_current_data: Dict[str, Any], sample_previous_data: Dict[str, Any]
    ) -> None:
        """Test the _find_increased_patterns function."""
        increased_patterns = _find_increased_patterns(sample_current_data, sample_previous_data)

        # Should find "Error message 1" as increased (from 5 to 10)
        assert len(increased_patterns) == 1
        assert increased_patterns[0]["pattern"] == "Error message 1"
        assert increased_patterns[0]["count"] == 10

    def test_find_decreased_patterns(
        self, sample_current_data: Dict[str, Any], sample_previous_data: Dict[str, Any]
    ) -> None:
        """Test the _find_decreased_patterns function."""
        decreased_patterns = _find_decreased_patterns(sample_current_data, sample_previous_data)

        # Should find "Error message 2" as decreased (from 10 to 5)
        assert len(decreased_patterns) == 1
        assert decreased_patterns[0]["pattern"] == "Error message 2"
        assert decreased_patterns[0]["count"] == 5

    def test_compare_normalizations_with_sample_data(
        self, sample_current_data: Dict[str, Any], sample_previous_data: Dict[str, Any]
    ) -> None:
        """Test compare_normalizations with sample data."""
        # Create temporary files for input and output
        with (
            tempfile.NamedTemporaryFile(mode="w+", delete=False) as current_file,
            tempfile.NamedTemporaryFile(mode="w+", delete=False) as previous_file,
            tempfile.NamedTemporaryFile(mode="w+", delete=False) as output_file,
        ):

            # Write sample data to input files
            json.dump(sample_current_data, current_file)
            json.dump(sample_previous_data, previous_file)
            current_file.flush()
            previous_file.flush()

            current_path = Path(current_file.name)
            previous_path = Path(previous_file.name)
            output_path = Path(output_file.name)

            try:
                # Run the compare_normalizations function
                compare_normalizations(str(current_path), str(previous_path), str(output_path))

                # Read and verify the output
                with output_path.open("r") as f:
                    output_content = f.read()
                    comparison_results = json.loads(output_content)

                # Verify the structure of the output
                assert "current_patterns_count" in comparison_results
                assert "previous_patterns_count" in comparison_results
                assert "new_patterns" in comparison_results
                assert "disappeared_patterns" in comparison_results
                assert "increased_patterns" in comparison_results
                assert "decreased_patterns" in comparison_results

                # Verify the counts
                assert comparison_results["current_patterns_count"] == 3
                assert comparison_results["previous_patterns_count"] == 3

                # Verify the patterns
                assert len(comparison_results["new_patterns"]) == 1
                assert comparison_results["new_patterns"][0]["pattern"] == "Error message 3"

                assert len(comparison_results["disappeared_patterns"]) == 1
                assert comparison_results["disappeared_patterns"][0]["pattern"] == "Error message 4"

                assert len(comparison_results["increased_patterns"]) == 1
                assert comparison_results["increased_patterns"][0]["pattern"] == "Error message 1"

                assert len(comparison_results["decreased_patterns"]) == 1
                assert comparison_results["decreased_patterns"][0]["pattern"] == "Error message 2"

            finally:
                # Clean up temporary files
                Path(current_file.name).unlink(missing_ok=True)
                Path(previous_file.name).unlink(missing_ok=True)
                Path(output_file.name).unlink(missing_ok=True)

    def test_compare_normalizations_with_fixtures(
        self, current_normalization_path: str, previous_normalization_path: str
    ) -> None:
        """Test compare_normalizations with the fixture files."""
        # Create a temporary file for output
        with tempfile.NamedTemporaryFile(mode="w+", delete=False) as output_file:
            output_path = Path(output_file.name)

            try:
                # Run the compare_normalizations function with fixture files
                compare_normalizations(current_normalization_path, previous_normalization_path, str(output_path))

                # Read the output and expected results
                with output_path.open("r") as f:
                    output_content = f.read()
                    comparison_results = json.loads(output_content)

                # Verify the structure of the output
                assert "current_patterns_count" in comparison_results
                assert "previous_patterns_count" in comparison_results
                assert "new_patterns" in comparison_results
                assert "disappeared_patterns" in comparison_results
                assert "increased_patterns" in comparison_results
                assert "decreased_patterns" in comparison_results

                # Verify the output contains the expected keys and structure
                # Note: We don't check exact counts as they may vary between test runs
                # depending on the fixture data
                assert isinstance(comparison_results["current_patterns_count"], int)
                assert isinstance(comparison_results["previous_patterns_count"], int)

                # Verify the pattern lists exist
                assert isinstance(comparison_results["new_patterns"], list)
                assert isinstance(comparison_results["disappeared_patterns"], list)

                # Verify some specific patterns are found
                new_patterns_text = [p["pattern"] for p in comparison_results["new_patterns"]]
                disappeared_patterns_text = [p["pattern"] for p in comparison_results["disappeared_patterns"]]

                # Check for specific patterns in the results
                assert any("Component <*> not found" in pattern for pattern in new_patterns_text)
                assert any('Component \\"LinkedIcon\\" not found' in pattern for pattern in disappeared_patterns_text)

            finally:
                # Clean up temporary file
                Path(output_file.name).unlink(missing_ok=True)

    def test_compare_normalizations_with_missing_file(self) -> None:
        """Test compare_normalizations with a non-existent input file."""
        # Create a temporary file for output
        with tempfile.NamedTemporaryFile(mode="w+", delete=False) as output_file:
            output_path = Path(output_file.name)

            try:
                # Try to run compare_normalizations with a non-existent input file
                with pytest.raises(FileNotFoundError):
                    compare_normalizations("non_existent_file.json", "also_non_existent.json", str(output_path))
            finally:
                # Clean up temporary file
                Path(output_file.name).unlink(missing_ok=True)

    def test_compare_normalizations_with_invalid_json(self) -> None:
        """Test compare_normalizations with invalid JSON input."""
        # Create temporary files for input and output
        with (
            tempfile.NamedTemporaryFile(mode="w+", delete=False) as current_file,
            tempfile.NamedTemporaryFile(mode="w+", delete=False) as previous_file,
            tempfile.NamedTemporaryFile(mode="w+", delete=False) as output_file,
        ):

            # Write invalid JSON to input file
            current_file.write("{invalid json")
            current_file.flush()

            # Write valid JSON to previous file
            json.dump({"patterns": []}, previous_file)
            previous_file.flush()

            current_path = Path(current_file.name)
            previous_path = Path(previous_file.name)
            output_path = Path(output_file.name)

            try:
                # Try to run compare_normalizations with invalid JSON
                with pytest.raises(json.JSONDecodeError):
                    compare_normalizations(str(current_path), str(previous_path), str(output_path))
            finally:
                # Clean up temporary files
                Path(current_file.name).unlink(missing_ok=True)
                Path(previous_file.name).unlink(missing_ok=True)
                Path(output_file.name).unlink(missing_ok=True)

    def test_increased_patterns_contains_required_fields(
        self, sample_current_data: Dict[str, Any], sample_previous_data: Dict[str, Any]
    ) -> None:
        """Test that increased patterns contain all fields required by the email generation."""
        increased_patterns = _find_increased_patterns(sample_current_data, sample_previous_data)

        # There should be one increased pattern based on our test data
        assert len(increased_patterns) == 1
        pattern = increased_patterns[0]

        # The increased pattern should have proper pattern text
        assert pattern["pattern"] == "Error message 1"

        # Verify it contains all the fields required by email generation
        assert "count" in pattern, "Pattern is missing 'count' field"
        assert pattern["count"] == 10, "Pattern has incorrect current count"

        # These fields are expected by step9_generate_email_bodies.py but are missing
        assert "current_count" in pattern, "Pattern is missing 'current_count' field"
        assert pattern["current_count"] == 10, "Pattern has incorrect current count"
        assert "previous_count" in pattern, "Pattern is missing 'previous_count' field"
        assert pattern["previous_count"] == 5, "Pattern has incorrect previous count"
        assert "absolute_change" in pattern, "Pattern is missing 'absolute_change' field"
        assert pattern["absolute_change"] == 5, "Pattern has incorrect absolute change"
        assert "percent_change" in pattern, "Pattern is missing 'percent_change' field"
        assert pattern["percent_change"] == 100, "Pattern has incorrect percent change"

    def test_decreased_patterns_contains_required_fields(
        self, sample_current_data: Dict[str, Any], sample_previous_data: Dict[str, Any]
    ) -> None:
        """Test that decreased patterns contain all fields required by the email generation."""
        decreased_patterns = _find_decreased_patterns(sample_current_data, sample_previous_data)

        # There should be one decreased pattern based on our test data
        assert len(decreased_patterns) == 1
        pattern = decreased_patterns[0]

        # The decreased pattern should have proper pattern text
        assert pattern["pattern"] == "Error message 2"

        # Verify it contains all the fields required by email generation
        assert "count" in pattern, "Pattern is missing 'count' field"
        assert pattern["count"] == 5, "Pattern has incorrect current count"

        # These fields are expected by step9_generate_email_bodies.py but are missing
        assert "current_count" in pattern, "Pattern is missing 'current_count' field"
        assert pattern["current_count"] == 5, "Pattern has incorrect current count"
        assert "previous_count" in pattern, "Pattern is missing 'previous_count' field"
        assert pattern["previous_count"] == 10, "Pattern has incorrect previous count"
        assert "absolute_change" in pattern, "Pattern is missing 'absolute_change' field"
        assert pattern["absolute_change"] == 5, "Pattern has incorrect absolute change"
        assert "percent_change" in pattern, "Pattern is missing 'percent_change' field"
        assert pattern["percent_change"] == 50, "Pattern has incorrect percent change"

    def test_no_patterns_with_zero_change(self) -> None:
        """Test that patterns with zero change are not included in increased or decreased lists."""
        # Create test data with patterns that have the same count
        current_data = {
            "patterns": [
                {"cluster_id": 1, "count": 10, "pattern": "Same count pattern", "sample_doc_references": ["index:id1"]}
            ]
        }

        previous_data = {
            "patterns": [
                {"cluster_id": 1, "count": 10, "pattern": "Same count pattern", "sample_doc_references": ["index:id1"]}
            ]
        }

        # There should be no increased patterns
        increased_patterns = _find_increased_patterns(current_data, previous_data)
        assert len(increased_patterns) == 0, "Patterns with no increase should not be in increased_patterns"

        # There should be no decreased patterns
        decreased_patterns = _find_decreased_patterns(current_data, previous_data)
        assert len(decreased_patterns) == 0, "Patterns with no decrease should not be in decreased_patterns"

    def test_zero_counts_handled_correctly(self) -> None:
        """Test that zero counts are handled correctly in comparison."""
        # Create test data with patterns that have zero count
        current_data = {
            "patterns": [
                {"cluster_id": 1, "count": 0, "pattern": "Zero count current", "sample_doc_references": ["index:id1"]},
                {"cluster_id": 2, "count": 5, "pattern": "Zero count previous", "sample_doc_references": ["index:id2"]},
            ]
        }

        previous_data = {
            "patterns": [
                {"cluster_id": 1, "count": 5, "pattern": "Zero count current", "sample_doc_references": ["index:id1"]},
                {"cluster_id": 2, "count": 0, "pattern": "Zero count previous", "sample_doc_references": ["index:id2"]},
            ]
        }

        # "Zero count current" should be in decreased patterns
        decreased_patterns = _find_decreased_patterns(current_data, previous_data)
        assert len(decreased_patterns) == 1
        assert decreased_patterns[0]["pattern"] == "Zero count current"
        assert "current_count" in decreased_patterns[0], "Pattern is missing 'current_count' field"
        assert "previous_count" in decreased_patterns[0], "Pattern is missing 'previous_count' field"
        assert "absolute_change" in decreased_patterns[0], "Pattern is missing 'absolute_change' field"
        assert "percent_change" in decreased_patterns[0], "Pattern is missing 'percent_change' field"

        # "Zero count previous" should be in increased patterns
        increased_patterns = _find_increased_patterns(current_data, previous_data)
        assert len(increased_patterns) == 1
        assert increased_patterns[0]["pattern"] == "Zero count previous"
        assert "current_count" in increased_patterns[0], "Pattern is missing 'current_count' field"
        assert "previous_count" in increased_patterns[0], "Pattern is missing 'previous_count' field"
        assert "absolute_change" in increased_patterns[0], "Pattern is missing 'absolute_change' field"
        assert "percent_change" in increased_patterns[0], "Pattern is missing 'percent_change' field"
