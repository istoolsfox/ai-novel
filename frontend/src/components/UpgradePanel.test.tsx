import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, expect, test, vi } from 'vitest';
import { securityApi } from '../securityApi';
import { upgradeApi } from '../upgradeApi';
import UpgradePanel from './UpgradePanel';

const plan = {
  status: 'pending',
  current_version: 1,
  latest_version: 3,
  pending: [
    { version: 2, name: 'security_runtime_indexes', description: 'Add indexes.', checksum: 'abcdef1234567890' },
    { version: 3, name: 'application_release_state', description: 'Add release state.', checksum: '1234567890abcdef' },
  ],
  applied: [],
  drift: [],
  unknown_versions: [],
  auto_migrate: true,
  blockers: [],
  can_apply: true,
  will_create_backup: true,
};

const run = {
  id: 'run-1', status: 'completed', from_version: 0, to_version: 1,
  planned_versions: [1], applied_versions: [1], backup_id: 'backup-pre-upgrade',
  error_message: '', started_at: '2026-07-20T00:00:00Z', completed_at: '2026-07-20T00:01:00Z',
};

function mocks() {
  vi.spyOn(upgradeApi, 'plan').mockResolvedValue(plan);
  vi.spyOn(upgradeApi, 'runs').mockResolvedValue([run]);
  vi.spyOn(upgradeApi, 'rotations').mockResolvedValue([{
    id: 'rotation-1', status: 'completed', previous_fingerprint: 'old', new_fingerprint: 'new',
    credential_count: 1, backup_id: 'key-backup', key_backup_path: '/data/key.bak',
    error_message: '', started_at: '', completed_at: '',
  }]);
  vi.spyOn(securityApi, 'status').mockResolvedValue({
    status: 'ok', master_key_source: 'file', master_key_path: '/data/master.key',
    master_key_fingerprint: 'fingerprint', credential_count: 1, unreadable_credentials: 0,
    admin_token_required: false,
  });
}

afterEach(() => {
  vi.restoreAllMocks();
  sessionStorage.clear();
});

test('requires APPLY and ROLLBACK confirmations for migration actions', async () => {
  mocks();
  const apply = vi.spyOn(upgradeApi, 'apply').mockResolvedValue({ status: 'completed' });
  const rollback = vi.spyOn(upgradeApi, 'rollback').mockResolvedValue({ status: 'rolled_back' });

  render(<UpgradePanel onClose={() => undefined} />);
  expect(await screen.findByText('升级状态已刷新。')).toBeInTheDocument();

  const applyButton = screen.getByRole('button', { name: '应用全部迁移' });
  expect(applyButton).toBeDisabled();
  fireEvent.change(screen.getByLabelText('迁移确认'), { target: { value: 'APPLY' } });
  expect(applyButton).toBeEnabled();
  fireEvent.click(applyButton);
  await waitFor(() => expect(apply).toHaveBeenCalled());

  fireEvent.change(screen.getByLabelText('回滚快照'), { target: { value: 'backup-pre-upgrade' } });
  const rollbackButton = screen.getByRole('button', { name: '执行回滚' });
  expect(rollbackButton).toBeDisabled();
  fireEvent.change(screen.getByLabelText('回滚确认'), { target: { value: 'ROLLBACK' } });
  fireEvent.click(rollbackButton);
  await waitFor(() => expect(rollback).toHaveBeenCalledWith('backup-pre-upgrade'));
});

test('rotates and restores a master key only after explicit confirmation', async () => {
  mocks();
  const rotate = vi.spyOn(upgradeApi, 'rotateKey').mockResolvedValue({ status: 'completed' });
  const restore = vi.spyOn(upgradeApi, 'restoreKey').mockResolvedValue({ status: 'restored' });

  render(<UpgradePanel onClose={() => undefined} />);
  await screen.findByText('升级状态已刷新。');

  const rotateButton = screen.getByRole('button', { name: '轮换主密钥' });
  expect(rotateButton).toBeDisabled();
  fireEvent.change(screen.getByLabelText('密钥轮换确认'), { target: { value: 'ROTATE' } });
  fireEvent.click(rotateButton);
  await waitFor(() => expect(rotate).toHaveBeenCalledWith(''));

  fireEvent.change(screen.getByLabelText('密钥轮换记录'), { target: { value: 'rotation-1' } });
  fireEvent.change(screen.getByLabelText('密钥恢复确认'), { target: { value: 'RESTORE_KEY' } });
  fireEvent.click(screen.getByRole('button', { name: '恢复旧密钥' }));
  await waitFor(() => expect(restore).toHaveBeenCalledWith('rotation-1'));
});
