#!/usr/bin/env python3
"""Generate email bodies for platform problem monitoring reports."""

import argparse
import sys
from datetime import datetime, UTC
from typing import Optional, List, Dict, Any, Tuple

from platform_problem_monitoring_core.utils import logger, load_json


def generate_pattern_list_html(patterns: List[Dict[str, Any]], kibana_url: Optional[str] = None) -> str:
    """
    Generate HTML for a list of patterns.
    
    Args:
        patterns: List of patterns to display
        kibana_url: Optional Kibana base URL for deep links
        
    Returns:
        HTML string for the pattern list
    """
    if not patterns:
        return "<p class='text-gray-500 dark:text-dark-200'>No patterns found.</p>"
    
    html = "<div class='space-y-6'>"
    
    for i, pattern in enumerate(patterns, 1):
        count = pattern.get("count", 0)
        pattern_text = pattern.get("pattern", "")
        
        # Create a unique ID for each pattern
        pattern_id = f"pattern-{i}"
        
        html += f"""
        <div class='pattern-item'>
            <div class='flex items-start'>
                <div class='pattern-number'>{i}.</div>
                <div class='pattern-count'>{count}</div>
                <div class='pattern-text'>
                    <pre id='{pattern_id}'>{pattern_text}</pre>
                </div>
            </div>
        """
        
        # Add sample document links if available and kibana_url is provided
        if kibana_url and "sample_doc_references" in pattern and pattern["sample_doc_references"]:
            html += "<div class='sample-links'>"
            html += "Sample documents: "
            
            for j, doc_ref in enumerate(pattern["sample_doc_references"][:5], 1):
                # Handle doc_ref as a string in format "index:id"
                if isinstance(doc_ref, str) and ":" in doc_ref:
                    parts = doc_ref.split(":", 1)
                    index = parts[0]
                    doc_id = parts[1]
                    
                    if index and doc_id and kibana_url:
                        # Create a deep link to Kibana
                        kibana_link = f"{kibana_url}/app/discover#/doc/{index}/{doc_id}"
                        html += f"<a href='{kibana_link}' class='jwui-link-default'>Sample {j}</a>"
                        
                        # Add comma if not the last item
                        if j < len(pattern["sample_doc_references"][:5]):
                            html += ", "
                else:
                    # Handle as dictionary if it's not a string
                    index = doc_ref.get("index", "") if isinstance(doc_ref, dict) else ""
                    doc_id = doc_ref.get("id", "") if isinstance(doc_ref, dict) else ""
                    
                    if index and doc_id and kibana_url:
                        # Create a deep link to Kibana
                        kibana_link = f"{kibana_url}/app/discover#/doc/{index}/{doc_id}"
                        html += f"<a href='{kibana_link}' class='jwui-link-default'>Sample {j}</a>"
                        
                        # Add comma if not the last item
                        if j < len(pattern["sample_doc_references"][:5]):
                            html += ", "
            
            html += "</div>"
        
        html += "</div>"
    
    html += "</div>"
    return html


