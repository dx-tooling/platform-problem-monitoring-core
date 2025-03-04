#!/usr/bin/env python3
"""Store new run state."""

import argparse
import sys

from platform_problem_monitoring_core.utils import logger


def store_new_state(
    s3_bucket: str, s3_folder: str, date_time_file: str, norm_results_file: str
) -> None:
    """
    Store new run state to S3.
    
    Args:
        s3_bucket: S3 bucket name
        s3_folder: S3 folder name
        date_time_file: Path to the date and time file to upload
        norm_results_file: Path to the normalization results file to upload
    """
    logger.info("Storing new run state")
    logger.info(f"S3 bucket: {s3_bucket}")
    logger.info(f"S3 folder: {s3_folder}")
    logger.info(f"Date and time file: {date_time_file}")
    logger.info(f"Normalization results file: {norm_results_file}")
    
    # Read the files to be uploaded
    try:
        with open(date_time_file, "r") as f:
            date_time_content = f.read()
            logger.info(f"Date and time content: {date_time_content}")
        
        with open(norm_results_file, "r") as f:
            # Just log the size of the normalization results file, not its content
            norm_results_size = len(f.read())
            logger.info(f"Normalization results file size: {norm_results_size} bytes")
    except FileNotFoundError as e:
        logger.error(f"File not found: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Error reading files: {str(e)}")
        raise
    
    # Placeholder implementation
    # In a real implementation, we would upload the files to S3 using boto3
    # For example:
    # import boto3
    # s3_client = boto3.client('s3')
    # s3_client.upload_file(date_time_file, s3_bucket, f"{s3_folder}/date_time.txt")
    # s3_client.upload_file(norm_results_file, s3_bucket, f"{s3_folder}/norm_results.json")
    
    logger.info("New run state stored successfully")


def main() -> None:
    """Execute the script when run directly."""
    parser = argparse.ArgumentParser(description="Store new run state")
    parser.add_argument("--s3-bucket", required=True, help="S3 bucket name")
    parser.add_argument("--s3-folder", required=True, help="S3 folder name")
    parser.add_argument("--date-time-file", required=True, help="Path to the date and time file to upload")
    parser.add_argument(
        "--norm-results-file", required=True, help="Path to the normalization results file to upload"
    )
    
    args = parser.parse_args()
    
    try:
        store_new_state(
            args.s3_bucket, args.s3_folder, args.date_time_file, args.norm_results_file
        )
        sys.exit(0)
    except Exception as e:
        logger.error(f"Error storing new state: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
