#!/usr/bin/env python3
"""Download previous state from S3."""

import argparse
import datetime
import sys
from pathlib import Path

import boto3
from botocore.exceptions import ClientError

from platform_problem_monitoring_core.utils import logger, save_json


def download_previous_state(
    s3_bucket: str, s3_folder: str, date_time_file: str, norm_results_file: str
) -> None:
    """
    Download previous state from S3.
    
    Args:
        s3_bucket: S3 bucket name
        s3_folder: S3 folder name
        date_time_file: Path to store the start date and time
        norm_results_file: Path to store the previous normalization results
    """
    logger.info("Downloading previous state")
    logger.info(f"S3 bucket: {s3_bucket}")
    logger.info(f"S3 folder: {s3_folder}")
    
    # Create S3 client
    s3_client = boto3.client('s3')
    
    # Download date time file
    date_time_key = f"{s3_folder}/current_date_time.txt"
    try:
        logger.info(f"Downloading date time file from s3://{s3_bucket}/{date_time_key}")
        s3_client.download_file(s3_bucket, date_time_key, date_time_file)
        logger.info(f"Date time file downloaded to {date_time_file}")
    except ClientError as e:
        logger.warning(f"Failed to download date time file: {e}")
        logger.info("Using fallback: 24 hours ago")
        # Set default to 24 hours ago
        now = datetime.datetime.now(datetime.UTC)
        yesterday = now - datetime.timedelta(days=1)
        with Path(date_time_file).open('w') as f:
            f.write(yesterday.isoformat())
        logger.info(f"Created fallback date time file at {date_time_file}")
    
    # Download normalization results file
    norm_results_key = f"{s3_folder}/norm_results.json"
    try:
        logger.info(f"Downloading normalization results from s3://{s3_bucket}/{norm_results_key}")
        s3_client.download_file(s3_bucket, norm_results_key, norm_results_file)
        logger.info(f"Normalization results downloaded to {norm_results_file}")
    except ClientError as e:
        logger.warning(f"Failed to download normalization results: {e}")
        logger.info("Creating empty normalization results file")
        # Create empty normalization results file
        save_json({}, norm_results_file)
        logger.info(f"Created empty normalization results file at {norm_results_file}")
    
    logger.info("Previous state download completed")


def main() -> None:
    """Parse command line arguments and download previous state."""
    parser = argparse.ArgumentParser(description="Download previous state from S3")
    parser.add_argument(
        "--s3-bucket", required=True, help="S3 bucket name"
    )
    parser.add_argument(
        "--s3-folder", required=True, help="S3 folder name"
    )
    parser.add_argument(
        "--date-time-file", required=True, help="Path to store the start date and time"
    )
    parser.add_argument(
        "--norm-results-file", required=True, help="Path to store the previous normalization results"
    )
    
    args = parser.parse_args()
    
    try:
        download_previous_state(
            args.s3_bucket,
            args.s3_folder,
            args.date_time_file,
            args.norm_results_file
        )
    except Exception as e:
        logger.error(f"Error downloading previous state: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
