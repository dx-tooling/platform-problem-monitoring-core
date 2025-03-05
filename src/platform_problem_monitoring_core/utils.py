"""Utility functions for Platform Problem Monitoring Core."""

import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("platform_problem_monitoring")


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
    config = {}
    
    if not Path(config_file_path).exists():
        error_msg = f"Configuration file not found: {config_file_path}"
        logger.error(error_msg)
        raise FileNotFoundError(error_msg)
        
    with Path(config_file_path).open("r") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
                
            if "=" in line:
                key, value = line.split("=", 1)
                config[key.strip()] = value.strip().strip('"')
            else:
                logger.warning("Ignoring invalid line in config file: %s", line)
                
    return config


def save_json(data: Any, file_path: str) -> None:
    """
    Save data to a JSON file.
    
    Args:
        data: Data to save
        file_path: Path to the file
    """
    with Path(file_path).open("w") as f:
        json.dump(data, f, indent=2)
        
        
def load_json(file_path: str) -> Any:
    """
    Load data from a JSON file.
    
    Args:
        file_path: Path to the file
        
    Returns:
        Loaded data
        
    Raises:
        FileNotFoundError: If the file doesn't exist
    """
    if not Path(file_path).exists():
        error_msg = f"File not found: {file_path}"
        logger.error(error_msg)
        raise FileNotFoundError(error_msg)
        
    with Path(file_path).open("r") as f:
        return json.load(f)


def ensure_dir_exists(path: str) -> None:
    """
    Ensure a directory exists.
    
    Args:
        path: Directory path
    """
    Path(path).mkdir(parents=True, exist_ok=True) 