def generate_increased_pattern_list_html(patterns: List[Dict[str, Any]], kibana_url: Optional[str] = None) -> str:
    """
    Generate HTML for a list of increased patterns.
    
    Args:
        patterns: List of increased patterns to display
        kibana_url: Optional Kibana base URL for deep links
        
    Returns:
        HTML string for the increased pattern list
    """
    if not patterns:
        return "<p class='text-gray-500 dark:text-dark-200'>No increased patterns found.</p>"
    
    html = "<div class='space-y-6'>"
    
    for i, pattern in enumerate(patterns, 1):
        current_count = pattern.get("current_count", 0)
        previous_count = pattern.get("previous_count", 0)
        absolute_change = pattern.get("absolute_change", 0)
        percent_change = pattern.get("percent_change", 0)
        pattern_text = pattern.get("pattern", "")
        
        # Create a unique ID for each pattern
        pattern_id = f"increased-pattern-{i}"
        
        html += f"""
        <div class='pattern-item'>
            <div class='flex items-start'>
                <div class='pattern-number'>{i}.</div>
                <div class='pattern-count increased'>
                    {current_count}
                    <span class='change-indicator'>
                        (+{absolute_change}, +{percent_change:.1f}%)
                    </span>
                </div>
                <div class='pattern-text'>
                    <pre id='{pattern_id}'>{pattern_text}</pre>
                </div>
            </div>
        """
        
        # Add sample document links if available and kibana_url is provided
        if kibana_url and "sample_doc_references" in pattern and pattern["sample_doc_references"]:
            html += "<div class='sample-links'>"
            html += "Sample documents: "
            
            for j, doc_ref in enumerate(pattern["sample_doc_references"][:5], 1):
                # Handle doc_ref as a string in format "index:id"
                if isinstance(doc_ref, str) and ":" in doc_ref:
                    parts = doc_ref.split(":", 1)
                    index = parts[0]
                    doc_id = parts[1]
                    
                    if index and doc_id and kibana_url:
                        # Create a deep link to Kibana
                        kibana_link = f"{kibana_url}/app/discover#/doc/{index}/{doc_id}"
                        html += f"<a href='{kibana_link}' class='jwui-link-default'>Sample {j}</a>"
                        
                        # Add comma if not the last item
                        if j < len(pattern["sample_doc_references"][:5]):
                            html += ", "
                else:
                    # Handle as dictionary if it's not a string
                    index = doc_ref.get("index", "") if isinstance(doc_ref, dict) else ""
                    doc_id = doc_ref.get("id", "") if isinstance(doc_ref, dict) else ""
                    
                    if index and doc_id and kibana_url:
                        # Create a deep link to Kibana
                        kibana_link = f"{kibana_url}/app/discover#/doc/{index}/{doc_id}"
                        html += f"<a href='{kibana_link}' class='jwui-link-default'>Sample {j}</a>"
                        
                        # Add comma if not the last item
                        if j < len(pattern["sample_doc_references"][:5]):
                            html += ", "
            
            html += "</div>"
        
        html += "</div>"
    
    html += "</div>"
    return html


def generate_decreased_pattern_list_html(patterns: List[Dict[str, Any]], kibana_url: Optional[str] = None) -> str:
    """
    Generate HTML for a list of decreased patterns.
    
    Args:
        patterns: List of decreased patterns to display
        kibana_url: Optional Kibana base URL for deep links
        
    Returns:
        HTML string for the decreased pattern list
    """
    if not patterns:
        return "<p class='text-gray-500 dark:text-dark-200'>No decreased patterns found.</p>"
    
    html = "<div class='space-y-6'>"
    
    for i, pattern in enumerate(patterns, 1):
        current_count = pattern.get("current_count", 0)
        previous_count = pattern.get("previous_count", 0)
        absolute_change = pattern.get("absolute_change", 0)
        percent_change = pattern.get("percent_change", 0)
        pattern_text = pattern.get("pattern", "")
        
        # Create a unique ID for each pattern
        pattern_id = f"decreased-pattern-{i}"
        
        html += f"""
        <div class='pattern-item'>
            <div class='flex items-start'>
                <div class='pattern-number'>{i}.</div>
                <div class='pattern-count decreased'>
                    {current_count}
                    <span class='change-indicator'>
                        (-{absolute_change}, -{percent_change:.1f}%)
                    </span>
                </div>
                <div class='pattern-text'>
                    <pre id='{pattern_id}'>{pattern_text}</pre>
                </div>
            </div>
        """
        
        # Add sample document links if available and kibana_url is provided
        if kibana_url and "sample_doc_references" in pattern and pattern["sample_doc_references"]:
            html += "<div class='sample-links'>"
            html += "Sample documents: "
            
            for j, doc_ref in enumerate(pattern["sample_doc_references"][:5], 1):
                # Handle doc_ref as a string in format "index:id"
                if isinstance(doc_ref, str) and ":" in doc_ref:
                    parts = doc_ref.split(":", 1)
                    index = parts[0]
                    doc_id = parts[1]
                    
                    if index and doc_id and kibana_url:
                        # Create a deep link to Kibana
                        kibana_link = f"{kibana_url}/app/discover#/doc/{index}/{doc_id}"
                        html += f"<a href='{kibana_link}' class='jwui-link-default'>Sample {j}</a>"
                        
                        # Add comma if not the last item
                        if j < len(pattern["sample_doc_references"][:5]):
                            html += ", "
                else:
                    # Handle as dictionary if it's not a string
                    index = doc_ref.get("index", "") if isinstance(doc_ref, dict) else ""
                    doc_id = doc_ref.get("id", "") if isinstance(doc_ref, dict) else ""
                    
                    if index and doc_id and kibana_url:
                        # Create a deep link to Kibana
                        kibana_link = f"{kibana_url}/app/discover#/doc/{index}/{doc_id}"
                        html += f"<a href='{kibana_link}' class='jwui-link-default'>Sample {j}</a>"
                        
                        # Add comma if not the last item
                        if j < len(pattern["sample_doc_references"][:5]):
                            html += ", "
            
            html += "</div>"
        
        html += "</div>"
    
    html += "</div>"
    return html


