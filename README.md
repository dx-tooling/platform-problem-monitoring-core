# platform-problem-monitoring-core

A tool for monitoring platform problems using Elasticsearch logs. This application processes log messages, normalizes them, identifies patterns, and sends email reports about potential issues.

## Overview

The platform-problem-monitoring-core application is a command-line tool that:

1. Downloads log data from Elasticsearch
2. Extracts relevant fields from log messages
3. Normalizes messages to identify patterns
4. Compares current patterns with previous runs
5. Generates and sends email reports about identified issues

The application is designed to be modular, with each step implemented as a separate script that can be run independently or as part of a pipeline.

## Installation

### Prerequisites

- Python 3.8 or higher
- Access to an Elasticsearch server
- SMTP server for sending emails
- AWS S3 access (for storing state between runs)

### Setting Up a Virtual Environment

It's strongly recommended to use a virtual environment for this application to isolate its dependencies from other Python projects and your system Python installation.

1. First, make sure you have the `venv` module installed:
   ```bash
   # On Debian/Ubuntu
   sudo apt-get install python3-venv
   
   # On macOS (using Homebrew)
   brew install python3
   ```

2. Create a virtual environment in the project directory:
   ```bash
   # Navigate to the project directory
   cd platform-problem-monitoring-core
   
   # Create a virtual environment named 'venv'
   python3 -m venv venv
   ```

3. Activate the virtual environment:
   ```bash
   # On macOS/Linux
   source venv/bin/activate
   
   # On Windows
   venv\Scripts\activate
   ```
   
   When the virtual environment is activated, your command prompt will be prefixed with `(venv)`.

4. To deactivate the virtual environment when you're done working with the application:
   ```bash
   deactivate
   ```

### Install from Source

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd platform-problem-monitoring-core
   ```

2. Create and activate a virtual environment as described above.

3. Install the package:
   ```bash
   pip3 install -e .
   ```

4. For development, install development dependencies:
   ```bash
   pip3 install -e ".[dev]"
   ```

### Dependency Management

Dependencies are managed through the `pyproject.toml` file at the root of the project. The application uses modern Python packaging with PEP 621 standards. Key dependencies include:

- **elasticsearch**: For connecting to and querying Elasticsearch servers
- **boto3**: For AWS S3 interactions to store state between runs
- **drain3**: For log message normalization and pattern detection
- **jinja2**: For templating (used in email generation)
- **argparse**: For command-line argument parsing

Development dependencies include testing tools (pytest), code formatting (black), linting (flake8), and type checking (mypy).

If you need to add a new dependency:

1. Add it to the `dependencies` list in `pyproject.toml`
2. Reinstall the package with `pip3 install -e .`

Example of adding a new dependency:
```toml
dependencies = [
    "elasticsearch>=8.0.0",
    "boto3>=1.28.0",
    "drain3>=0.9.6",
    "jinja2>=3.0.0",
    "argparse>=1.4.0",
    "new-package>=1.0.0",  # New dependency
]
```

## Configuration

The application uses a configuration file with environment variable-style settings. Copy the template and modify it:

```bash
cp src/platform_problem_monitoring_core.conf.dist platform_problem_monitoring_core.conf
```

Edit the configuration file to include your specific settings:

```
REMOTE_STATE_S3_BUCKET_NAME="your-s3-bucket"
REMOTE_STATE_S3_FOLDER_NAME="platform-monitoring"

ELASTICSEARCH_SERVER_BASE_URL="https://your-elasticsearch-server:9200"
ELASTICSEARCH_LUCENE_QUERY_FILE_PATH="path/to/lucene_query.json"

KIBANA_BASE_URL="https://your-kibana-server:5601"

