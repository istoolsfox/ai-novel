import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, expect, test, vi } from 'vitest';
import { releaseApi } from '../releaseApi';
import { securityApi } from '../securityApi';
import FirstRunWizard from './FirstRunWizard';

const releaseInfo = {
  version: '1.0.0-rc.1',
  release_channel: 'release-candidate',
  commit: 'abcdef',
  built_at: '',
  image_revision: '',
  schema_version: 4,
  latest_schema_version: 4,
  setup_completed: false,
  setup_step: 'welcome',
  capabilities: ['autopilot', 'encrypted-credentials', 'versioned-migrations'],
  python: '3.12.0',
  database_path: '/data/app.db',
  data_directory: '/data',
};

const setupState = {
  id: 'current',
  installed_version: '1.0.0-rc.1',
  release_channel: 'release-candidate',
  first_run_completed: false,
  setup_step: 'welcome',
  setup_payload: {},
  completed_at: '',
  updated_at: '2026-07-20T00:00:00Z',
};

function mockApis({ modelWarning = true, adminTokenRequired = false } = {}) {
  vi.spyOn(releaseApi, 'info').mockResolvedValue(releaseInfo);
  vi.spyOn(releaseApi, 'setupState').mockResolvedValue(setupState);
  vi.spyOn(releaseApi, 'readiness').mockResolvedValue({
    status: 'ready',
    ready: true,
    checks: [
      { id: 'database', label: 'SQLite 完整性', status: 'pass', required: true, detail: 'ok' },
      { id: 'migrations', label: '数据库迁移', status: 'pass', required: true, detail: '4/4 · current' },
      { id: 'model', label: '模型配置', status: modelWarning ? 'warning' : 'pass', required: false, detail: modelWarning ? '0 configs' : '1 config' },
    ],
    blockers: [],
    warnings: modelWarning
      ? [{ id: 'model', label: '模型配置', status: 'warning', required: false, detail: '0 configs' }]
      : [],
    checked_at: '2026-07-20T00:00:00Z',
  });
  vi.spyOn(securityApi, 'status').mockResolvedValue({
    status: 'ok',
    master_key_source: 'file',
    master_key_path: '/data/master.key',
    master_key_fingerprint: 'fingerprint',
    credential_count: modelWarning ? 0 : 1,
    unreadable_credentials: 0,
    admin_token_required: adminTokenRequired,
  });
}

afterEach(() => {
  vi.restoreAllMocks();
  sessionStorage.clear();
});

test('requires explicit stub-mode acknowledgement before completing without a model', async () => {
  mockApis({ modelWarning: true });
  const update = vi.spyOn(releaseApi, 'updateSetup').mockResolvedValue({ ...setupState, setup_step: 'review' });
  const complete = vi.spyOn(releaseApi, 'completeSetup').mockResolvedValue({
    status: 'completed',
    state: { ...setupState, first_run_completed: true, setup_step: 'completed' },
  });
  const onComplete = vi.fn();

  render(<FirstRunWizard onComplete={onComplete} onDismiss={() => undefined} />);

  expect(await screen.findByText('核心环境已准备完成。')).toBeInTheDocument();
  expect(screen.getByText('1.0.0-rc.1')).toBeInTheDocument();
  expect(screen.getByText('SQLite 完整性')).toBeInTheDocument();

  const finish = screen.getByRole('button', { name: '完成首次启动' });
  expect(finish).toBeDisabled();
  fireEvent.click(screen.getByRole('checkbox'));
  expect(finish).toBeEnabled();
  fireEvent.click(finish);

  await waitFor(() => expect(update).toHaveBeenCalledWith('review', { acknowledge_without_model: true }));
  await waitFor(() => expect(complete).toHaveBeenCalledWith(true));
  await waitFor(() => expect(onComplete).toHaveBeenCalled());
});

test('completes directly when model and credential readiness pass', async () => {
  mockApis({ modelWarning: false, adminTokenRequired: true });
  vi.spyOn(releaseApi, 'updateSetup').mockResolvedValue({ ...setupState, setup_step: 'review' });
  const complete = vi.spyOn(releaseApi, 'completeSetup').mockResolvedValue({
    status: 'completed',
    state: { ...setupState, first_run_completed: true, setup_step: 'completed' },
  });

  render(<FirstRunWizard onComplete={() => undefined} onDismiss={() => undefined} />);
  expect(await screen.findByText('核心环境已准备完成。')).toBeInTheDocument();
  expect(screen.getByLabelText('首次启动运维令牌')).toBeInTheDocument();
  const finish = screen.getByRole('button', { name: '完成首次启动' });
  expect(finish).toBeEnabled();
  fireEvent.click(finish);
  await waitFor(() => expect(complete).toHaveBeenCalledWith(false));
});

test('allows dismissing the wizard without marking setup complete', async () => {
  mockApis();
  const onDismiss = vi.fn();
  render(<FirstRunWizard onComplete={() => undefined} onDismiss={onDismiss} />);
  await screen.findByText('核心环境已准备完成。');
  fireEvent.click(screen.getByLabelText('稍后完成首次启动设置'));
  expect(onDismiss).toHaveBeenCalled();
});
