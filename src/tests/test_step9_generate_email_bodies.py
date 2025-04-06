"""Tests for the step9_generate_email_bodies module."""

import re
import tempfile
from pathlib import Path
from typing import Any, Dict
import json

import pytest

from platform_problem_monitoring_core.step9_generate_email_bodies import (
    _create_enhanced_kibana_url,
    _extract_lucene_query,
    _extract_must_not_clauses,
    _extract_should_clauses,
    _generate_html_content,
    _generate_text_content,
    _parse_start_date_time,
    _prepare_email_data,
    _process_bool_clause,
    _process_bool_query,
    _process_exists_query,
    _process_match_query,
    _process_query_node,
    _process_query_string,
    _process_range_query,
    _process_term_query,
    _process_terms_query,
    _process_wildcard_query,
    elasticsearch_query_to_lucene,
    find_template_file,
    generate_decreased_pattern_list_html,
    generate_decreased_pattern_list_text,
    generate_email_bodies,
    generate_increased_pattern_list_html,
    generate_increased_pattern_list_text,
    generate_pattern_list_html,
    generate_pattern_list_text,
    generate_sample_links_html,
    get_count,
    json_to_kibana_url_params,
    load_html_template,
)


class TestStep9GenerateEmailBodies:
    """Test suite for the generate_email_bodies module."""

    @pytest.fixture
    def comparison_results_path(self) -> str:
        """Return the path to the comparison_results.json fixture."""
        return str(Path(__file__).parent / "fixtures" / "comparison_results.json")

    @pytest.fixture
    def current_normalization_path(self) -> str:
        """Return the path to the current_normalization_results.json fixture."""
        return str(Path(__file__).parent / "fixtures" / "current_normalization_results.json")

    @pytest.fixture
    def elasticsearch_query_path(self) -> str:
        """Return the path to the lucene_query.json fixture."""
        return str(Path(__file__).parent / "fixtures" / "lucene_query.json")

    @pytest.fixture
    def start_date_time_path(self) -> str:
        """Return the path to the current_date_time.txt fixture."""
        return str(Path(__file__).parent / "fixtures" / "current_date_time.txt")

    @pytest.fixture
    def high_priority_alerts_path(self) -> str:
        """Create a temporary file with high priority alerts data."""
        with tempfile.NamedTemporaryFile(mode="w+", delete=False) as tmp:
            alerts_data = {
                "alerts": [
                    {
                        "message": "Disk full on database server",
                        "threshold": 5,
                        "actual_count": 10,
                        "percentage_above_threshold": 100.0
                    },
                    {
                        "message": "Critical security breach",
                        "threshold": 0,
                        "actual_count": 5,
                        "percentage_above_threshold": 100.0
                    }
                ]
            }
            json.dump(alerts_data, tmp)
            tmp.flush()
            return tmp.name

    @pytest.fixture
    def sample_pattern(self) -> Dict[str, Any]:
        """Return a sample pattern for testing."""
        return {
            "cluster_id": 1,
            "count": 10,
            "pattern": "Error in application: Connection refused",
            "first_seen": "logstash-errors-2025.03.05:abc123",
            "last_seen": "logstash-errors-2025.03.05:xyz789",
            "sample_log_lines": [],
            "sample_doc_references": [
                "logstash-errors-2025.03.05:abc123",
                "logstash-errors-2025.03.05:def456",
                "logstash-errors-2025.03.05:xyz789",
            ],
        }

    @pytest.fixture
    def sample_increased_pattern(self) -> Dict[str, Any]:
        """Return a sample increased pattern for testing."""
        return {
            "cluster_id": 2,
            "current_count": 20,
            "previous_count": 10,
            "absolute_change": 10,
            "percent_change": 100,
            "pattern": "Database connection timeout",
            "first_seen": "logstash-errors-2025.03.05:db123",
            "last_seen": "logstash-errors-2025.03.05:db789",
            "sample_log_lines": [],
            "sample_doc_references": [
                "logstash-errors-2025.03.05:db123",
                "logstash-errors-2025.03.05:db456",
                "logstash-errors-2025.03.05:db789",
            ],
        }

    @pytest.fixture
    def sample_decreased_pattern(self) -> Dict[str, Any]:
        """Return a sample decreased pattern for testing."""
        return {
            "cluster_id": 3,
            "current_count": 5,
            "previous_count": 15,
            "absolute_change": 10,
            "percent_change": 67,
            "pattern": "Memory allocation failed",
            "first_seen": "logstash-errors-2025.03.05:mem123",
            "last_seen": "logstash-errors-2025.03.05:mem789",
            "sample_log_lines": [],
            "sample_doc_references": [
                "logstash-errors-2025.03.05:mem123",
                "logstash-errors-2025.03.05:mem456",
                "logstash-errors-2025.03.05:mem789",
            ],
        }

    @pytest.fixture
    def sample_comparison_data(self) -> Dict[str, Any]:
        """Return sample comparison data for testing."""
        return {
            "current_patterns_count": 23,
            "previous_patterns_count": 32,
            "new_patterns": [self.sample_pattern()],
            "disappeared_patterns": [self.sample_pattern()],
            "increased_patterns": [self.sample_increased_pattern()],
            "decreased_patterns": [self.sample_decreased_pattern()],
        }

    def test_json_to_kibana_url_params(self) -> None:
        """Test json_to_kibana_url_params function."""
        json_obj = {"query": {"match": {"field": "value"}}}
        result = json_to_kibana_url_params(json_obj)
        assert isinstance(result, str)
        assert "(query:" in result
        assert "match:" in result
        assert "field:" in result
        assert "value" in result

    def test_elasticsearch_query_to_lucene(self) -> None:
        """Test elasticsearch_query_to_lucene function."""
        # Test with a simple query
        query_data = {"query": {"match": {"message": {"query": "error"}}}}
        result = elasticsearch_query_to_lucene(query_data)
        assert isinstance(result, str)
        assert "message" in result
        assert "error" in result

    def test_process_query_node(self) -> None:
        """Test _process_query_node function."""
        # Test with a match query
        node = {"match": {"message": {"query": "error"}}}
        result = _process_query_node(node)
        assert "message" in result
        assert "error" in result

    def test_process_query_string(self) -> None:
        """Test _process_query_string function."""
        query_string = {"query": "error OR warning", "default_field": "message"}
        result = _process_query_string(query_string)
        assert result == "error OR warning"

    def test_process_bool_query(self) -> None:
        """Test _process_bool_query function."""
        bool_query = {
            "must": [{"match": {"message": {"query": "error"}}}],
            "must_not": [{"match": {"level": {"query": "debug"}}}],
            "should": [{"match": {"source": {"query": "app1"}}}, {"match": {"source": {"query": "app2"}}}],
        }
        result = _process_bool_query(bool_query)
        assert "AND" in result
        assert "NOT" in result
        assert "OR" in result
        assert "message" in result
        assert "level" in result
        assert "source" in result
        assert "error" in result
        assert "debug" in result
        assert "app1" in result
        assert "app2" in result

    def test_process_bool_clause(self) -> None:
        """Test _process_bool_clause function."""
        clauses = [{"match": {"field1": {"query": "value1"}}}, {"match": {"field2": {"query": "value2"}}}]
        result = _process_bool_clause(clauses, "OR")
        assert "OR" in result
        assert "field1" in result
        assert "field2" in result
        assert "value1" in result
        assert "value2" in result

    def test_process_term_query(self) -> None:
        """Test _process_term_query function."""
        # Create a dictionary with the same structure as the actual implementation expects
        term_query = {"field": {"value": "value"}}
        result = _process_term_query(term_query)
        assert result == 'field:"value"'

    def test_process_terms_query(self) -> None:
        """Test _process_terms_query function."""
        terms_query = {"field": ["value1", "value2", "value3"]}
        result = _process_terms_query(terms_query)
        assert result == '(field:"value1" OR field:"value2" OR field:"value3")'

    def test_process_match_query(self) -> None:
        """Test _process_match_query function."""
        # Create a dictionary with the same structure as the actual implementation expects
        modified_match_query = {"field": {"query": "value"}}

        # Test with a string value
        result = _process_match_query(modified_match_query)
        assert result == 'field:"value"'

    def test_process_range_query(self) -> None:
        """Test _process_range_query function."""
        range_query = {"timestamp": {"gte": "2023-01-01", "lt": "2023-01-02"}}
        result = _process_range_query(range_query)
        assert result == "(timestamp:>=2023-01-01 AND timestamp:<2023-01-02)"

    def test_process_wildcard_query(self) -> None:
        """Test _process_wildcard_query function."""
        # Create a dictionary with the same structure as the actual implementation expects
        wildcard_query = {"field": {"value": "val*"}}
        result = _process_wildcard_query(wildcard_query)
        assert "field" in result
        assert "val*" in result

    def test_process_exists_query(self) -> None:
        """Test _process_exists_query function."""
        exists_query = {"field": "field_name"}
        result = _process_exists_query(exists_query)
        assert result == "_exists_:field_name"

    def test_find_template_file(self) -> None:
        """Test find_template_file function."""
        template_path = find_template_file()
        assert template_path is not None
        assert Path(template_path).exists()
        assert template_path.endswith("html_email_template.html")

    def test_load_html_template(self) -> None:
        """Test load_html_template function."""
        templates = load_html_template()
        assert isinstance(templates, dict)
        assert "document-template" in templates
        assert "pattern-item-template" in templates
        assert "new-pattern-item-template" in templates
        assert "disappeared-pattern-item-template" in templates
        assert "increased-pattern-item-template" in templates
        assert "decreased-pattern-item-template" in templates
        assert "sample-links-template" in templates
        assert "sample-link-item-template" in templates

    def test_generate_sample_links_html(self, sample_pattern: Dict[str, Any]) -> None:
        """Test generate_sample_links_html function."""
        kibana_url = "https://kibana.example.com"
        result = generate_sample_links_html(sample_pattern, kibana_url)
        assert '<div class="sample-links">' in result
        assert "Sample 1" in result
        assert "Sample 2" in result
        assert "Sample 3" in result

        # Use a more secure pattern matching approach
        href_pattern = re.compile(r'href=["\'](https://kibana\.example\.com[^"\']*)["\']')
        assert href_pattern.search(result) is not None, "URL not found in proper href attribute context"

    def test_generate_pattern_list_html(self, sample_pattern: Dict[str, Any]) -> None:
        """Test generate_pattern_list_html function."""
        kibana_url = "https://kibana.example.com"
        patterns = [sample_pattern]
        html, dark_html = generate_pattern_list_html(patterns, kibana_url)

        # Check light mode HTML
        assert '<div class="pattern-item">' in html
        assert sample_pattern["pattern"] in html
        assert str(sample_pattern["count"]) in html
        assert "Sample 1" in html

        # More secure URL check in sample links
        if kibana_url:
            href_pattern = re.compile(r'href=["\'](https://kibana\.example\.com[^"\']*)["\']')
            assert href_pattern.search(html) is not None, "URL not found in proper href attribute context"

        # Check dark mode HTML
        assert '<div class="pattern-item">' in dark_html
        assert sample_pattern["pattern"] in dark_html
        assert str(sample_pattern["count"]) in dark_html
        assert "Sample 1" in dark_html

    def test_generate_increased_pattern_list_html(self, sample_increased_pattern: Dict[str, Any]) -> None:
        """Test generate_increased_pattern_list_html function."""
        kibana_url = "https://kibana.example.com"
        patterns = [sample_increased_pattern]
        html, dark_html = generate_increased_pattern_list_html(patterns, kibana_url)

        # Check light mode HTML
        assert '<div class="pattern-item increased-pattern">' in html
        assert sample_increased_pattern["pattern"] in html
        assert str(sample_increased_pattern["current_count"]) in html
        assert str(sample_increased_pattern["absolute_change"]) in html
        assert str(sample_increased_pattern["percent_change"]) in html

        # Check dark mode HTML
        assert '<div class="pattern-item increased-pattern">' in dark_html
        assert sample_increased_pattern["pattern"] in dark_html
        assert str(sample_increased_pattern["current_count"]) in dark_html
        assert str(sample_increased_pattern["absolute_change"]) in dark_html
        assert str(sample_increased_pattern["percent_change"]) in dark_html

    def test_generate_decreased_pattern_list_html(self, sample_decreased_pattern: Dict[str, Any]) -> None:
        """Test generate_decreased_pattern_list_html function."""
        kibana_url = "https://kibana.example.com"
        patterns = [sample_decreased_pattern]
        html, dark_html = generate_decreased_pattern_list_html(patterns, kibana_url)

        # Check light mode HTML
        assert '<div class="pattern-item decreased-pattern">' in html
        assert sample_decreased_pattern["pattern"] in html
        assert str(sample_decreased_pattern["current_count"]) in html
        assert str(sample_decreased_pattern["absolute_change"]) in html
        assert "-66.7%" in html  # Check for formatted percentage

    def test_generate_pattern_list_text(self, sample_pattern: Dict[str, Any]) -> None:
        """Test generate_pattern_list_text function."""
        patterns = [sample_pattern]
        text = generate_pattern_list_text(patterns)
        assert "1. " in text
        assert str(sample_pattern["count"]) in text
        assert sample_pattern["pattern"] in text

    def test_generate_increased_pattern_list_text(self, sample_increased_pattern: Dict[str, Any]) -> None:
        """Test generate_increased_pattern_list_text function."""
        patterns = [sample_increased_pattern]
        text = generate_increased_pattern_list_text(patterns)
        assert "1. " in text
        assert str(sample_increased_pattern["current_count"]) in text
        assert str(sample_increased_pattern["previous_count"]) in text
        assert str(sample_increased_pattern["absolute_change"]) in text
        assert str(sample_increased_pattern["percent_change"]) in text
        assert sample_increased_pattern["pattern"] in text

    def test_generate_decreased_pattern_list_text(self, sample_decreased_pattern: Dict[str, Any]) -> None:
        """Test generate_decreased_pattern_list_text function."""
        patterns = [sample_decreased_pattern]
        text = generate_decreased_pattern_list_text(patterns)
        assert "1. " in text
        assert str(sample_decreased_pattern["current_count"]) in text
        assert "-67.0%" in text  # Check for formatted percentage
        assert str(sample_decreased_pattern["absolute_change"]) in text

    def test_get_count(self, sample_pattern: Dict[str, Any]) -> None:
        """Test get_count function."""
        count = get_count(sample_pattern)
        assert count == sample_pattern["count"]

    def test_parse_start_date_time(self, start_date_time_path: str) -> None:
        """Test _parse_start_date_time function."""
        start_date_time = _parse_start_date_time(start_date_time_path)
        assert start_date_time is not None
        assert "2025-03-05" in start_date_time

    def test_extract_lucene_query(self, elasticsearch_query_path: str) -> None:
        """Test _extract_lucene_query function."""
        lucene_query = _extract_lucene_query(elasticsearch_query_path)
        assert lucene_query is not None
        assert "message" in lucene_query
        assert "error" in lucene_query
        assert "failure" in lucene_query
        assert "critical" in lucene_query
        assert "alert" in lucene_query
        assert "exception" in lucene_query

    def test_extract_should_clauses(self) -> None:
        """Test _extract_should_clauses function."""
        query_data = {
            "query": {
                "bool": {
                    "should": [
                        {"match": {"field1": "value1"}},
                        {"match": {"field2": "value2"}},
                    ]
                }
            }
        }
        result = _extract_should_clauses(query_data)
        assert "field1" in result
        assert "field2" in result
        assert "value1" in result
        assert "value2" in result
        assert "OR" in result

    def test_extract_must_not_clauses(self) -> None:
        """Test _extract_must_not_clauses function."""
        query_data = {
            "query": {
                "bool": {
                    "must_not": [
                        {"match": {"field1": "value1"}},
                        {"match": {"field2": "value2"}},
                    ]
                }
            }
        }
        result = _extract_must_not_clauses(query_data)
        assert "NOT" in result
        assert "field1" in result
        assert "field2" in result
        assert "value1" in result
        assert "value2" in result
        assert "AND" in result

    def test_create_enhanced_kibana_url(self, elasticsearch_query_path: str, start_date_time_path: str) -> None:
        """Test _create_enhanced_kibana_url function."""
        kibana_url = "https://kibana.example.com"
        enhanced_url = _create_enhanced_kibana_url(kibana_url, elasticsearch_query_path, start_date_time_path)
        assert enhanced_url.startswith(kibana_url)
        assert "message" in enhanced_url
        assert "error" in enhanced_url
        assert "2025-03-05" in enhanced_url

    def test_prepare_email_data(self, comparison_results_path: str, current_normalization_path: str) -> None:
        """Test _prepare_email_data function."""
        data = _prepare_email_data(comparison_results_path, current_normalization_path)
        assert "current_patterns_count" in data
        assert "current_patterns" in data
        assert "new_patterns" in data
        assert "disappeared_patterns" in data
        assert "increased_patterns" in data
        assert "decreased_patterns" in data
        assert len(data["current_patterns"]) > 0

    def test_generate_html_content(self, sample_pattern: Dict[str, Any]) -> None:
        """Test generate_html_content function."""
        # Create a data dictionary directly
        data = {
            "timestamp": "2025-03-05 20:45:36 UTC",
            "current_patterns_count": 10,
            "previous_patterns_count": 15,
            "new_patterns": [sample_pattern],
            "disappeared_patterns": [],
            "increased_patterns": [],
            "decreased_patterns": [],
            "top_patterns": [sample_pattern],
        }

        # Load the HTML template
        templates = load_html_template()
        kibana_url = "https://kibana.example.com"

        html_content = _generate_html_content(data, templates, kibana_url)

        assert "Platform Problem Monitoring Report" in html_content
        assert "new problem patterns" in html_content
        assert sample_pattern["pattern"] in html_content

    def test_generate_text_content(self, sample_pattern: Dict[str, Any]) -> None:
        """Test generate_text_content function."""
        # Create a data dictionary directly
        data = {
            "timestamp": "2025-03-05 20:45:36 UTC",
            "current_patterns_count": 10,
            "previous_patterns_count": 15,
            "new_patterns": [sample_pattern],
            "disappeared_patterns": [],
            "increased_patterns": [],
            "decreased_patterns": [],
            "top_patterns": [sample_pattern],
        }

        text_content = _generate_text_content(data)

        assert "PLATFORM PROBLEM MONITORING REPORT" in text_content
        assert "NEW PROBLEM PATTERNS" in text_content
        assert sample_pattern["pattern"] in text_content

    def test_generate_email_bodies_with_return_values(
        self,
        comparison_results_path: str,
        current_normalization_path: str,
        elasticsearch_query_path: str,
        start_date_time_path: str,
    ) -> None:
        """Test generate_email_bodies function with return values."""
        with tempfile.TemporaryDirectory() as temp_dir:
            html_output = Path(temp_dir) / "email.html"
            text_output = Path(temp_dir) / "email.txt"
            kibana_url = "https://kibana.example.com"

            # Call the function
            generate_email_bodies(
                comparison_results_path,
                current_normalization_path,
                str(html_output),
                str(text_output),
                None,  # high_priority_alerts_file
                None,  # trend_chart_file
                24,    # trend_hours_back
                kibana_url,  # kibana_url
                None,  # kibana_deeplink_structure
                elasticsearch_query_path,
                start_date_time_path,
            )

            # Check that the files were created
            assert Path(html_output).exists()
            assert Path(text_output).exists()

    def test_generate_email_bodies_with_missing_files(self) -> None:
        """Test generate_email_bodies function with missing files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            html_output = Path(temp_dir) / "email.html"
            text_output = Path(temp_dir) / "email.txt"

            # Test with non-existent comparison file
            with pytest.raises(FileNotFoundError):
                generate_email_bodies(
                    "non_existent_file.json",
                    "non_existent_file.json",
                    str(html_output),
                    str(text_output),
                )

    def test_generate_high_priority_alerts_html(self, sample_pattern: Dict[str, Any]) -> None:
        """Test generating HTML for high priority alerts."""
        # Arrange
        alerts = [
            {
                "message": "Disk full on database server",
                "threshold": 5,
                "actual_count": 10,
                "percentage_above_threshold": 100.0
            },
            {
                "message": "Critical security breach",
                "threshold": 0,
                "actual_count": 5,
                "percentage_above_threshold": 100.0
            }
        ]

        # Act
        from platform_problem_monitoring_core.step9_generate_email_bodies import _generate_high_priority_alerts_html
        html = _generate_high_priority_alerts_html(alerts)
        html_dark = _generate_high_priority_alerts_html(alerts, dark_mode=True)

        # Assert
        assert "Disk full on database server" in html
        assert "10" in html
        assert "Threshold: 5" in html
        assert "Critical security breach" in html
        assert "5" in html
        assert "Threshold: 0" in html

        # Dark mode should contain similar content
        assert "Disk full on database server" in html_dark
        assert "10" in html_dark
        assert "Threshold: 5" in html_dark

    def test_generate_high_priority_alerts_html_empty(self) -> None:
        """Test generating HTML for empty high priority alerts."""
        # Act
        from platform_problem_monitoring_core.step9_generate_email_bodies import _generate_high_priority_alerts_html
        html = _generate_high_priority_alerts_html([])
        html_dark = _generate_high_priority_alerts_html([], dark_mode=True)

        # Assert
        assert "No high priority alerts detected" in html
        assert "No high priority alerts detected" in html_dark

    def test_generate_high_priority_alerts_text(self) -> None:
        """Test generating text for high priority alerts."""
        # Arrange
        alerts = [
            {
                "message": "Disk full on database server",
                "threshold": 5,
                "actual_count": 10,
                "percentage_above_threshold": 100.0
            }
        ]

        # Act
        from platform_problem_monitoring_core.step9_generate_email_bodies import _generate_high_priority_alerts_text
        text = _generate_high_priority_alerts_text(alerts)

        # Assert
        assert "HIGH PRIORITY ALERTS" in text
        assert "Disk full on database server" in text
        assert "Count: 10" in text
        assert "Threshold: 5" in text

    def test_generate_high_priority_alerts_text_empty(self) -> None:
        """Test generating text for empty high priority alerts."""
        # Act
        from platform_problem_monitoring_core.step9_generate_email_bodies import _generate_high_priority_alerts_text
        text = _generate_high_priority_alerts_text([])

        # Assert
        assert "No high priority alerts detected" in text

    def test_prepare_email_data_with_high_priority_alerts(
        self, comparison_results_path: str, current_normalization_path: str, high_priority_alerts_path: str
    ) -> None:
        """Test preparing email data with high priority alerts."""
        # Act
        from platform_problem_monitoring_core.step9_generate_email_bodies import _prepare_email_data
        data = _prepare_email_data(comparison_results_path, current_normalization_path, high_priority_alerts_path)

        # Assert
        assert "high_priority_alerts" in data
        assert len(data["high_priority_alerts"]) == 2
        assert data["high_priority_alerts"][0]["message"] == "Disk full on database server"
        assert data["high_priority_alerts"][1]["message"] == "Critical security breach"

    def test_generate_email_bodies_with_high_priority_alerts(
        self,
        comparison_results_path: str,
        current_normalization_path: str,
        high_priority_alerts_path: str,
    ) -> None:
        """Test generating email bodies with high priority alerts."""
        # Arrange
        html_output = tempfile.mktemp()
        text_output = tempfile.mktemp()

        try:
            # Act
            from platform_problem_monitoring_core.step9_generate_email_bodies import generate_email_bodies
            generate_email_bodies(
                comparison_results_path,
                current_normalization_path,
                html_output,
                text_output,
                high_priority_alerts_path,
            )

            # Assert
            with open(html_output, "r") as f:
                html_content = f.read()
            with open(text_output, "r") as f:
                text_content = f.read()

            # Check HTML content
            assert "HIGH PRIORITY ALERTS" in html_content
            assert "Disk full on database server" in html_content
            assert "Critical security breach" in html_content

            # Check text content
            assert "HIGH PRIORITY ALERTS" in text_content
            assert "Disk full on database server" in text_content
            assert "Critical security breach" in text_content

        finally:
            # Clean up
            Path(html_output).unlink(missing_ok=True)
            Path(text_output).unlink(missing_ok=True)
