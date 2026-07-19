export type MigrationItem = {
  version: number;
  name: string;
  description: string;
  checksum: string;
};

export type MigrationStatus = {
  status: string;
  current_version: number;
  latest_version: number;
  pending: MigrationItem[];
  applied: Array<Record<string, unknown>>;
  drift: Array<Record<string, unknown>>;
  unknown_versions: number[];
  auto_migrate: boolean;
};

export type MigrationPlan = MigrationStatus & {
  blockers: string[];
  can_apply: boolean;
  will_create_backup: boolean;
};

export type MigrationRun = {
  id: string;
  status: string;
  from_version: number;
  to_version: number;
  planned_versions: number[];
  applied_versions: number[];
  backup_id: string;
  error_message: string;
  started_at: string;
  completed_at: string;
};

export type KeyRotation = {
  id: string;
  status: string;
  previous_fingerprint: string;
  new_fingerprint: string;
  credential_count: number;
  backup_id: string;
  key_backup_path: string;
  error_message: string;
  started_at: string;
  completed_at: string;
};

const API_BASE = import.meta.env.VITE_API_BASE ?? '';
let adminToken = '';

export function setUpgradeAdminToken(value: string) {
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
      // Keep the HTTP status text for non-JSON errors.
    }
    throw new Error(detail);
  }
  return response.json() as Promise<T>;
}

function post<T>(path: string, payload: unknown) {
  return request<T>(path, { method: 'POST', body: JSON.stringify(payload) });
}

export const upgradeApi = {
  status: () => request<MigrationStatus>('/api/migrations/status'),
  plan: () => request<MigrationPlan>('/api/migrations/plan'),
  runs: () => request<MigrationRun[]>('/api/migrations/runs'),
  apply: () => post<Record<string, unknown>>('/api/migrations/apply', { confirmation: 'APPLY' }),
  rollback: (backupId: string) => post<Record<string, unknown>>(`/api/migrations/rollback/${backupId}`, { confirmation: 'ROLLBACK' }),
  rotations: () => request<KeyRotation[]>('/api/security/master-key/rotations'),
  rotateKey: (newMasterKey = '') => post<Record<string, unknown>>('/api/security/master-key/rotate', {
    confirmation: 'ROTATE',
    new_master_key: newMasterKey,
  }),
  restoreKey: (rotationId: string) => post<Record<string, unknown>>(`/api/security/master-key/rotations/${rotationId}/restore`, {
    confirmation: 'RESTORE_KEY',
  }),
};
