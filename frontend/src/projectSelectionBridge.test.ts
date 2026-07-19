import { expect, test, vi } from 'vitest';
import { api } from './api';
import {
  installProjectSelectionBridge,
  setPreferredProjectId,
  subscribeProjectSelection,
} from './projectSelectionBridge';

test('prioritizes the console-selected project and observes editor project loads', async () => {
  const listProjects = vi.spyOn(api, 'listProjects').mockResolvedValue([
    { id: 'project-a', title: '主项目' },
    { id: 'project-b', title: '分支项目' },
  ]);
  const listChapters = vi.spyOn(api, 'listChapters').mockResolvedValue([]);
  const observed: string[] = [];
  const unsubscribe = subscribeProjectSelection((projectId) => observed.push(projectId));
  const uninstall = installProjectSelectionBridge();

  setPreferredProjectId('project-b');
  const projects = await api.listProjects();
  await api.listChapters('project-a');

  expect(projects.map((project) => project.id)).toEqual(['project-b', 'project-a']);
  expect(observed).toEqual(['project-a']);
  expect(listProjects).toHaveBeenCalledTimes(1);
  expect(listChapters).toHaveBeenCalledWith('project-a');

  unsubscribe();
  uninstall();
  vi.restoreAllMocks();
});
