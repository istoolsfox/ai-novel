export type ReleaseInfo = {
  version: string;
  release_channel: string;
  commit: string;
  built_at: string;
  image_revision: string;
  schema_version: number;
  latest_schema_version: number;
  setup_completed: boolean;
  setup_step: string;
  capabilities: string[];
  python: string;
  database_path: string;
  data_directory: string;
};

export type ReadinessCheck = {
  id: string;
  label: string;
  status: 'pass' | 'warning' | 'fail';
  required: boolean;
  detail: string;
};

export type ReleaseReadiness = {
  status: string;
  ready: boolean;
  checks: ReadinessCheck[];
  blockers: ReadinessCheck[];
  warnings: ReadinessCheck[];
  checked_at: string;
};

export type SetupState = {
  id: string;
  installed_version: string;
  release_channel: string;
  first_run_completed: boolean;
  setup_step: string;
  setup_payload: Record<string, unknown>;
  completed_at: string;
  updated_at: string;
};

const API_BASE = import.meta.env.VITE_API_BASE ?? '';
let adminToken = '';

export function setReleaseAdminToken(value: string) {
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
      // Preserve status text for non-JSON responses.
    }
    throw new Error(detail);
  }
  return response.json() as Promise<T>;
}

export const releaseApi = {
  info: () => request<ReleaseInfo>('/api/release/info'),
  readiness: () => request<ReleaseReadiness>('/api/release/readiness'),
  setupState: () => request<SetupState>('/api/setup/state'),
  updateSetup: (setupStep: string, payload: Record<string, unknown> = {}) => request<SetupState>('/api/setup/state', {
    method: 'PUT',
    body: JSON.stringify({ setup_step: setupStep, payload }),
  }),
  completeSetup: (acknowledgeWithoutModel: boolean) => request<{ status: string; state: SetupState }>('/api/setup/complete', {
    method: 'POST',
    body: JSON.stringify({ confirmation: 'COMPLETE_SETUP', acknowledge_without_model: acknowledgeWithoutModel }),
  }),
  resetSetup: () => request<SetupState>('/api/setup/reset', {
    method: 'POST',
    body: JSON.stringify({ confirmation: 'RESET_SETUP' }),
  }),
};
