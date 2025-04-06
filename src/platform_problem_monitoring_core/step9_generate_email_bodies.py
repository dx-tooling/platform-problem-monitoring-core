#!/usr/bin/env python3
"""Generate email bodies for platform problem monitoring reports."""

import argparse
import base64
import importlib.resources as pkg_resources
import json
import re
import sys
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import requests

from platform_problem_monitoring_core.utils import load_json, logger, save_json


def json_to_kibana_url_params(json_obj: Any) -> str:
    """
    Convert a JSON object to a Kibana-compatible URL parameter string (RISON format).

    Kibana uses a simplified format for URL parameters that's different from standard JSON.
    This function converts a Python object to this format.

    Args:
        json_obj: The Python object to convert

    Returns:
        A string in Kibana's URL parameter format (RISON)
    """
    if isinstance(json_obj, dict):
        parts = []
        for key, value in json_obj.items():
            parts.append(f"{key}:{json_to_kibana_url_params(value)}")
        return "(" + ",".join(parts) + ")"
    elif isinstance(json_obj, list):
        parts = []
        for item in json_obj:
            parts.append(json_to_kibana_url_params(item))
        return "!(" + ",".join(parts) + ")"
    elif isinstance(json_obj, bool):
        return "!t" if json_obj else "!f"
    elif isinstance(json_obj, (int, float)):
        return str(json_obj)
    elif isinstance(json_obj, str):
        # Escape special characters in strings
        escaped = json_obj.replace("'", "\\'")
        return f"'{escaped}'"
    elif json_obj is None:
        return "!n"
    else:
        return str(json_obj)


def elasticsearch_query_to_lucene(query_data: Dict[str, Any]) -> str:
    """
    Convert an Elasticsearch JSON query to Lucene query syntax.

    Args:
        query_data: Elasticsearch query in JSON format

    Returns:
        Lucene query string
    """
    # Extract the query part from the query_data structure
    if "query" in query_data:
        return _process_query_node(query_data["query"])
    return _process_query_node(query_data)


def _process_query_node(node: Any) -> str:
    """
    Process a node in the Elasticsearch query and convert it to Lucene syntax.

    Args:
        node: A node in the Elasticsearch query

    Returns:
        Lucene query string for this node
    """
    if not isinstance(node, dict):
        return str(node)

    # Define a mapping of query types to their processing functions
    query_processors = {
        "bool": lambda n: _process_bool_query(n["bool"]),
        "term": lambda n: _process_term_query(n["term"]),
        "terms": lambda n: _process_terms_query(n["terms"]),
        "match": lambda n: _process_match_query(n["match"]),
        "range": lambda n: _process_range_query(n["range"]),
        "wildcard": lambda n: _process_wildcard_query(n["wildcard"]),
        "exists": lambda n: _process_exists_query(n["exists"]),
        "query_string": lambda n: _process_query_string(n["query_string"]),
    }

    # Process the node based on its query type
    for query_type, processor in query_processors.items():
        if query_type in node:
            return processor(node)

    # If we don't recognize the query type, return an empty string
    return ""


def _process_query_string(query_string: Dict[str, Any]) -> str:
    """
    Process a query_string query and convert it to Lucene syntax.

    Args:
        query_string: The query_string part of an Elasticsearch query

    Returns:
        Lucene query string
    """
    query = query_string.get("query")
    if query is None:
        return ""
    return str(query)


def _process_bool_query(bool_query: Dict[str, Any]) -> str:
    """Process a bool query and convert it to Lucene syntax."""
    parts = []

    # Process each clause type using helper functions
    if "must" in bool_query:
        must_part = _process_bool_clause(bool_query["must"], "AND")
        if must_part:
            parts.append(f"({must_part})")

    if "should" in bool_query:
        should_part = _process_bool_clause(bool_query["should"], "OR")
        if should_part:
            parts.append(f"({should_part})")

    if "must_not" in bool_query:
        must_not_part = _process_bool_clause(bool_query["must_not"], "OR")
        if must_not_part:
            parts.append(f"(NOT ({must_not_part}))")

    return " AND ".join(parts)


def _process_bool_clause(clauses: Any, join_operator: str) -> str:
    """
    Process a boolean clause (must, should, must_not) and join the results.

    Args:
        clauses: The clauses to process (can be a list or a single clause)
        join_operator: The operator to join multiple clauses with ("AND" or "OR")

    Returns:
        A string representation of the processed clauses
    """
    if isinstance(clauses, list):
        parts = [_process_query_node(clause) for clause in clauses]
        # Remove empty parts
        parts = [part for part in parts if part]
        if parts:
            return f" {join_operator} ".join(parts)
        return ""
    else:
        return _process_query_node(clauses) or ""


def _process_term_query(term_query: Dict[str, Any]) -> str:
    """Process a term query and convert it to Lucene syntax."""
    if not term_query:
        return ""

    field = list(term_query.keys())[0]
    value = term_query[field].get("value", term_query[field])

    # Handle string values
    if isinstance(value, str):
        # Escape special characters and wrap in quotes
        value = f'"{value}"'

    return f"{field}:{value}"


def _process_terms_query(terms_query: Dict[str, Any]) -> str:
    """Process a terms query and convert it to Lucene syntax."""
    if not terms_query:
        return ""

    field = list(terms_query.keys())[0]
    values = terms_query[field]

    if not values:
        return ""

    # Format each value and join with OR
    formatted_values = []
    for value in values:
        if isinstance(value, str):
            formatted_values.append(f'{field}:"{value}"')
        else:
            formatted_values.append(f"{field}:{value}")

    return f"({' OR '.join(formatted_values)})"


def _process_match_query(match_query: Dict[str, Any]) -> str:
    """Process a match query and convert it to Lucene syntax."""
    if not match_query:
        return ""

    field = list(match_query.keys())[0]
    value = match_query[field].get("query", match_query[field])

    if isinstance(value, str):
        # Escape special characters and wrap in quotes
        value = f'"{value}"'

    return f"{field}:{value}"


