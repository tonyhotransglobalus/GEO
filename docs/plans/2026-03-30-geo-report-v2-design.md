# GEO Report V2 Design

## Rollout Addendum

V2 now includes a small rollout metadata contract so shadow-mode runs and V1 comparison eligibility are explicit in the payload.

### Rollout Metadata

- `shadow_run`: indicates whether the run is intended as an internal shadow run
- `comparable_to_v1`: indicates whether the run can be compared against V1 for rollout review

### Promotion Gate

Before V2 is treated as client-ready, the rollout checklist should confirm:

- decision-grade thresholds are reviewed
- the report is readable by a non-technical reviewer
- a named promotion owner signs off
- the V1 versus V2 comparison outcome is recorded
- shadow-mode runs preserve comparison history and do not overwrite the stable compatibility copy

### Acceptance Checklist

The detailed checklist lives in [2026-03-30-geo-report-v2-acceptance-checklist.md](2026-03-30-geo-report-v2-acceptance-checklist.md).
