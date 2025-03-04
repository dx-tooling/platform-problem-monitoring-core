#!/usr/bin/env python3
"""Compare normalization results between current and previous runs."""

import argparse
import json
import sys
from typing import Dict, List, Any, Tuple

from platform_problem_monitoring_core.utils import logger, load_json, save_json


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
        
        # Create dictionaries for easier comparison
        current_dict = {pattern["pattern"]: pattern for pattern in current_patterns}
        previous_dict = {pattern["pattern"]: pattern for pattern in previous_patterns}
        
        # Find new patterns (in current but not in previous)
        new_patterns = []
        for pattern, data in current_dict.items():
            if pattern not in previous_dict:
                new_patterns.append({
                    "pattern": pattern,
                    "count": data["count"],
                    "sample_doc_references": data.get("sample_doc_references", [])
                })
        
        # Sort new patterns by count (descending)
        new_patterns.sort(key=lambda x: x["count"], reverse=True)
        logger.info(f"New patterns: {len(new_patterns)}")
        
        # Find disappeared patterns (in previous but not in current)
        disappeared_patterns = []
        for pattern, data in previous_dict.items():
            if pattern not in current_dict:
                disappeared_patterns.append({
                    "pattern": pattern,
                    "count": data["count"],
                    "sample_doc_references": data.get("sample_doc_references", [])
                })
        
        # Sort disappeared patterns by count (descending)
        disappeared_patterns.sort(key=lambda x: x["count"], reverse=True)
        logger.info(f"Disappeared patterns: {len(disappeared_patterns)}")
        
        # Find patterns with increased counts
        increased_patterns = []
        for pattern, current_data in current_dict.items():
            if pattern in previous_dict:
                current_count = current_data["count"]
                previous_count = previous_dict[pattern]["count"]
                
                if current_count > previous_count:
                    percent_increase = ((current_count - previous_count) / previous_count) * 100
                    increased_patterns.append({
                        "pattern": pattern,
                        "current_count": current_count,
                        "previous_count": previous_count,
                        "absolute_change": current_count - previous_count,
                        "percent_change": percent_increase,
                        "sample_doc_references": current_data.get("sample_doc_references", [])
                    })
        
        # Sort increased patterns by percent change (descending)
        increased_patterns.sort(key=lambda x: x["percent_change"], reverse=True)
        logger.info(f"Increased patterns: {len(increased_patterns)}")
        
        # Find patterns with decreased counts
        decreased_patterns = []
        for pattern, current_data in current_dict.items():
            if pattern in previous_dict:
                current_count = current_data["count"]
                previous_count = previous_dict[pattern]["count"]
                
                if current_count < previous_count:
                    percent_decrease = ((previous_count - current_count) / previous_count) * 100
                    decreased_patterns.append({
                        "pattern": pattern,
                        "current_count": current_count,
                        "previous_count": previous_count,
                        "absolute_change": previous_count - current_count,
                        "percent_change": percent_decrease,
                        "sample_doc_references": current_data.get("sample_doc_references", [])
                    })
        
        # Sort decreased patterns by percent change (descending)
        decreased_patterns.sort(key=lambda x: x["percent_change"], reverse=True)
        logger.info(f"Decreased patterns: {len(decreased_patterns)}")
        
        # Prepare comparison results
        comparison_results = {
            "current_patterns_count": len(current_patterns),
            "previous_patterns_count": len(previous_patterns),
            "new_patterns": new_patterns,
            "disappeared_patterns": disappeared_patterns,
            "increased_patterns": increased_patterns,
            "decreased_patterns": decreased_patterns
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
    parser.add_argument(
        "--current-file", required=True, help="Path to the current normalization results file"
    )
    parser.add_argument(
        "--previous-file", required=True, help="Path to the previous normalization results file"
    )
    parser.add_argument(
        "--output-file", required=True, help="Path to store the comparison results"
    )
    
    args = parser.parse_args()
    
    try:
        compare_normalizations(args.current_file, args.previous_file, args.output_file)
    except Exception as e:
        logger.error(f"Error comparing normalization results: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
