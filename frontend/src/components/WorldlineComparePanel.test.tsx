import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, expect, test, vi } from 'vitest';
import { controlApi } from '../controlApi';
import WorldlineComparePanel from './WorldlineComparePanel';

const worldlines = [
  {
    id: 'line-main',
    root_project_id: 'project-main',
    project_id: 'project-main',
    name: '主世界线',
    fork_chapter_number: 0,
    status: 'active',
    is_primary: true,
  },
  {
    id: 'line-branch',
    root_project_id: 'project-main',
    project_id: 'project-branch',
    name: '地面调查线',
    fork_chapter_number: 2,
    status: 'active',
    is_primary: false,
  },
];

afterEach(() => vi.restoreAllMocks());

test('compares two worldlines and renders chapter and state differences', async () => {
  const compare = vi.spyOn(controlApi, 'compareWorldlines').mockResolvedValue({
    root_project_id: 'project-main',
    left: { ...worldlines[0], chapter_count: 4 },
    right: { ...worldlines[1], chapter_count: 3 },
    shared_prefix_chapter: 2,
    chapter_differences: [
      {
        chapter_number: 3,
        change: 'modified',
        left: { title: '进入旧档案馆' },
        right: { title: '转向地面调查' },
      },
    ],
    memory_facts: { only_left: ['archive_truth'], only_right: ['surface_witness'], changed: [] },
    story_threads: { only_left: [], only_right: [], changed: ['archive_main'] },
    story_nodes: { only_left: ['enter_archive'], only_right: ['find_witness'], changed: [] },
    rolling_plan: { only_left: [], only_right: [], changed: ['4'] },
  });

  render(<WorldlineComparePanel projectId="project-main" worldlines={worldlines} />);
  fireEvent.click(screen.getByRole('button', { name: '开始比较' }));

  await waitFor(() => expect(compare).toHaveBeenCalledWith('project-main', 'line-main', 'line-branch'));
  expect(await screen.findByText('第 2 章')).toBeInTheDocument();
  expect(screen.getByText('进入旧档案馆')).toBeInTheDocument();
  expect(screen.getByText('转向地面调查')).toBeInTheDocument();
  expect(screen.getByText('archive_main')).toBeInTheDocument();
});
