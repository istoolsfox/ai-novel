export type SecurityStatus = {
  status: string;
  master_key_source: string;
  master_key_path: string;
  master_key_fingerprint: string;
  master_key_permissions?: string | null;
  credential_count: number;
  unreadable_credentials: number;
  admin_token_required: boolean;
};

export type EncryptedCredential = {
  id: string;
  project_id: string;
  name: string;
  provider: string;
  secret_hint: string;
  metadata: Record<string, unknown>;
  status: string;
  key_fingerprint: string;
  created_at: string;
  updated_at: string;
  last_used_at: string;
  rotated_at: string;
};

export type SecurityEvent = {
  id: string;
  project_id: string;
  credential_id: string;
  event_type: string;
  message: string;
  payload?: Record<string, unknown>;
  created_at: string;
};

const API_BASE = import.meta.env.VITE_API_BASE ?? '';
let adminToken = '';

export function setSecurityAdminToken(value: string) {
  adminToken = value.trim();
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: {
      'Content-Type': 'application/json',
      ...(adminToken ? { 'X-AI-Novel-Admin-Token': adminToken } : {}),
      ...(options?.headers ?? {}),
    },
    ...options,
  });
  if (!response.ok) {
    let detail = response.statusText;
    try {
      const payload = await response.json() as { detail?: string };
      detail = payload.detail || detail;
    } catch {
      // Preserve status text when the response is not JSON.
    }
    throw new Error(detail);
  }
  return response.json() as Promise<T>;
}

function post<T>(path: string, payload?: unknown) {
  return request<T>(path, { method: 'POST', body: payload === undefined ? undefined : JSON.stringify(payload) });
}

export const securityApi = {
  status: () => request<SecurityStatus>('/api/security/status'),
  events: (projectId = '') => request<SecurityEvent[]>(`/api/security/events?project_id=${encodeURIComponent(projectId)}`),
  credentials: (projectId: string) => request<EncryptedCredential[]>(`/api/security/projects/${projectId}/credentials`),
  createCredential: (projectId: string, payload: { name: string; provider: string; secret: string; metadata?: Record<string, unknown> }) =>
    post<EncryptedCredential>(`/api/security/projects/${projectId}/credentials`, payload),
  updateCredential: (projectId: string, credentialId: string, payload: { name?: string; provider?: string; secret?: string; status?: string }) =>
    request<EncryptedCredential>(`/api/security/projects/${projectId}/credentials/${credentialId}`, {
      method: 'PATCH',
      body: JSON.stringify(payload),
    }),
  deleteCredential: (projectId: string, credentialId: string) =>
    request<{ deleted: boolean }>(`/api/security/projects/${projectId}/credentials/${credentialId}`, { method: 'DELETE' }),
  testCredential: (projectId: string, credentialId: string, payload: { base_url: string; model_name: string }) =>
    post<{ ok: boolean; model: string; message: string }>(
      `/api/security/projects/${projectId}/credentials/${credentialId}/test`,
      payload,
    ),
  migrateLegacy: () => post<{ migrated: number; skipped: number }>('/api/security/migrate-plaintext-model-configs'),
};
