#!/bin/bash
# Platform Problem Monitoring Core - Main execution script

set -e  # Exit immediately if a command exits with a non-zero status

# Check if configuration file is provided
if [ $# -ne 1 ]; then
    echo "Usage: $0 <path-to-config-file>"
    exit 1
fi

CONFIG_FILE="$1"

# Check if configuration file exists
if [ ! -f "$CONFIG_FILE" ]; then
    echo "Error: Configuration file not found: $CONFIG_FILE"
    exit 1
fi

# Source the configuration file
source "$CONFIG_FILE"

# Step 0: Prepare Python environment
echo "Step 0: Preparing Python environment..."

# Resolve the actual script location, even when called through a symlink
SOURCE=${BASH_SOURCE[0]}
if [ -z "$SOURCE" ]; then
    echo "Failed to determine script source" >&2
    exit 1
fi

while [ -L "$SOURCE" ]; do
    DIR=$( cd -P "$( dirname "$SOURCE" )" >/dev/null 2>&1 && pwd )
    if [ -z "$DIR" ]; then
        echo "Failed to resolve symlink directory" >&2
        exit 1
    fi
    SOURCE=$(readlink "$SOURCE")
    [[ $SOURCE != /* ]] && SOURCE=$DIR/$SOURCE
done

# Get the script directory and the package root (2 levels up)
SCRIPT_DIR=$( cd -P "$( dirname "$SOURCE" )" >/dev/null 2>&1 && pwd )
PACKAGE_ROOT=$( cd -P "$SCRIPT_DIR/../.." >/dev/null 2>&1 && pwd )

echo "Script directory: $SCRIPT_DIR"
echo "Package root directory: $PACKAGE_ROOT"

# Set up Python environment
# If running from installed package:
if python -c "import platform_problem_monitoring_core" &>/dev/null; then
    echo "Running from installed package"
    PYTHON_CMD="python"
else
    # If running from source, create and use virtual environment
    echo "Running from source, setting up virtual environment"
    cd "$PACKAGE_ROOT"

    if [ ! -d "venv" ]; then
        echo "Creating virtual environment"
        python3 -m venv venv
    fi

    source venv/bin/activate
    pip install --upgrade pip
    pip install -e . -q
    PYTHON_CMD="python"
fi

# Define file paths for intermediate results
WORK_DIR=""
START_DATE_TIME_FILE=""
CURRENT_DATE_TIME_FILE=""
LOGSTASH_DOCUMENTS_FILE=""
EXTRACTED_FIELDS_FILE=""
NORM_RESULTS_PREV_FILE=""
NORM_RESULTS_FILE=""
COMPARISON_RESULTS_FILE=""
HTML_EMAIL_BODY_FILE=""
TEXT_EMAIL_BODY_FILE=""
HOURLY_DATA_FILE=""
TREND_CHART_FILE=""

echo "Starting Platform Problem Monitoring process..."

# Step 1: Prepare application environment
echo "Step 1: Preparing application environment..."
# Capture all output but only use the last line as the work directory
PREPARE_OUTPUT=$($PYTHON_CMD -m platform_problem_monitoring_core.step1_prepare)
if [ $? -ne 0 ]; then
    echo "Error: Failed to prepare environment"
    exit 1
fi
# Display the output for logging purposes
echo "$PREPARE_OUTPUT"
# Extract only the last line as the work directory
WORK_DIR=$(echo "$PREPARE_OUTPUT" | tail -n 1)
echo "Work directory created: $WORK_DIR"

# Define paths for intermediate files
START_DATE_TIME_FILE="$WORK_DIR/start_date_time.txt"
CURRENT_DATE_TIME_FILE="$WORK_DIR/current_date_time.txt"
LOGSTASH_DOCUMENTS_FILE="$WORK_DIR/logstash_documents.json"
EXTRACTED_FIELDS_FILE="$WORK_DIR/extracted_fields.jsonl"
NORM_RESULTS_PREV_FILE="$WORK_DIR/norm_results_prev.json"
NORM_RESULTS_FILE="$WORK_DIR/norm_results.json"
COMPARISON_RESULTS_FILE="$WORK_DIR/comparison_results.json"
HTML_EMAIL_BODY_FILE="$WORK_DIR/email_body.html"
TEXT_EMAIL_BODY_FILE="$WORK_DIR/email_body.txt"
HOURLY_DATA_FILE="$WORK_DIR/hourly_problem_numbers.json"
TREND_CHART_FILE="$WORK_DIR/trend_chart.png"

# Step 2: Download previous state
echo "Step 2: Downloading previous state..."
$PYTHON_CMD -m platform_problem_monitoring_core.step2_download_previous_state \
    --s3-bucket "$REMOTE_STATE_S3_BUCKET_NAME" \
    --s3-folder "$REMOTE_STATE_S3_FOLDER_NAME" \
    --date-time-file "$START_DATE_TIME_FILE" \
    --norm-results-file "$NORM_RESULTS_PREV_FILE"
if [ $? -ne 0 ]; then
    echo "Error: Failed to download previous state"
    exit 1
fi
echo "Previous state downloaded successfully"

# Step 3: Retrieve hourly problem numbers
echo "Step 3: Retrieving hourly problem numbers..."
$PYTHON_CMD -m platform_problem_monitoring_core.step3_retrieve_hourly_problem_numbers \
    --elasticsearch-url "$ELASTICSEARCH_SERVER_BASE_URL" \
    --query-file "$ELASTICSEARCH_LUCENE_QUERY_FILE_PATH" \
    --hours-back "${TREND_HOURS_BACK:-24}" \
    --output-file "$HOURLY_DATA_FILE"
if [ $? -ne 0 ]; then
    echo "Error: Failed to retrieve hourly problem numbers"
    exit 1
fi
echo "Hourly problem numbers retrieved successfully"

# Step 4: Generate trend chart
echo "Step 4: Generating trend chart..."
$PYTHON_CMD -m platform_problem_monitoring_core.step4_generate_trend_chart \
    --hourly-data-file "$HOURLY_DATA_FILE" \
    --output-file "$TREND_CHART_FILE"
if [ $? -ne 0 ]; then
    echo "Error: Failed to generate trend chart"
    exit 1
fi
echo "Trend chart generated successfully"

# Step 5: Download logstash documents
echo "Step 5: Downloading logstash documents..."
$PYTHON_CMD -m platform_problem_monitoring_core.step5_download_logstash_documents \
    --elasticsearch-url "$ELASTICSEARCH_SERVER_BASE_URL" \
    --query-file "$ELASTICSEARCH_LUCENE_QUERY_FILE_PATH" \
    --start-date-time-file "$START_DATE_TIME_FILE" \
    --output-file "$LOGSTASH_DOCUMENTS_FILE" \
    --current-date-time-file "$CURRENT_DATE_TIME_FILE"
if [ $? -ne 0 ]; then
    echo "Error: Failed to download logstash documents"
    exit 1
fi
echo "Logstash documents downloaded successfully"

# Step 6: Extract fields from logstash documents
echo "Step 6: Extracting fields from logstash documents..."
$PYTHON_CMD -m platform_problem_monitoring_core.step6_extract_fields \
    --logstash-file "$LOGSTASH_DOCUMENTS_FILE" \
    --output-file "$EXTRACTED_FIELDS_FILE"
if [ $? -ne 0 ]; then
    echo "Error: Failed to extract fields"
    exit 1
fi
echo "Fields extracted successfully"

# Step 7: Normalize messages
echo "Step 7: Normalizing messages..."
$PYTHON_CMD -m platform_problem_monitoring_core.step7_normalize_messages \
    --fields-file "$EXTRACTED_FIELDS_FILE" \
    --output-file "$NORM_RESULTS_FILE"
if [ $? -ne 0 ]; then
    echo "Error: Failed to normalize messages"
    exit 1
fi
echo "Messages normalized successfully"

# Step 8: Compare normalizations
echo "Step 8: Comparing normalization results..."
$PYTHON_CMD -m platform_problem_monitoring_core.step8_compare_normalizations \
    --current-file "$NORM_RESULTS_FILE" \
    --previous-file "$NORM_RESULTS_PREV_FILE" \
    --output-file "$COMPARISON_RESULTS_FILE"
if [ $? -ne 0 ]; then
    echo "Error: Failed to compare normalization results"
    exit 1
fi
echo "Normalization results compared successfully"

# Step 9: Generate email bodies
echo "Step 9: Generating email bodies..."
$PYTHON_CMD -m platform_problem_monitoring_core.step9_generate_email_bodies \
    --comparison-file "$COMPARISON_RESULTS_FILE" \
    --norm-results-file "$NORM_RESULTS_FILE" \
    --html-output "$HTML_EMAIL_BODY_FILE" \
    --text-output "$TEXT_EMAIL_BODY_FILE" \
    --trend-chart-file "$TREND_CHART_FILE" \
    --hours-back "${TREND_HOURS_BACK:-24}" \
    ${KIBANA_DISCOVER_BASE_URL:+--kibana-url "$KIBANA_DISCOVER_BASE_URL"} \
    ${KIBANA_DOCUMENT_DEEPLINK_URL_STRUCTURE:+--kibana-deeplink-structure "$KIBANA_DOCUMENT_DEEPLINK_URL_STRUCTURE"} \
    ${ELASTICSEARCH_LUCENE_QUERY_FILE_PATH:+--elasticsearch-query-file "$ELASTICSEARCH_LUCENE_QUERY_FILE_PATH"} \
    ${START_DATE_TIME_FILE:+--start-date-time-file "$START_DATE_TIME_FILE"}
if [ $? -ne 0 ]; then
    echo "Error: Failed to generate email bodies"
    exit 1
fi
echo "Email bodies generated successfully"

# Step 10: Send email report
echo "Step 10: Sending email report..."
EMAIL_SUBJECT="Platform Problem Monitoring Report $(date +"%Y-%m-%d")"
$PYTHON_CMD -m platform_problem_monitoring_core.step10_send_email_report \
    --html-file "$HTML_EMAIL_BODY_FILE" \
    --text-file "$TEXT_EMAIL_BODY_FILE" \
    --subject "$EMAIL_SUBJECT" \
    --smtp-host "$SMTP_SERVER_HOSTNAME" \
    --smtp-port "$SMTP_SERVER_PORT" \
    --smtp-user "$SMTP_SERVER_USERNAME" \
    --smtp-pass "$SMTP_SERVER_PASSWORD" \
    --sender "$SMTP_SENDER_ADDRESS" \
    --receiver "$SMTP_RECEIVER_ADDRESS"
if [ $? -ne 0 ]; then
    echo "Error: Failed to send email report"
    exit 1
fi
echo "Email report sent successfully"

# Step 11: Store new state
echo "Step 11: Storing new state..."
$PYTHON_CMD -m platform_problem_monitoring_core.step11_store_new_state \
    --s3-bucket "$REMOTE_STATE_S3_BUCKET_NAME" \
    --s3-folder "$REMOTE_STATE_S3_FOLDER_NAME" \
    --date-time-file "$CURRENT_DATE_TIME_FILE" \
    --norm-results-file "$NORM_RESULTS_FILE"
if [ $? -ne 0 ]; then
    echo "Error: Failed to store new state"
    exit 1
fi
echo "New state stored successfully"

# No step 12 (cleanup) for now because it helps with debugging
# when the work folder files are available

echo "Steps 1-11 completed successfully"
echo "Work directory: $WORK_DIR"
echo "Downloaded documents: $LOGSTASH_DOCUMENTS_FILE"
echo "Extracted fields: $EXTRACTED_FIELDS_FILE"
echo "Normalization results: $NORM_RESULTS_FILE"
echo "Comparison results: $COMPARISON_RESULTS_FILE"
echo "Email bodies: $HTML_EMAIL_BODY_FILE, $TEXT_EMAIL_BODY_FILE"
echo "Email report sent to: $SMTP_RECEIVER_ADDRESS"

exit 0
