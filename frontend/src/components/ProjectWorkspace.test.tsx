import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { expect, test, vi } from 'vitest';
import { api, Project } from '../api';
import { WorkspaceProvider } from '../shell/workspace';
import { ProjectSwitcher } from './ProjectSwitcher';
import { ProjectsManagerModal } from './ProjectsManagerModal';

if (!globalThis.ResizeObserver) {
  globalThis.ResizeObserver = class ResizeObserver {
    observe() {}
    unobserve() {}
    disconnect() {}
  };
}

const projectA: Project = { id: 'p1', title: '雨夜玫瑰', genre: '悬疑', topic: '记忆改写' };
const projectB: Project = { id: 'p2', title: '长夜灯', genre: '古风' };

function mockProjects() {
  vi.spyOn(api, 'listProjects').mockResolvedValue([projectA, projectB]);
  vi.spyOn(api, 'createProject').mockResolvedValue({ id: 'p3', title: '新故事' });
  vi.spyOn(api, 'updateProject').mockResolvedValue({ id: 'p1', title: '雨夜玫瑰·修订' });
  vi.spyOn(api, 'deleteProject').mockResolvedValue({ ok: true });
}

function renderWithProviders(ui: React.ReactElement, projectId?: string) {
  return render(
    <MemoryRouter initialEntries={[projectId ? `/projects/${projectId}/overview` : '/projects']}>
      <WorkspaceProvider projectId={projectId}>{ui}</WorkspaceProvider>
    </MemoryRouter>,
  );
}

test('切换器显示当前项目，展开后可见全部项目与管理入口', async () => {
  mockProjects();
  renderWithProviders(<ProjectSwitcher />, 'p1');

  expect(await screen.findByText('雨夜玫瑰')).toBeInTheDocument();
  fireEvent.click(screen.getByRole('button', { name: '切换项目' }));
  expect(screen.getByText('长夜灯')).toBeInTheDocument();
  expect(screen.getByText('管理')).toBeInTheDocument();
  expect(screen.getByText('新建项目')).toBeInTheDocument();
});

test('管理弹窗支持新建项目', async () => {
  mockProjects();
  renderWithProviders(<ProjectsManagerModal onClose={() => undefined} />);

  fireEvent.click(await screen.findByText('新建项目'));
  fireEvent.change(screen.getByPlaceholderText('如：雨夜玫瑰'), { target: { value: '新故事' } });
  fireEvent.click(screen.getByRole('button', { name: '创建项目' }));

  await waitFor(() => expect(api.createProject).toHaveBeenCalledTimes(1));
  expect(vi.mocked(api.createProject).mock.calls[0][0]).toMatchObject({ title: '新故事' });
});

test('管理弹窗编辑项目并保存', async () => {
  mockProjects();
  renderWithProviders(<ProjectsManagerModal onClose={() => undefined} />);

  fireEvent.click(await screen.findByRole('button', { name: '编辑 雨夜玫瑰' }));
  fireEvent.change(screen.getByDisplayValue('雨夜玫瑰'), { target: { value: '雨夜玫瑰·修订' } });
  fireEvent.click(screen.getByRole('button', { name: '保存修改' }));

  await waitFor(() => expect(api.updateProject).toHaveBeenCalledTimes(1));
  expect(vi.mocked(api.updateProject).mock.calls[0][1]).toMatchObject({ title: '雨夜玫瑰·修订' });
});

test('删除项目需要输入项目名确认', async () => {
  mockProjects();
  renderWithProviders(<ProjectsManagerModal onClose={() => undefined} />);

  fireEvent.click(await screen.findByRole('button', { name: '删除 雨夜玫瑰' }));
  expect(screen.getByRole('button', { name: '永久删除' })).toBeDisabled();

  const input = screen.getByPlaceholderText('输入项目名称「雨夜玫瑰」以确认删除');
  fireEvent.change(input, { target: { value: '错的名字' } });
  expect(screen.getByRole('button', { name: '永久删除' })).toBeDisabled();
  fireEvent.change(input, { target: { value: '雨夜玫瑰' } });
  expect(screen.getByRole('button', { name: '永久删除' })).toBeEnabled();

  fireEvent.click(screen.getByRole('button', { name: '永久删除' }));
  await waitFor(() => expect(api.deleteProject).toHaveBeenCalledWith('p1', '雨夜玫瑰'));
});