def _process_range_query(range_query: Dict[str, Any]) -> str:
    """Process a range query and convert it to Lucene syntax."""
    if not range_query:
        return ""

    field = list(range_query.keys())[0]
    conditions = range_query[field]

    parts = []
    if "gt" in conditions:
        parts.append(f"{field}:>{conditions['gt']}")
    if "gte" in conditions:
        parts.append(f"{field}:>={conditions['gte']}")
    if "lt" in conditions:
        parts.append(f"{field}:<{conditions['lt']}")
    if "lte" in conditions:
        parts.append(f"{field}:<={conditions['lte']}")

    return f"({' AND '.join(parts)})"


def _process_wildcard_query(wildcard_query: Dict[str, Any]) -> str:
    """Process a wildcard query and convert it to Lucene syntax."""
    if not wildcard_query:
        return ""

    field = list(wildcard_query.keys())[0]
    value = wildcard_query[field].get("value", wildcard_query[field])

    return f"{field}:{value}"


def _process_exists_query(exists_query: Dict[str, Any]) -> str:
    """Process an exists query and convert it to Lucene syntax."""
    field = exists_query.get("field", "")
    if not field:
        return ""

    return f"_exists_:{field}"


# Define possible paths to the HTML template file
def find_template_file() -> str:
    """
    Find the HTML template file using package resources.

    Returns:
        Path to the HTML template file
    """
    try:
        # Try to find the template using package resources (works for installed packages)
        with pkg_resources.path("platform_problem_monitoring_core.resources", "html_email_template.html") as path:
            logger.info(f"Found HTML template using package resources at: {path}")
            return str(path)
    except Exception as e:
        logger.warning(f"Could not find template using package resources: {e}")

        # Fallback paths for development/source installations
        possible_paths = [
            # Path if running from source
            Path(__file__).parent / "resources" / "html_email_template.html",
            # Path relative to the current directory
            Path("src/platform_problem_monitoring_core/resources/html_email_template.html"),
        ]

        # Try each path
        for path in possible_paths:
            if path.exists():
                logger.info(f"Found HTML template at fallback path: {path}")
                return str(path)

        # If we get here, we couldn't find the template
        error_msg = (
            "Could not find HTML template file. Make sure it's installed with the package "
            "or available in one of these locations: " + ", ".join(str(p) for p in possible_paths)
        )
        logger.error(error_msg)
        raise FileNotFoundError(error_msg) from e


# Get the template file path
TEMPLATE_FILE_PATH = find_template_file()


def load_html_template() -> Dict[str, str]:
    """
    Load the HTML template file and extract the different template sections.

    Returns:
        Dictionary containing the different template sections
    """
    logger.info(f"Loading HTML template from: {TEMPLATE_FILE_PATH}")

    try:
        with Path(TEMPLATE_FILE_PATH).open("r") as f:
            template_content = f.read()

        # Extract templates using regex
        templates = {}

        # Extract CSS styles
        css_match = re.search(r"<style>(.*?)</style>", template_content, re.DOTALL)
        if css_match:
            templates["css"] = css_match.group(1)
        else:
            logger.warning("No CSS styles found in the HTML template")
            templates["css"] = ""

        # Extract all template sections
        template_matches = re.finditer(r'<template id="([^"]+)">(.*?)</template>', template_content, re.DOTALL)
        template_count = 0
        for match in template_matches:
            template_id = match.group(1)
            template_content = match.group(2)
            templates[template_id] = template_content
            template_count += 1

        if template_count == 0:
            logger.warning("No template sections found in the HTML template")
        else:
            logger.info(f"Loaded {template_count} template sections")

        # Check for required templates
        required_templates = [
            "document-template",
            "pattern-item-template",
            "increased-pattern-item-template",
            "decreased-pattern-item-template",
        ]
        missing_templates = [t for t in required_templates if t not in templates]

        if missing_templates:
            logger.warning(f"Missing required templates: {', '.join(missing_templates)}")

        return templates

    except FileNotFoundError:
        logger.error(f"HTML template file not found: {TEMPLATE_FILE_PATH}")
        raise
    except Exception as e:
        logger.error(f"Error loading HTML template: {str(e)}")
        raise


def generate_sample_links_html(
    pattern: Dict[str, Any],
    kibana_url: Optional[str] = None,
    kibana_deeplink_structure: Optional[str] = None,
    dark_mode: bool = False,
) -> str:
    """
    Generate HTML for sample document links.

    Args:
        pattern: Pattern data containing sample document references
        kibana_url: Optional Kibana base URL for deep links (used for backward compatibility)
        kibana_deeplink_structure: Optional URL structure for Kibana document links {{index}} and {{id}} placeholders
        dark_mode: Whether to use dark mode templates

    Returns:
        HTML string for the sample links
    """
    # Skip if no sample documents
    if "sample_doc_references" not in pattern or not pattern["sample_doc_references"]:
        return ""

    # Skip if no way to generate links
    if not kibana_url and not kibana_deeplink_structure:
        return ""

    templates = load_html_template()
    sample_links_template = templates.get("sample-links-template", "")
    sample_link_item_template = templates.get(
        "dark-sample-link-item-template" if dark_mode else "sample-link-item-template", ""
    )

    sample_links_list = ""

    for j, doc_ref in enumerate(pattern["sample_doc_references"][:5], 1):
        # Handle doc_ref as a string in format "index:id"
        if isinstance(doc_ref, str) and ":" in doc_ref:
            parts = doc_ref.split(":", 1)
            index = parts[0]
            doc_id = parts[1]
        else:
            # Handle as dictionary if it's not a string
            index = doc_ref.get("index", "") if isinstance(doc_ref, dict) else ""
            doc_id = doc_ref.get("id", "") if isinstance(doc_ref, dict) else ""

        if index and doc_id:
            # Truncate very long IDs for URL length safety
            if len(doc_id) > 100:
                doc_id = doc_id[:100]

            # Create a deep link to Kibana
            if kibana_deeplink_structure:
                # Use the new configurable deeplink structure
                kibana_link = kibana_deeplink_structure.replace("{{index}}", index).replace("{{id}}", doc_id)
            elif kibana_url:
                # Fall back to old style if no deeplink structure but kibana_url is provided
                kibana_link = f"{kibana_url}/app/discover#/doc/{index}/{doc_id}?_g=()"
            else:
                # No valid link can be created
                continue

            # Add the link to the list
            link_html = sample_link_item_template.replace("{{KIBANA_LINK}}", kibana_link)
            link_html = link_html.replace("{{INDEX}}", str(j))
            link_html = link_html.replace(
                "{{COMMA}}", ", " if j < min(5, len(pattern["sample_doc_references"])) else ""
            )
            sample_links_list += link_html

    if sample_links_list:
        return sample_links_template.replace("{{SAMPLE_LINKS_LIST}}", sample_links_list)
    return ""


