# CLAUDE.md - gh-galaxy-quest

Human-in-the-loop pipeline to identify high-value GitHub Discussions for the Galaxy Brain achievement.

## What This Repo Is

Scans targeted GitHub repos for unanswered Q&A discussions, scores them against an expertise matrix (MSEE, MSCS, PE Power, AWS Security, CISSP, CCSP, multi-agent orchestration, serverless AI), and surfaces the best opportunities via a rich terminal console.

## Architecture

Four-node pipeline:
- n0_target_ingest — loads target repos and expertise matrix from YAML config
- n1_graphql_fetch — retrieves open discussions via GitHub GraphQL API
- n2_relevance_score — ranks questions against expertise matrix
- n3_triage_queue — pushes high-scoring questions to SQLite state DB

Entry point: hitl_console.py (rich-based terminal UI)

## Running

```bash
poetry run python src/hitl_console.py
```

## Stack

- Python 3.14, managed via poetry
- GitHub GraphQL API (via gh CLI token or PAT)
- SQLite for state tracking (seen, answered, ignored)
- rich for terminal UI

## Repo Conventions

- Branch protection requires approving review (Cerberus-AZ auto-approves)
- Squash merge only
- Every PR references an issue: title ends with (#N), body contains Closes #N
