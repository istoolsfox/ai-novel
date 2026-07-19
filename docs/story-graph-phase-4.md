# Phase 4: Multi-thread Story Graph

This phase adds a structured story graph on top of the persistent autopilot, continuity, and layered-memory systems.

## Scope

The system now models a novel as multiple parallel story threads instead of a single chapter sequence.

Supported thread types:

- main plot
- character arc
- romance
- mystery
- faction
- world change
- foreshadowing
- theme
- subplot

Each finalized chapter can create or update:

- story threads
- story nodes
- node-to-node edges
- per-thread chapter progress

## Persistence

New tables:

- `story_graph_compilations`
- `story_threads`
- `story_thread_states`
- `story_nodes`
- `story_node_states`
- `story_edges`
- `chapter_story_progress`

`story_threads` and `story_nodes` are current-state caches. Their chapter-by-chapter history is retained in the corresponding state tables.

Recompiling the same chapter replaces that chapter's derived graph rows before rebuilding them. It does not duplicate progress or leave removed nodes from the same compilation behind.

## Autopilot integration

The existing `compile_chapter_memory` step now also extracts:

```json
{
  "story_thread_changes": [],
  "story_node_changes": [],
  "story_edge_changes": [],
  "story_progress": []
}
```

The next chapter contract receives:

- active story threads
- open/planned story nodes
- active story edges
- recommended focus threads
- stalled threads

Focus ranking is deterministic and currently uses thread priority, chapters since last progress, stall tolerance, and blocked status. It recommends what should receive attention but does not yet rewrite future plans.

## API

```text
GET  /api/projects/{project_id}/story-graph
GET  /api/projects/{project_id}/story-graph/threads
POST /api/projects/{project_id}/story-graph/threads
GET  /api/projects/{project_id}/story-graph/nodes
POST /api/projects/{project_id}/story-graph/nodes
GET  /api/projects/{project_id}/story-graph/edges
POST /api/projects/{project_id}/story-graph/edges
GET  /api/projects/{project_id}/story-graph/chapters/{chapter_id}/progress
GET  /api/projects/{project_id}/story-graph/focus
```

Manual POST endpoints allow an author or future frontend to seed and adjust graph objects before autonomous generation.

## Deliberate limits

This phase does not yet implement:

- weighted impact propagation across the graph
- automatic future-plan rewriting
- branch/worldline-specific graphs
- graph visualization in the frontend
- Obsidian export
- semantic relevance retrieval for very large graphs

Those belong to later phases.
