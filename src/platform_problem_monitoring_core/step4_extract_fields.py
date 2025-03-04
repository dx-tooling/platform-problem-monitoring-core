#!/usr/bin/env python3
"""Extract relevant fields from logstash documents."""

import argparse
import json
import sys

from platform_problem_monitoring_core.utils import logger, load_json


def extract_fields(logstash_file: str, output_file: str) -> None:
    """
    Extract relevant fields from logstash documents.
    
    Args:
        logstash_file: Path to the logstash documents file
        output_file: Path to store the extracted fields
    """
    logger.info("Extracting fields from logstash documents")
    logger.info(f"Logstash file: {logstash_file}")
    logger.info(f"Output file: {output_file}")
    
    # Load the logstash documents
    docs = load_json(logstash_file)
    logger.info(f"Loaded {len(docs)} documents")
    
    # Extract the fields
    extracted = []
    for doc in docs:
        index = doc.get("_index", "")
        doc_id = doc.get("_id", "")
        message = doc.get("_source", {}).get("message", "")
        
        if message:
            extracted.append(f"{index}|{doc_id}|{message}")
    
    # Write the extracted fields to the output file
    with open(output_file, "w") as f:
        for line in extracted:
            f.write(f"{line}\n")
    
    logger.info(f"Extracted fields from {len(extracted)} documents")
    logger.info("Fields extracted successfully")


def main() -> None:
    """Execute the script when run directly."""
    parser = argparse.ArgumentParser(description="Extract fields from logstash documents")
    parser.add_argument("--logstash-file", required=True, help="Path to the logstash documents file")
    parser.add_argument("--output-file", required=True, help="Path to store the extracted fields")
    
    args = parser.parse_args()
    
    try:
        extract_fields(args.logstash_file, args.output_file)
        sys.exit(0)
    except Exception as e:
        logger.error(f"Error extracting fields: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
