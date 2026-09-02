export type Project = {
  id: string;
  title: string;
  topic?: string;
  genre?: string;
  audience?: string;
  tone?: string;
  target_chapter_count?: number;
  target_words_per_chapter?: number;
  synopsis?: string;
  project_root_path?: string;
  privacy_mode?: boolean | number;
};

export type Chapter = {
  id: string;
  project_id: string;
  chapter_number: number;
  title: string;
  brief: string;
  draft: string;
  summary: string;
  status: string;
  selected_version_id?: string;
  quality_score?: number;
};

export type ChapterVersion = {
  id: string;
  label: string;
  content: string;
  created_at: string;
};

export type ImportPreviewItem = { title: string; words: number; preview: string };

export type ImportPreview = {
  mode: 'novel' | 'fragment';
  chapter_count?: number;
  total_words?: number;
  items?: ImportPreviewItem[];
  layer?: string;
  layer_label?: string;
  words?: number;
  preview?: string;
  matched_chapter?: { id: string; chapter_number: number; title: string; score: number } | null;
};

export type ImportResult = {
  mode: string;
  layer?: string;
  layer_label?: string;
  imported_chapters?: number;
  chapters?: Array<{ id: string; chapter_number: number; title: string }>;
  appended_to?: { id: string; chapter_number: number; title: string };
  created_chapter?: { id: string; chapter_number: number; title: string };
  record_id?: string;
  title?: string;
};

export type GenericRecord = {
  id: string;
  title: string;
  category: string;
  content: string;
  payload?: Record<string, unknown>;
  status: string;
};

export type RecordRevision = {
  id: string;
  resource: string;
  record_id: string;
  title: string;
  category: string;
  content: string;
  payload?: Record<string, unknown>;
  status: string;
  origin: string;
  created_at: string;
};

export type CharacterProfilePayload = {
  name: string;
  role: string;
  faction: string;
  appearance: string;
  traits: string;
  desire: string;
  fear: string;
  mainline_relation: string;
  arc: string;
  voice: string;
  related_chapters: string;
  notes: string;
};

export type RelationshipPayload = {
  source_character: string;
  target_character: string;
  relationship_type: string;
  strength: number;
  conflict: string;
  change_history: string;
  related_chapters: string;
};

export type OutlinePayload = {
  chapter_id?: string;
  chapter_number?: string;
  volume: string;
  chapter_title: string;
  chapter_goal: string;
  main_conflict: string;
  key_events: string;
  emotional_rhythm: string;
  foreshadowing: string;
  hook: string;
  related_characters: string;
  completion_status: string;
};

export type TimelineEventPayload = {
  event_time: string;
  chapter: string;
  characters: string;
  cause: string;
  status: string;
  consequence: string;
};

export type ForeshadowingPayload = {
  setup_chapter: string;
  payoff_chapter: string;
  status: string;
  related_characters: string;
  hint: string;
  payoff_plan: string;
};

export type TabooRulePayload = {
  rule: string;
  severity: string;
  scope: string;
  response: string;
};

export type KnowledgeDocumentPayload = {
  source_type: string;
  tags: string;
  content: string;
  wiki_path: string;
};

export type AiResult = {
  workflow: string;
  text: string;
  structured?: unknown;
  context?: unknown;
  score: number;
  model?: string;
  status?: string;
  error?: string;
  items: Array<{ title: string; content: string }>;
};

export type ModelConnectionPayload = {
  provider: string;
  api_key: string;
  base_url: string;
  model_name: string;
  temperature: number;
  max_tokens: number;
};

export type ModelConnectionTestResult = {
  ok: boolean;
  model: string;
  message: string;
};

export type WorkbenchAIResult = {
  id: string;
  title: string;
  content: string;
  status?: 'ready' | 'loading' | 'error';
  error?: string;
  sourceWorkflow?: string;
};

export type AuthUser = {
  id: string;
  provider: string;
  name: string;
  email: string;
  avatar_url?: string;
};

export type AuthStatus = {
  mode: 'local' | 'cloud';
  authenticated: boolean;
  user: AuthUser | null;
  sync_enabled: boolean;
  message: string;
  account_mode?: boolean;
  username?: string | null;
};

export type OAuthStart = {
  provider: string;
  requires_redirect: boolean;
  authorization_url: string;
  state: string;
  message: string;
  available_providers: string[];
};

const API_BASE = import.meta.env.VITE_API_BASE ?? '';

const TOKEN_KEY = 'ai-novel-token';
const USER_KEY = 'ai-novel-user';

export function getToken(): string {
  return localStorage.getItem(TOKEN_KEY) ?? '';
}

export function setToken(token: string, username?: string): void {
  if (token) {
    localStorage.setItem(TOKEN_KEY, token);
    if (username) localStorage.setItem(USER_KEY, username);
  } else {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
  }
}

export function getStoredUsername(): string {
  return localStorage.getItem(USER_KEY) ?? '';
}

export const UNAUTHORIZED_EVENT = 'ai-novel-unauthorized';

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const token = getToken();
  const response = await fetch(`${API_BASE}${path}`, {
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(options?.headers ?? {}),
    },
    ...options,
  });
  if (response.status === 401) {
    setToken('');
    window.dispatchEvent(new Event(UNAUTHORIZED_EVENT));
  }
  if (!response.ok) {
    const text = await response.text();
    try {
      const data = JSON.parse(text) as { detail?: string };
      if (data.detail) throw new Error(data.detail);
    } catch (exc) {
      if (exc instanceof SyntaxError) {
        // 非 JSON 响应体
      } else {
        throw exc;
      }
    }
    throw new Error(text || response.statusText);
  }
  return response.json() as Promise<T>;
}

