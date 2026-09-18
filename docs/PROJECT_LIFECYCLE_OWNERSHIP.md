# Project Lifecycle Ownership

## Purpose

Define ownership boundaries between QA execution and Project lifecycle control.

## Roles

### QA_EXECUTOR

Allowed:
- create QA evidence;
- create QA result artifacts;
- validate execution state.

Not allowed:
- mutate Project lifecycle;
- move cards independently of approved flow.

### PROJECT_CONTROLLER

Allowed:
- perform Project lifecycle synchronization;
- update Project state after accepted QA result.

## Required flow

Issue
→ PR
→ QA_RESULT
→ QA_ACCEPT
→ QUEUE-GUARD
→ Project Sync
→ Project Card

## Protection rule

Any operation where QA execution directly changes Project lifecycle must be blocked.
