# Phase 7: Obsidian vault export and visual knowledge base

## Goal

Export every isolated worldline as a self-contained Obsidian vault without changing the existing writing, memory, story-graph, impact, or planning services.

Each backing worldline project receives its own vault and ZIP archive. The exporter reads the current project-scoped state, so no facts, chapters, graph nodes, impact paths, or plans cross worldline boundaries.

## Vault structure

```text
README.md
manifest.json
00-首页/
01-章节/
02-人物/
03-人物关系/
04-剧情线/
05-剧情节点/
06-时间线/
07-伏笔/
08-叙事债务/
09-物品/
10-影响传播/
11-滚动计划/
Canvas/
```

Markdown notes include YAML frontmatter, stable source keys, worldline tags, and Obsidian wikilinks. The export includes:

- complete chapter notes and chapter-ending state;
- current character state and per-character knowledge boundaries;
- current relationship and item ownership state;
- story threads, nodes, dependencies, chapter progress, and status;
- timeline summaries from chapter bridges;
- foreshadowing and narrative-debt lifecycle state;
- impact paths, scores, depths, and planning observations;
- current rolling-plan items and lock/risk state.

## Canvas files

`Canvas/剧情网络.canvas` lays story threads out as columns and links story-node files with the persisted graph edges.

`Canvas/世界线总览.canvas` lays chapters out chronologically, adds story-thread files below them, and links each chapter to the threads it actually advanced.

Both files use Obsidian's JSON Canvas file-node and edge shape and point to the generated Markdown files.

## Incremental rebuild

The exporter stores a SHA-256 hash for every managed file. A later export:

- creates new files;
- rewrites only files whose content changed;
- leaves unchanged files untouched;
- deletes stale files that were managed by the previous export;
- never deletes untracked notes added by the writer;
- preserves the previous generated timestamp when the vault content hash is unchanged.

A machine-readable `manifest.json` records project/worldline metadata, aggregate counts, the vault content hash, and every generated file's source key and hash.

## APIs

```text
POST   /api/projects/{project_id}/obsidian/export
GET    /api/projects/{project_id}/obsidian/status
GET    /api/projects/{project_id}/obsidian/manifest
GET    /api/projects/{project_id}/obsidian/download
DELETE /api/projects/{project_id}/obsidian/export
```

The export request accepts:

- `include_drafts`: include non-final chapters;
- `force_rebuild`: rewrite all managed files even when hashes match;
- `create_archive`: create or remove the ZIP archive.

## Storage

Vaults are written beneath the backing project's export directory:

```text
<project_root>/exports/obsidian/<worldline-name>-<worldline-id>/
```

The ZIP archive is written next to the vault directory. Download paths are resolved and checked against the project's root before they are served.

## Current limits

- The frontend does not yet expose export controls or embedded Canvas previews.
- Obsidian community plugins and custom CSS snippets are not bundled.
- User-authored notes inside an exported vault are preserved locally but are not imported back into the application database.
- Canvas layout is deterministic rather than interactively optimized for very large graphs.
- Export runs synchronously in the API process; a later phase can move large-vault packaging into a durable background job.
