# Phase 9 — Production integration and visualization

## Scope

Phase 9 turns the phase-eight control console into a production-facing part of the main React application without rewriting the existing editor.

## Shared project selection

`ProductionShell` coordinates the editor and the control console through a small API bridge:

- editor project changes are observed from the editor's existing chapter-loading call
- console project changes become the preferred project and remount the editor once
- activating or promoting a worldline switches both surfaces to that worldline's backing project
- the original `App.tsx` remains unchanged

This is an incremental migration bridge. A future decomposition of `App.tsx` can replace it with a normal React context once the editor state is split into smaller stores.

## Lazy loading and code splitting

The initial application now loads only the lightweight console launcher. Additional chunks are loaded in stages:

1. `UnifiedConsolePanel` when the writer opens the console
2. `StoryGraphCanvas` when the graph section is opened
3. `WorldlineComparePanel` when the worldline section is opened

This keeps graph and comparison code out of the first-load bundle.

## Draggable story graph

The story graph uses React Flow and supports:

- thread-column layout
- story-node status styling
- causal, dependency, reveal, plant, payoff and other graph edges
- node selection and details
- drag-and-drop positioning
- local per-project position persistence
- minimap, zoom, pan and fit-to-view controls

The operational thread and node lists remain below the canvas so the graph is still usable when the visual layout is dense.

## Worldline comparison

The worldline section can compare two active worldlines and displays:

- shared chapter prefix
- modified, left-only and right-only chapters
- memory fact differences
- story-thread differences
- story-node differences
- rolling-plan differences

The comparison is read-only. It does not merge branches.

## Validation

Frontend validation includes:

- all existing application tests
- project selection bridge behavior
- graph layout and saved-position restoration
- worldline comparison requests and rendering
- TypeScript production build
- Vite chunk output

Backend phase-one through phase-seven tests remain unchanged.