export type AccountLoginResult = { token: string; username: string; expires_at: string };

export const api = {
  accountLogin: (username: string, password: string) =>
    request<AccountLoginResult>('/api/auth/login', {
      method: 'POST',
      body: JSON.stringify({ username, password }),
    }),
  accountLogout: () => request<{ ok: boolean }>('/api/auth/logout', { method: 'POST' }),
  authStatus: () => request<AuthStatus>('/api/auth/status'),
  startOauth: (provider: string) => request<OAuthStart>(`/api/auth/oauth/${provider}/start`),
  logout: () => request<AuthStatus>('/api/auth/logout', { method: 'POST' }),
  listProjects: () => request<Project[]>('/api/projects'),
  createProject: (payload: Partial<Project>) =>
    request<Project>('/api/projects', { method: 'POST', body: JSON.stringify(payload) }),
  updateProject: (projectId: string, payload: Partial<Project>) =>
    request<Project>(`/api/projects/${projectId}`, { method: 'PATCH', body: JSON.stringify(payload) }),
  deleteProject: (projectId: string, password: string) =>
    request<{ ok: boolean }>(`/api/projects/${projectId}`, {
      method: 'DELETE',
      body: JSON.stringify({ password }),
    }),
  listChapters: (projectId: string) => request<Chapter[]>(`/api/projects/${projectId}/chapters`),
  createChapter: (projectId: string, payload: Partial<Chapter>) =>
    request<Chapter>(`/api/projects/${projectId}/chapters`, { method: 'POST', body: JSON.stringify(payload) }),
  updateChapter: (projectId: string, chapterId: string, payload: Partial<Chapter>) =>
    request<Chapter>(`/api/projects/${projectId}/chapters/${chapterId}`, {
      method: 'PATCH',
      body: JSON.stringify(payload),
    }),
  deleteChapter: (projectId: string, chapterId: string) =>
    request<{ ok: boolean }>(`/api/projects/${projectId}/chapters/${chapterId}`, { method: 'DELETE' }),
  finalizeChapter: (projectId: string, chapterId: string) =>
    request<Chapter>(`/api/projects/${projectId}/chapters/${chapterId}/finalize`, { method: 'POST' }),
  listVersions: (projectId: string, chapterId: string) =>
    request<ChapterVersion[]>(`/api/projects/${projectId}/chapters/${chapterId}/versions`),  createVersion: (projectId: string, chapterId: string, label: string, content: string) =>
    request<ChapterVersion>(`/api/projects/${projectId}/chapters/${chapterId}/versions`, {
      method: 'POST',
      body: JSON.stringify({ label, content }),
    }),
  selectVersion: (projectId: string, chapterId: string, versionId: string) =>
    request<Chapter>(`/api/projects/${projectId}/chapters/${chapterId}/versions/${versionId}/select`, {
      method: 'POST',
    }),
  importPreview: (projectId: string, content: string) =>
    request<ImportPreview>(`/api/projects/${projectId}/import/preview`, {
      method: 'POST',
      body: JSON.stringify({ content }),
    }),
  importContent: (projectId: string, payload: { content: string; filename?: string; layer?: string; target_chapter_id?: string }) =>
    request<ImportResult>(`/api/projects/${projectId}/import`, {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  listRecords: (projectId: string, resource: string) =>
    request<GenericRecord[]>(`/api/projects/${projectId}/${resource}`),
  createRecord: (projectId: string, resource: string, payload: Partial<GenericRecord>) =>
    request<GenericRecord>(`/api/projects/${projectId}/${resource}`, {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  updateRecord: (projectId: string, resource: string, recordId: string, payload: Partial<GenericRecord>) =>
    request<GenericRecord>(`/api/projects/${projectId}/${resource}/${recordId}`, {
      method: 'PATCH',
      body: JSON.stringify(payload),
    }),
  deleteRecord: (projectId: string, resource: string, recordId: string) =>
    request<{ ok: boolean }>(`/api/projects/${projectId}/${resource}/${recordId}`, { method: 'DELETE' }),
  listRecordRevisions: (projectId: string, resource: string, recordId: string) =>
    request<RecordRevision[]>(`/api/projects/${projectId}/${resource}/${recordId}/revisions`),
  restoreRecordRevision: (projectId: string, resource: string, recordId: string, revisionId: string) =>
    request<GenericRecord>(
      `/api/projects/${projectId}/${resource}/${recordId}/revisions/${revisionId}/restore`,
      { method: 'POST' },
    ),
  runAi: (projectId: string, workflow: string, payload: Record<string, unknown>) =>
    request<AiResult>(`/api/projects/${projectId}/ai/${workflow}`, {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  testModelConnection: (projectId: string, payload: ModelConnectionPayload) =>
    request<ModelConnectionTestResult>(`/api/projects/${projectId}/ai/test-connection`, {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  wikiWrite: (projectId: string, path: string, content: string) =>
    request<GenericRecord>(`/api/projects/${projectId}/wiki/write`, {
      method: 'POST',
      body: JSON.stringify({ path, content }),
    }),
  wikiCount: (projectId: string) => request<{ count: number }>(`/api/projects/${projectId}/wiki/count`),
  wikiSearch: (projectId: string, q = '') =>
    request<Array<{ path: string; content: string }>>(`/api/projects/${projectId}/wiki/search?q=${encodeURIComponent(q)}`),
};