def generate_pattern_list_html(
    patterns: List[Dict[str, Any]],
    kibana_url: Optional[str] = None,
    kibana_deeplink_structure: Optional[str] = None,
) -> Tuple[str, str]:
    """
    Generate HTML for a list of patterns.

    Args:
        patterns: List of patterns to display
        kibana_url: Optional Kibana base URL for deep links (used for backward compatibility)
        kibana_deeplink_structure: Optional URL structure for Kibana document deeplinks

    Returns:
        Tuple of (light mode HTML, dark mode HTML) for the pattern list
    """
    if not patterns:
        templates = load_html_template()
        empty_template = templates.get("empty-pattern-list-template", "")
        light_html = empty_template.replace("{{MESSAGE}}", "No patterns found.")
        return light_html, light_html

    templates = load_html_template()
    pattern_item_template = templates.get("pattern-item-template", "")

    light_html = "<div class='space-y-6'>"

    for i, pattern in enumerate(patterns, 1):
        count = pattern.get("count", 0)
        pattern_text = pattern.get("pattern", "")

        # Ensure pattern text doesn't have excessively long lines
        # This helps prevent SMTP line length issues and improves rendering
        pattern_text = _safe_html_encode(pattern_text)

        # Create a unique ID for each pattern
        pattern_id = f"pattern-{i}"

        # Generate sample links
        sample_links = generate_sample_links_html(pattern, kibana_url, kibana_deeplink_structure, dark_mode=False)

        # Replace placeholders in the template
        pattern_html = pattern_item_template.replace("{{INDEX}}", str(i))
        pattern_html = pattern_html.replace("{{COUNT}}", str(count))
        pattern_html = pattern_html.replace("{{PATTERN_ID}}", pattern_id)
        pattern_html = pattern_html.replace("{{PATTERN_TEXT}}", pattern_text)
        pattern_html = pattern_html.replace("{{SAMPLE_LINKS}}", sample_links)

        light_html += pattern_html

    light_html += "</div>"
    return light_html, light_html


def _safe_html_encode(text: str) -> str:
    """
    Safely encode text for HTML, adding word breaks for very long words.

    Args:
        text: Text to encode

    Returns:
        HTML-safe text with word breaks for long content
    """
    # Replace HTML entities
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    # Add word breaks for very long words
    words = text.split()
    for i, word in enumerate(words):
        # If a word is longer than 50 characters, add <wbr> tags every 50 chars
        if len(word) > 50:
            result = ""
            for j in range(0, len(word), 50):
                result += word[j : j + 50]
                if j + 50 < len(word):
                    result += "<wbr>"
            words[i] = result

    return " ".join(words)


def generate_increased_pattern_list_html(
    patterns: List[Dict[str, Any]],
    kibana_url: Optional[str] = None,
    kibana_deeplink_structure: Optional[str] = None,
) -> Tuple[str, str]:
    """
    Generate HTML for a list of patterns that have increased in occurrence.

    Args:
        patterns: List of patterns to display
        kibana_url: Optional Kibana base URL for deep links (used for backward compatibility)
        kibana_deeplink_structure: Optional URL structure for Kibana document deeplinks

    Returns:
        Tuple of (light mode HTML, dark mode HTML) for the pattern list
    """
    if not patterns:
        templates = load_html_template()
        empty_template = templates.get("empty-pattern-list-template", "")
        light_html = empty_template.replace("{{MESSAGE}}", "No increased patterns found.")
        return light_html, light_html

    templates = load_html_template()
    increased_pattern_item_template = templates.get("increased-pattern-item-template", "")

    light_html = "<div class='space-y-6'>"

    for i, pattern in enumerate(patterns, 1):
        current_count = pattern.get("current_count", 0)
        previous_count = pattern.get("previous_count", 0)
        pattern_text = pattern.get("pattern", "")

        # Ensure pattern text doesn't have excessively long lines
        pattern_text = _safe_html_encode(pattern_text)

        # Calculate absolute and percentage change
        absolute_change = current_count - previous_count
        percent_change = round((absolute_change / previous_count) * 100, 1) if previous_count > 0 else 0

        # Create a unique ID for each pattern
        pattern_id = f"increased-pattern-{i}"

        # Generate sample links
        sample_links = generate_sample_links_html(pattern, kibana_url, kibana_deeplink_structure, dark_mode=False)

        # Replace placeholders in the template
        pattern_html = increased_pattern_item_template.replace("{{INDEX}}", str(i))
        pattern_html = pattern_html.replace("{{CURRENT_COUNT}}", str(current_count))
        pattern_html = pattern_html.replace("{{ABSOLUTE_CHANGE}}", str(absolute_change))
        pattern_html = pattern_html.replace("{{PERCENT_CHANGE}}", str(percent_change))
        pattern_html = pattern_html.replace("{{PATTERN_ID}}", pattern_id)
        pattern_html = pattern_html.replace("{{PATTERN_TEXT}}", pattern_text)
        pattern_html = pattern_html.replace("{{SAMPLE_LINKS}}", sample_links)

        light_html += pattern_html

    light_html += "</div>"
    return light_html, light_html


