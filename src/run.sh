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

# Define file paths for intermediate results
WORK_DIR=""
START_DATE_TIME_FILE=""
CURRENT_DATE_TIME_FILE=""
LOGSTASH_DOCUMENTS_FILE=""
NORM_RESULTS_PREV_FILE=""
NORM_RESULTS_FILE=""

echo "Starting Platform Problem Monitoring process..."

# Step 1: Prepare environment
echo "Step 1: Preparing environment..."
# Capture all output but only use the last line as the work directory
PREPARE_OUTPUT=$(python -m platform_problem_monitoring_core.step1_prepare)
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
NORM_RESULTS_PREV_FILE="$WORK_DIR/norm_results_prev.json"
NORM_RESULTS_FILE="$WORK_DIR/norm_results.json"

# Step 2: Download previous state
echo "Step 2: Downloading previous state..."
python -m platform_problem_monitoring_core.step2_download_previous_state \
    --s3-bucket "$REMOTE_STATE_S3_BUCKET_NAME" \
    --s3-folder "$REMOTE_STATE_S3_FOLDER_NAME" \
    --date-time-file "$START_DATE_TIME_FILE" \
    --norm-results-file "$NORM_RESULTS_PREV_FILE"
if [ $? -ne 0 ]; then
    echo "Error: Failed to download previous state"
    exit 1
fi
echo "Previous state downloaded successfully"

# Step 3: Download logstash documents
echo "Step 3: Downloading logstash documents..."
python -m platform_problem_monitoring_core.step3_download_logstash_documents \
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

# Create an empty normalization results file (temporary until steps 4-5 are implemented)
echo "Creating temporary empty normalization results file..."
echo "" > "$NORM_RESULTS_FILE"
echo "Empty normalization results file created at $NORM_RESULTS_FILE"

# Step 9: Store new state
echo "Step 9: Storing new state..."
python -m platform_problem_monitoring_core.step9_store_new_state \
    --s3-bucket "$REMOTE_STATE_S3_BUCKET_NAME" \
    --s3-folder "$REMOTE_STATE_S3_FOLDER_NAME" \
    --date-time-file "$CURRENT_DATE_TIME_FILE" \
    --norm-results-file "$NORM_RESULTS_FILE"
if [ $? -ne 0 ]; then
    echo "Error: Failed to store new state"
    exit 1
fi
echo "New state stored successfully"

echo "Steps 1-3 and 9 completed successfully"
echo "Work directory: $WORK_DIR"
echo "Downloaded documents: $LOGSTASH_DOCUMENTS_FILE"

# The script would continue with steps 4-8 and 10 in a complete implementation

exit 0
