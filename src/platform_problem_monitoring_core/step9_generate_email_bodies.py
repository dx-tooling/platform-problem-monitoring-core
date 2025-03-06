#!/usr/bin/env python3
"""Generate email bodies for platform problem monitoring reports."""

import argparse
import base64
import json
import re
import sys
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from platform_problem_monitoring_core.utils import load_json, logger


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
    Find the HTML template file by checking multiple possible locations.

    Returns:
        Path to the HTML template file
    """
    # List of possible relative paths to try
    possible_paths = [
        # Path if installed as a package (highest priority)
        Path(__file__).parent
        / "resources"
        / "html_email_template.html"
    ]

    # Try each path
    for path in possible_paths:
        if path.exists():
            logger.info(f"Found HTML template at: {path}")
            return str(path)

    # If we get here, we couldn't find the template
    error_msg = f"Could not find HTML template file. Tried the following paths: {possible_paths}"
    logger.error(error_msg)
    raise FileNotFoundError(error_msg)


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

    # Split very long words with zero-width spaces to allow breaking in HTML
    words = text.split()
    for i, word in enumerate(words):
        # If word is longer than 80 chars, add zero-width spaces every 80 chars
        if len(word) > 80:
            # Insert zero-width space (&#8203;) every 80 chars
            chars = list(word)
            for j in range(80, len(chars), 80):
                chars.insert(j, "&#8203;")
            words[i] = "".join(chars)

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


def _prepare_email_data(comparison_file: str, norm_results_file: str) -> Dict[str, Any]:
    """
    Prepare data for email generation.

    Args:
        comparison_file: Path to the comparison results file
        norm_results_file: Path to the normalization results file

    Returns:
        Dictionary with data for email generation
    """
    # Load the comparison results
    comparison = load_json(comparison_file)

    # Load the normalization results
    norm_results = load_json(norm_results_file)

    # Get the top 25 patterns from the normalization results
    top_patterns = sorted(norm_results.get("patterns", []), key=get_count, reverse=True)[:25]

    # Extract data from comparison results
    current_patterns_count = comparison.get("current_patterns_count", 0)
    previous_patterns_count = comparison.get("previous_patterns_count", 0)
    new_patterns = comparison.get("new_patterns", [])
    disappeared_patterns = comparison.get("disappeared_patterns", [])
    increased_patterns = comparison.get("increased_patterns", [])
    decreased_patterns = comparison.get("decreased_patterns", [])

    # Generate timestamp
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    return {
        "top_patterns": top_patterns,
        "current_patterns_count": current_patterns_count,
        "previous_patterns_count": previous_patterns_count,
        "new_patterns": new_patterns,
        "disappeared_patterns": disappeared_patterns,
        "increased_patterns": increased_patterns,
        "decreased_patterns": decreased_patterns,
        "timestamp": timestamp,
    }


def _generate_html_content(
    data: Dict[str, Any],
    templates: Dict[str, str],
    kibana_url: Optional[str] = None,
    kibana_deeplink_structure: Optional[str] = None,
    enhanced_kibana_url: Optional[str] = None,
) -> str:
    """
    Generate HTML content for the email.

    Args:
        data: Data for email generation
        templates: HTML templates
        kibana_url: Kibana base URL
        kibana_deeplink_structure: URL structure for Kibana deeplinks
        enhanced_kibana_url: Enhanced Kibana URL with query and timeframe

    Returns:
        HTML content for the email
    """
    document_template = templates.get("document-template", "")
    kibana_button_template = templates.get("kibana-button-template", "")
    css_styles = templates.get("css", "")

    # Generate Kibana button if URL is provided
    kibana_button = ""
    if enhanced_kibana_url:
        kibana_button = kibana_button_template.replace("{{KIBANA_URL}}", enhanced_kibana_url)

    # Generate HTML for pattern lists
    new_patterns_html, new_patterns_dark_html = generate_pattern_list_html(
        data["new_patterns"][:10], kibana_url, kibana_deeplink_structure
    )
    disappeared_patterns_html, disappeared_patterns_dark_html = generate_pattern_list_html(
        data["disappeared_patterns"][:10], kibana_url, kibana_deeplink_structure
    )
    increased_patterns_html, increased_patterns_dark_html = generate_increased_pattern_list_html(
        data["increased_patterns"][:10], kibana_url, kibana_deeplink_structure
    )
    decreased_patterns_html, decreased_patterns_dark_html = generate_decreased_pattern_list_html(
        data["decreased_patterns"][:10], kibana_url, kibana_deeplink_structure
    )
    top_patterns_html, top_patterns_dark_html = generate_pattern_list_html(
        data["top_patterns"][:25], kibana_url, kibana_deeplink_structure
    )

    # Replace placeholders in the main template
    html = document_template
    html = html.replace("{{CSS_STYLES}}", f"<style>{css_styles}</style>")
    html = html.replace("{{TIMESTAMP}}", data["timestamp"])
    html = html.replace("{{CURRENT_PATTERNS_COUNT}}", str(data["current_patterns_count"]))
    html = html.replace("{{PREVIOUS_PATTERNS_COUNT}}", str(data["previous_patterns_count"]))
    html = html.replace("{{NEW_PATTERNS_COUNT}}", str(len(data["new_patterns"])))
    html = html.replace("{{DISAPPEARED_PATTERNS_COUNT}}", str(len(data["disappeared_patterns"])))
    html = html.replace("{{KIBANA_BUTTON}}", kibana_button)

    # Ensure all instances of {{KIBANA_URL}} are replaced
    html = html.replace("{{KIBANA_URL}}", enhanced_kibana_url or kibana_url or "")

    # Replace light mode pattern lists
    html = html.replace("{{NEW_PATTERNS_LIST}}", new_patterns_html)
    html = html.replace("{{DISAPPEARED_PATTERNS_LIST}}", disappeared_patterns_html)
    html = html.replace("{{INCREASED_PATTERNS_LIST}}", increased_patterns_html)
    html = html.replace("{{DECREASED_PATTERNS_LIST}}", decreased_patterns_html)
    html = html.replace("{{TOP_PATTERNS_LIST}}", top_patterns_html)

    # Replace dark mode pattern lists
    html = html.replace("{{NEW_PATTERNS_LIST_DARK}}", new_patterns_dark_html)
    html = html.replace("{{DISAPPEARED_PATTERNS_LIST_DARK}}", disappeared_patterns_dark_html)
    html = html.replace("{{INCREASED_PATTERNS_LIST_DARK}}", increased_patterns_dark_html)
    html = html.replace("{{DECREASED_PATTERNS_LIST_DARK}}", decreased_patterns_dark_html)
    html = html.replace("{{TOP_PATTERNS_LIST_DARK}}", top_patterns_dark_html)

    return html


def _generate_text_content(data: Dict[str, Any]) -> str:
    """
    Generate plaintext content for the email.

    Args:
        data: Data for email generation

    Returns:
        Plaintext content for the email
    """
    return f"""