def generate_decreased_pattern_list_html(
    patterns: List[Dict[str, Any]],
    kibana_url: Optional[str] = None,
    kibana_deeplink_structure: Optional[str] = None,
) -> Tuple[str, str]:
    """
    Generate HTML for a list of patterns that have decreased in occurrence.

    Args:
        patterns: List of patterns to display
        kibana_url: Optional Kibana base URL for deep links (used for backward compatibility)
        kibana_deeplink_structure: Optional URL structure for Kibana document deeplinks

    Returns:
        Tuple of (light mode HTML, dark mode HTML) for the pattern list
    """
    if not patterns:
        templates = load_html_template()
        empty_template = templates.get("empty-pattern-list-template", "")
        light_html = empty_template.replace("{{MESSAGE}}", "No decreased patterns found.")
        return light_html, light_html

    templates = load_html_template()
    decreased_pattern_item_template = templates.get("decreased-pattern-item-template", "")

    light_html = "<div class='space-y-6'>"

    for i, pattern in enumerate(patterns, 1):
        current_count = pattern.get("current_count", 0)
        previous_count = pattern.get("previous_count", 0)
        pattern_text = pattern.get("pattern", "")

        # Ensure pattern text doesn't have excessively long lines
        pattern_text = _safe_html_encode(pattern_text)

        # Calculate absolute and percentage change
        absolute_change = previous_count - current_count
        percent_change = round((absolute_change / previous_count) * 100, 1) if previous_count > 0 else 0

        # Create a unique ID for each pattern
        pattern_id = f"decreased-pattern-{i}"

        # Generate sample links
        sample_links = generate_sample_links_html(pattern, kibana_url, kibana_deeplink_structure, dark_mode=False)

        # Replace placeholders in the template
        pattern_html = decreased_pattern_item_template.replace("{{INDEX}}", str(i))
        pattern_html = pattern_html.replace("{{CURRENT_COUNT}}", str(current_count))
        pattern_html = pattern_html.replace("{{ABSOLUTE_CHANGE}}", str(absolute_change))
        pattern_html = pattern_html.replace("{{PERCENT_CHANGE}}", str(percent_change))
        pattern_html = pattern_html.replace("{{PATTERN_ID}}", pattern_id)
        pattern_html = pattern_html.replace("{{PATTERN_TEXT}}", pattern_text)
        pattern_html = pattern_html.replace("{{SAMPLE_LINKS}}", sample_links)

        light_html += pattern_html

    light_html += "</div>"
    return light_html, light_html


def generate_pattern_list_text(patterns: List[Dict[str, Any]]) -> str:
    """
    Generate plaintext for a list of patterns.

    Args:
        patterns: List of patterns to display

    Returns:
        Plaintext string for the pattern list
    """
    if not patterns:
        return "No patterns found.\n"

    text = ""

    for i, pattern in enumerate(patterns, 1):
        count = pattern.get("count", 0)
        pattern_text = pattern.get("pattern", "")

        text += f"{i}. [{count}] {pattern_text}\n"

        # Add sample document references if available
        if "sample_doc_references" in pattern and pattern["sample_doc_references"]:
            text += "   Sample documents: "
            sample_refs = []

            for j, doc_ref in enumerate(pattern["sample_doc_references"][:5], 1):
                # Handle doc_ref as a string in format "index:id"
                if isinstance(doc_ref, str) and ":" in doc_ref:
                    parts = doc_ref.split(":", 1)
                    index = parts[0]
                    doc_id = parts[1]

                    if index and doc_id:
                        sample_refs.append(f"Sample {j} ({index}/{doc_id})")
                else:
                    # Handle as dictionary if it's not a string
                    index = doc_ref.get("index", "") if isinstance(doc_ref, dict) else ""
                    doc_id = doc_ref.get("id", "") if isinstance(doc_ref, dict) else ""

                    if index and doc_id:
                        sample_refs.append(f"Sample {j} ({index}/{doc_id})")

            text += " · ".join(sample_refs) + "\n"

        text += "\n"

    return text


def generate_increased_pattern_list_text(patterns: List[Dict[str, Any]]) -> str:
    """
    Generate plaintext for a list of increased patterns.

    Args:
        patterns: List of increased patterns to display

    Returns:
        Plaintext string for the increased pattern list
    """
    if not patterns:
        return "No increased patterns found.\n"

    text = ""

    for i, pattern in enumerate(patterns, 1):
        current_count = pattern.get("current_count", 0)
        pattern_text = pattern.get("pattern", "")
        absolute_change = pattern.get("absolute_change", 0)
        percent_change = pattern.get("percent_change", 0)

        text += f"{i}. [{current_count}] (+{absolute_change}, +{percent_change:.1f}%) {pattern_text}\n"

        # Add sample document references if available
        if "sample_doc_references" in pattern and pattern["sample_doc_references"]:
            text += "   Sample documents: "
            sample_refs = []

            for j, doc_ref in enumerate(pattern["sample_doc_references"][:5], 1):
                # Handle doc_ref as a string in format "index:id"
                if isinstance(doc_ref, str) and ":" in doc_ref:
                    parts = doc_ref.split(":", 1)
                    index = parts[0]
                    doc_id = parts[1]

                    if index and doc_id:
                        sample_refs.append(f"Sample {j} ({index}/{doc_id})")
                else:
                    # Handle as dictionary if it's not a string
                    index = doc_ref.get("index", "") if isinstance(doc_ref, dict) else ""
                    doc_id = doc_ref.get("id", "") if isinstance(doc_ref, dict) else ""

                    if index and doc_id:
                        sample_refs.append(f"Sample {j} ({index}/{doc_id})")

            text += " · ".join(sample_refs) + "\n"

        text += "\n"

    return text


