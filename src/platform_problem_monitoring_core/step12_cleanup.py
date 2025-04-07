#!/usr/bin/env python3
"""Clean up work environment."""

import argparse
import logging
import os
import shutil
import sys
from pathlib import Path
from typing import List

from platform_problem_monitoring_core.utils import logger


def _verify_safe_path(work_dir: Path) -> None:
    """
    Verify that the path is safe to remove.

    Args:
        work_dir: Path to verify

    Raises:
        ValueError: If the path is not a directory, doesn't exist, or doesn't look like a temporary work directory
    """
    # Check if the directory exists
    if not work_dir.exists():
        error_msg = f"Directory does not exist: {work_dir}"
        raise ValueError(error_msg)

    # Check if the path is a directory
    if not work_dir.is_dir():
        error_msg = f"Path is not a directory: {work_dir}"
        raise ValueError(error_msg)

    # Verify that the directory looks like a temporary work directory
    # This is a safety check to avoid accidentally deleting important directories
    if not work_dir.name.startswith("platform_problem_monitoring_"):
        error_msg = f"Directory does not appear to be a temporary work directory: {work_dir}"
        raise ValueError(error_msg)


def _list_remaining_files(work_dir: Path) -> List[str]:
    """
    List files remaining in the directory.

    Args:
        work_dir: Path to the directory

    Returns:
        List of files found in the directory
    """
    files = []
    try:
        for root, _dirs, filenames in os.walk(work_dir):
            for filename in filenames:
                file_path = Path(root) / filename
                files.append(str(file_path.relative_to(work_dir)))
        return files
    except (OSError, ValueError) as e:
        logger.warning(f"Error listing files in {work_dir}: {e}")
        return []


def cleanup_environment(work_dir: str) -> None:
    """
    Clean up the work environment by removing the temporary work directory.

    Args:
        work_dir: Path to the temporary work folder to remove

    Raises:
        ValueError: If the path is not suitable for removal
        OSError: If there's an error removing the directory
    """
    logger.info("Cleaning up work environment")
    logger.info(f"Removing temporary work directory: {work_dir}")

    # Convert to Path object
    work_path = Path(work_dir)

    try:
        # Check if the path is safe to remove
        _verify_safe_path(work_path)

        # Optional: List files before deletion (for debugging if needed)
        if logger.isEnabledFor(logging.DEBUG):
            files = _list_remaining_files(work_path)
            if files:
                logger.debug(f"Files to be removed: {', '.join(files)}")

        # Remove the directory and all its contents
        shutil.rmtree(work_dir)
        logger.info(f"Successfully removed directory: {work_dir}")

    except ValueError as e:
        # Non-fatal errors (directory doesn't exist or isn't a temp directory)
        logger.warning(f"Skipping cleanup: {str(e)}")
    except OSError as e:
        error_msg = f"Error removing directory {work_dir}: {str(e)}"
        logger.error(error_msg)
        raise OSError(error_msg) from e

    logger.info("Cleanup complete")


def main() -> None:
    """Execute the script when run directly."""
    parser = argparse.ArgumentParser(description="Clean up work environment")
    parser.add_argument("--work-dir", required=True, help="Path to the temporary work folder to remove")

    args = parser.parse_args()

    try:
        cleanup_environment(args.work_dir)
        sys.exit(0)
    except Exception as e:
        logger.error(f"Error cleaning up environment: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
