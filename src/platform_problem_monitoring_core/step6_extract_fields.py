#!/usr/bin/env python3
"""Extract relevant fields from logstash documents."""

import argparse
import json
import sys
from pathlib import Path

from platform_problem_monitoring_core.utils import load_json, logger


def extract_fields(logstash_file: str, output_file: str) -> None:
    """
    Extract relevant fields from logstash documents.

    Args:
        logstash_file: Path to the logstash documents file
        output_file: Path to store the extracted fields

    Raises:
        FileNotFoundError: If the logstash file doesn't exist
        json.JSONDecodeError: If the file contains invalid JSON
        OSError: If the output cannot be written
    """
    logger.info("Extracting fields from logstash documents")
    logger.info(f"Logstash file: {logstash_file}")
    logger.info(f"Output file: {output_file}")

    # Load logstash documents
    documents = load_json(logstash_file)
    logger.info(f"Loaded {len(documents)} logstash documents")

    # Ensure the output directory exists
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Process the documents and write them to the output file
    processed_count = 0
    skipped_count = 0

    try:
        # Open output file for writing
        with Path(output_file).open("w") as f:
            # Process each document
            for doc in documents:
                try:
                    # Extract required fields: index name, document id, and message
                    index_name = doc.get("_index", "unknown")
                    doc_id = doc.get("_id", "unknown")

                    # Extract message from _source
                    source = doc.get("_source", {})
                    message = source.get("message", "")

                    if not message:
                        skipped_count += 1
                        continue

                    # Write extracted fields to output file as JSON
                    extracted = {"index": index_name, "id": doc_id, "message": message}
                    f.write(json.dumps(extracted) + "\n")
                    processed_count += 1

                    # Log progress for large document sets
                    if processed_count % 10000 == 0:
                        logger.info(f"Processed {processed_count} documents so far")
                except (KeyError, TypeError) as e:
                    skipped_count += 1
                    logger.warning(f"Error processing document: {e}")
                    continue
                except Exception as e:
                    logger.warning(f"Unexpected error processing document: {e}")
                    skipped_count += 1
                    continue

        logger.info(f"Extracted fields from {processed_count} documents")
        if skipped_count > 0:
            logger.warning(f"Skipped {skipped_count} documents due to errors or missing fields")
    except OSError as e:
        logger.error(f"Error writing to output file: {e}")
        error_msg = f"Failed to write to output file {output_file}: {e}"
        raise OSError(error_msg) from e

    logger.info("Field extraction completed")


def main() -> None:
    """Parse command line arguments and extract fields from logstash documents."""
    parser = argparse.ArgumentParser(description="Extract fields from logstash documents")
    parser.add_argument("--logstash-file", required=True, help="Path to the logstash documents file")
    parser.add_argument("--output-file", required=True, help="Path to store the extracted fields")

    args = parser.parse_args()

    try:
        extract_fields(args.logstash_file, args.output_file)
        sys.exit(0)
    except Exception as e:
        logger.error(f"Error extracting fields: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
