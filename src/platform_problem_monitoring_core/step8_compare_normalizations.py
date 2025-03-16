#!/usr/bin/env python3
"""Compare normalization results between current and previous runs."""

import argparse
import json
import sys
from typing import List, NotRequired, TypedDict

from platform_problem_monitoring_core.utils import load_json, logger, save_json


class PatternDict(TypedDict):
    """Type for pattern dictionaries."""

    cluster_id: str
    count: int
    pattern: str
    first_seen: str
    last_seen: str
    sample_log_lines: List[str]
    sample_doc_references: List[str]
    # Fields required by step9_generate_email_bodies
    current_count: NotRequired[int]  # Current count (same as count for clarity)
    previous_count: NotRequired[int]  # Count from previous run
    absolute_change: NotRequired[int]  # Absolute difference between counts
    percent_change: NotRequired[float]  # Percentage difference


# Define a function to get the count safely with a proper return type
def get_count(pattern: PatternDict) -> int:
    """Safely get the count from a pattern dictionary.

    Args:
        pattern: The pattern dictionary.

    Returns:
        The count as an integer (defaults to 0 if missing).
    """
    return pattern["count"]


def _find_new_patterns(current_dict: dict, previous_dict: dict) -> List[PatternDict]:
    """
    Find patterns that are in the current data but not in the previous data.

    Args:
        current_dict: Dictionary containing the current normalization results.
        previous_dict: Dictionary containing the previous normalization results.

    Returns:
        List of new patterns that weren't in the previous data.
    """
    new_patterns: List[PatternDict] = []
    current_patterns = current_dict.get("patterns", [])
    previous_patterns = {p["pattern"]: p for p in previous_dict.get("patterns", [])}

    # Find patterns that are in current but not in previous
    for pattern in current_patterns:
        if pattern["pattern"] not in previous_patterns:
            # Ensure all required fields are present
            new_pattern: PatternDict = {
                "cluster_id": pattern["cluster_id"],
                "count": pattern["count"],
                "pattern": pattern["pattern"],
                "first_seen": pattern.get("first_seen", ""),
                "last_seen": pattern.get("last_seen", ""),
                "sample_log_lines": pattern.get("sample_log_lines", []),
                "sample_doc_references": pattern.get("sample_doc_references", []),
            }
            new_patterns.append(new_pattern)

    # Sort new patterns by count (descending)
    new_patterns.sort(key=get_count, reverse=True)
    return new_patterns


def _find_disappeared_patterns(current_dict: dict, previous_dict: dict) -> List[PatternDict]:
    """
    Find patterns that are in the previous data but not in the current data.

    Args:
        current_dict: Dictionary containing the current normalization results.
        previous_dict: Dictionary containing the previous normalization results.

    Returns:
        List of patterns that disappeared from previous to current data.
    """
    disappeared_patterns: List[PatternDict] = []
    current_patterns = {p["pattern"]: p for p in current_dict.get("patterns", [])}
    previous_patterns = previous_dict.get("patterns", [])

    # Extract the disappeared patterns
    for pattern in previous_patterns:
        if pattern["pattern"] not in current_patterns:
            # Ensure all required fields are present
            disappeared_pattern: PatternDict = {
                "cluster_id": pattern["cluster_id"],
                "count": pattern["count"],
                "pattern": pattern["pattern"],
                "first_seen": pattern.get("first_seen", ""),
                "last_seen": pattern.get("last_seen", ""),
                "sample_log_lines": pattern.get("sample_log_lines", []),
                "sample_doc_references": pattern.get("sample_doc_references", []),
            }
            disappeared_patterns.append(disappeared_pattern)

    # Sort disappeared patterns by count (descending)
    disappeared_patterns.sort(key=get_count, reverse=True)
    return disappeared_patterns


def _find_increased_patterns(current_dict: dict, previous_dict: dict) -> List[PatternDict]:
    """
    Find patterns that have increased in count from the previous data to the current data.

    Args:
        current_dict: Dictionary containing the current normalization results.
        previous_dict: Dictionary containing the previous normalization results.

    Returns:
        List of patterns with increased counts.
    """
    increased_patterns: List[PatternDict] = []

    # Build dictionaries for easier lookup
    current_patterns = {p["pattern"]: p for p in current_dict.get("patterns", [])}
    previous_patterns = {p["pattern"]: p for p in previous_dict.get("patterns", [])}

    # Find patterns with increased counts
    for pattern_text, current_pattern in current_patterns.items():
        if pattern_text in previous_patterns:
            previous_count = previous_patterns[pattern_text]["count"]
            current_count = current_pattern["count"]

            # Only include patterns with actual increases
            if current_count > previous_count:
                # Calculate absolute and percentage change
                absolute_change = current_count - previous_count
                percent_change = round((absolute_change / previous_count) * 100, 1) if previous_count > 0 else 100

                # Ensure all required fields are present
                increased_pattern: PatternDict = {
                    "cluster_id": current_pattern["cluster_id"],
                    "count": current_count,
                    "current_count": current_count,
                    "previous_count": previous_count,
                    "absolute_change": absolute_change,
                    "percent_change": percent_change,
                    "pattern": pattern_text,
                    "first_seen": current_pattern.get("first_seen", ""),
                    "last_seen": current_pattern.get("last_seen", ""),
                    "sample_log_lines": current_pattern.get("sample_log_lines", []),
                    "sample_doc_references": current_pattern.get("sample_doc_references", []),
                }
                increased_patterns.append(increased_pattern)

    # Sort by percent change (descending), then by absolute change for ties, then by count
    increased_patterns.sort(key=lambda p: (p["percent_change"], p["absolute_change"], p["count"]), reverse=True)
    return increased_patterns


