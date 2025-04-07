"""Platform Problem Monitoring Core.

A tool for monitoring platform problems using Elasticsearch logs.
"""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("platform_problem_monitoring_core")
except PackageNotFoundError:
    __version__ = "0.1.0"  # Default version if package is not installed