def generate_decreased_pattern_list_text(patterns: List[Dict[str, Any]]) -> str:
    """
    Generate plaintext for a list of decreased patterns.

    Args:
        patterns: List of decreased patterns to display

    Returns:
        Plaintext string for the decreased pattern list
    """
    if not patterns:
        return "No decreased patterns found.\n"

    text = ""

    for i, pattern in enumerate(patterns, 1):
        current_count = pattern.get("current_count", 0)
        pattern_text = pattern.get("pattern", "")
        absolute_change = pattern.get("absolute_change", 0)
        percent_change = pattern.get("percent_change", 0)

        text += f"{i}. [{current_count}] (-{absolute_change}, -{percent_change:.1f}%) {pattern_text}\n"

        # Add sample document references if available
        if "sample_doc_references" in pattern and pattern["sample_doc_references"]:
            text += "   Sample documents: "
            sample_refs = []

            for j, doc_ref in enumerate(pattern["sample_doc_references"][:5], 1):
                # Handle doc_ref as a string in format "index:id"
                if isinstance(doc_ref, str) and ":" in doc_ref:
                    parts = doc_ref.split(":", 1)
                    index = parts[0]
                    doc_id = parts[1]

                    if index and doc_id:
                        sample_refs.append(f"Sample {j} ({index}/{doc_id})")
                else:
                    # Handle as dictionary if it's not a string
                    index = doc_ref.get("index", "") if isinstance(doc_ref, dict) else ""
                    doc_id = doc_ref.get("id", "") if isinstance(doc_ref, dict) else ""

                    if index and doc_id:
                        sample_refs.append(f"Sample {j} ({index}/{doc_id})")

            text += " · ".join(sample_refs) + "\n"

        text += "\n"

    return text


# Define a function to get the count safely with a proper return type
def get_count(pattern: Dict[str, Any]) -> int:
    """Safely get the count from a pattern dictionary.

    Args:
        pattern: The pattern dictionary.

    Returns:
        The count as an integer (defaults to 0 if missing).
    """
    count = pattern.get("count", 0)
    return 0 if count is None else int(count)


def _parse_start_date_time(start_date_time_file: str) -> str:
    """
    Parse the start date time from a file and format it for Kibana.

    Args:
        start_date_time_file: Path to the file containing the start date time

    Returns:
        Formatted start date time for Kibana
    """
    with Path(start_date_time_file).open("r") as f:
        start_date_time_raw = f.read().strip()

    try:
        # Try to parse the datetime
        dt = datetime.fromisoformat(start_date_time_raw.replace("Z", "+00:00"))
        # Format it in the way Kibana expects
        return dt.strftime("%Y-%m-%dT%H:%M:%S.000Z")
    except ValueError:
        # If parsing fails, use a default format
        logger.warning(f"Could not parse start date time: {start_date_time_raw}, using default format")
        return start_date_time_raw


def _extract_lucene_query(elasticsearch_query_file: str) -> str:
    """
    Extract a Lucene query from an Elasticsearch query file.

    Args:
        elasticsearch_query_file: Path to the Elasticsearch query file

    Returns:
        Lucene query string
    """
    # Get the Lucene query directly from the file
    with Path(elasticsearch_query_file).open("r") as f:
        query_data = json.load(f)

    # Extract the query parts we need
    lucene_parts = []

    # Process should clauses (OR conditions)
    should_part = _extract_should_clauses(query_data)
    if should_part:
        lucene_parts.append(should_part)

    # Process must_not clauses (NOT conditions)
    must_not_part = _extract_must_not_clauses(query_data)
    if must_not_part:
        lucene_parts.append(must_not_part)

    # Combine all parts with AND
    lucene_query = " AND ".join(lucene_parts)
    logger.info(f"Generated Lucene query: {lucene_query}")

    return lucene_query


def _extract_should_clauses(query_data: Dict[str, Any]) -> str:
    """
    Extract 'should' clauses from an Elasticsearch query.

    Args:
        query_data: Elasticsearch query data

    Returns:
        Lucene query string for 'should' clauses
    """
    if "query" in query_data and "bool" in query_data["query"] and "should" in query_data["query"]["bool"]:
        should_clauses = query_data["query"]["bool"]["should"]
        should_parts = []

        for clause in should_clauses:
            if "match" in clause:
                for field, value in clause["match"].items():
                    should_parts.append(f'{field}:"{value}"')

        if should_parts:
            return f"({' OR '.join(should_parts)})"

    return ""


def _extract_must_not_clauses(query_data: Dict[str, Any]) -> str:
    """
    Extract 'must_not' clauses from an Elasticsearch query.

    Args:
        query_data: Elasticsearch query data

    Returns:
        Lucene query string for 'must_not' clauses
    """
    if "query" in query_data and "bool" in query_data["query"] and "must_not" in query_data["query"]["bool"]:
        must_not_clauses = query_data["query"]["bool"]["must_not"]
        must_not_parts = []

        for clause in must_not_clauses:
            if "match" in clause:
                for field, value in clause["match"].items():
                    must_not_parts.append(f'{field}:"{value}"')
            elif "term" in clause:
                for field, value in clause["term"].items():
                    must_not_parts.append(f'{field}:"{value}"')

        if must_not_parts:
            return f"(NOT {' AND NOT '.join(must_not_parts)})"

    return ""


def _create_enhanced_kibana_url(
    kibana_url: str,
    elasticsearch_query_file: str,
    start_date_time_file: str,
) -> str:
    """
    Create an enhanced Kibana URL with query and timeframe.

    Args:
        kibana_url: Base Kibana URL
        elasticsearch_query_file: Path to the Elasticsearch query file
        start_date_time_file: Path to the file containing the start date time

    Returns:
        Enhanced Kibana URL with query and timeframe
    """
    try:
        # Parse the start date time
        start_date_time = _parse_start_date_time(start_date_time_file)

        # Extract the Lucene query
        lucene_query = _extract_lucene_query(elasticsearch_query_file)

        # URL encode the Lucene query
        encoded_query = urllib.parse.quote(lucene_query)

        # Create the Kibana URL directly using the format from the working URL
        enhanced_kibana_url = (
            f"{kibana_url}#/?_g=(filters:!(),refreshInterval:(pause:!t,value:0),"
            f"time:(from:'{start_date_time}',to:now))&"
            f"_a=(columns:!(_source),filters:!(),index:'logstash-*',interval:auto,"
            f"query:(language:lucene,query:'{encoded_query}'),sort:!())"
        )

        logger.info(f"Created enhanced Kibana URL with query and timeframe: {enhanced_kibana_url}")
        return enhanced_kibana_url
    except Exception as e:
        logger.warning(f"Failed to create enhanced Kibana URL: {str(e)}")
        logger.exception(e)  # Log the full exception for debugging
        return kibana_url


