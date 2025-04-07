#!/usr/bin/env python3
"""Prepare environment for a process run."""

import argparse
import os
import sys
import tempfile
from pathlib import Path

from platform_problem_monitoring_core.utils import ensure_dir_exists, logger


def prepare_environment() -> str:
    """
    Prepare environment for a process run.

    Creates a temporary work directory for storing intermediate files.

    Returns:
        Path to the temporary work folder

    Raises:
        PermissionError: If unable to create or write to the temporary directory
        OSError: If any other OS-level error occurs
    """
    logger.info("Preparing environment for process run")

    try:
        # Create temporary work directory
        work_dir = tempfile.mkdtemp(prefix="platform_problem_monitoring_")
        logger.info(f"Created temporary work directory: {work_dir}")

        # Check if directory exists and is writable
        work_path = Path(work_dir)
        if not work_path.exists():
            error_msg = f"Failed to create temporary directory: {work_dir}"
            raise FileNotFoundError(error_msg)

        if not os.access(work_dir, os.W_OK):
            error_msg = f"No write access to temporary directory: {work_dir}"
            raise PermissionError(error_msg)

        # Create any additional subdirectories if needed
        # This isn't strictly necessary but helps demonstrate the directory is writable
        test_subdir = work_path / "test"
        ensure_dir_exists(str(test_subdir))
        test_subdir.rmdir()  # Clean up the test directory

        logger.info("Environment preparation complete")
        return work_dir
    except (OSError, PermissionError) as e:
        logger.error(f"Failed to prepare environment: {str(e)}")
        raise


def main() -> None:
    """Execute the script when run directly."""
    parser = argparse.ArgumentParser(description="Prepare environment for a process run")
    # Parse arguments but don't assign to a variable since we don't use them
    parser.parse_args()

    try:
        work_dir = prepare_environment()
        # Print the work directory path for the next step to use
        print(work_dir)
        sys.exit(0)
    except Exception as e:
        logger.error(f"Error preparing environment: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