def generate_pattern_list_text(patterns: List[Dict[str, Any]]) -> str:
    """
    Generate plaintext for a list of patterns.
    
    Args:
        patterns: List of patterns to display
        
    Returns:
        Plaintext string for the pattern list
    """
    if not patterns:
        return "No patterns found.\n"
    
    text = ""
    
    for i, pattern in enumerate(patterns, 1):
        count = pattern.get("count", 0)
        pattern_text = pattern.get("pattern", "")
        
        text += f"{i}. [{count}] {pattern_text}\n"
        
        # Add sample document references if available
        if "sample_doc_references" in pattern and pattern["sample_doc_references"]:
            text += "   Sample documents: "
            sample_refs = []
            
            for j, doc_ref in enumerate(pattern["sample_doc_references"][:5], 1):
                # Handle doc_ref as a string in format "index:id"
                if isinstance(doc_ref, str) and ":" in doc_ref:
                    parts = doc_ref.split(":", 1)
                    index = parts[0]
                    doc_id = parts[1]
                    
                    if index and doc_id:
                        sample_refs.append(f"Sample {j} ({index}/{doc_id})")
                else:
                    # Handle as dictionary if it's not a string
                    index = doc_ref.get("index", "") if isinstance(doc_ref, dict) else ""
                    doc_id = doc_ref.get("id", "") if isinstance(doc_ref, dict) else ""
                    
                    if index and doc_id:
                        sample_refs.append(f"Sample {j} ({index}/{doc_id})")
            
            text += ", ".join(sample_refs) + "\n"
        
        text += "\n"
    
    return text


def generate_increased_pattern_list_text(patterns: List[Dict[str, Any]]) -> str:
    """
    Generate plaintext for a list of increased patterns.
    
    Args:
        patterns: List of increased patterns to display
        
    Returns:
        Plaintext string for the increased pattern list
    """
    if not patterns:
        return "No increased patterns found.\n"
    
    text = ""
    
    for i, pattern in enumerate(patterns, 1):
        current_count = pattern.get("current_count", 0)
        previous_count = pattern.get("previous_count", 0)
        absolute_change = pattern.get("absolute_change", 0)
        percent_change = pattern.get("percent_change", 0)
        pattern_text = pattern.get("pattern", "")
        
        text += f"{i}. [{current_count}] (+{absolute_change}, +{percent_change:.1f}%) {pattern_text}\n"
        
        # Add sample document references if available
        if "sample_doc_references" in pattern and pattern["sample_doc_references"]:
            text += "   Sample documents: "
            sample_refs = []
            
            for j, doc_ref in enumerate(pattern["sample_doc_references"][:5], 1):
                # Handle doc_ref as a string in format "index:id"
                if isinstance(doc_ref, str) and ":" in doc_ref:
                    parts = doc_ref.split(":", 1)
                    index = parts[0]
                    doc_id = parts[1]
                    
                    if index and doc_id:
                        sample_refs.append(f"Sample {j} ({index}/{doc_id})")
                else:
                    # Handle as dictionary if it's not a string
                    index = doc_ref.get("index", "") if isinstance(doc_ref, dict) else ""
                    doc_id = doc_ref.get("id", "") if isinstance(doc_ref, dict) else ""
                    
                    if index and doc_id:
                        sample_refs.append(f"Sample {j} ({index}/{doc_id})")
            
            text += ", ".join(sample_refs) + "\n"
        
        text += "\n"
    
    return text


