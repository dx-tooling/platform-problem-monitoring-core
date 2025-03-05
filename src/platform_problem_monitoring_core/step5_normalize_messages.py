#!/usr/bin/env python3
"""Normalize messages using drain3 for pattern recognition."""

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, TypedDict

from drain3 import TemplateMiner
from drain3.masking import MaskingInstruction
from drain3.template_miner_config import TemplateMinerConfig

from platform_problem_monitoring_core.utils import logger, save_json


def configure_template_miner() -> TemplateMiner:
    """
    Configure the drain3 template miner with custom masking instructions.

    Returns:
        Configured TemplateMiner instance
    """
    config = TemplateMinerConfig()
    config.mask_prefix = "<"
    config.mask_suffix = ">"

    # Clear default masking instructions and add custom ones
    config.masking_instructions = []

    # IP addresses
    config.masking_instructions.append(
        MaskingInstruction(pattern=r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}", mask_with="IP")
    )

    # Timestamps in various formats
    config.masking_instructions.append(
        MaskingInstruction(
            pattern=r"\[\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?(\+|-)\d{2}:\d{2}\]",
            mask_with="[TIMESTAMP]",
        )
    )
    config.masking_instructions.append(
        MaskingInstruction(
            pattern=r"\[\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}(\.\d+)?\]", mask_with="[TIMESTAMP]"
        )
    )
    config.masking_instructions.append(
        MaskingInstruction(
            pattern=r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?(\+|-)\d{2}:\d{2}",
            mask_with="TIMESTAMP",
        )
    )
    config.masking_instructions.append(
        MaskingInstruction(
            pattern=r"\d{2}/[A-Za-z]{3}/\d{4}:\d{2}:\d{2}:\d{2} (\+|-)\d{4}", mask_with="TIMESTAMP"
        )
    )
    config.masking_instructions.append(
        MaskingInstruction(
            pattern=r"[A-Z][a-z]{2} \d{1,2} \d{2}:\d{2}:\d{2}", mask_with="TIMESTAMP"
        )
    )
    config.masking_instructions.append(
        MaskingInstruction(pattern=r"\d{4}-\d{2}-\d{2}", mask_with="DATE")
    )
    config.masking_instructions.append(
        MaskingInstruction(pattern=r"\d{2}:\d{2}:\d{2}(\.\d+)?", mask_with="TIME")
    )

    # UUIDs
    config.masking_instructions.append(
        MaskingInstruction(
            pattern=r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
            mask_with="UUID",
        )
    )

    # Hexadecimal identifiers
    config.masking_instructions.append(
        MaskingInstruction(pattern=r"\b[0-9a-f]{16,}\b", mask_with="HEX")
    )

    # Process IDs
    config.masking_instructions.append(MaskingInstruction(pattern=r"\[\d+\]", mask_with="[PID]"))

    # Line numbers in stack traces
    config.masking_instructions.append(
        MaskingInstruction(pattern=r"line:? \d+", mask_with="line: NUM")
    )
    config.masking_instructions.append(MaskingInstruction(pattern=r":\d+\)", mask_with=":NUM)"))

    # Query parameters in URLs
    config.masking_instructions.append(
        MaskingInstruction(pattern=r'\?[^"\'<>\s]*', mask_with="?PARAMS")
    )

    return TemplateMiner(config=config)


def protect_file_paths(line: str) -> str:
    """
    Identify and protect file paths in log messages.

    Args:
        line: Log message line

    Returns:
        Line with protected file paths
    """
    # Common file path patterns in error messages
    file_path_patterns = [
        # Pattern for PHP errors: in /path/to/file.php on line 123
        r"(in\s+)(/[^\s:]+)(\s+on\s+line\s+)(\d+)",
        # Pattern for stack traces: at /path/to/file.php:123
        r"(at\s+)(/[^\s:]+):(\d+)",
        # Pattern for file paths with line numbers: /path/to/file.php:123
        r"(^|\s)(/[^\s:]+):(\d+)(\s|$)",
        # Pattern for file paths in quotes: '/path/to/file.php'
        r'[\'"](/[^\'"]+)[\'"]',
    ]

    for pattern in file_path_patterns:
        if "on line" in pattern:
            # For PHP-style errors: "in /path/to/file.php on line 123"
            line = re.sub(pattern, r"\1\2\3<NUM>", line)
        elif "at" in pattern:
            # For stack traces: "at /path/to/file.php:123"
            line = re.sub(pattern, r"\1\2:<NUM>", line)
        elif ":" in pattern:
            # For general file paths with line numbers: "/path/to/file.php:123"
            line = re.sub(pattern, r"\1\2:<NUM>\4", line)

    return line


