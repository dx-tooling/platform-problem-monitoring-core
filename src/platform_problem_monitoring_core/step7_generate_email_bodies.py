#!/usr/bin/env python3
"""Generate email bodies for platform problem monitoring reports."""

import argparse
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from platform_problem_monitoring_core.utils import load_json, logger


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
            # Create a deep link to Kibana
            if kibana_deeplink_structure:
                # Use the new configurable deeplink structure
                kibana_link = kibana_deeplink_structure.replace("{{index}}", index).replace("{{id}}", doc_id)
            elif kibana_url:
                # Fallback to the old method for backward compatibility
                kibana_link = f"{kibana_url}/app/discover#/doc/logstash-*/{index}?id={doc_id}"
            else:
                continue

            # Add comma if not the last item
            comma = ", " if j < len(pattern["sample_doc_references"][:5]) else ""

            link_html = sample_link_item_template.replace("{{KIBANA_LINK}}", kibana_link)
            link_html = link_html.replace("{{INDEX}}", str(j))
            link_html = link_html.replace("{{COMMA}}", comma)

            sample_links_list += link_html

    if sample_links_list:
        result = sample_links_template.replace("{{SAMPLE_LINKS_LIST}}", sample_links_list)
        return result

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


def generate_increased_pattern_list_html(
    patterns: List[Dict[str, Any]],
    kibana_url: Optional[str] = None,
    kibana_deeplink_structure: Optional[str] = None,
) -> Tuple[str, str]:
    """
    Generate HTML for a list of increased patterns.

    Args:
        patterns: List of patterns to display
        kibana_url: Optional Kibana base URL for deep links
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
    pattern_item_template = templates.get("increased-pattern-item-template", "")

    light_html = "<div class='space-y-6'>"

    for i, pattern in enumerate(patterns, 1):
        current_count = pattern.get("current_count", 0)
        pattern_text = pattern.get("pattern", "")
        absolute_change = current_count - pattern.get("previous_count", 0)
        percent_change = (
            round((absolute_change / pattern.get("previous_count", 1)) * 100, 1)
            if pattern.get("previous_count", 1) > 0
            else 0
        )

        # Create a unique ID for each pattern
        pattern_id = f"increased-pattern-{i}"

        # Generate sample links
        sample_links = generate_sample_links_html(pattern, kibana_url, kibana_deeplink_structure, dark_mode=False)

        # Replace placeholders in the template
        pattern_html = pattern_item_template.replace("{{INDEX}}", str(i))
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
    Generate HTML for a list of decreased patterns.

    Args:
        patterns: List of patterns to display
        kibana_url: Optional Kibana base URL for deep links
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
    pattern_item_template = templates.get("decreased-pattern-item-template", "")

    light_html = "<div class='space-y-6'>"

    for i, pattern in enumerate(patterns, 1):
        current_count = pattern.get("current_count", 0)
        pattern_text = pattern.get("pattern", "")
        absolute_change = pattern.get("previous_count", 0) - current_count
        percent_change = (
            round((absolute_change / pattern.get("previous_count", 1)) * 100, 1)
            if pattern.get("previous_count", 1) > 0
            else 0
        )

        # Create a unique ID for each pattern
        pattern_id = f"decreased-pattern-{i}"

        # Generate sample links
        sample_links = generate_sample_links_html(pattern, kibana_url, kibana_deeplink_structure, dark_mode=False)

        # Replace placeholders in the template
        pattern_html = pattern_item_template.replace("{{INDEX}}", str(i))
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

            text += ", ".join(sample_refs) + "\n"

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

            text += ", ".join(sample_refs) + "\n"

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

            text += ", ".join(sample_refs) + "\n"

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


def generate_email_bodies(
    comparison_file: str,
    norm_results_file: str,
    html_output: str,
    text_output: str,
    kibana_url: Optional[str] = None,
    kibana_deeplink_structure: Optional[str] = None,
) -> None:
    """
    Generate HTML and plaintext email bodies.

    Args:
        comparison_file: Path to the comparison results file
        norm_results_file: Path to the normalization results file
        html_output: Path to store the HTML email body
        text_output: Path to store the plaintext email body
        kibana_url: Kibana base URL for the "View in Kibana" button (optional)
        kibana_deeplink_structure: URL structure for individual Kibana document deeplinks (optional)
    """
    logger.info("Generating email bodies")
    logger.info(f"Comparison file: {comparison_file}")
    logger.info(f"Normalization results file: {norm_results_file}")
    logger.info(f"HTML output: {html_output}")
    logger.info(f"Text output: {text_output}")
    if kibana_url:
        logger.info(f"Kibana URL: {kibana_url}")
    if kibana_deeplink_structure:
        logger.info(f"Kibana deeplink structure: {kibana_deeplink_structure}")

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

    # Load HTML templates
    templates = load_html_template()
    document_template = templates.get("document-template", "")
    kibana_button_template = templates.get("kibana-button-template", "")
    css_styles = templates.get("css", "")

    # Generate Kibana button if URL is provided
    kibana_button = ""
    if kibana_url:
        kibana_button = kibana_button_template.replace("{{KIBANA_URL}}", kibana_url)

    # Generate HTML for pattern lists
    new_patterns_html, new_patterns_dark_html = generate_pattern_list_html(
        new_patterns[:10], kibana_url, kibana_deeplink_structure
    )
    disappeared_patterns_html, disappeared_patterns_dark_html = generate_pattern_list_html(
        disappeared_patterns[:10], kibana_url, kibana_deeplink_structure
    )
    increased_patterns_html, increased_patterns_dark_html = generate_increased_pattern_list_html(
        increased_patterns[:10], kibana_url, kibana_deeplink_structure
    )
    decreased_patterns_html, decreased_patterns_dark_html = generate_decreased_pattern_list_html(
        decreased_patterns[:10], kibana_url, kibana_deeplink_structure
    )
    top_patterns_html, top_patterns_dark_html = generate_pattern_list_html(
        top_patterns[:25], kibana_url, kibana_deeplink_structure
    )

    # Replace placeholders in the main template
    html = document_template
    html = html.replace("{{CSS_STYLES}}", f"<style>{css_styles}</style>")
    html = html.replace("{{TIMESTAMP}}", timestamp)
    html = html.replace("{{CURRENT_PATTERNS_COUNT}}", str(current_patterns_count))
    html = html.replace("{{PREVIOUS_PATTERNS_COUNT}}", str(previous_patterns_count))
    html = html.replace("{{NEW_PATTERNS_COUNT}}", str(len(new_patterns)))
    html = html.replace("{{DISAPPEARED_PATTERNS_COUNT}}", str(len(disappeared_patterns)))
    html = html.replace("{{KIBANA_BUTTON}}", kibana_button)

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

    # Generate plaintext email body
    text = f"""
