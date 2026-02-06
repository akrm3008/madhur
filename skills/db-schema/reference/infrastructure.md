# Infrastructure Models

Source: `common-python-utils/src/db/models/infrastructure/`

## TaskRun (`task_runs`)

Base: TimestampedIdBase

| Column | Type | Constraints |
|--------|------|-------------|
| id | Integer | PK |
| scan_id | Integer | FK → scans.id, nullable, indexed |
| content_discovery_scan_id | Integer | FK → content_discovery_scans.id, nullable, indexed |
| task_name | String(100) | indexed — e.g., "waymore", "content_discovery", "nuclei_scan", "ffuf" |
| flow_run_id | String(250) | nullable, indexed — Prefect flow run ID |
| status | Enum(TaskRunStatus) | default PENDING |
| started_at | DateTime | nullable |
| completed_at | DateTime | nullable |
| task_metadata | JSONB | nullable — e.g., {"urls_found": 5000, "duration_seconds": 3600} |

Relationships: domain_collection_scan, content_discovery_scan

### TaskRunStatus Enum
PENDING, RUNNING, COMPLETED, FAILED, CANCELLED, SKIPPED
