#!/usr/bin/env python3
"""Clean up work environment."""

import argparse
import shutil
import sys
from pathlib import Path

from platform_problem_monitoring_core.utils import logger


def cleanup_environment(work_dir: str) -> None:
    """
    Clean up the work environment by removing the temporary work directory.

    Args:
        work_dir: Path to the temporary work folder to remove
    """
    logger.info("Cleaning up work environment")
    logger.info(f"Removing temporary work directory: {work_dir}")

    # Convert to Path object
    work_path = Path(work_dir)

    # Check if the directory exists
    if not work_path.exists():
        logger.warning(f"Work directory does not exist: {work_dir}")
        return

    # Check if the path is a directory
    if not work_path.is_dir():
        error_msg = f"Path is not a directory: {work_dir}"
        logger.error(error_msg)
        raise ValueError(error_msg)

    # Verify that the directory looks like a temporary work directory
    # This is a safety check to avoid accidentally deleting important directories
    if not work_path.name.startswith("platform_problem_monitoring_"):
        error_msg = f"Directory does not appear to be a temporary work directory: {work_dir}"
        logger.error(error_msg)
        raise ValueError(error_msg)

    try:
        # Remove the directory and all its contents
        shutil.rmtree(work_dir)
        logger.info(f"Successfully removed directory: {work_dir}")
    except Exception as e:
        logger.error(f"Error removing directory {work_dir}: {str(e)}")
        raise

    logger.info("Cleanup complete")


def main() -> None:
    """Execute the script when run directly."""
    parser = argparse.ArgumentParser(description="Clean up work environment")
    parser.add_argument(
        "--work-dir", required=True, help="Path to the temporary work folder to remove"
    )

    args = parser.parse_args()

    try:
        cleanup_environment(args.work_dir)
        sys.exit(0)
    except Exception as e:
        logger.error(f"Error cleaning up environment: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
