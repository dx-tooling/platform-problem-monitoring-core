# Requirements

## General overview

The following describes the functional and non-functional features, as well as the technical requirements, for the
commandline-based core component of a software application for unixoid systems called "Platform Problem Monitoring".

## Top-level: The requirements in one line

Input: Logstash messages from an Elasticsearch server; Output: An email with a summary report of the problems found
within those messages.

## High-level: Use-case and motivation, raison d'etre

On a high level, the software solution works as follows:

- Logstash messages are downloaded from an Elasticsearch server.
- The downloaded messages are normalized and summarized, to allow for generalizations like "message 'error for
  user <UUID>: wrong password' occured 10 times"
- A detailed email report with these generalizations, and their deviations compared to a previous run, is sent out.

The motivation for this solution is to allow software engineering teams that already have a working ELK (Elasticsearch,
logstash, Kibana) stack in place, and are thus already collecting relevant information from their own platform (of
systems and software applications), to periodically determine the overall health of their platform, and to do so without
the need to actively take steps for this kind of assessment.

Receiving, in regular intervals, an email that carries the aforementioned kind of information ("what kinds of problem
patterns exist in the logs, and how have these developed since the previous email"), and therefore an email that only
needs to be quickly "scanned" upon receival, fullfills this requirement.

## Mid-level: Process and work mechanisms

Whenever triggered, be it manually or through a task system like cron, the software application will:

1. download all "problem-related" (errors, exceptions, warnings, etc.) logstash documents from the Elasticsearch
   server (of an ELK stack setup) that have been created since the software application last ran,
2. extract the message field from all documents, plus some additional fields,
3. "normalize" these messages by replacing dynamic message parts like timestamps, uuids, numbers etc.,
4. "summarize" these messages by treating identical "normalized" messages as one message "pattern" and counting the
   number of message occurences per pattern
5. compare this summary with the one from the previous run, by asking questions like: which patterns are new?, which
   ones increased or decreased in numbers?, which ones disappeared?, and compile a summary comparison from this,
6. generate, from the summary comparison data and from the latest messages summary, a report in form of a well-designed
   HTML email that visualizes the "problem status quo" of the platform that feeds into the ELK stack, with a special
   emphasis on showing how the problems evolved since the previous run of the software application.

## Mid-level: General architecture, tech stack, technological contraints

Users must be able to install and set up this software solution application quickly and easily on typical unixoid
computer systems like macOS, GNU/Linux, or a BSD variant, without being disproportionately bothered with additional
dependencies that would need to be in place before the software can work.

Therefore, the general constraints that inform the architecture and tech stack look like this:

- The application can be installed by downloading its program files into a single local folder (e.g. through git clone),
  followed by a manageable amount of setup procedure. The resulting installation of the application is then more or
  less "self-contained".
- The application can be run from any widespread command-line shell (e.g. sh, bash, zsh) by starting a single central
  command from within the installation folder.

The following prerequisites are assumed to be fulfilled for the software to be able to do its jobs:

- An Elasticsearch server is available and can, network-wise, be reached and read by means of HTTP requests that
  originate from the machine that hosts the software application.
- An AWS S3 bucket can be read from and written to by the software application, allowing it to store relevant state
  between application runs.
- The application can create a temporary work folder on the local file system while running, and read from and write to
  files within this work folder.
- The application has network access to an SMTP server which can be used to send the resulting report email.
- Any information that is required to connect to these services (Elasticsearch, AWS S3, SMTP server) is provided through
  a central, locally available configuration file whose path is provided when launching the application.

Some further assumptions:

- The application cannot assume that any state from previous runs is available locally when it is started; instead, all
  state that is relevant not only during a single run, but over multiple runs, must be stored centrally in AWS S3
- The application is not a persitent process or daemon; it is launched, does its job, and afterwards exits
- S3 is assumed to be reliably available; no local fallback mechanism is required for state storage
- Storing credentials as plain text in configuration files is acceptable; no encryption is needed
- If any step of the process fails, the entire process should fail immediately

The tech stack for this application is defined as follows:

- It is a software application written in Python 3, and provided in source-code form
- Setup and dependencies are managed via the pyproject.toml approach
- A bash shell script is provided which allows the user to start the application in a straightforward manner, e.g.
  ./run.sh <path-to-config-file>

The architecture is defined as follows:

While the process of generating a new email report will be started through a single run script and executed "in one go",
the underlying application architecture is very modular. This means that the full process is made up of single, isolated
steps, each with their own inputs and outputs; therefore, any single step can be executed in isolation, as long as its
inputs are available.

These are the steps that as a whole form the complete process end-to-end:

1. Prepare environment for a process run
2. Download previous run state
3. Download logstash documents
4. Extract relevant fields from the logstash documents
5. Normalize messages
6. Generate normalization results comparison
7. Generate report email HTML body
8. Send email report
9. Store new run state
10. Clean up work environment

Each of these steps is a Python 3 script that can execute its operation in isolation when given correct inputs.

The different step scripts do not include or call each other.

However, any functionality that is worth sharing between these scripts, will be implemented in a shared library which
the different step scripts will use as needed.

## Performance considerations

The application must be capable of handling large volumes of log data, potentially up to multiple millions of Elasticsearch 
logstash documents between runs. To handle this efficiently:

- Streaming and pagination techniques must be used when interacting with Elasticsearch to prevent memory or resource exhaustion
- It is acceptable if a full process run takes several minutes to complete
- All operations should be optimized for memory efficiency, especially when processing large datasets
- The application should provide appropriate progress feedback during long-running operations

## Normalization logic and email design

The message normalization logic should follow the approach demonstrated in the proof-of-concept implementation, using the 
drain3 library to replace dynamic parts of messages (like timestamps, UUIDs, numbers) with placeholders, allowing for pattern 
recognition across similar message types.

For the HTML email report design:
- The report should be well-designed and visually appealing
- It must work well in as many email clients as possible
- The design should prioritize readability and allow quick scanning of information
- The report should clearly highlight new problems, increased occurrences, and other significant changes
- Visual elements should follow the style patterns demonstrated in the Janus design system reference materials

## Low-level: the process in detail

Here is a blow-by-blow description for all process steps that lead to a new report email, with their respective Inputs, Main operations & side effects, and Outputs:

1. Prepare environment for a process run - file step1_prepare.py
    - Inputs: none
    - Main operations & side effects:
        - verification that all requirements for a run are fulfilled
        - creation of a temporary work folder on the local file system
    - Outputs:
        - the path to the temporary work folder - step2_download_previous_state.py
2. Download previous run state - file step1_prepare.py
    - Inputs:
        - the name of the S3 bucket used for state persistence
        - the name of the S3 subfolder where state is stored
        - the local file path to use for storing a copy of the "date and time of Elasticsearch download from latest run"
          state file
        - the local file path to use for storing a copy of the "normalization results from latest run" state file
    - Main operations & side effects:
        - stored state is downloaded into the local temporary work folder
    - Outputs: none (besides exit code and progress, success, and error messages)
3. Download logstash documents - file step3_download_logstash_documents.py
    - Inputs:
        - the date and time from which to start downloading messages
        - the HTTP base URL of an Elasticsearch server
        - the path to a JSON file that holds the Lucene query definition that defines how to find "problem-related"
          logstash messages
        - the file path to use for storing the downloaded logstash messages in JSON format
        - the file path to use for storing the "date and time of Elasticsearch download" information
    - Main operations & side effects:
        - the inputs are used to download, into the target file, all relevant logstash messages from the Elasticsearch
          server
        - the date and time of this download is stored into a new file at the provided date and time file path
        - pagination and streaming techniques must be used to handle potentially millions of documents
    - Outputs: none (besides exit code and progress, success, and error messages)
4. Extract relevant fields from the logstash documents - file step4_extract_fields.py
    - Inputs:
        - the path to a logstash message documents JSON file
        - the file path to use for storing the extracted fields
    - Main operations & side effects:
        - from each logstash document in the provided file, the Elasticsearch index name, the Elasticsearch document id,
          and the logstash message field is extracted and written into a single like of the target file
    - Outputs: none (besides exit code and progress, success, and error messages)
5. Normalize messages - file step5_normalize_messages.py
    - Inputs:
        - the path to a extracted logstash fields file
        - the local file path to use for storing the normalization results
    - Main operations & side effects:
        - Using the drain3 library, messages in the input file are normalized, and identical normalized messages are
          summarized into one line item in the results file that carries a) the normalized message, b) the number of
          messages that match this normalized message, and c) up to 5 Elasticsearch index names and document ids that
          represent examples of messages matching this normalized message
        - The normalization approach should follow the patterns established in the proof-of-concept implementation
    - Outputs: none (besides exit code and progress, success, and error messages)
