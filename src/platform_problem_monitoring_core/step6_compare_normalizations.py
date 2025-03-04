#!/usr/bin/env python3
"""Compare normalization results."""

import argparse
import json
import sys

from platform_problem_monitoring_core.utils import logger, load_json


def compare_normalizations(current_file: str, previous_file: str, output_file: str) -> None:
    """
    Compare current and previous normalization results.
    
    Args:
        current_file: Path to the current normalization results file
        previous_file: Path to the previous normalization results file
        output_file: Path to store the comparison results
    """
    logger.info("Comparing normalization results")
    logger.info(f"Current file: {current_file}")
    logger.info(f"Previous file: {previous_file}")
    logger.info(f"Output file: {output_file}")
    
    # Load the normalization results
    current_results = load_json(current_file)
    previous_results = load_json(previous_file)
    
    logger.info(f"Loaded {len(current_results)} current patterns")
    logger.info(f"Loaded {len(previous_results)} previous patterns")
    
    # Create dictionaries for easier comparison
    current_dict = {item["normalized_message"]: item["count"] for item in current_results}
    previous_dict = {item["normalized_message"]: item["count"] for item in previous_results}
    
    # Find new patterns
    new_patterns = []
    for message, count in current_dict.items():
        if message not in previous_dict:
            new_patterns.append({
                "normalized_message": message,
                "count": count,
                # Find the examples from the current results
                "examples": next((item["examples"] for item in current_results if item["normalized_message"] == message), [])
            })
    
    # Sort by count (descending)
    new_patterns.sort(key=lambda x: x["count"], reverse=True)
    
    # Find disappeared patterns
    disappeared_patterns = []
    for message, count in previous_dict.items():
        if message not in current_dict:
            disappeared_patterns.append({
                "normalized_message": message,
                "count": count,
                # No examples for disappeared patterns
                "examples": []
            })
    
    # Sort by count (descending)
    disappeared_patterns.sort(key=lambda x: x["count"], reverse=True)
    
    # Find increased patterns
    increased_patterns = []
    for message, count in current_dict.items():
        if message in previous_dict and count > previous_dict[message]:
            increased_patterns.append({
                "normalized_message": message,
                "current_count": count,
                "previous_count": previous_dict[message],
                "difference": count - previous_dict[message],
                "percentage_change": (count - previous_dict[message]) / previous_dict[message] * 100,
                "examples": next((item["examples"] for item in current_results if item["normalized_message"] == message), [])
            })
    
    # Sort by percentage change (descending)
    increased_patterns.sort(key=lambda x: x["percentage_change"], reverse=True)
    
    # Find decreased patterns
    decreased_patterns = []
    for message, count in current_dict.items():
        if message in previous_dict and count < previous_dict[message]:
            decreased_patterns.append({
                "normalized_message": message,
                "current_count": count,
                "previous_count": previous_dict[message],
                "difference": previous_dict[message] - count,
                "percentage_change": (count - previous_dict[message]) / previous_dict[message] * 100,
                "examples": next((item["examples"] for item in current_results if item["normalized_message"] == message), [])
            })
    
    # Sort by percentage change (ascending)
    decreased_patterns.sort(key=lambda x: x["percentage_change"])
    
    # Prepare the comparison results
    comparison_results = {
        "new_patterns": new_patterns,
        "disappeared_patterns": disappeared_patterns,
        "increased_patterns": increased_patterns,
        "decreased_patterns": decreased_patterns,
        "current_pattern_count": len(current_results),
        "previous_pattern_count": len(previous_results)
    }
    
    # Write the comparison results to the output file
    with open(output_file, "w") as f:
        json.dump(comparison_results, f, indent=2)
    
    logger.info(f"Found {len(new_patterns)} new patterns")
    logger.info(f"Found {len(disappeared_patterns)} disappeared patterns")
    logger.info(f"Found {len(increased_patterns)} increased patterns")
    logger.info(f"Found {len(decreased_patterns)} decreased patterns")
    logger.info("Comparison completed successfully")


def main() -> None:
    """Execute the script when run directly."""
    parser = argparse.ArgumentParser(description="Compare normalization results")
    parser.add_argument("--current-file", required=True, help="Path to the current normalization results file")
    parser.add_argument("--previous-file", required=True, help="Path to the previous normalization results file")
    parser.add_argument("--output-file", required=True, help="Path to store the comparison results")
    
    args = parser.parse_args()
    
    try:
        compare_normalizations(args.current_file, args.previous_file, args.output_file)
        sys.exit(0)
    except Exception as e:
        logger.error(f"Error comparing normalizations: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
