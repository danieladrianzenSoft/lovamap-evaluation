# Job Logs & Monitoring

This document explains how to use the `logs` subcommand to query job status and retrieve execution logs from the LOVAMAP Core API.

## Prerequisites

- API credentials configured in `.env` (same as for `submit`)
- The LOVAMAP Core API must be running and accessible

## Quick Reference

```bash
# Get logs for a single job
python run.py logs <job_id>

# Save logs to a file
python run.py logs <job_id> --save logs/my_job.txt

# List recent failed jobs (last 7 days by default)
python run.py logs --status Failed

# List failed jobs from a specific date
python run.py logs --status Failed --start 2026-11-22

# List all jobs in a date range
python run.py logs --start 2026-11-01 --end 2026-11-22

# List jobs with inline stdout/stderr
python run.py logs --status Failed --include-logs

# Paginate through results
python run.py logs --status Completed --limit 25 --page 2

# Fetch all pages at once
python run.py logs --status Failed --all-pages
```

## Single Job Logs

When you provide a job ID, the command fetches the full formatted log from `GET /jobs/{jobId}/logs`. This includes:

- Job metadata (type, status, timestamps)
- Error message (if the job failed)
- Full stdout from the compute container
- Full stderr from the compute container

```bash
$ python run.py logs beadInfo_square100_20261122_103045

=== Job Logs: beadInfo_square100_20261122_103045 ===
Type:      Lovamap
Status:    Failed
Submitted: 2026-11-22T10:30:45Z
Started:   2026-11-22T10:30:46Z
Completed: 2026-11-22T10:31:12Z

=== Error Message ===
[INPUT] Error: Missing required parameters: dz

=== STDOUT ===
...

=== STDERR ===
...
```

Use `--save` to write the output to a file instead of printing:

```bash
python run.py logs beadInfo_square100_20261122_103045 --save data/debug/failed_job.txt
```

## Listing Jobs

When no job ID is given, the command lists jobs matching the provided filters via `GET /jobs`.

### Filtering by status

Valid statuses: `Pending`, `Running`, `Completed`, `Failed`, `Stopped` (case-insensitive). Comma-separate for multiple:

```bash
python run.py logs --status Failed
python run.py logs --status Failed,Stopped
```

### Filtering by date

By default the API returns jobs from the last 7 days. Use `--start` and `--end` to override:

```bash
# All jobs from November 22
python run.py logs --start 2026-11-22

# Custom range
python run.py logs --start 2026-11-01 --end 2026-11-15
```

Dates can be `YYYY-MM-DD` or full ISO 8601 (`2026-11-22T10:00:00Z`).

### Pagination

Results are paginated (default: 50 per page, max 200):

```bash
# Second page, 25 items per page
python run.py logs --page 2 --limit 25

# Fetch and display all pages
python run.py logs --status Failed --all-pages
```

### Including logs in list output

By default, job listings don't include stdout/stderr to keep output concise. Add `--include-logs` to show truncated log previews inline:

```bash
python run.py logs --status Failed --include-logs
```

## Common Use Cases

### After a batch submission run

After running `python run.py submit` on a large batch, check for failures:

```bash
# See all failures from today
python run.py logs --status Failed --start 2026-11-22

# Get detailed logs for a specific failure
python run.py logs beadInfo_square100_20261122_103045
```

### Reconciliation after a crash

If the submission process crashed mid-batch, you can query the API to see what actually ran:

```bash
# All jobs submitted today
python run.py logs --start 2026-11-22 --all-pages

# Just the failures
python run.py logs --status Failed --start 2026-11-22 --all-pages
```

Compare against the output directory to find jobs that completed on the API but weren't downloaded locally.

### Admin debugging

```bash
# Check if any jobs are stuck running
python run.py logs --status Running

# Review all stopped/cancelled jobs
python run.py logs --status Stopped --start 2026-11-01

# Get full logs for a failed job
python run.py logs some-job-id --save debug_logs.txt
```

## API Endpoints Used

| Use Case | Endpoint |
|---|---|
| Single job logs | `GET /jobs/{jobId}/logs` |
| List/query jobs | `GET /jobs?page=&limit=&status=&start=&end=&include=` |

Both endpoints require JWT authentication (handled automatically using `.env` credentials).

## CLI Options Reference

| Option | Description |
|---|---|
| `job_id` (positional) | Job ID to fetch logs for. If omitted, lists jobs. |
| `--api-url URL` | Override the API base URL |
| `--save PATH` | Save single-job logs to a file |
| `--status STATUS` | Filter by status (comma-separated) |
| `--start DATE` | Start of date range (default: 7 days ago) |
| `--end DATE` | End of date range (default: now) |
| `--page N` | Page number (default: 1) |
| `--limit N` | Items per page (default: 50, max: 200) |
| `--include-logs` | Include stdout/stderr preview in list output |
| `--all-pages` | Fetch all pages instead of just the first |
