#!/usr/bin/env python3
"""Store new state to S3."""

import argparse
import sys
from pathlib import Path

import boto3
from botocore.exceptions import ClientError

from platform_problem_monitoring_core.utils import logger


def store_new_state(s3_bucket: str, s3_folder: str, date_time_file: str, norm_results_file: str) -> None:
    """
    Store new state to S3.

    Args:
        s3_bucket: S3 bucket name
        s3_folder: S3 folder name
        date_time_file: Path to the date and time file to upload
        norm_results_file: Path to the normalization results file to upload
    """
    logger.info("Storing new state")
    logger.info(f"S3 bucket: {s3_bucket}")
    logger.info(f"S3 folder: {s3_folder}")
    logger.info(f"Date time file: {date_time_file}")
    logger.info(f"Normalization results file: {norm_results_file}")

    # Check if files exist
    if not Path(date_time_file).exists():
        error_msg = f"Date time file not found: {date_time_file}"
        logger.error(error_msg)
        raise FileNotFoundError(error_msg)

    if not Path(norm_results_file).exists():
        error_msg = f"Normalization results file not found: {norm_results_file}"
        logger.error(error_msg)
        raise FileNotFoundError(error_msg)

    # Create S3 client
    s3_client = boto3.client("s3")

    # Upload date time file
    date_time_key = f"{s3_folder}/current_date_time.txt"
    try:
        logger.info(f"Uploading date time file to s3://{s3_bucket}/{date_time_key}")
        s3_client.upload_file(date_time_file, s3_bucket, date_time_key)
        logger.info("Date time file uploaded successfully")
    except ClientError as e:
        logger.error(f"Failed to upload date time file: {e}")
        raise

    # Upload normalization results file
    norm_results_key = f"{s3_folder}/norm_results.json"
    try:
        logger.info(f"Uploading normalization results to s3://{s3_bucket}/{norm_results_key}")
        s3_client.upload_file(norm_results_file, s3_bucket, norm_results_key)
        logger.info("Normalization results uploaded successfully")
    except ClientError as e:
        logger.error(f"Failed to upload normalization results: {e}")
        raise

    logger.info("New state stored successfully")


def main() -> None:
    """Parse command line arguments and store new state."""
    parser = argparse.ArgumentParser(description="Store new state to S3")
    parser.add_argument("--s3-bucket", required=True, help="S3 bucket name")
    parser.add_argument("--s3-folder", required=True, help="S3 folder name")
    parser.add_argument("--date-time-file", required=True, help="Path to the date and time file to upload")
    parser.add_argument(
        "--norm-results-file",
        required=True,
        help="Path to the normalization results file to upload",
    )

    args = parser.parse_args()

    try:
        store_new_state(args.s3_bucket, args.s3_folder, args.date_time_file, args.norm_results_file)
    except Exception as e:
        logger.error(f"Error storing new state: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
