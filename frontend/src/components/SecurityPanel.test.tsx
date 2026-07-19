import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, expect, test, vi } from 'vitest';
import { controlApi } from '../controlApi';
import { securityApi } from '../securityApi';
import SecurityPanel from './SecurityPanel';

const credential = {
  id: 'credential-1',
  project_id: 'project-1',
  name: '主模型 API Key',
  provider: 'OpenAI',
  secret_hint: 'sk-••••999',
  metadata: {},
  status: 'active',
  key_fingerprint: 'fingerprint',
  created_at: '2026-07-20T00:00:00Z',
  updated_at: '2026-07-20T00:00:00Z',
  last_used_at: '',
  rotated_at: '',
};

function mockSecurityApi() {
  vi.spyOn(controlApi, 'listProjects').mockResolvedValue([{ id: 'project-1', title: '安全小说' }]);
  vi.spyOn(securityApi, 'status').mockResolvedValue({
    status: 'ok',
    master_key_source: 'file',
    master_key_path: '/data/.ai-novel-master.key',
    master_key_fingerprint: '1234567890abcdef',
    master_key_permissions: '0o600',
    credential_count: 1,
    unreadable_credentials: 0,
    admin_token_required: false,
  });
  vi.spyOn(securityApi, 'credentials').mockResolvedValue([credential]);
  vi.spyOn(securityApi, 'events').mockResolvedValue([{
    id: 'event-1', project_id: 'project-1', credential_id: 'credential-1',
    event_type: 'credential.created', message: '加密凭证已创建。', created_at: '2026-07-20T00:00:00Z',
  }]);
}

afterEach(() => {
  vi.restoreAllMocks();
  sessionStorage.clear();
});

test('renders masked credentials and creates a new encrypted credential', async () => {
  mockSecurityApi();
  const create = vi.spyOn(securityApi, 'createCredential').mockResolvedValue(credential);

  render(<SecurityPanel selectedProjectId="project-1" onClose={() => undefined} />);
  expect(await screen.findByText('安全小说')).toBeInTheDocument();
  expect(screen.getByText(/sk-••••999/)).toBeInTheDocument();
  expect(screen.queryByText('real-secret')).not.toBeInTheDocument();

  fireEvent.change(screen.getByLabelText('新凭证 API Key'), { target: { value: 'real-secret' } });
  fireEvent.click(screen.getByRole('button', { name: '加密保存' }));

  await waitFor(() => expect(create).toHaveBeenCalledWith('project-1', {
    name: '主模型 API Key', provider: 'OpenAI', secret: 'real-secret',
  }));
  await waitFor(() => expect(screen.getByLabelText('新凭证 API Key')).toHaveValue(''));
});

test('rotates and disables a credential without exposing the previous secret', async () => {
  mockSecurityApi();
  const update = vi.spyOn(securityApi, 'updateCredential').mockResolvedValue({ ...credential, rotated_at: '2026-07-20T01:00:00Z' });

  render(<SecurityPanel selectedProjectId="project-1" onClose={() => undefined} />);
  await screen.findByText('安全小说');

  fireEvent.change(screen.getByLabelText('轮换 API Key'), { target: { value: 'new-secret' } });
  fireEvent.change(screen.getAllByRole('combobox')[2], { target: { value: 'credential-1' } });
  fireEvent.click(screen.getByRole('button', { name: '轮换密钥' }));
  await waitFor(() => expect(update).toHaveBeenCalledWith('project-1', 'credential-1', { secret: 'new-secret' }));

  fireEvent.click(screen.getByRole('button', { name: '停用' }));
  await waitFor(() => expect(update).toHaveBeenCalledWith('project-1', 'credential-1', { status: 'disabled' }));
});