Platform Problem Monitoring Report
=================================

Report generated at: {timestamp}

SUMMARY:
- Current Patterns: {current_patterns_count}
- Previous Patterns: {previous_patterns_count}
- New Patterns: {len(new_patterns)}
- Disappeared Patterns: {len(disappeared_patterns)}

{f'View in Kibana: {kibana_url}' if kibana_url else ''}

SUMMARY OF CHANGES IN PROBLEM PATTERNS
=====================================

TOP 10 NEW PROBLEM PATTERNS
---------------------------
These patterns appeared in the new summary but were not present in the previous one.

{generate_pattern_list_text(new_patterns[:10])}

TOP 10 DISAPPEARED PROBLEM PATTERNS
----------------------------------
These patterns were present in the previous summary but are not in the current one.

{generate_pattern_list_text(disappeared_patterns[:10])}

TOP 10 INCREASED PROBLEM PATTERNS
--------------------------------
These patterns have increased in occurrence count since the last report.

{generate_increased_pattern_list_text(increased_patterns[:10])}

TOP 10 DECREASED PROBLEM PATTERNS
--------------------------------
These patterns have decreased in occurrence count since the last report.

{generate_decreased_pattern_list_text(decreased_patterns[:10])}

TOP 25 CURRENT PROBLEM PATTERNS
==============================
The most frequent problem patterns in the current report.

{generate_pattern_list_text(top_patterns)}

This is an automated report from the Platform Problem Monitoring system.
"""

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
    parser.add_argument("--kibana-url", help="Kibana base URL for the 'View in Kibana' button")
    parser.add_argument(
        "--kibana-deeplink-structure",
        help="URL structure for individual Kibana document deeplinks with {{index}} and {{id}} placeholders",
    )

    args = parser.parse_args()

    try:
        generate_email_bodies(
            args.comparison_file,
            args.norm_results_file,
            args.html_output,
            args.text_output,
            args.kibana_url,
            args.kibana_deeplink_structure,
        )
        sys.exit(0)
    except Exception as e:
        logger.error(f"Error generating email bodies: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
