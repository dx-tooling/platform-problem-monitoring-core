#!/usr/bin/env python3
"""Generate email bodies."""

import argparse
import sys
from datetime import datetime
from typing import Optional, List, Dict, Any

from platform_problem_monitoring_core.utils import logger, load_json


def generate_email_bodies(
    comparison_file: str,
    norm_results_file: str,
    html_output: str,
    text_output: str,
    kibana_url: Optional[str] = None,
) -> None:
    """
    Generate HTML and plaintext email bodies.
    
    Args:
        comparison_file: Path to the comparison results file
        norm_results_file: Path to the normalization results file
        html_output: Path to store the HTML email body
        text_output: Path to store the plaintext email body
        kibana_url: Kibana base URL (optional)
    """
    logger.info("Generating email bodies")
    logger.info(f"Comparison file: {comparison_file}")
    logger.info(f"Normalization results file: {norm_results_file}")
    logger.info(f"HTML output: {html_output}")
    logger.info(f"Text output: {text_output}")
    if kibana_url:
        logger.info(f"Kibana URL: {kibana_url}")
    
    # Load the comparison results
    comparison = load_json(comparison_file)
    
    # Load the normalization results
    norm_results = load_json(norm_results_file)
    
    # Get the top 25 normalization results
    top_results = norm_results[:25] if len(norm_results) > 25 else norm_results
    
    # Generate a simple HTML email body for now
    html = f"""
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; }}
            h1 {{ color: #2c3e50; }}
            h2 {{ color: #3498db; }}
        </style>
    </head>
    <body>
        <h1>Platform Problem Monitoring Report</h1>
        <p>Report generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        
        <h2>Summary</h2>
        <ul>
            <li>Current Patterns: {comparison.get("current_pattern_count", 0)}</li>
            <li>Previous Patterns: {comparison.get("previous_pattern_count", 0)}</li>
            <li>New Patterns: {len(comparison.get("new_patterns", []))}</li>
            <li>Disappeared Patterns: {len(comparison.get("disappeared_patterns", []))}</li>
        </ul>
        
        <p>This is a placeholder email. In a real implementation, this would contain detailed information about the patterns.</p>
    </body>
    </html>
    """
    
    # Generate a simple plaintext email body for now
    text = f"""
    Platform Problem Monitoring Report
    =================================
    
    Report generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
    
    Summary:
    - Current Patterns: {comparison.get("current_pattern_count", 0)}
    - Previous Patterns: {comparison.get("previous_pattern_count", 0)}
    - New Patterns: {len(comparison.get("new_patterns", []))}
    - Disappeared Patterns: {len(comparison.get("disappeared_patterns", []))}
    
    This is a placeholder email. In a real implementation, this would contain detailed information about the patterns.
    """
    
    # Write the email bodies to the output files
    with open(html_output, "w") as f:
        f.write(html)
    
    with open(text_output, "w") as f:
        f.write(text)
    
    logger.info("Email bodies generated successfully")


def main() -> None:
    """Execute the script when run directly."""
    parser = argparse.ArgumentParser(description="Generate email bodies")
    parser.add_argument("--comparison-file", required=True, help="Path to the comparison results file")
    parser.add_argument("--norm-results-file", required=True, help="Path to the normalization results file")
    parser.add_argument("--html-output", required=True, help="Path to store the HTML email body")
    parser.add_argument("--text-output", required=True, help="Path to store the plaintext email body")
    parser.add_argument("--kibana-url", help="Kibana base URL")
    
    args = parser.parse_args()
    
    try:
        generate_email_bodies(
            args.comparison_file,
            args.norm_results_file,
            args.html_output,
            args.text_output,
            args.kibana_url,
        )
        sys.exit(0)
    except Exception as e:
        logger.error(f"Error generating email bodies: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