PLATFORM PROBLEM MONITORING REPORT
=================================
Generated: {data["timestamp"]}

SUMMARY
-------
Current problem patterns: {data["current_patterns_count"]}
Previous problem patterns: {data["previous_patterns_count"]}
New problem patterns: {len(data["new_patterns"])}
Disappeared problem patterns: {len(data["disappeared_patterns"])}

NEW PROBLEM PATTERNS
===================
These patterns have appeared since the last report.

{generate_pattern_list_text(data["new_patterns"][:10])}

DISAPPEARED PROBLEM PATTERNS
==========================
These patterns were present in the previous report but are no longer occurring.

{generate_pattern_list_text(data["disappeared_patterns"][:10])}

INCREASED PROBLEM PATTERNS
========================
These patterns have increased in occurrence count since the last report.

{generate_increased_pattern_list_text(data["increased_patterns"][:10])}

DECREASED PROBLEM PATTERNS
========================
These patterns have decreased in occurrence count since the last report.

{generate_decreased_pattern_list_text(data["decreased_patterns"][:10])}

TOP 25 CURRENT PROBLEM PATTERNS
==============================
The most frequent problem patterns in the current report.

{generate_pattern_list_text(data["top_patterns"])}

This is an automated report from the Platform Problem Monitoring system.
"""


def generate_email_bodies(
    comparison_file: str,
    norm_results_file: str,
    html_output: str,
    text_output: str,
    trend_chart_file: Optional[str] = None,
    trend_hours_back: int = 24,
    kibana_url: Optional[str] = None,
    kibana_deeplink_structure: Optional[str] = None,
    elasticsearch_query_file: Optional[str] = None,
    start_date_time_file: Optional[str] = None,
) -> None:
    """
    Generate HTML and plaintext email bodies.

    Args:
        comparison_file: Path to the comparison results file
        norm_results_file: Path to the normalization results file
        html_output: Path to store the HTML email body
        text_output: Path to store the plaintext email body
        trend_chart_file: Path to the trend chart image file (optional)
        trend_hours_back: Number of hours to look back for problem trends (default: 24)
        kibana_url: Kibana base URL for the "View in Kibana" button (optional)
        kibana_deeplink_structure: URL structure for individual Kibana document deeplinks (optional)
        elasticsearch_query_file: Path to the Elasticsearch Lucene query file (optional)
        start_date_time_file: Path to the file containing the start date time (optional)
    """
    logger.info("Generating email bodies")
    logger.info(f"Comparison file: {comparison_file}")
    logger.info(f"Normalization results file: {norm_results_file}")
    logger.info(f"HTML output: {html_output}")
    logger.info(f"Text output: {text_output}")
    logger.info(f"Hours back: {trend_hours_back}")
    if trend_chart_file:
        logger.info(f"Trend chart file: {trend_chart_file}")
    if kibana_url:
        logger.info(f"Kibana URL: {kibana_url}")
    if kibana_deeplink_structure:
        logger.info(f"Kibana deeplink structure: {kibana_deeplink_structure}")
    if elasticsearch_query_file:
        logger.info(f"Elasticsearch query file: {elasticsearch_query_file}")
    if start_date_time_file:
        logger.info(f"Start date time file: {start_date_time_file}")

    # Prepare data for email generation
    data = _prepare_email_data(comparison_file, norm_results_file)

    # Load HTML templates
    templates = load_html_template()

    # Create enhanced Kibana URL if possible
    enhanced_kibana_url = kibana_url
    if (
        kibana_url
        and elasticsearch_query_file
        and start_date_time_file
        and Path(elasticsearch_query_file).exists()
        and Path(start_date_time_file).exists()
    ):
        enhanced_kibana_url = _create_enhanced_kibana_url(kibana_url, elasticsearch_query_file, start_date_time_file)

    # Generate HTML and text content
    html = _generate_html_content(data, templates, kibana_url, kibana_deeplink_structure, enhanced_kibana_url)

    # Replace hours back placeholder
    html = html.replace("{{TREND_HOURS_BACK}}", str(trend_hours_back))

    # Embed trend chart if available
    if trend_chart_file and Path(trend_chart_file).exists():
        try:
            with Path(trend_chart_file).open("rb") as img_file:
                encoded_image = base64.b64encode(img_file.read()).decode("utf-8")
                html = html.replace(
                    "<!--TREND_CHART_PLACEHOLDER-->",
                    f'<img src="data:image/png;base64,{encoded_image}"'
                    f' alt="PROBLEM MESSAGES TREND" style="max-width:100%; height:auto; border-radius:8px;">',
                )
                logger.info("Trend chart embedded in HTML")
        except Exception as e:
            logger.warning(f"Failed to embed trend chart: {str(e)}")

    text = _generate_text_content(data)

    # Write the email bodies to the output files
    with Path(html_output).open("w") as f:
        f.write(html)

    with Path(text_output).open("w") as f:
        f.write(text)

    logger.info("Email bodies generated successfully")


def main() -> None:
    """Execute the script when run directly."""
    parser = argparse.ArgumentParser(description="Generate email bodies")
    parser.add_argument("--comparison-file", required=True, help="Path to the comparison results file")
    parser.add_argument("--norm-results-file", required=True, help="Path to the normalization results file")
    parser.add_argument("--html-output", required=True, help="Path to store the HTML email body")
    parser.add_argument("--text-output", required=True, help="Path to store the plaintext email body")
    parser.add_argument("--trend-chart-file", help="Path to the trend chart image file")
    parser.add_argument("--hours-back", type=int, default=24, help="Number of hours to look back for problem trends")
    parser.add_argument("--kibana-url", help="Kibana base URL for the 'View in Kibana' button")
    parser.add_argument(
        "--kibana-deeplink-structure",
        help="URL structure for individual Kibana document deeplinks with {{index}} and {{id}} placeholders",
    )
    parser.add_argument("--elasticsearch-query-file", help="Path to the Elasticsearch Lucene query file")
    parser.add_argument("--start-date-time-file", help="Path to the file containing the start date time")

    args = parser.parse_args()

    try:
        generate_email_bodies(
            args.comparison_file,
            args.norm_results_file,
            args.html_output,
            args.text_output,
            args.trend_chart_file,
            args.hours_back,
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