6. Generate normalization results comparison - file step6_compare_normalizations.py
    - Inputs:
        - the path to a normalization results file (with the "new" normalization results)
        - the path to a normalization results file (with the "previous" normalization results)
        - the file path to use for storing the normalized messages comparison results
    - Main operations & side effects:
        - both input files are compared, and the results of this comparison are written to the normalized messages
          comparison results file
        - the comparison needs to detect:
            - what are new normalized messages that are found in the new normalization results file, but not in the
              previous normalization results file?
            - what are disappeared normalized messages that are found in the previous normalization results file, but
              not in the new normalization results file?
            - what are normalization results that increased in number since the previous run, and by how much?
            - what are normalization results that decreased in number since the previous run, and by how much?
            - all comparisons must be sorted descending by either the number of messages matching a normalization
              result (for new and disappeared normalized message) or descending by the amount of percentual change (for
              increased and decreased normalization results)
    - Outputs: none (besides exit code and progress, success, and error messages)
7. Generate report email HTML body - file step7_generate_email_bodies.py
    - Inputs:
        - the path to a normalized messages comparison results file
        - the path to a normalization results file
        - the file path to use for storing the HTML version of the resulting email message body
        - the file path to use for storing the plaintext version of the resulting email message body
        - Optionally: a Kibana base URL (KIBANA_DISCOVER_BASE_URL) for the "View in Kibana" button
        - Optionally: a Kibana document deeplink URL structure (KIBANA_DOCUMENT_DEEPLINK_URL_STRUCTURE) with {{index}} and {{id}} placeholders for individual document links
    - Main operations & side effects:
        - creation of a well-designed email report that presents the normalized messages comparison results, followed by
          the top 25 normalization results, in an easy-to-scan and easy-to-comprehend form
        - If a Kibana base URL is provided, a "View in Kibana" button is added to the report
        - If a Kibana document deeplink URL structure is provided, each normalized message presented in the report is accompanied by up to 5
          deep links to message samples matching the normalized message (using the Elasticsearch index name and
          Elasticsearch document id from the normalization results file)
        - If only the Kibana base URL is provided (without the deeplink structure), a legacy format will be used to generate document links
        - The email design should be compatible with a wide range of email clients
        - Both HTML and plaintext versions of the email must be created
    - Outputs: none (besides exit code and progress, success, and error messages)
