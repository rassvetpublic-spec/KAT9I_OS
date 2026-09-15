# QA Legacy Migration

## Current mode

Old QA Worker protocols remain supported.

## Transition rule

New QA checks may provide additional context:

- PR reference
- exact commit SHA
- required result format
- Evidence summary

## Compatibility

Legacy Worker:
- may continue existing checks;
- must not claim PASS without evidence.

New Worker:
- uses WORKER_QA contract;
- returns structured QA result.
