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

export type GenericRecord = {
  id: string;
  title: string;
  category: string;
  content: string;
  payload?: Record<string, unknown>;
  status: string;
};

export type AiResult = {
  workflow: string;
  text: string;
  score: number;
  items: Array<{ title: string; content: string }>;
};

const API_BASE = import.meta.env.VITE_API_BASE ?? '';

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...(options?.headers ?? {}) },
    ...options,
  });
  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || response.statusText);
  }
  return response.json() as Promise<T>;
}

export const api = {
  listProjects: () => request<Project[]>('/api/projects'),
  createProject: (payload: Partial<Project>) =>
    request<Project>('/api/projects', { method: 'POST', body: JSON.stringify(payload) }),
  listChapters: (projectId: string) => request<Chapter[]>(`/api/projects/${projectId}/chapters`),
  createChapter: (projectId: string, payload: Partial<Chapter>) =>
    request<Chapter>(`/api/projects/${projectId}/chapters`, { method: 'POST', body: JSON.stringify(payload) }),
  updateChapter: (projectId: string, chapterId: string, payload: Partial<Chapter>) =>
    request<Chapter>(`/api/projects/${projectId}/chapters/${chapterId}`, {
      method: 'PATCH',
      body: JSON.stringify(payload),
    }),
  finalizeChapter: (projectId: string, chapterId: string) =>
    request<Chapter>(`/api/projects/${projectId}/chapters/${chapterId}/finalize`, { method: 'POST' }),
  listVersions: (projectId: string, chapterId: string) =>
    request<ChapterVersion[]>(`/api/projects/${projectId}/chapters/${chapterId}/versions`),
  createVersion: (projectId: string, chapterId: string, label: string, content: string) =>
    request<ChapterVersion>(`/api/projects/${projectId}/chapters/${chapterId}/versions`, {
      method: 'POST',
      body: JSON.stringify({ label, content }),
    }),
  selectVersion: (projectId: string, chapterId: string, versionId: string) =>
    request<Chapter>(`/api/projects/${projectId}/chapters/${chapterId}/versions/${versionId}/select`, {
      method: 'POST',
    }),
  listRecords: (projectId: string, resource: string) =>
    request<GenericRecord[]>(`/api/projects/${projectId}/${resource}`),
  createRecord: (projectId: string, resource: string, payload: Partial<GenericRecord>) =>
    request<GenericRecord>(`/api/projects/${projectId}/${resource}`, {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  runAi: (projectId: string, workflow: string, payload: Record<string, unknown>) =>
    request<AiResult>(`/api/projects/${projectId}/ai/${workflow}`, {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  wikiWrite: (projectId: string, path: string, content: string) =>
    request<GenericRecord>(`/api/projects/${projectId}/wiki/write`, {
      method: 'POST',
      body: JSON.stringify({ path, content }),
    }),
  wikiSearch: (projectId: string, q = '') =>
    request<Array<{ path: string; content: string }>>(`/api/projects/${projectId}/wiki/search?q=${encodeURIComponent(q)}`),
};