def _generate_high_priority_alerts_html(
    alerts: List[Dict[str, Any]],
    dark_mode: bool = False,
) -> str:
    """
    Generate HTML for high priority alerts.

    Args:
        alerts: List of high priority alerts
        dark_mode: Whether to use dark mode styling

    Returns:
        HTML string for high priority alerts
    """
    if not alerts:
        template_name = "dark-empty-high-priority-alerts-template" if dark_mode else "empty-high-priority-alerts-template"
        template = load_html_template().get(template_name, "")
        if not template:
            return "<p>No high priority alerts detected.</p>"
        return template.replace("{{MESSAGE}}", "No high priority alerts detected.")

    template_name = "high-priority-alert-item-dark-template" if dark_mode else "high-priority-alert-item-template"
    item_template = load_html_template().get(template_name, "")
    if not item_template:
        return "<p>Error: High priority alert item template not found.</p>"

    result = []
    for idx, alert in enumerate(alerts[:10], 1):  # Limit to top 10
        item_html = item_template
        item_html = item_html.replace("{{INDEX}}", str(idx))
        item_html = item_html.replace("{{ACTUAL_COUNT}}", str(alert.get("actual_count", 0)))
        item_html = item_html.replace("{{THRESHOLD}}", str(alert.get("threshold", 0)))
        item_html = item_html.replace("{{PERCENTAGE_ABOVE}}", f"{alert.get('percentage_above_threshold', 0):.1f}")
        item_html = item_html.replace("{{MESSAGE}}", _safe_html_encode(alert.get("message", "")))
        item_html = item_html.replace("{{ALERT_ID}}", f"alert-{idx}")
        result.append(item_html)

    return "\n".join(result)


def _generate_high_priority_alerts_text(alerts: List[Dict[str, Any]]) -> str:
    """
    Generate plain text for high priority alerts.

    Args:
        alerts: List of high priority alerts

    Returns:
        Plain text string for high priority alerts
    """
    if not alerts:
        return "No high priority alerts detected."

    lines = ["HIGH PRIORITY ALERTS", "=" * 20]
    for idx, alert in enumerate(alerts[:10], 1):  # Limit to top 10
        lines.append(
            f"{idx}. {alert.get('message', '')} - Count: {alert.get('actual_count', 0)} "
            f"(Threshold: {alert.get('threshold', 0)}, +{alert.get('percentage_above_threshold', 0):.1f}%)"
        )
    lines.append("")  # Empty line at the end
    return "\n".join(lines)


def _prepare_email_data(comparison_file: str, norm_results_file: str, high_priority_alerts_file: str = None) -> Dict[str, Any]:
    """
    Prepare data for the email body.

    Args:
        comparison_file: Path to the comparison file
        norm_results_file: Path to the normalized results file
        high_priority_alerts_file: Path to the high priority alerts file

    Returns:
        Dictionary with data for the email body
    """
    # Load the comparison data
    comparison_data = load_json(comparison_file)

    # Load the normalized results
    norm_results = load_json(norm_results_file)

    # High priority alerts
    high_priority_alerts = []
    if high_priority_alerts_file and Path(high_priority_alerts_file).exists():
        try:
            high_priority_data = load_json(high_priority_alerts_file)
            high_priority_alerts = sorted(
                high_priority_data.get("alerts", []),
                key=lambda x: x.get("percentage_above_threshold", 0),
                reverse=True
            )
        except Exception as e:
            logger.warning(f"Error loading high priority alerts: {e}")

    # Extract the relevant data
    new_patterns = comparison_data.get("new_patterns", [])
    disappeared_patterns = comparison_data.get("disappeared_patterns", [])
    increased_patterns = comparison_data.get("increased_patterns", [])
    decreased_patterns = comparison_data.get("decreased_patterns", [])

    # Sort the current patterns by count
    current_patterns = sorted(
        norm_results.get("patterns", []),
        key=get_count,
        reverse=True
    )

    # Limit to top 25
    current_patterns = current_patterns[:25]

    # Return the data
    return {
        "new_patterns": new_patterns,
        "disappeared_patterns": disappeared_patterns,
        "increased_patterns": increased_patterns,
        "decreased_patterns": decreased_patterns,
        "current_patterns": current_patterns,
        "current_patterns_count": len(norm_results.get("patterns", [])),
        "high_priority_alerts": high_priority_alerts,
    }


