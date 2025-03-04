"""Utility functions for Platform Problem Monitoring Core."""

import os
import sys
import logging
import json
from typing import Dict, Any, Optional

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
    
    if not os.path.exists(config_file_path):
        logger.error(f"Configuration file not found: {config_file_path}")
        raise FileNotFoundError(f"Configuration file not found: {config_file_path}")
        
    with open(config_file_path, "r") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
                
            if "=" in line:
                key, value = line.split("=", 1)
                config[key.strip()] = value.strip().strip('"')
            else:
                logger.warning(f"Ignoring invalid line in config file: {line}")
                
    return config


def save_json(data: Any, file_path: str) -> None:
    """
    Save data to a JSON file.
    
    Args:
        data: Data to save
        file_path: Path to the file
    """
    with open(file_path, "w") as f:
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
    if not os.path.exists(file_path):
        logger.error(f"File not found: {file_path}")
        raise FileNotFoundError(f"File not found: {file_path}")
        
    with open(file_path, "r") as f:
        return json.load(f)


def ensure_dir_exists(path: str) -> None:
    """
    Ensure a directory exists.
    
    Args:
        path: Directory path
    """
    os.makedirs(path, exist_ok=True) 