# Notes

## Runbook

    python3 -m platform_problem_monitoring_core.step5_download_logstash_documents \
        --elasticsearch-url "http://127.0.0.1:9201" \
        --query-file "/Users/manuel/git/github/dx-tooling/platform-problem-monitoring-core/src/lucene_query.json" \
        --start-date-time-file "/tmp/latest-date-time.txt" \
        --output-file "/tmp/docs.json" \
        --current-date-time-file "/tmp/cur-date-time.txt"

    curl -s -X GET "http://127.0.0.1:9201/_search?pretty" -H 'Content-Type: application/json' -d'
        {
        "query": {
        "query_string" : {
        "query" : "@timestamp: ['2025-03-04T00:00:00.000' TO '2025-03-04T01:00:00.000'] AND type: \"symfony-errors\""
        }
        }
    }
    '

## TODOs & Ideas

- add step 12 (cleanup) to ppmc
- add ppmc option to disable cleanup step 12