def _generate_html_content(
    data: Dict[str, Any],
    templates: Dict[str, str],
    kibana_url: Optional[str] = None,
    kibana_deeplink_structure: Optional[str] = None,
    enhanced_kibana_url: Optional[str] = None,
) -> str:
    """
    Generate HTML content for the email body.

    Args:
        data: Data for the email body
        templates: HTML templates
        kibana_url: Optional Kibana URL
        kibana_deeplink_structure: Optional Kibana deeplink structure
        enhanced_kibana_url: Optional enhanced Kibana URL

    Returns:
        HTML content
    """
    document_template = templates.get("document-template", "")
    if not document_template:
        return "<p>Error: Document template not found</p>"

    # Replace the CSS styles
    css_styles = templates.get("style", "")
    document_template = document_template.replace("{{CSS_STYLES}}", css_styles)

    # Generate timestamp
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    document_template = document_template.replace("{{TIMESTAMP}}", now)

    # Pattern counts
    document_template = document_template.replace("{{CURRENT_PATTERNS_COUNT}}", str(data.get("current_patterns_count", 0)))
    document_template = document_template.replace(
        "{{PREVIOUS_PATTERNS_COUNT}}",
        str(data.get("current_patterns_count", 0) - len(data.get("new_patterns", [])) + len(data.get("disappeared_patterns", []))))
    document_template = document_template.replace("{{NEW_PATTERNS_COUNT}}", str(len(data.get("new_patterns", []))))
    document_template = document_template.replace("{{DISAPPEARED_PATTERNS_COUNT}}", str(len(data.get("disappeared_patterns", []))))

    # Generate the pattern lists
    new_html, new_html_dark = generate_pattern_list_html(
        data.get("new_patterns", []), kibana_url, kibana_deeplink_structure
    )
    disappeared_html, disappeared_html_dark = generate_pattern_list_html(
        data.get("disappeared_patterns", []), kibana_url, kibana_deeplink_structure
    )
    increased_html, increased_html_dark = generate_increased_pattern_list_html(
        data.get("increased_patterns", []), kibana_url, kibana_deeplink_structure
    )
    decreased_html, decreased_html_dark = generate_decreased_pattern_list_html(
        data.get("decreased_patterns", []), kibana_url, kibana_deeplink_structure
    )
    top_html, top_html_dark = generate_pattern_list_html(
        data.get("current_patterns", []), kibana_url, kibana_deeplink_structure
    )

    # High priority alerts
    high_priority_html = _generate_high_priority_alerts_html(data.get("high_priority_alerts", []))
    high_priority_html_dark = _generate_high_priority_alerts_html(data.get("high_priority_alerts", []), dark_mode=True)

    # Replace the pattern lists in the template
    document_template = document_template.replace("{{NEW_PATTERNS_LIST}}", new_html)
    document_template = document_template.replace("{{DISAPPEARED_PATTERNS_LIST}}", disappeared_html)
    document_template = document_template.replace("{{INCREASED_PATTERNS_LIST}}", increased_html)
    document_template = document_template.replace("{{DECREASED_PATTERNS_LIST}}", decreased_html)
    document_template = document_template.replace("{{TOP_PATTERNS_LIST}}", top_html)

    # Replace dark mode versions
    document_template = document_template.replace("{{NEW_PATTERNS_LIST_DARK}}", new_html_dark)
    document_template = document_template.replace("{{DISAPPEARED_PATTERNS_LIST_DARK}}", disappeared_html_dark)
    document_template = document_template.replace("{{INCREASED_PATTERNS_LIST_DARK}}", increased_html_dark)
    document_template = document_template.replace("{{DECREASED_PATTERNS_LIST_DARK}}", decreased_html_dark)
    document_template = document_template.replace("{{TOP_PATTERNS_LIST_DARK}}", top_html_dark)

    # Replace high priority alerts
    document_template = document_template.replace("{{HIGH_PRIORITY_ALERTS_LIST}}", high_priority_html)
    document_template = document_template.replace("{{HIGH_PRIORITY_ALERTS_LIST_DARK}}", high_priority_html_dark)

    # Kibana URL
    if enhanced_kibana_url:
        kibana_button_template = templates.get("kibana-button-template", "")
        kibana_button = kibana_button_template.replace("{{KIBANA_URL}}", enhanced_kibana_url)
        document_template = document_template.replace("{{KIBANA_BUTTON}}", kibana_button)
    else:
        document_template = document_template.replace("{{KIBANA_BUTTON}}", "")

    # Replace any remaining Kibana URL references
    document_template = document_template.replace("{{KIBANA_URL}}", kibana_url or "")

    # Replace trend hours back
    document_template = document_template.replace("{{TREND_HOURS_BACK}}", "24")  # Default value

    return document_template


def _generate_text_content(data: Dict[str, Any]) -> str:
    """
    Generate text content for the email body.

    Args:
        data: Data for the email body

    Returns:
        Text content
    """
    # Generate timestamp
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    lines = [
        "PLATFORM PROBLEM MONITORING REPORT",
        "=" * 40,
        f"Report generated at: {now}",
        "",
        f"Current Patterns: {data.get('current_patterns_count', 0)}",
        f"Previous Patterns: {data.get('current_patterns_count', 0) - len(data.get('new_patterns', [])) + len(data.get('disappeared_patterns', []))}",
        f"New Patterns: {len(data.get('new_patterns', []))}",
        f"Disappeared Patterns: {len(data.get('disappeared_patterns', []))}",
        "",
    ]

    # Add high priority alerts
    high_priority_text = _generate_high_priority_alerts_text(data.get("high_priority_alerts", []))
    lines.append(high_priority_text)

    # New patterns
    new_patterns_text = generate_pattern_list_text(data.get("new_patterns", []))
    lines.append("NEW PROBLEM PATTERNS")
    lines.append("=" * 20)
    lines.append(new_patterns_text)
    lines.append("")

    # Increased patterns
    increased_patterns_text = generate_increased_pattern_list_text(data.get("increased_patterns", []))
    lines.append("INCREASED PROBLEM PATTERNS")
    lines.append("=" * 25)
    lines.append(increased_patterns_text)
    lines.append("")

    # Decreased patterns
    decreased_patterns_text = generate_decreased_pattern_list_text(data.get("decreased_patterns", []))
    lines.append("DECREASED PROBLEM PATTERNS")
    lines.append("=" * 25)
    lines.append(decreased_patterns_text)
    lines.append("")

    # Disappeared patterns
    disappeared_patterns_text = generate_pattern_list_text(data.get("disappeared_patterns", []))
    lines.append("DISAPPEARED PROBLEM PATTERNS")
    lines.append("=" * 27)
    lines.append(disappeared_patterns_text)
    lines.append("")

    # Top patterns
    top_patterns_text = generate_pattern_list_text(data.get("current_patterns", []))
    lines.append("TOP 25 CURRENT PROBLEM PATTERNS")
    lines.append("=" * 30)
    lines.append(top_patterns_text)

    return "\n".join(lines)