def generate_decreased_pattern_list_text(patterns: List[Dict[str, Any]]) -> str:
    """
    Generate plaintext for a list of decreased patterns.
    
    Args:
        patterns: List of decreased patterns to display
        
    Returns:
        Plaintext string for the decreased pattern list
    """
    if not patterns:
        return "No decreased patterns found.\n"
    
    text = ""
    
    for i, pattern in enumerate(patterns, 1):
        current_count = pattern.get("current_count", 0)
        previous_count = pattern.get("previous_count", 0)
        absolute_change = pattern.get("absolute_change", 0)
        percent_change = pattern.get("percent_change", 0)
        pattern_text = pattern.get("pattern", "")
        
        text += f"{i}. [{current_count}] (-{absolute_change}, -{percent_change:.1f}%) {pattern_text}\n"
        
        # Add sample document references if available
        if "sample_doc_references" in pattern and pattern["sample_doc_references"]:
            text += "   Sample documents: "
            sample_refs = []
            
            for j, doc_ref in enumerate(pattern["sample_doc_references"][:5], 1):
                # Handle doc_ref as a string in format "index:id"
                if isinstance(doc_ref, str) and ":" in doc_ref:
                    parts = doc_ref.split(":", 1)
                    index = parts[0]
                    doc_id = parts[1]
                    
                    if index and doc_id:
                        sample_refs.append(f"Sample {j} ({index}/{doc_id})")
                else:
                    # Handle as dictionary if it's not a string
                    index = doc_ref.get("index", "") if isinstance(doc_ref, dict) else ""
                    doc_id = doc_ref.get("id", "") if isinstance(doc_ref, dict) else ""
                    
                    if index and doc_id:
                        sample_refs.append(f"Sample {j} ({index}/{doc_id})")
            
            text += ", ".join(sample_refs) + "\n"
        
        text += "\n"
    
    return text


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
    
    # Get the top 25 patterns from the normalization results
    top_patterns = sorted(norm_results.get("patterns", []), key=lambda x: x.get("count", 0), reverse=True)[:25]
    
    # Extract data from comparison results
    current_patterns_count = comparison.get("current_patterns_count", 0)
    previous_patterns_count = comparison.get("previous_patterns_count", 0)
    new_patterns = comparison.get("new_patterns", [])
    disappeared_patterns = comparison.get("disappeared_patterns", [])
    increased_patterns = comparison.get("increased_patterns", [])
    decreased_patterns = comparison.get("decreased_patterns", [])
    
    # Generate timestamp
    timestamp = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC")
    
    # Generate HTML email body
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Platform Problem Monitoring Report</title>
        <style>
            /* Base styles */
            body {{
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
                line-height: 1.5;
                color: #1a202c;
                background-color: #f7fafc;
                margin: 0;
                padding: 20px;
            }}
            
            /* Dark mode support for email clients that support it */
            @media (prefers-color-scheme: dark) {{
                body {{
                    background-color: #1a202c;
                    color: #f7fafc;
                }}
                
                .card {{
                    background-color: #2d3748 !important;
                    border-color: #4a5568 !important;
                }}
                
                .section-title {{
                    color: #90cdf4 !important;
                    border-bottom-color: #4a5568 !important;
                }}
                
                .text-gray-500 {{
                    color: #a0aec0 !important;
                }}
                
                pre {{
                    background-color: #2d3748 !important;
                    border-color: #4a5568 !important;
                }}
                
                .badge {{
                    border: 1px solid #4a5568 !important;
                }}
            }}
            
            /* Layout */
            .container {{
                max-width: 800px;
                margin: 0 auto;
            }}
            
            .card {{
                background-color: #ffffff;
                border-radius: 8px;
                box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1), 0 1px 2px 0 rgba(0, 0, 0, 0.06);
                padding: 24px;
                margin-bottom: 24px;
                border: 1px solid #e2e8f0;
            }}
            
            /* Typography */
            h1 {{
                font-size: 24px;
                font-weight: 700;
                margin-top: 0;
                margin-bottom: 16px;
                color: #2c3e50;
            }}
            
            h2 {{
                font-size: 20px;
                font-weight: 600;
                margin-top: 0;
                margin-bottom: 16px;
                color: #3498db;
            }}
            
            .section-title {{
                font-size: 18px;
                font-weight: 600;
                margin-top: 24px;
                margin-bottom: 16px;
                padding-bottom: 8px;
                border-bottom: 1px solid #e2e8f0;
                color: #4a5568;
            }}
            
            p {{
                margin-top: 0;
                margin-bottom: 16px;
            }}
            
            .text-sm {{
                font-size: 14px;
            }}
            
            .text-gray-500 {{
                color: #718096;
            }}
            
            /* Components */
            .stats-grid {{
                display: flex;
                flex-wrap: wrap;
                gap: 16px;
                margin-bottom: 24px;
            }}
            
            .stat-card {{
                flex: 1;
                min-width: 120px;
                padding: 16px;
                background-color: #f8fafc;
                border-radius: 6px;
                border: 1px solid #e2e8f0;
                text-align: center;
            }}
            
            .stat-value {{
                font-size: 24px;
                font-weight: 700;
                margin-bottom: 4px;
            }}
            
            .stat-label {{
                font-size: 14px;
                color: #718096;
            }}
            
            .badge {{
                display: inline-block;
                padding: 4px 8px;
                border-radius: 4px;
                font-size: 12px;
                font-weight: 600;
                margin-right: 8px;
            }}
            
            .badge-success {{
                background-color: #c6f6d5;
                color: #22543d;
            }}
            
            .badge-warning {{
                background-color: #feebc8;
                color: #744210;
            }}
            
            .badge-error {{
                background-color: #fed7d7;
                color: #822727;
            }}
            
            .badge-info {{
                background-color: #bee3f8;
                color: #2a4365;
            }}
            
            /* Pattern display */
            .pattern-item {{
                margin-bottom: 16px;
                padding-bottom: 16px;
                border-bottom: 1px solid #e2e8f0;
            }}
            
            .pattern-item:last-child {{
                border-bottom: none;
            }}
            
            .pattern-number {{
                font-weight: 600;
                min-width: 30px;
                margin-right: 8px;
            }}
            
            .pattern-count {{
                font-weight: 700;
                min-width: 60px;
                margin-right: 16px;
                text-align: right;
            }}
            
            .increased {{
                color: #e53e3e;
            }}
            
            .decreased {{
                color: #38a169;
            }}
            
            .change-indicator {{
                font-size: 12px;
                font-weight: 400;
                display: block;
            }}
            
            .pattern-text {{
                flex: 1;
            }}
            
            pre {{
                margin: 0;
                padding: 8px;
                background-color: #f7fafc;
                border-radius: 4px;
                border: 1px solid #e2e8f0;
                overflow-x: auto;
                font-family: SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
                font-size: 13px;
                white-space: pre-wrap;
                word-break: break-word;
            }}
            
            .sample-links {{
                margin-top: 8px;
                margin-left: 38px;
                font-size: 13px;
            }}
            
            .sample-links a {{
                color: #3182ce;
                text-decoration: none;
            }}
            
            .sample-links a:hover {{
                text-decoration: underline;
            }}
            
            /* Button */
            .button {{
                display: inline-block;
                background-color: #3182ce;
                color: white;
                padding: 8px 16px;
                border-radius: 4px;
                text-decoration: none;
                font-weight: 600;
                margin-top: 8px;
            }}
            
            .button:hover {{
                background-color: #2c5282;
            }}
            
            /* Utilities */
            .flex {{
                display: flex;
            }}
            
            .items-start {{
                align-items: flex-start;
            }}
            
            .space-y-6 > * + * {{
                margin-top: 24px;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="card">
                <h1>Platform Problem Monitoring Report</h1>
                <p class="text-sm">Report generated at: {timestamp}</p>
                
                <div class="stats-grid">
                    <div class="stat-card">
                        <div class="stat-value">{current_patterns_count}</div>
                        <div class="stat-label">Current Patterns</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value">{previous_patterns_count}</div>
                        <div class="stat-label">Previous Patterns</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value">{len(new_patterns)}</div>
                        <div class="stat-label">New Patterns</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value">{len(disappeared_patterns)}</div>
                        <div class="stat-label">Disappeared</div>
                    </div>
                </div>
                
                {f'''
                <div style="text-align: center; margin: 20px 0;">
                    <a href="{kibana_url}" class="button">View in Kibana</a>
                </div>
                ''' if kibana_url else ''}
            </div>
            
            <div class="card">
                <h2>SUMMARY OF CHANGES IN PROBLEM PATTERNS</h2>
                <p class="text-sm text-gray-500">Generated on {timestamp}</p>
                
                <div class="stats-grid">
                    <div class="stat-card">
                        <div class="stat-value">{current_patterns_count}</div>
                        <div class="stat-label">Current Patterns</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value">{previous_patterns_count}</div>
                        <div class="stat-label">Previous Patterns</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value">{len(new_patterns)}</div>
                        <div class="stat-label">New Patterns</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value">{len(disappeared_patterns)}</div>
                        <div class="stat-label">Disappeared</div>
                    </div>
                </div>
                
                <h3 class="section-title">TOP 10 NEW PROBLEM PATTERNS</h3>
                <p class="text-sm text-gray-500">These patterns appeared in the new summary but were not present in the previous one.</p>
                {generate_pattern_list_html(new_patterns[:10], kibana_url)}
                
                <h3 class="section-title">TOP 10 DISAPPEARED PROBLEM PATTERNS</h3>
                <p class="text-sm text-gray-500">These patterns were present in the previous summary but are not in the current one.</p>
                {generate_pattern_list_html(disappeared_patterns[:10], kibana_url)}
                
                <h3 class="section-title">TOP 10 INCREASED PROBLEM PATTERNS</h3>
                <p class="text-sm text-gray-500">These patterns have increased in occurrence count since the last report.</p>
                {generate_increased_pattern_list_html(increased_patterns[:10], kibana_url)}
                
                <h3 class="section-title">TOP 10 DECREASED PROBLEM PATTERNS</h3>
                <p class="text-sm text-gray-500">These patterns have decreased in occurrence count since the last report.</p>
                {generate_decreased_pattern_list_html(decreased_patterns[:10], kibana_url)}
            </div>
            
            <div class="card">
                <h2>TOP 25 CURRENT PROBLEM PATTERNS</h2>
                <p class="text-sm text-gray-500">The most frequent problem patterns in the current report.</p>
                {generate_pattern_list_html(top_patterns, kibana_url)}
            </div>
            
            <div style="text-align: center; margin-top: 20px; color: #718096; font-size: 12px;">
                <p>This is an automated report from the Platform Problem Monitoring system.</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    # Generate plaintext email body
    text = f"""
Platform Problem Monitoring Report
=================================

Report generated at: {timestamp}

SUMMARY:
- Current Patterns: {current_patterns_count}
- Previous Patterns: {previous_patterns_count}
- New Patterns: {len(new_patterns)}
- Disappeared Patterns: {len(disappeared_patterns)}

{f'View in Kibana: {kibana_url}' if kibana_url else ''}

SUMMARY OF CHANGES IN PROBLEM PATTERNS
=====================================

TOP 10 NEW PROBLEM PATTERNS
---------------------------
These patterns appeared in the new summary but were not present in the previous one.

{generate_pattern_list_text(new_patterns[:10])}

TOP 10 DISAPPEARED PROBLEM PATTERNS
----------------------------------
These patterns were present in the previous summary but are not in the current one.

{generate_pattern_list_text(disappeared_patterns[:10])}

TOP 10 INCREASED PROBLEM PATTERNS
--------------------------------
These patterns have increased in occurrence count since the last report.

{generate_increased_pattern_list_text(increased_patterns[:10])}

TOP 10 DECREASED PROBLEM PATTERNS
--------------------------------
These patterns have decreased in occurrence count since the last report.

{generate_decreased_pattern_list_text(decreased_patterns[:10])}

TOP 25 CURRENT PROBLEM PATTERNS
==============================
The most frequent problem patterns in the current report.

{generate_pattern_list_text(top_patterns)}

This is an automated report from the Platform Problem Monitoring system.
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
