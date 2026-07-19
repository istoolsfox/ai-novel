import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, expect, test, vi } from 'vitest';
import { controlApi } from '../controlApi';
import { UnifiedConsole } from './UnifiedConsole';

const project = {
  id: 'project-main',
  title: '测试长篇',
  genre: '悬疑',
  target_chapter_count: 8,
};

const chapters = [
  { id: 'chapter-1', project_id: project.id, chapter_number: 1, title: '第一章', status: 'final' },
  { id: 'chapter-2', project_id: project.id, chapter_number: 2, title: '第二章', status: 'final' },
];

const idleSnapshot = {
  job: null,
  steps: [],
  events: [],
  progress: { completed: 0, total: 0, percent: 0 },
};

const runningSnapshot = {
  job: {
    id: 'job-1',
    project_id: project.id,
    mode: 'full_autopilot',
    status: 'running',
    start_chapter: 3,
    end_chapter: 8,
    current_chapter: 3,
    current_step: 'generate_chapter_brief',
    total_steps: 48,
    completed_steps: 1,
  },
  steps: [
    {
      id: 'step-1',
      chapter_id: 'chapter-3',
      chapter_number: 3,
      step_order: 1,
      workflow: 'generate_chapter_brief',
      status: 'running',
      attempt_count: 1,
      max_retries: 2,
    },
  ],
  events: [],
  progress: { completed: 1, total: 48, percent: 2.08 },
};

function mockConsoleApi() {
  vi.spyOn(controlApi, 'listProjects').mockResolvedValue([project]);
  vi.spyOn(controlApi, 'listChapters').mockResolvedValue(chapters);
  vi.spyOn(controlApi, 'autopilotStatus').mockResolvedValue(idleSnapshot);
  vi.spyOn(controlApi, 'memoryContext').mockResolvedValue({
    hard_facts: [{ fact_key: 'map', fact_text: '主角已经找到入口地图。', fact_status: 'confirmed', confidence: 1 }],
    relationship_states: [],
    item_ownership: [],
    narrative_debts: [{ debt_key: 'owner', description: '谁控制档案馆？', status: 'open' }],
    active_foreshadowings: [],
  });
  vi.spyOn(controlApi, 'storyGraph').mockResolvedValue({
    all_threads: [{ thread_key: 'archive_main', title: '旧档案馆主线', status: 'active' }],
    all_nodes: [{ node_key: 'enter_archive', title: '进入档案馆', status: 'planned' }],
    story_edges: [],
    stalled_threads: [],
  });
  vi.spyOn(controlApi, 'currentPlan').mockResolvedValue([
    {
      chapter_number: 3,
      status: 'planned',
      locked: false,
      primary_thread_key: 'archive_main',
      secondary_thread_keys: [],
      target_node_keys: ['enter_archive'],
      goal: '进入档案馆',
      must_address: [],
      avoid: [],
      risk_score: 0.2,
      revision: 1,
    },
  ]);
  vi.spyOn(controlApi, 'impactRuns').mockResolvedValue([]);
  vi.spyOn(controlApi, 'worldlines').mockResolvedValue({
    root_project_id: project.id,
    current_worldline_id: 'line-main',
    current_project_id: project.id,
    active_worldline_id: 'line-main',
    primary_worldline_id: 'line-main',
    isolation_model: 'project_backed',
    events: [],
    worldlines: [
      {
        id: 'line-main',
        root_project_id: project.id,
        project_id: project.id,
        name: '主世界线',
        fork_chapter_number: 0,
        status: 'active',
        is_primary: true,
        is_active: true,
      },
    ],
  });
  vi.spyOn(controlApi, 'obsidianStatus').mockResolvedValue({ status: 'not_exported', file_count: 0 });
  vi.spyOn(controlApi, 'continuityChecks').mockResolvedValue([
    {
      id: 'check-1',
      chapter_id: 'chapter-2',
      chapter_number: 2,
      stage: 'final',
      status: 'pass',
      score: 96,
      payload: { issues: [] },
    },
  ]);
}

afterEach(() => {
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

test('loads the autonomous dashboard and starts a managed chapter range', async () => {
  vi.stubGlobal('EventSource', undefined);
  mockConsoleApi();
  const start = vi.spyOn(controlApi, 'startAutopilot').mockResolvedValue(runningSnapshot);

  render(<UnifiedConsole />);
  fireEvent.click(screen.getByRole('button', { name: '打开统一托管控制台' }));

  expect(await screen.findByRole('dialog', { name: '统一托管控制台' })).toBeInTheDocument();
  expect(await screen.findByText('旧档案馆主线')).toBeInTheDocument();
  expect(screen.getByText('1 条关系状态')).toBeInTheDocument();
  expect(screen.getByText('project_backed')).toBeInTheDocument();

  fireEvent.click(screen.getByRole('button', { name: /托管任务/ }));
  fireEvent.change(screen.getByLabelText('起始章节'), { target: { value: '3' } });
  fireEvent.change(screen.getByLabelText('结束章节'), { target: { value: '6' } });
  fireEvent.click(screen.getByRole('button', { name: '启动托管' }));

  await waitFor(() => {
    expect(start).toHaveBeenCalledWith(project.id, {
      start_chapter: 3,
      end_chapter: 6,
      mode: 'full_autopilot',
      max_retries: 2,
    });
  });
  expect(await screen.findByText('generate_chapter_brief')).toBeInTheDocument();
  expect(screen.getByText('running')).toBeInTheDocument();
});

test('exports the selected worldline to Obsidian and exposes the archive download', async () => {
  vi.stubGlobal('EventSource', undefined);
  mockConsoleApi();
  const exportVault = vi.spyOn(controlApi, 'exportObsidian').mockResolvedValue({ status: 'completed' });
  vi.mocked(controlApi.obsidianStatus)
    .mockResolvedValueOnce({ status: 'not_exported', file_count: 0 })
    .mockResolvedValue({
      status: 'completed',
      file_count: 24,
      vault_path: '/data/project-main/exports/obsidian/main',
      archive_path: '/data/project-main/exports/obsidian/main.zip',
    });

  render(<UnifiedConsole />);
  fireEvent.click(screen.getByRole('button', { name: '打开统一托管控制台' }));
  await screen.findByRole('dialog', { name: '统一托管控制台' });
  fireEvent.click(screen.getByRole('button', { name: /Obsidian/ }));
  fireEvent.click(screen.getByRole('button', { name: '生成 Vault 与 ZIP' }));

  await waitFor(() => {
    expect(exportVault).toHaveBeenCalledWith(project.id, {
      include_drafts: true,
      force_rebuild: false,
      create_archive: true,
    });
  });
  expect(await screen.findByText('/data/project-main/exports/obsidian/main')).toBeInTheDocument();
  const download = screen.getByRole('link', { name: '下载 ZIP' });
  expect(download).toHaveAttribute('href', `/api/projects/${project.id}/obsidian/download`);
});
