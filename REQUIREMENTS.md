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
    - Inputs: none
    - Main operations & side effects:
        - verification that all requirements for a run are fulfilled
        - creation of a temporary work folder on the local file system
    - Outputs:
        - the path to the temporary work folder
2. Download previous run state
    - Inputs:
        - the name of the S3 bucket used for state persistence
        - the name of the S3 subfolder where state is stored
        - the local file path to use for storing a copy of the "date and time of Elasticsearch download from latest run"
          state file
        - the local file path to use for storing a copy of the "messages summary from latest run" state file
    - Main operations & side effects:
        - stored state is downloaded into the local temporary work folder
    - Outputs: none (besides exit code)
3. Download logstash documents
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
    - Outputs: none (besides exit code)
4. Extract relevant fields from the logstash documents
    - Inputs:
        - the path to a logstash message documents JSON file
        - the file path to use for storing the extracted fields
    - Main operations & side effects:
        - from each logstash document in the provided file, the Elasticsearch index name, the Elasticsearch document id,
          and the logstash message field is extracted and written into a single like of the target file
    - Outputs: none (besides exit code)
5. Normalize messages
    - Inputs:
        - the path to a extracted logstash fields file
        - the local file path to use for storing the normalization results
    - Main operations & side effects:
        - Using the drain3 library, messages in the input file are normalized, and identical normalized messages are
          summarized into one line item in the results file that carries a) the normalized message, b) the number of
          messages that match this normalized message, and c) up to 5 Elasticsearch index names and document ids that
          represent examples of messages matching this normalized message
    - Outputs: none (besides exit code)
6. Generate summary comparison
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
    - Outputs: none (besides exit code)
7. Generate report email HTML body
    - Inputs:
        - the path to a normalized messages comparison results file
        - the path to a normalization results file
        - the file path to use for storing the HTML version of the resulting email message body
        - the file path to use for storing the plaintext version of the resulting email message body
        - Optionally: a Kibana base URL
    - Main operations & side effects:
        - creation of a well-designed email report that presents the normalized messages comparison results, followed by
          the top 25 normalization results, in an easy-to-scan and easy-to-comprehend form
        - If a Kibana base URL is provided, each normalized message presented in the report is accompanied by up to 5
          deep links to message samples matching the normalized message (using the Elasticsearch index name and
          Elasticsearch document id from the normalization results file)

- Outputs: none (besides exit code)

Each of these steps is a Python 3 script that can execute its operation in isolation when given correct inputs.
The different step scripts do not include or call each other. However, any functionality that is worth sharing between
these scripts, can be implemented in a shared library which the different step scripts use as needed.
