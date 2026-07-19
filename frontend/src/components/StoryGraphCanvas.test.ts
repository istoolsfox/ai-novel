import { expect, test } from 'vitest';
import { buildStoryFlow } from './StoryGraphCanvas';

test('builds thread columns, story nodes, graph edges, and restores saved positions', () => {
  window.localStorage.setItem(
    'ai-novel:story-graph-positions:project-1',
    JSON.stringify({ 'node:enter_archive': { x: 810, y: 320 } }),
  );

  const flow = buildStoryFlow(
    'project-1',
    [
      { thread_key: 'archive_main', title: '旧档案馆主线', status: 'active', current_stage: '寻找入口' },
      { thread_key: 'trust_arc', title: '信任线', status: 'active' },
    ],
    [
      { node_key: 'find_map', thread_key: 'archive_main', title: '找到地图', status: 'completed', planned_chapter: 1 },
      { node_key: 'enter_archive', thread_key: 'archive_main', title: '进入档案馆', status: 'planned', planned_chapter: 3 },
    ],
    [
      { id: 'edge-1', source_node_key: 'find_map', target_node_key: 'enter_archive', relation_type: 'causes', weight: 0.9 },
    ],
  );

  expect(flow.nodes.map((node) => node.id)).toEqual(expect.arrayContaining([
    'thread:archive_main',
    'thread:trust_arc',
    'node:find_map',
    'node:enter_archive',
  ]));
  expect(flow.nodes.find((node) => node.id === 'node:enter_archive')?.position).toEqual({ x: 810, y: 320 });
  expect(flow.edges).toEqual(expect.arrayContaining([
    expect.objectContaining({ id: 'edge-1', source: 'node:find_map', target: 'node:enter_archive', label: 'causes' }),
    expect.objectContaining({ id: 'membership:archive_main:enter_archive' }),
  ]));
});