def normalize_json(json_obj: Any) -> Any:
    """
    Recursively process a JSON object and mask variable parts while preserving structure.

    Args:
        json_obj: JSON object to normalize

    Returns:
        Normalized JSON object
    """
    if isinstance(json_obj, dict):
        result = {}
        for key, value in json_obj.items():
            # Keep the keys as is, normalize the values
            result[key] = normalize_json(value)
        return result
    elif isinstance(json_obj, list):
        # For lists, normalize each element
        return [normalize_json(item) for item in json_obj]
    elif isinstance(json_obj, str):
        # Mask UUIDs
        if re.match(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", json_obj):
            return "<UUID>"
        # Mask timestamps
        elif re.match(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?(\+|-)\d{2}:\d{2}$", json_obj):
            return "<TIMESTAMP>"
        # Mask emails
        elif re.match(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", json_obj):
            return "<EMAIL>"
        # For other strings, keep them as is
        return json_obj
    elif isinstance(json_obj, (int, float)):
        # Mask numbers
        return "<NUM>"
    else:
        # For booleans, null, etc., keep them as is
        return json_obj


def preprocess_log_line(line: str) -> str:
    """
    Preprocess a log line to handle special cases before template mining.

    Args:
        line: Log message line

    Returns:
        Preprocessed log line
    """
    # Handle timestamp patterns in square brackets
    timestamp_pattern = r"\[\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?(\+|-)\d{2}:\d{2}\]"
    line = re.sub(timestamp_pattern, "[TIMESTAMP]", line)

    alt_timestamp_pattern = r"\[\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}(\.\d+)?\]"
    line = re.sub(alt_timestamp_pattern, "[TIMESTAMP]", line)

    iso_timestamp = r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?(\+|-)\d{2}:\d{2}"
    line = re.sub(iso_timestamp, "TIMESTAMP", line)

    # Identify and protect file paths
    line = protect_file_paths(line)

    # Handle JSON structures in log messages
    json_pattern = r"(\{.*\})"
    json_matches = re.findall(json_pattern, line)

    for json_str in json_matches:
        try:
            # Try to parse the JSON
            parsed_json = json.loads(json_str)

            # Create a normalized version with masked values but preserved structure
            normalized_json = normalize_json(parsed_json)

            # Replace the original JSON with the normalized version
            line = line.replace(json_str, json.dumps(normalized_json))
        except json.JSONDecodeError:
            # If it's not valid JSON, continue with normal processing
            pass

    # Identify and temporarily mark HTTP verb + URL patterns
    http_pattern = r"(GET|POST|PUT|DELETE|PATCH|HEAD|OPTIONS) ([^ ]+) HTTP/\d+\.\d+"

    def replace_numbers_except_in_urls(match: re.Match) -> str:
        verb = match.group(1)
        url = match.group(2)
        http_version = match.group(0).split(" ")[-1]

        # Replace numbers in the HTTP version
        http_version = re.sub(r"\d+", "<NUM>", http_version)

        # Keep the URL path intact, but mask query parameters
        url_parts = url.split("?", 1)
        path = url_parts[0]

        # If there are query parameters, mask them
        if len(url_parts) > 1:
            return f"{verb} {path}<?PARAMS> {http_version}"
        else:
            return f"{verb} {path} {http_version}"

    # Apply the URL handling
    line = re.sub(http_pattern, replace_numbers_except_in_urls, line)

    # Replace numbers in the rest of the line (not in URLs or file paths)
    line = re.sub(r"(?<![a-zA-Z0-9/_.-])(\d+)(?![a-zA-Z0-9/_.-])", "<NUM>", line)
    line = re.sub(r"(?<![a-zA-Z0-9/_.-])(\d+\.\d+)(?![a-zA-Z0-9/_.-])", "<NUM>.<NUM>", line)

    return line


def post_process_template(template: str) -> str:
    """
    Post-process a template to make it more readable.

    Args:
        template: Template to post-process

    Returns:
        Post-processed template
    """
    # Replace consecutive masked parameters with a single mask
    template = re.sub(r"(<[^>]+>)(\s*\1)+", r"\1", template)

    # Ensure timestamp components are consistently masked
    # Replace patterns like <NUM>:<NUM>:<NUM> with <TIME>
    template = re.sub(r"<NUM>:<NUM>:<NUM>(\.<NUM>)?", "<TIME>", template)

    # Replace patterns like <NUM>-<NUM>-<NUM> with <DATE>
    template = re.sub(r"<NUM>-<NUM>-<NUM>", "<DATE>", template)

    # Replace patterns like [<DATE>T<TIME>+<NUM>:<NUM>] with [<TIMESTAMP>]
    template = re.sub(r"\[<DATE>T<TIME>(\+|-)<NUM>:<NUM>\]", "[<TIMESTAMP>]", template)

    # Handle alternative format with space instead of 'T'
    template = re.sub(r"\[<DATE> <TIME>\]", "[<TIMESTAMP>]", template)

    # Handle any remaining timestamp-like patterns
    template = re.sub(
        r"\[<NUM>-<NUM>-<NUM>T?<NUM>:<NUM>:<NUM>(.<NUM>)?(\+|-)?<NUM>?:?<NUM>?\]",
        "[<TIMESTAMP>]",
        template,
    )

    return template


class PatternResult(TypedDict):
    """Type for pattern results."""

    cluster_id: str
    count: int
    pattern: str
    first_seen: str
    last_seen: str
    sample_log_lines: List[str]
    sample_doc_references: List[str]


def _process_document(
    doc: dict, template_miner: TemplateMiner, pattern_doc_references: dict
) -> bool:
    """
    Process a single document to extract and normalize its message.

    Args:
        doc: Document to process
        template_miner: Configured template miner
        pattern_doc_references: Dictionary to store document references for each pattern

    Returns:
        True if processing was successful, False otherwise
    """
    index_name = doc.get("index", "unknown")
    doc_id = doc.get("id", "unknown")
    message = doc.get("message", "")

    if not message:
        return False

    # Apply custom pre-processing to the message
    processed_message = preprocess_log_line(message)

    # Add to template miner
    result = template_miner.add_log_message(processed_message)

    # Store the document ID with its template
    template_id = result["cluster_id"]
    if template_id not in pattern_doc_references:
        pattern_doc_references[template_id] = []

    # Add the doc ID and index to the lists, keeping only the 5 most recent
    doc_reference = f"{index_name}:{doc_id}"
    pattern_doc_references[template_id].append(doc_reference)
    if len(pattern_doc_references[template_id]) > 5:
        pattern_doc_references[template_id].pop(0)

    return True


# Define a function to get the count safely with a proper return type
def get_count(pattern: PatternResult) -> int:
    """Safely get the count from a pattern dictionary.

    Args:
        pattern: The pattern dictionary.

    Returns:
        The count value.
    """
    return pattern["count"]


def _prepare_results(
    template_miner: TemplateMiner, pattern_doc_references: dict
) -> List[PatternResult]:
    """
    Prepare results from template miner.

    Args:
        template_miner: The template miner instance.
        pattern_doc_references: Dictionary mapping cluster IDs to document references.

    Returns:
        List of pattern results.
    """
    results: List[PatternResult] = []

    # Access the id_to_cluster dictionary directly instead of using clusters
    for cluster_id, cluster in template_miner.drain.id_to_cluster.items():
        # Post-process the template to make it more readable
        template = post_process_template(cluster.get_template())

        # Create result entry
        result: PatternResult = {
            "cluster_id": cluster_id,
            "count": cluster.size,
            "pattern": template,
            "first_seen": (
                pattern_doc_references.get(cluster_id, [""])[0]
                if pattern_doc_references.get(cluster_id, [])
                else ""
            ),
            "last_seen": (
                pattern_doc_references.get(cluster_id, [""])[-1]
                if pattern_doc_references.get(cluster_id, [])
                else ""
            ),
            "sample_log_lines": (
                cluster.get_sample_logs() if hasattr(cluster, "get_sample_logs") else []
            ),
            "sample_doc_references": pattern_doc_references.get(cluster_id, []),
        }
        results.append(result)

    # Sort results by count (descending)
    results.sort(key=get_count, reverse=True)
    return results


def normalize_messages(fields_file: str, output_file: str) -> None:
    """
    Normalize messages and summarize them.

    Args:
        fields_file: Path to the extracted fields file
        output_file: Path to store the normalization results
    """
    logger.info("Normalizing messages")
    logger.info(f"Fields file: {fields_file}")
    logger.info(f"Output file: {output_file}")

    # Configure template miner
    template_miner = configure_template_miner()

    # Dictionary to store document IDs for each template
    pattern_doc_references: Dict[str, List[str]] = {}  # Changed from List[dict] to List[str]

    try:
        # Process the input file
        with Path(fields_file).open("r") as f:
            line_count = 0
            for line in f:
                line = line.strip()
                if not line:
                    continue

                try:
                    # Parse the JSON line
                    doc = json.loads(line)
                    if _process_document(doc, template_miner, pattern_doc_references):
                        line_count += 1
                        if line_count % 1000 == 0:
                            logger.info(f"Processed {line_count} messages")
                except json.JSONDecodeError:
                    logger.warning(f"Invalid JSON line: {line}")
                    continue
                except Exception as e:
                    logger.warning(f"Error processing message: {e}")
                    continue

        logger.info(f"Processed {line_count} messages in total")
        logger.info(f"Found {len(template_miner.drain.clusters)} unique patterns")

        # Prepare results
        results = _prepare_results(template_miner, pattern_doc_references)

        # Save results to output file
        save_json({"patterns": results}, output_file)
        logger.info(f"Normalization results saved to {output_file}")

    except FileNotFoundError:
        logger.error(f"Fields file not found: {fields_file}")
        raise
    except Exception as e:
        logger.error(f"Error normalizing messages: {e}")
        raise


def main() -> None:
    """Parse command line arguments and normalize messages."""
    parser = argparse.ArgumentParser(description="Normalize messages and summarize them")
    parser.add_argument("--fields-file", required=True, help="Path to the extracted fields file")
    parser.add_argument(
        "--output-file", required=True, help="Path to store the normalization results"
    )

    args = parser.parse_args()

    try:
        normalize_messages(args.fields_file, args.output_file)
    except Exception as e:
        logger.error(f"Error normalizing messages: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