def generate_email_bodies(
    comparison_file: str,
    norm_results_file: str,
    html_output: str,
    text_output: str,
    high_priority_alerts_file: Optional[str] = None,
    trend_chart_file: Optional[str] = None,
    trend_hours_back: int = 24,
    kibana_url: Optional[str] = None,
    kibana_deeplink_structure: Optional[str] = None,
    elasticsearch_query_file: Optional[str] = None,
    start_date_time_file: Optional[str] = None,
) -> None:
    """
    Generate email bodies for the platform problem monitoring report.

    Args:
        comparison_file: Path to the comparison results file
        norm_results_file: Path to the normalization results file
        html_output: Path to store the HTML email body
        text_output: Path to store the plaintext email body
        high_priority_alerts_file: Path to the high priority alerts file
        trend_chart_file: Optional path to the trend chart file
        trend_hours_back: Number of hours to go back in time for trend analysis
        kibana_url: Optional Kibana URL
        kibana_deeplink_structure: Optional Kibana document deeplink URL structure
        elasticsearch_query_file: Optional path to the Elasticsearch query file
        start_date_time_file: Optional path to the start date and time file
    """
    logger.info("Generating email bodies")
    logger.info(f"Comparison file: {comparison_file}")
    logger.info(f"Normalization results file: {norm_results_file}")
    logger.info(f"HTML output: {html_output}")
    logger.info(f"Text output: {text_output}")

    if high_priority_alerts_file:
        logger.info(f"High priority alerts file: {high_priority_alerts_file}")

    if trend_chart_file:
        logger.info(f"Trend chart file: {trend_chart_file}")

    if kibana_url:
        logger.info(f"Kibana URL: {kibana_url}")

    if kibana_deeplink_structure:
        logger.info(f"Kibana deeplink structure: {kibana_deeplink_structure}")

    # Prepare data for the email
    try:
        data = _prepare_email_data(comparison_file, norm_results_file, high_priority_alerts_file)
    except FileNotFoundError as e:
        logger.error(f"File not found: {str(e)}")
        raise
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON: {str(e)}")
        raise

    # Load HTML templates
    try:
        templates = load_html_template()
    except Exception as e:
        logger.error(f"Error loading HTML templates: {str(e)}")
        raise

    # Create enhanced Kibana URL if possible
    enhanced_kibana_url = None
    if kibana_url and elasticsearch_query_file and start_date_time_file:
        try:
            enhanced_kibana_url = _create_enhanced_kibana_url(
                kibana_url, elasticsearch_query_file, start_date_time_file
            )
            logger.info(f"Created enhanced Kibana URL: {enhanced_kibana_url}")
        except Exception as e:
            logger.warning(f"Failed to create enhanced Kibana URL: {str(e)}")

    # Generate HTML content
    try:
        html_content = _generate_html_content(
            data, templates, kibana_url, kibana_deeplink_structure, enhanced_kibana_url
        )

        # If there's a trend chart, include it in the HTML
        if trend_chart_file and Path(trend_chart_file).exists():
            try:
                # Read the trend chart file
                with open(trend_chart_file, "rb") as f:
                    image_data = f.read()

                # Convert to base64
                import base64
                encoded_image = base64.b64encode(image_data).decode("utf-8")

                # Replace the placeholder with the image
                img_tag = f'<img src="data:image/png;base64,{encoded_image}" alt="Trend Chart" style="max-width:100%;height:auto;">'
                html_content = html_content.replace("<!--TREND_CHART_PLACEHOLDER-->", img_tag)

                # Update trend hours back
                html_content = html_content.replace("{{TREND_HOURS_BACK}}", str(trend_hours_back))

                logger.info("Included trend chart in HTML")
            except Exception as e:
                logger.warning(f"Failed to include trend chart: {str(e)}")
                html_content = html_content.replace("<!--TREND_CHART_PLACEHOLDER-->", "")
        else:
            # No trend chart, remove the placeholder
            html_content = html_content.replace("<!--TREND_CHART_PLACEHOLDER-->", "")
            html_content = html_content.replace("{{TREND_HOURS_BACK}}", str(trend_hours_back))

        # Write HTML content to output file
        with open(html_output, "w") as f:
            f.write(html_content)

        logger.info(f"HTML email body saved to {html_output}")
    except Exception as e:
        logger.error(f"Error generating HTML content: {str(e)}")
        raise

    # Generate text content
    try:
        text_content = _generate_text_content(data)

        # Write text content to output file
        with open(text_output, "w") as f:
            f.write(text_content)

        logger.info(f"Text email body saved to {text_output}")
    except Exception as e:
        logger.error(f"Error generating text content: {str(e)}")
        raise

    logger.info("Email bodies generated successfully")


def main() -> None:
    """Execute the script when run directly."""
    parser = argparse.ArgumentParser(description="Generate email bodies for the platform problem monitoring report")
    parser.add_argument("--comparison-file", required=True, help="Path to the comparison results file")
    parser.add_argument("--norm-results-file", required=True, help="Path to the normalization results file")
    parser.add_argument("--html-output", required=True, help="Path to store the HTML email body")
    parser.add_argument("--text-output", required=True, help="Path to store the plaintext email body")
    parser.add_argument("--high-priority-alerts-file", help="Path to the high priority alerts file")
    parser.add_argument("--trend-chart-file", help="Path to the trend chart file")
    parser.add_argument("--trend-hours-back", type=int, default=24, help="Number of hours to go back in time for trend")
    parser.add_argument("--kibana-url", help="Kibana URL")
    parser.add_argument("--kibana-deeplink-structure", help="Kibana document deeplink URL structure")
    parser.add_argument("--elasticsearch-query-file", help="Path to the Elasticsearch query file")
    parser.add_argument("--start-date-time-file", help="Path to the start date and time file")

    args = parser.parse_args()

    try:
        generate_email_bodies(
            args.comparison_file,
            args.norm_results_file,
            args.html_output,
            args.text_output,
            args.high_priority_alerts_file,
            args.trend_chart_file,
            args.trend_hours_back,
            args.kibana_url,
            args.kibana_deeplink_structure,
            args.elasticsearch_query_file,
            args.start_date_time_file,
        )
        sys.exit(0)
    except Exception as e:
        logger.error(f"Error generating email bodies: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
