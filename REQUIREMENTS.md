# Requirements

## General overview

The following describes the functional and non-functional features, as well as the technical requirements, for the commandline-based core component of a software application for unixoid systems called "Platform Problem Monitoring".


## Top-level: The requirements in one line

Input: Logstash messages from an Elasticsearch server; Output: An email with a summary report of the problems found within those messages.


## High-level: Use-case and motivation, raison d'etre

On a high level, the software solution works as follows:

- Logstash messages are downloaded from an Elasticsearch server.
- The downloaded messages are normalized and summarized, to allow for generalizations like "message 'error for user <UUID>: wrong password' occured 10 times"
- A detailed email report with these generalizations, and their deviations compared to a previous run, is sent out.

The motivation for this solution is to allow software engineering teams that already have a working ELK (Elasticsearch, logstash, Kibana) stack in place, and are thus already collecting relevant information from their own platform (of systems and software applications), to periodically determine the overall health of their platform, and to do so without the need to actively take steps for this kind of assessment.

Receiving, in regular intervals, an email that carries the aforementioned kind of information ("what kinds of problem patterns exist in the logs, and how have these developed since the previous email"), and therefore an email that only needs to be quickly "scanned" upon receival, fullfills this requirement. 


## Mid-level: Process and work mechanisms

Whenever triggered, be it manually or through a task system like cron, the software application will:

1. download all "problem-related" (errors, exceptions, warnings, etc.) logstash documents from the Elasticsearch server (of an ELK stack setup) that have been created since the software application last ran,
2. extract the message field from all documents, plus some additional fields,
3. "normalize" these messages by replacing dynamic message parts like timestamps, uuids, numbers etc.,
4. "summarize" these messages by treating identical "normalized" messages as one message "pattern" and counting the number of message occurences per pattern 
5. compare this summary with the one from the previous run, by asking questions like: which patterns are new?, which ones increased or decreased in numbers?, which ones disappeared?, and compile a summary comparison from this,
6. generate, from the summary comparison data and from the latest messages summary, a report in form of a well-designed HTML email that visualizes the "problem status quo" of the platform that feeds into the ELK stack, with a special emphasis on showing how the problems evolved since the previous run of the software application.


## Mid-level: General architecture, tech stack, technological contraints

Users must be able to install and set up this software solution application quickly and easily on typical unixoid computer systems like macOS, GNU/Linux, or a BSD variant, without being disproportionately bothered with additional dependencies that would need to be in place before the software can work.

Therefore, the general constraints that inform the architecture and tech stack look like this:

- The application can be installed by downloading its program files into a single local folder (e.g. through git clone), followed by a manageable amount of setup procedure. The resulting installation of the application is then more or less "self-contained".
- The application can be run from any widespread command-line shell (e.g. sh, bash, zsh) by starting a single central command from within the installation folder.

The following prerequisites are assumed to be fulfilled for the software to be able to do its jobs:

- An Elasticsearch server is available and can, network-wise, be reached and read by means of HTTP requests that originate from the machine that hosts the software application.
- An AWS S3 bucket can be read from and written to by the software application, allowing it to store relevant state between application runs.
- The application can create a temporary work folder on the local file system while running, and read from and write to files within this work folder.
- The application has network access to an SMTP server which can be used to send the resulting report email.
- Any information that is required to connect to these services (Elasticsearch, AWS S3, SMTP server) is provided through a central, locally available configuration file whose path is provided when launching the application.

Some further assumptions:

- The application cannot assume that any state from previous runs is available locally when it is started; instead, all state that is relevant not only during a single run, but over multiple runs, must be stored centrally in AWS S3
- The application is not a persitent process or daemon; it is launched, does its job, and afterwards exits

The tech stack for this application is defined as follows:

- It is a software application written in Python 3, and provided in source-code form
- Setup and dependencies are managed via the pyproject.toml approach
- A bash shell script is provided which allows the user to start the application in a straightforward manner, e.g. ./run.sh <path-to-config-file>

The architecture is defined as follows:

While the process of generating a new email report will be started through a single run script and executed "in one go", the underlying application architecture is very modular. This means that the full process is made up of single, isolated steps, each with their own inputs and outputs; therefore, any single step can be executed in isolation, as long as its inputs are available.

These are the steps that as a whole form the complete process end-to-end:

1. Prepare environment for a process run
   - Inputs: none
   - Operation: Verification that all requirements for a run a fulfilled, creation of a temporary work folder on the local file system
   - Outputs:
     - The path to the temporary work folder
2. Download previous run state
   - Inputs:
     - The path to the temporary work folder from step 1
     - The name of the S3 bucket used for state persistence
     - The name of the S3 subfolder where state is stored
   - Operation:
     - Stored state is downloaded into the local temporary work folder
   - Outputs: the path
3. Download logstash documents
   - Inputs:
     - the HTTP base URL of an Elasticsearch server
     - the date and time of the previous run's Elasticsearch download
     - the path to a local JSON file that holds the Lucene query definition that defines how to find "problem-related" logstash messages
   - Operation:
     - All inputs are used to download all relevant logstash messages from the Elasticsearch server that were added since the previous run


Each of these 
