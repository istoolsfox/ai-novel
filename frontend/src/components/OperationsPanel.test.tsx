import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, expect, test, vi } from 'vitest';
import { controlApi } from '../controlApi';
import OperationsPanel from './OperationsPanel';

const schedule = {
  id: 'default',
  enabled: true,
  interval_hours: 24,
  retention_count: 7,
  next_run_at: '2026-07-20T00:00:00+00:00',
  last_run_at: '',
  last_backup_id: '',
  last_error: '',
  claimed_by: '',
  lease_expires_at: '',
};

function mockOperationsApi() {
  vi.spyOn(controlApi, 'runtimeHealth').mockResolvedValue({
    status: 'ok',
    database: { ok: true, quick_check: 'ok', path: '/data/app.db' },
    storage: { ok: true, path: '/data' },
    runtime: { active_workers: 1, generation_jobs: { completed: 2 }, runtime_tasks: {}, workers: [] },
    backup_schedule: schedule,
    warnings: [],
    checked_at: '2026-07-19T00:00:00+00:00',
  });
  vi.spyOn(controlApi, 'runtimeWorkers').mockResolvedValue([{
    id: 'worker-1', worker_type: 'all', status: 'active', hostname: 'local', pid: 123,
    started_at: '', heartbeat_at: '2026-07-19T00:00:00+00:00', stopped_at: '',
    current_task_type: '', current_task_id: '', healthy: true,
  }]);
  vi.spyOn(controlApi, 'runtimeTasks').mockResolvedValue([]);
  vi.spyOn(controlApi, 'runtimeEvents').mockResolvedValue([]);
  vi.spyOn(controlApi, 'backups').mockResolvedValue([{
    id: 'backup-1', status: 'completed', kind: 'manual', note: '测试备份', file_path: '/data/backups/backup-1.sqlite',
    size_bytes: 1024, sha256: 'abcdef1234567890', integrity: 'ok', created_at: '2026-07-19T00:00:00+00:00', exists: true,
  }]);
  vi.spyOn(controlApi, 'backupSchedule').mockResolvedValue(schedule);
}

afterEach(() => {
  vi.restoreAllMocks();
});

test('shows runtime health and updates automatic backup schedule', async () => {
  mockOperationsApi();
  const updateSchedule = vi.spyOn(controlApi, 'updateBackupSchedule').mockResolvedValue({ ...schedule, interval_hours: 12 });

  render(<OperationsPanel onClose={() => undefined} />);
  expect(await screen.findByText('运行正常')).toBeInTheDocument();
  expect(screen.getByText('/data/app.db')).toBeInTheDocument();

  fireEvent.click(screen.getByRole('button', { name: /备份恢复/ }));
  fireEvent.change(await screen.findByLabelText('备份间隔小时'), { target: { value: '12' } });
  fireEvent.click(screen.getByRole('button', { name: '保存计划' }));

  await waitFor(() => {
    expect(updateSchedule).toHaveBeenCalledWith({ enabled: true, interval_hours: 12, retention_count: 7 });
  });
});

test('requires explicit restore confirmation before restoring a selected backup', async () => {
  mockOperationsApi();
  const restore = vi.spyOn(controlApi, 'restoreBackup').mockResolvedValue({ status: 'restored' });

  render(<OperationsPanel onClose={() => undefined} />);
  await screen.findByText('运行正常');
  fireEvent.click(screen.getByRole('button', { name: /备份恢复/ }));
  fireEvent.click(await screen.findByRole('button', { name: /backup-1/ }));

  const restoreButton = screen.getByRole('button', { name: '恢复所选备份' });
  expect(restoreButton).toBeDisabled();
  fireEvent.change(screen.getByLabelText('恢复确认'), { target: { value: 'RESTORE' } });
  expect(restoreButton).toBeEnabled();
  fireEvent.click(restoreButton);

  await waitFor(() => expect(restore).toHaveBeenCalledWith('backup-1'));
});
