# Phase 6: Versions, branches, and worldlines

## Goal

Allow a writer to fork the novel at any chapter and continue along multiple isolated timelines without leaking later facts, character state, graph progress, impact results, or rolling plans across branches.

## Isolation model

Each worldline is backed by a separate internal project record. Existing services already scope all state by `project_id`, so this provides hard isolation without adding `worldline_id` to every table or rewriting the first five phases.

The worldline metadata connects those isolated projects into one family:

- the original project becomes the main worldline lazily;
- a fork creates a new project ID;
- existing APIs operate on the returned worldline project ID;
- active and primary worldlines are pointers, not destructive merges;
- promoting a worldline changes the canonical pointer and does not overwrite the old main line.

## Fork behavior

Forking at chapter `N` copies only state valid at or before `N`:

- chapters and chapter versions through `N`;
- chapter contracts, bridges, checks, character state, and knowledge;
- layered memory history and compilation records;
- story-thread, node, edge, and chapter-progress history;
- impact events and runs through the fork point;
- rolling-plan snapshots and revisions whose source chapter is at or before the fork;
- static project configuration and author-maintained resources;
- wiki revisions that do not depend on later chapters.

Current story-thread and node caches are rebuilt from copied history. They are not copied from the source project's latest state, which prevents a fork at chapter 2 from inheriting chapter 3 outcomes.

## Version history

Every fork writes an immutable `worldline_snapshot` containing:

- source worldline and project;
- fork chapter;
- per-table record counts;
- hashes of inherited chapter drafts and summaries;
- a manifest hash for audit and reproducibility.

Chapter versions are cloned with remapped chapter and version IDs, then evolve independently.

## APIs

```text
GET  /api/projects/{project_id}/worldlines
POST /api/projects/{project_id}/worldlines/fork
GET  /api/projects/{project_id}/worldlines/{worldline_id}
GET  /api/projects/{project_id}/worldlines/compare/{left_id}/{right_id}
POST /api/projects/{project_id}/worldlines/{worldline_id}/activate
POST /api/projects/{project_id}/worldlines/{worldline_id}/promote
POST /api/projects/{project_id}/worldlines/{worldline_id}/archive
```

`activate` returns the project ID clients should use for all normal chapter, memory, graph, impact, and planning APIs.

## Safety rules

- A worldline cannot be forked while its project has a queued, running, or paused generation job.
- The active or primary worldline cannot be archived.
- Archived worldlines cannot be activated or promoted.
- Fork names must be unique among non-archived lines in the same family.
- Promoting a line changes pointers only; it never silently copies or deletes content.

## Current limits

- There is no automatic three-way merge between divergent worldlines.
- The existing project-list endpoint may still show the backing projects; a future frontend should group them by worldline family.
- Filesystem wiki output is reconstructed from copied revisions rather than byte-for-byte copying the source directory.
- Active-worldline selection is metadata; clients switch to the returned project ID instead of transparently rewriting all incoming root-project requests.
