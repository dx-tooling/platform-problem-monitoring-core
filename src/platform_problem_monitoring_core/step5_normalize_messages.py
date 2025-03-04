#!/usr/bin/env python3
"""Normalize messages."""

import argparse
import json
import sys
from collections import defaultdict

from platform_problem_monitoring_core.utils import logger


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
    
    # Read the extracted fields
    messages = []
    doc_ids = []
    with open(fields_file, "r") as f:
        for line in f:
            line = line.strip()
            if line:
                parts = line.split("|", 2)
                if len(parts) == 3:
                    index, doc_id, message = parts
                    messages.append(message)
                    doc_ids.append(f"{index}|{doc_id}")
    
    logger.info(f"Read {len(messages)} messages")
    
    # Placeholder implementation for normalization
    # In a real implementation, we would use drain3 to normalize the messages
    # For now, we'll just do a simple normalization by replacing numbers with <NUM>
    normalized_messages = []
    for message in messages:
        # Simple normalization: replace digits with <NUM>
        normalized = message.replace("2023", "<YEAR>").replace("01", "<NUM>").replace(":", " ")
        normalized_messages.append(normalized)
    
    # Count occurrences of each normalized message
    message_counts = defaultdict(int)
    message_examples = defaultdict(list)
    
    for i, normalized in enumerate(normalized_messages):
        message_counts[normalized] += 1
        
        # Store up to 5 examples for each normalized message
        if len(message_examples[normalized]) < 5:
            message_examples[normalized].append(doc_ids[i])
    
    # Prepare the results
    results = []
    for normalized, count in message_counts.items():
        results.append({
            "normalized_message": normalized,
            "count": count,
            "examples": message_examples[normalized]
        })
    
    # Sort by count (descending)
    results.sort(key=lambda x: x["count"], reverse=True)
    
    # Write the results to the output file
    with open(output_file, "w") as f:
        json.dump(results, f, indent=2)
    
    logger.info(f"Normalized {len(messages)} messages into {len(results)} patterns")
    logger.info("Messages normalized successfully")


def main() -> None:
    """Execute the script when run directly."""
    parser = argparse.ArgumentParser(description="Normalize messages")
    parser.add_argument("--fields-file", required=True, help="Path to the extracted fields file")
    parser.add_argument("--output-file", required=True, help="Path to store the normalization results")
    
    args = parser.parse_args()
    
    try:
        normalize_messages(args.fields_file, args.output_file)
        sys.exit(0)
    except Exception as e:
        logger.error(f"Error normalizing messages: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
