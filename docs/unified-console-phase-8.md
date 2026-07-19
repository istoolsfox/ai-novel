# Phase 8: Unified frontend control console

## Goal

Expose the autonomous writing runtime through one React control center without rewriting the existing chapter editor or coupling the new console to the large monolithic `App.tsx` component.

## Integration model

The console is mounted beside the existing application in `main.tsx` and opens from a fixed launcher. It maintains its own project/worldline selection and calls the same public backend APIs used by external clients.

This keeps the current editor stable while making phases 1–7 accessible from one place.

## Modules

- Overview: job progress, chapter count, memory totals, graph totals, planning, worldlines, continuity, and Obsidian status.
- Autopilot: start ranges, select mode, set retries, pause, resume, stop, retry failed steps, and watch live events.
- Continuity: inspect the latest chapter's initial, repair, and final checks.
- Layered memory: inspect hard facts, relationship states, item ownership, narrative debts, and active foreshadowing.
- Story graph: inspect threads, nodes, edges, stages, statuses, and stalled lines.
- Rolling planning: inspect future chapter plans and lock or unlock individual plans.
- Worldlines: fork, activate, promote, and archive isolated story timelines.
- Obsidian: create an incremental vault/ZIP for the selected worldline and download the archive.

## Live task updates

The browser subscribes to the autopilot SSE endpoint. A four-second status poll remains active while a job is queued, running, or paused so the console can recover if the SSE connection is unavailable.

## Frontend isolation

The existing editor remains unchanged. The new implementation is contained in:

- `frontend/src/controlApi.ts`
- `frontend/src/components/UnifiedConsole.tsx`
- `frontend/src/unified-console.css`
- `frontend/src/components/UnifiedConsole.test.tsx`

Only `frontend/src/main.tsx` is changed to mount the console.

## CI

A dedicated frontend workflow runs:

```text
npm ci
npm test
npm run build
```

The backend workflow remains unchanged and continues to validate all phase 1–7 behavior.

## Current limits

- The console has its own selected project instead of synchronizing the existing editor's selected project state.
- Story graph visualization uses dense operational lists; an interactive node canvas remains a later enhancement.
- Large continuity payloads are shown as structured JSON rather than a dedicated issue editor.
- Worldline comparison is not yet rendered in the frontend.
- Obsidian export is synchronous because the phase-seven backend endpoint is synchronous.
