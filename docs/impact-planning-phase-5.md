# Phase 5: Dynamic Impact Propagation and Rolling Planning

## Goal

Turn finalized chapter changes into bounded, explainable impact calculations and use those results to continuously maintain the next 3–10 chapters without rewriting finalized text.

## Runtime placement

Impact analysis and rolling-plan reconciliation run inside the finalization barrier, after layered memory and story-graph compilation have committed and before the chapter is finalized. They are independently persisted in their own tables, while the existing eight-step autopilot contract remains compatible with older clients and queued jobs.

## Impact propagation

- Root events are compiled from chapter-specific changes in story threads, nodes, edges, facts, relationships, items, narrative debts and foreshadowings.
- Story-node effects propagate through active graph edges with relation-specific attenuation.
- Default maximum depth: 3.
- Default cutoff threshold: 0.15.
- Reverse dependency awareness uses a reduced weight so downstream changes can still flag upstream assumptions without overwhelming the graph.
- Each target stores score, depth, path and reason.

Default relation factors:

| Relation | Factor |
|---|---:|
| causes | 0.90 |
| depends_on | 0.88 |
| blocks | 0.92 |
| pays_off | 0.86 |
| reveals | 0.78 |
| conflicts_with | 0.76 |
| continues | 0.74 |
| plants | 0.68 |
| alternative_to | 0.58 |

## Observations

The engine emits planning observations for:

- future plans that reference impacted nodes or threads;
- overdue narrative debts;
- stalled story threads;
- high-risk changes that should be addressed in the rolling window.

## Rolling planner

The planner maintains a current plan for each future chapter and a revision history.

Each plan item includes:

- primary and secondary story threads;
- target story nodes;
- chapter goal;
- must-address obligations;
- avoid rules;
- risk score;
- rationale;
- lock state and revision.

Rules:

1. Finalized chapters are never rewritten.
2. Locked plan items are preserved.
3. Impacted unlocked items are recalculated.
4. Overdue debts and near-payoff foreshadowings enter `must_address`.
5. Re-running the same reconciliation does not append a revision when the plan is unchanged.
6. The next chapter brief and chapter contract receive the current rolling-plan item.

## Tables

- `impact_events`
- `impact_runs`
- `impact_targets`
- `impact_observations`
- `rolling_plan_snapshots`
- `rolling_plan_items`
- `rolling_plan_item_revisions`

## APIs

- `GET /api/projects/{project_id}/impact/runs`
- `GET /api/projects/{project_id}/impact/runs/{run_id}`
- `GET /api/projects/{project_id}/impact/chapters/{chapter_id}`
- `POST /api/projects/{project_id}/impact/analyze`
- `GET /api/projects/{project_id}/planning/current`
- `GET /api/projects/{project_id}/planning/history`
- `GET /api/projects/{project_id}/planning/chapters/{chapter_number}`
- `POST /api/projects/{project_id}/planning/chapters/{chapter_number}/lock`
- `POST /api/projects/{project_id}/planning/reconcile`

## Current limits

- Planning is deterministic and does not yet ask a model to rewrite a full volume outline.
- Entity-to-node links outside the story graph are represented as observations rather than propagated graph edges.
- Plans are project-wide and are not yet isolated by branch or worldline.
- The frontend does not yet include impact-path or rolling-calendar views.
