# Phase 2: Chapter continuity and memory bridge

This phase extends the persistent autopilot runtime with a continuity loop that runs before a chapter is finalized.

## Pipeline

Each chapter now runs through eight persisted steps:

1. `generate_chapter_brief`
2. `build_chapter_contract`
3. `generate_chapter_draft`
4. `check_chapter_continuity`
5. `repair_chapter_continuity`
6. `recheck_chapter_continuity`
7. `compile_chapter_memory`
8. `finalize_chapter`

The chapter contract makes the previous finalized chapter's ending state, character state, open actions, emotional residue, knowledge boundaries, and anti-repetition notes explicit before draft generation.

## Persisted continuity data

The database now stores:

- `chapter_contracts`: the executable constraints used to generate a chapter
- `chapter_bridges`: the finalized ending state passed to the next chapter
- `continuity_checks`: initial and post-repair validation reports
- `character_states`: chapter-scoped character location, health, emotion, and goal state
- `character_knowledge`: chapter-scoped changes to what each character knows, suspects, or believes

Chapter and project deletion triggers clean up these records.

## Automated repair

The initial check reports time, location, character state, knowledge, emotion, plot, and repetition issues. High or critical issues trigger one targeted repair pass. The repaired chapter is saved as a separate chapter version and checked again. A high-risk failure after recheck stops the job before memory compilation and finalization.

## Inspection API

```text
GET /api/projects/{project_id}/continuity/chapters/{chapter_id}/contract
GET /api/projects/{project_id}/continuity/chapters/{chapter_id}/bridge
GET /api/projects/{project_id}/continuity/chapters/{chapter_id}/checks
GET /api/projects/{project_id}/continuity/character-states
GET /api/projects/{project_id}/continuity/character-knowledge
```

## Deliberate limits

- State and memory extraction still depend on the configured remote model.
- Repair is limited to one targeted pass before recheck.
- Relationship state and item ownership remain part of the next memory expansion.
- A separate worker process and frontend continuity inspector are not included yet.
