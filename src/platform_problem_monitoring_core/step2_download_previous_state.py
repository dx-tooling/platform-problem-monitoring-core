#!/usr/bin/env python3
"""Download previous state from S3."""

import argparse
import datetime
import sys
from datetime import timezone
from pathlib import Path

import boto3
from botocore.exceptions import ClientError, NoCredentialsError

from platform_problem_monitoring_core.utils import logger, save_json


def _create_fallback_date_time_file(date_time_path: Path) -> None:
    """
    Create a fallback date time file with timestamp from 24 hours ago.

    Args:
        date_time_path: Path where to create the file

    Raises:
        OSError: If unable to write to the file
    """
    now = datetime.datetime.now(timezone.utc)
    yesterday = now - datetime.timedelta(days=1)

    try:
        with date_time_path.open("w") as f:
            f.write(yesterday.isoformat())
        logger.info(f"Created fallback date time file at {date_time_path}")
    except OSError as write_error:
        error_msg = f"Failed to create fallback date time file: {write_error}"
        logger.error(error_msg)
        raise OSError(error_msg) from write_error


def _create_empty_norm_results_file(norm_results_path: Path) -> None:
    """
    Create an empty normalization results file.

    Args:
        norm_results_path: Path where to create the file

    Raises:
        OSError: If unable to write to the file
    """
    try:
        save_json({}, str(norm_results_path))
        logger.info(f"Created empty normalization results file at {norm_results_path}")
    except OSError as write_error:
        error_msg = f"Failed to create empty normalization results file: {write_error}"
        logger.error(error_msg)
        raise OSError(error_msg) from write_error


def download_previous_state(s3_bucket: str, s3_folder: str, date_time_file: str, norm_results_file: str) -> None:
    """
    Download previous state from S3.

    Args:
        s3_bucket: S3 bucket name
        s3_folder: S3 folder name
        date_time_file: Path to store the start date and time
        norm_results_file: Path to store the previous normalization results

    Raises:
        NoCredentialsError: If AWS credentials are not found
        ClientError: If any AWS S3 operation fails
        OSError: If any file operation fails
    """
    logger.info("Downloading previous state")
    logger.info(f"S3 bucket: {s3_bucket}")
    logger.info(f"S3 folder: {s3_folder}")

    # Ensure parent directories exist
    date_time_path = Path(date_time_file)
    norm_results_path = Path(norm_results_file)

    date_time_path.parent.mkdir(parents=True, exist_ok=True)
    norm_results_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        # Create S3 client
        s3_client = boto3.client("s3")

        # Test connection to S3
        s3_client.head_bucket(Bucket=s3_bucket)
        logger.info(f"Successfully connected to S3 bucket: {s3_bucket}")

        # Download date time file
        date_time_key = f"{s3_folder}/current_date_time.txt"
        try:
            logger.info(f"Downloading date time file from s3://{s3_bucket}/{date_time_key}")
            s3_client.download_file(s3_bucket, date_time_key, date_time_file)
            logger.info(f"Date time file downloaded to {date_time_file}")
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            if error_code == "404" or error_code == "NoSuchKey":
                logger.warning(f"Date time file not found in S3: {date_time_key}")
            else:
                logger.warning(f"Failed to download date time file: {e}")

            logger.info("Using fallback: 24 hours ago")
            _create_fallback_date_time_file(date_time_path)

        # Download normalization results file
        norm_results_key = f"{s3_folder}/norm_results.json"
        try:
            logger.info(f"Downloading normalization results from s3://{s3_bucket}/{norm_results_key}")
            s3_client.download_file(s3_bucket, norm_results_key, norm_results_file)
            logger.info(f"Normalization results downloaded to {norm_results_file}")
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            if error_code == "404" or error_code == "NoSuchKey":
                logger.warning(f"Normalization results file not found in S3: {norm_results_key}")
            else:
                logger.warning(f"Failed to download normalization results: {e}")

            logger.info("Creating empty normalization results file")
            _create_empty_norm_results_file(norm_results_path)

    except NoCredentialsError as e:
        logger.error(f"AWS credentials not found: {e}")
        raise
    except ClientError as e:
        if e.response.get("Error", {}).get("Code") == "NoSuchBucket":
            logger.error(f"S3 bucket not found: {s3_bucket}")
        else:
            logger.error(f"AWS S3 error: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise

    logger.info("Previous state download completed")


def main() -> None:
    """Parse command line arguments and download previous state."""
    parser = argparse.ArgumentParser(description="Download previous state from S3")
    parser.add_argument("--s3-bucket", required=True, help="S3 bucket name")
    parser.add_argument("--s3-folder", required=True, help="S3 folder name")
    parser.add_argument("--date-time-file", required=True, help="Path to store the start date and time")
    parser.add_argument(
        "--norm-results-file",
        required=True,
        help="Path to store the previous normalization results",
    )

    args = parser.parse_args()

    try:
        download_previous_state(args.s3_bucket, args.s3_folder, args.date_time_file, args.norm_results_file)
        sys.exit(0)
    except Exception as e:
        logger.error(f"Error downloading previous state: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
