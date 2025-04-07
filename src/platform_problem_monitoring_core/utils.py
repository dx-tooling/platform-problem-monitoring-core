"""Utility functions for Platform Problem Monitoring Core."""

import configparser
import json
import logging
import sys
from logging import Logger
from pathlib import Path
from typing import Any, Dict


def setup_logger(name: str = "platform_problem_monitoring", level: int = logging.INFO) -> Logger:
    """
    Configure and return a logger instance.

    Args:
        name: The name for the logger
        level: The logging level

    Returns:
        Configured logger instance
    """
    logger_instance = logging.getLogger(name)

    # Only configure if handlers haven't been added already
    if not logger_instance.handlers:
        logger_instance.setLevel(level)
        formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)

        logger_instance.addHandler(console_handler)

    return logger_instance


# Create a default logger instance for backward compatibility
logger = setup_logger()


def load_config(config_file_path: str) -> Dict[str, str]:
    """
    Load configuration from a file.

    Args:
        config_file_path: Path to the configuration file

    Returns:
        Dictionary containing configuration values

    Raises:
        FileNotFoundError: If the configuration file doesn't exist
        ValueError: If the configuration file is invalid
    """
    config_path = Path(config_file_path)

    if not config_path.exists():
        error_msg = f"Configuration file not found: {config_file_path}"
        logger.error(error_msg)
        raise FileNotFoundError(error_msg)

    # For backwards compatibility check file format
    with config_path.open("r") as f:
        first_line = f.readline().strip()
        f.seek(0)  # Reset file pointer

        # If it's a standard KEY=VALUE format without sections
        if first_line and "=" in first_line and not first_line.startswith("["):
            return _parse_key_value_config(f)

        # Otherwise use configparser
        return _parse_ini_config(config_path)


def _parse_key_value_config(file_obj: Any) -> Dict[str, str]:
    """
    Parse a config file with KEY=VALUE format.

    Args:
        file_obj: File object to parse

    Returns:
        Dictionary of parsed configuration
    """
    config: Dict[str, str] = {}

    for line in file_obj:
        line = line.strip()
        if not line or line.startswith("#"):
            continue

        if "=" in line:
            key, value = line.split("=", 1)
            config[key.strip()] = value.strip().strip('"')
        else:
            logger.warning("Ignoring invalid line in config file: %s", line)

    return config


def _parse_ini_config(config_path: Path) -> Dict[str, str]:
    """
    Parse a config file using configparser.

    Args:
        config_path: Path to the config file

    Returns:
        Dictionary of parsed configuration
    """
    parser = configparser.ConfigParser()

    try:
        parser.read(config_path)

        # Convert to flat dictionary for backward compatibility
        result: Dict[str, str] = {}
        for section in parser.sections():
            for key, value in parser[section].items():
                result[f"{section}.{key}"] = value

        # Handle DEFAULT section
        for key, value in parser.defaults().items():
            result[key] = value

        return result

    except configparser.Error as e:
        error_msg = f"Invalid configuration file: {e}"
        logger.error(error_msg)
        raise ValueError(error_msg) from e


def save_json(data: Any, file_path: str) -> None:
    """
    Save data to a JSON file.

    Args:
        data: Data to save
        file_path: Path to the file

    Raises:
        OSError: If there's an error writing to the file
        TypeError: If data is not JSON serializable
    """
    path = Path(file_path)

    # Ensure parent directory exists
    path.parent.mkdir(parents=True, exist_ok=True)

    try:
        with path.open("w") as f:
            json.dump(data, f, indent=2)
    except (OSError, TypeError) as e:
        logger.error("Failed to save JSON file %s: %s", file_path, str(e))
        raise


def load_json(file_path: str) -> Any:
    """
    Load data from a JSON file.

    Args:
        file_path: Path to the file

    Returns:
        Loaded data

    Raises:
        FileNotFoundError: If the file doesn't exist
        json.JSONDecodeError: If the file isn't valid JSON
    """
    path = Path(file_path)

    try:
        with path.open("r") as f:
            return json.load(f)
    except FileNotFoundError as e:
        error_msg = f"File not found: {file_path}"
        logger.error(error_msg)
        raise FileNotFoundError(error_msg) from e
    except json.JSONDecodeError as e:
        error_msg = f"Invalid JSON in {file_path}: {e}"
        logger.error(error_msg)
        raise json.JSONDecodeError(error_msg, e.doc, e.pos) from e


def ensure_dir_exists(path: str) -> None:
    """
    Ensure a directory exists.

    Args:
        path: Directory path

    Raises:
        OSError: If directory creation fails for reasons other than it already existing
    """
    Path(path).mkdir(parents=True, exist_ok=True)