def _find_decreased_patterns(current_dict: dict, previous_dict: dict) -> List[PatternDict]:
    """
    Find patterns that have decreased in count from the previous data to the current data.

    Args:
        current_dict: Dictionary containing the current normalization results.
        previous_dict: Dictionary containing the previous normalization results.

    Returns:
        List of patterns with decreased counts.
    """
    decreased_patterns: List[PatternDict] = []

    # Build dictionaries for easier lookup
    current_patterns = {p["pattern"]: p for p in current_dict.get("patterns", [])}
    previous_patterns = {p["pattern"]: p for p in previous_dict.get("patterns", [])}

    # Find patterns with decreased counts
    for pattern_text, current_pattern in current_patterns.items():
        if pattern_text in previous_patterns:
            previous_count = previous_patterns[pattern_text]["count"]
            current_count = current_pattern["count"]

            # Only include patterns with actual decreases
            if current_count < previous_count:
                # Calculate absolute and percentage change
                absolute_change = previous_count - current_count
                percent_change = round((absolute_change / previous_count) * 100, 1) if previous_count > 0 else 0

                # Ensure all required fields are present
                decreased_pattern: PatternDict = {
                    "cluster_id": current_pattern["cluster_id"],
                    "count": current_count,
                    "current_count": current_count,
                    "previous_count": previous_count,
                    "absolute_change": absolute_change,
                    "percent_change": percent_change,
                    "pattern": pattern_text,
                    "first_seen": current_pattern.get("first_seen", ""),
                    "last_seen": current_pattern.get("last_seen", ""),
                    "sample_log_lines": current_pattern.get("sample_log_lines", []),
                    "sample_doc_references": current_pattern.get("sample_doc_references", []),
                }
                decreased_patterns.append(decreased_pattern)

    # Sort by percent change (descending), then by absolute change for ties, then by count
    decreased_patterns.sort(key=lambda p: (p["percent_change"], p["absolute_change"], p["count"]), reverse=True)
    return decreased_patterns


def compare_normalizations(current_file: str, previous_file: str, output_file: str) -> None:
    """
    Compare normalization results between current and previous runs.

    Args:
        current_file: Path to the current normalization results file
        previous_file: Path to the previous normalization results file
        output_file: Path to store the comparison results
    """
    logger.info("Comparing normalization results")
    logger.info(f"Current file: {current_file}")
    logger.info(f"Previous file: {previous_file}")
    logger.info(f"Output file: {output_file}")

    try:
        # Load current and previous normalization results
        current_data = load_json(current_file)
        previous_data = load_json(previous_file)

        # Extract patterns from the loaded data
        current_patterns = current_data.get("patterns", [])
        previous_patterns = previous_data.get("patterns", [])

        logger.info(f"Current patterns: {len(current_patterns)}")
        logger.info(f"Previous patterns: {len(previous_patterns)}")

        # Find new patterns (in current but not in previous)
        new_patterns = _find_new_patterns({"patterns": current_patterns}, {"patterns": previous_patterns})
        logger.info(f"New patterns: {len(new_patterns)}")

        # Find disappeared patterns (in previous but not in current)
        disappeared_patterns = _find_disappeared_patterns(
            {"patterns": current_patterns}, {"patterns": previous_patterns}
        )
        logger.info(f"Disappeared patterns: {len(disappeared_patterns)}")

        # Find patterns with increased counts
        increased_patterns = _find_increased_patterns({"patterns": current_patterns}, {"patterns": previous_patterns})
        logger.info(f"Increased patterns: {len(increased_patterns)}")

        # Find patterns with decreased counts
        decreased_patterns = _find_decreased_patterns({"patterns": current_patterns}, {"patterns": previous_patterns})
        logger.info(f"Decreased patterns: {len(decreased_patterns)}")

        # Prepare comparison results
        comparison_results = {
            "current_patterns_count": len(current_patterns),
            "previous_patterns_count": len(previous_patterns),
            "new_patterns": new_patterns,
            "disappeared_patterns": disappeared_patterns,
            "increased_patterns": increased_patterns,
            "decreased_patterns": decreased_patterns,
        }

        # Save comparison results
        save_json(comparison_results, output_file)
        logger.info(f"Comparison results saved to {output_file}")

    except FileNotFoundError as e:
        logger.error(f"File not found: {e}")
        raise
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON: {e}")
        raise
    except Exception as e:
        logger.error(f"Error comparing normalization results: {e}")
        raise


def main() -> None:
    """Parse command line arguments and compare normalization results."""
    parser = argparse.ArgumentParser(description="Compare normalization results")
    parser.add_argument("--current-file", required=True, help="Path to the current normalization results file")
    parser.add_argument("--previous-file", required=True, help="Path to the previous normalization results file")
    parser.add_argument("--output-file", required=True, help="Path to store the comparison results")

    args = parser.parse_args()

    try:
        compare_normalizations(args.current_file, args.previous_file, args.output_file)
    except Exception as e:
        logger.error(f"Error comparing normalization results: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
