#!/usr/bin/env python3
"""Extract relevant fields from logstash documents."""

import argparse
import json
import sys
from typing import Dict, List, Any

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
    
    try:
        # Load logstash documents
        documents = load_json(logstash_file)
        logger.info(f"Loaded {len(documents)} logstash documents")
        
        # Open output file for writing
        with open(output_file, "w") as f:
            # Process each document
            processed_count = 0
            for doc in documents:
                try:
                    # Extract required fields: index name, document id, and message
                    index_name = doc.get("_index", "unknown")
                    doc_id = doc.get("_id", "unknown")
                    
                    # Extract message from _source
                    source = doc.get("_source", {})
                    message = source.get("message", "")
                    
                    if message:
                        # Write extracted fields to output file as JSON
                        extracted = {
                            "index": index_name,
                            "id": doc_id,
                            "message": message
                        }
                        f.write(json.dumps(extracted) + "\n")
                        processed_count += 1
                except Exception as e:
                    logger.warning(f"Error processing document: {e}")
                    continue
            
            logger.info(f"Extracted fields from {processed_count} documents")
    except FileNotFoundError:
        logger.error(f"Logstash file not found: {logstash_file}")
        raise
    except json.JSONDecodeError:
        logger.error(f"Invalid JSON in logstash file: {logstash_file}")
        raise
    except Exception as e:
        logger.error(f"Error extracting fields: {e}")
        raise
    
    logger.info("Field extraction completed")


def main() -> None:
    """Parse command line arguments and extract fields from logstash documents."""
    parser = argparse.ArgumentParser(description="Extract fields from logstash documents")
    parser.add_argument(
        "--logstash-file", required=True, help="Path to the logstash documents file"
    )
    parser.add_argument(
        "--output-file", required=True, help="Path to store the extracted fields"
    )
    
    args = parser.parse_args()
    
    try:
        extract_fields(args.logstash_file, args.output_file)
    except Exception as e:
        logger.error(f"Error extracting fields: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