8. Send email report - step8_send_email_report.py
    - Inputs:
        - the path to an HTML version of the email message body
        - the path to a plaintext version of the resulting email message body
        - an email subject line
        - an SMTP hostname
        - an SMTP port
        - an SMTP username
        - an SMTP password
        - an SMTP sender email address
        - an SMTP receiver email address
    - Main operations & side effects:
        - sends off the email based on the inputs
    - Outputs: none (besides exit code and progress, success, and error messages)
9. Store new run state - step9_store_new_state.py
    - Inputs:
        - the name of the S3 bucket used for state persistence
        - the name of the S3 subfolder where state is stored
        - the path to a file containing the "date and time of Elasticsearch download" state
        - the path to a file containing the "normalization results" state file
    - Main operations & side effects:
        - local state is uploaded to the remote S3 location
    - Outputs: none (besides exit code and progress, success, and error messages)
10. Clean up work environment - step10_cleanup.py
    - Inputs:
        - the path to a local folder
    - Main operations & side effects:
        - remove the local folder
    - Outputs: none (besides exit code and progress, success, and error messages)

The aforementioned run.sh shell script is able to read a configuration file with the following structure:

    REMOTE_STATE_S3_BUCKET_NAME=""
    REMOTE_STATE_S3_FOLDER_NAME=""
    
    ELASTICSEARCH_SERVER_BASE_URL=""
    ELASTICSEARCH_LUCENE_QUERY_FILE_PATH=""
    
    KIBANA_DISCOVER_BASE_URL=""
    KIBANA_DOCUMENT_DEEPLINK_URL_STRUCTURE=""
    
    SMTP_SERVER_HOSTNAME=""
    SMTP_SERVER_PORT=""
    SMTP_SERVER_USERNAME=""
    SMTP_SERVER_PASSWORD=""
    SMTP_SENDER_ADDRESS=""
    SMTP_RECEIVER_ADDRESS=""

If this configuration is stored in a file called platform_problem_monitoring_core.conf, then the run.sh script can be called
as `run.sh ./platform_problem_monitoring_core.conf` and will make use of these parameters when executing the different step
scripts.

Other parameters that are relevant between step script executions, like for example the name of the JSON file where
downloaded logstash documents are stored, are hardcoded within the run.sh shell script (but paths of intermediate result
files are of course located within the temporary work folder created in step 1).

The resulting Python and Bash code must be clean, well documented, with concise and comprehensible naming.

Parameters for scripts that take more than one parameter must always be name-based, not position-based, (that is, `step5_normalize_messages.py --logstash-fields-file=foo.txt --results-file=bar.txt`, not `step5_normalize_messages.py foo.txt bar.txt`)