SMTP_SERVER_HOSTNAME="smtp.example.com"
SMTP_SERVER_PORT="587"
SMTP_SERVER_USERNAME="your-smtp-username"
SMTP_SERVER_PASSWORD="your-smtp-password"
SMTP_SENDER_ADDRESS="monitoring@example.com"
SMTP_RECEIVER_ADDRESS="alerts@example.com"
```

You'll also need to configure the Elasticsearch query. A template is provided:

```bash
cp src/lucene_query.json.dist lucene_query.json
```

The default query looks for error messages and exceptions while excluding certain noise:

```json
{
    "query": {
        "bool": {
            "should": [
                { "match": { "message": "error" } },
                { "match": { "message": "failure" } },
                { "match": { "message": "critical" } },
                { "match": { "message": "alert" } },
                { "match": { "message": "exception" } }
            ],
            "must_not": [
                { "match": { "message": "User Deprecated" } },
                { "match": { "message": "logstash" } },
                { "term": { "syslog_program": "dd.collector" } },
                { "term": { "syslog_program": "dd.forwarder" } },
                { "term": { "syslog_program": "dd.dogstatsd" } }
            ],
            "minimum_should_match": 1
        }
    }
}
```

## Usage

The application consists of 10 modular steps that can be run individually or as part of a complete pipeline.

### Running the Complete Pipeline

The simplest way to run the application is using the provided shell script:

```bash
./src/run.sh ./platform_problem_monitoring_core.conf
```

This will execute all steps in sequence, using the configuration file you provided.

### Running Individual Steps

Each step can be run independently with specific command-line arguments, from folder `src/`:

1. **Prepare Environment**:
   ```bash
   python3 -m platform_problem_monitoring_core.step1_prepare
   ```

2. **Download Previous State**:
   ```bash
   python3 -m platform_problem_monitoring_core.step2_download_previous_state --s3-bucket your-bucket --s3-folder your-folder --date-time-file data/previous_date_time.txt --norm-results-file data/previous_norm_results.json
   ```

3. **Download Logstash Documents**:
   ```bash
   python3 -m platform_problem_monitoring_core.step3_download_logstash_documents --elasticsearch-url https://your-elasticsearch-server:9200 --query-file queries/default_query.json --start-date-time-file data/previous_date_time.txt --output-file data/logstash_documents.json --current-date-time-file data/current_date_time.txt
   ```

4. **Extract Fields**:
   ```bash
   python3 -m platform_problem_monitoring_core.step4_extract_fields --logstash-file data/logstash_documents.json --output-file data/extracted_fields.json
   ```

5. **Normalize Messages**:
   ```bash
   python3 -m platform_problem_monitoring_core.step5_normalize_messages --fields-file data/extracted_fields.json --output-file data/norm_results.json
   ```
6. **Compare Normalizations**:
   ```bash
   python3 -m platform_problem_monitoring_core.step6_compare_normalizations --current-file data/norm_results.json --previous-file data/previous_norm_results.json --output-file data/comparison_results.json
   ```

7. **Generate Email Bodies**:
   ```bash
   python3 -m platform_problem_monitoring_core.step7_generate_email_bodies --comparison-file data/comparison_results.json --norm-results-file data/norm_results.json --html-output data/email_body.html --text-output data/email_body.txt --kibana-url https://your-kibana-server:5601
   ```

8. **Send Email Report**:
   ```bash
   python3 -m platform_problem_monitoring_core.step8_send_email_report --html-file data/email_body.html --text-file data/email_body.txt --subject "Platform Monitoring Report" --smtp-host smtp.example.com --smtp-port 587 --smtp-user your-username --smtp-pass your-password --sender monitoring@example.com --receiver alerts@example.com
   ```

9. **Store New State**:
   ```bash
   python3 -m platform_problem_monitoring_core.step9_store_new_state --s3-bucket your-bucket --s3-folder your-folder --date-time-file data/current_date_time.txt --norm-results-file data/norm_results.json
   ```

10. **Clean Up**:
    ```bash
    python3 -m platform_problem_monitoring_core.step10_cleanup --work-dir /path/to/temp/work/dir
    ```

## Error Handling

The application includes robust error handling that will send immediate email notifications when errors occur. This ensures that you're aware of any issues with the monitoring process itself. The error reporting functionality is implemented in a dedicated `send_error_email.py` script, separate from the regular email reporting.

## Performance Considerations

The application is designed to handle large volumes of log data, potentially up to multiple millions of Elasticsearch logstash documents between runs. It uses streaming and pagination techniques when interacting with Elasticsearch to prevent memory or resource exhaustion.

## Development

### Running Tests

```bash
pytest
```

### Code Formatting

```bash
black src tests
```

### Type Checking

```bash
mypy src
```

## License

Proprietary - All rights reserved.

