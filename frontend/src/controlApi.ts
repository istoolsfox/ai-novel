export type JsonRecord = Record<string, unknown>;

export type ConsoleProject = {
  id: string;
  title: string;
  genre?: string;
  target_chapter_count?: number;
};

export type ConsoleChapter = {
  id: string;
  project_id: string;
  chapter_number: number;
  title: string;
  status: string;
};

export type GenerationJob = {
  id: string;
  project_id: string;
  mode: string;
  status: string;
  start_chapter: number;
  end_chapter: number;
  current_chapter: number;
  current_step: string;
  total_steps: number;
  completed_steps: number;
  error_message?: string;
};

export type GenerationStep = {
  id: string;
  chapter_id: string;
  chapter_number: number;
  step_order: number;
  workflow: string;
  status: string;
  attempt_count: number;
  max_retries: number;
  error_message?: string;
};

export type GenerationEvent = {
  id: string;
  event_type: string;
  message: string;
  created_at: string;
  payload?: JsonRecord;
};

export type AutopilotSnapshot = {
  job: GenerationJob | null;
  steps: GenerationStep[];
  events: GenerationEvent[];
  progress: {
    completed: number;
    total: number;
    percent: number;
  };
};

export type ContinuityCheck = {
  id: string;
  chapter_id: string;
  chapter_number: number;
  stage: string;
  status: string;
  score: number;
  payload?: JsonRecord;
  created_at?: string;
};

export type MemoryContext = {
  hard_facts?: JsonRecord[];
  relationship_states?: JsonRecord[];
  item_ownership?: JsonRecord[];
  narrative_debts?: JsonRecord[];
  active_foreshadowings?: JsonRecord[];
  [key: string]: unknown;
};

export type StoryGraph = {
  all_threads?: JsonRecord[];
  story_threads?: JsonRecord[];
  all_nodes?: JsonRecord[];
  story_nodes?: JsonRecord[];
  story_edges?: JsonRecord[];
  edges?: JsonRecord[];
  story_focus?: JsonRecord[];
  stalled_threads?: JsonRecord[];
  [key: string]: unknown;
};

export type RollingPlanItem = {
  id?: string;
  chapter_number: number;
  status: string;
  locked: boolean;
  primary_thread_key: string;
  secondary_thread_keys: string[];
  target_node_keys: string[];
  goal: string;
  must_address: string[];
  avoid: string[];
  risk_score: number;
  revision?: number;
  rationale?: string;
};

export type ImpactRun = {
  id: string;
  chapter_id: string;
  chapter_number: number;
  root_event_count: number;
  status: string;
  summary: string;
  created_at?: string;
};

export type Worldline = {
  id: string;
  root_project_id: string;
  project_id: string;
  parent_worldline_id?: string;
  name: string;
  description?: string;
  fork_chapter_number: number;
  status: string;
  is_primary: boolean;
  is_active?: boolean;
  project_title?: string;
  latest_chapter_number?: number;
  chapter_count?: number;
};

export type WorldlineFamily = {
  root_project_id: string;
  current_worldline_id: string;
  current_project_id: string;
  active_worldline_id: string;
  primary_worldline_id: string;
  worldlines: Worldline[];
  events: JsonRecord[];
  isolation_model: string;
};

export type WorldlineMapDiff = {
  only_left: string[];
  only_right: string[];
  changed: string[];
};

export type WorldlineChapterDifference = {
  chapter_number: number;
  left?: JsonRecord | null;
  right?: JsonRecord | null;
  change: 'only_left' | 'only_right' | 'modified';
};

export type WorldlineComparison = {
  root_project_id: string;
  left: Worldline;
  right: Worldline;
  shared_prefix_chapter: number;
  chapter_differences: WorldlineChapterDifference[];
  memory_facts: WorldlineMapDiff;
  story_threads: WorldlineMapDiff;
  story_nodes: WorldlineMapDiff;
  rolling_plan: WorldlineMapDiff;
};

export type ObsidianStatus = {
  exists?: boolean;
  status?: string;
  file_count?: number;
  vault_path?: string;
  archive_path?: string;
  latest_export?: JsonRecord | null;
  manifest?: JsonRecord | null;
  [key: string]: unknown;
};

const API_BASE = import.meta.env.VITE_API_BASE ?? '';

function errorMessage(text: string, fallback: string): string {
  if (!text) return fallback;
  try {
    const parsed = JSON.parse(text) as { detail?: unknown };
    if (typeof parsed.detail === 'string') return parsed.detail;
  } catch {
    // Keep the raw response body when it is not JSON.
  }
  return text;
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...(options?.headers ?? {}) },
    ...options,
  });
  if (!response.ok) {
    const body = await response.text();
    throw new Error(errorMessage(body, response.statusText));
  }
  return response.json() as Promise<T>;
}

function post<T>(path: string, payload?: unknown): Promise<T> {
  return request<T>(path, {
    method: 'POST',
    body: payload === undefined ? undefined : JSON.stringify(payload),
  });
}

export const controlApi = {
  listProjects: () => request<ConsoleProject[]>('/api/projects'),
  listChapters: (projectId: string) => request<ConsoleChapter[]>(`/api/projects/${projectId}/chapters`),

  autopilotStatus: (projectId: string) =>
    request<AutopilotSnapshot>(`/api/projects/${projectId}/autopilot/status`),
  autopilotStreamUrl: (projectId: string) =>
    `${API_BASE}/api/projects/${projectId}/autopilot/events/stream`,
  startAutopilot: (
    projectId: string,
    payload: {
      start_chapter: number;
      end_chapter: number;
      mode: 'full_autopilot' | 'chapter_checkpoint' | 'smart_checkpoint';
      max_retries: number;
    },
  ) => post<AutopilotSnapshot>(`/api/projects/${projectId}/autopilot/start`, payload),
  pauseAutopilot: (projectId: string, jobId: string) =>
    post<AutopilotSnapshot>(`/api/projects/${projectId}/autopilot/jobs/${jobId}/pause`),
  resumeAutopilot: (projectId: string, jobId: string) =>
    post<AutopilotSnapshot>(`/api/projects/${projectId}/autopilot/jobs/${jobId}/resume`),
  stopAutopilot: (projectId: string, jobId: string) =>
    post<AutopilotSnapshot>(`/api/projects/${projectId}/autopilot/jobs/${jobId}/stop`),
  retryAutopilotStep: (projectId: string, jobId: string, stepId: string) =>
    post<AutopilotSnapshot>(`/api/projects/${projectId}/autopilot/jobs/${jobId}/steps/${stepId}/retry`),

  continuityChecks: (projectId: string, chapterId: string) =>
    request<ContinuityCheck[]>(`/api/projects/${projectId}/continuity/chapters/${chapterId}/checks`),
  memoryContext: (projectId: string) => request<MemoryContext>(`/api/projects/${projectId}/memory/context`),
  storyGraph: (projectId: string) => request<StoryGraph>(`/api/projects/${projectId}/story-graph`),
  currentPlan: (projectId: string) =>
    request<RollingPlanItem[]>(`/api/projects/${projectId}/planning/current`),
  lockPlan: (projectId: string, chapterNumber: number, locked: boolean) =>
    post<RollingPlanItem>(`/api/projects/${projectId}/planning/chapters/${chapterNumber}/lock`, { locked }),
  impactRuns: (projectId: string) => request<ImpactRun[]>(`/api/projects/${projectId}/impact/runs`),

  worldlines: (projectId: string) => request<WorldlineFamily>(`/api/projects/${projectId}/worldlines`),
  compareWorldlines: (projectId: string, leftWorldlineId: string, rightWorldlineId: string) =>
    request<WorldlineComparison>(
      `/api/projects/${projectId}/worldlines/compare/${leftWorldlineId}/${rightWorldlineId}`,
    ),
  forkWorldline: (projectId: string, payload: { name: string; fork_chapter_number: number; description: string }) =>
    post<Worldline>(`/api/projects/${projectId}/worldlines/fork`, payload),
  activateWorldline: (projectId: string, worldlineId: string) =>
    post<Worldline>(`/api/projects/${projectId}/worldlines/${worldlineId}/activate`),
  promoteWorldline: (projectId: string, worldlineId: string) =>
    post<Worldline>(`/api/projects/${projectId}/worldlines/${worldlineId}/promote`),
  archiveWorldline: (projectId: string, worldlineId: string) =>
    post<Worldline>(`/api/projects/${projectId}/worldlines/${worldlineId}/archive`),

  obsidianStatus: (projectId: string) => request<ObsidianStatus>(`/api/projects/${projectId}/obsidian/status`),
  exportObsidian: (
    projectId: string,
    payload: { include_drafts: boolean; force_rebuild: boolean; create_archive: boolean },
  ) => post<JsonRecord>(`/api/projects/${projectId}/obsidian/export`, payload),
  obsidianDownloadUrl: (projectId: string) => `${API_BASE}/api/projects/${projectId}/obsidian/download`,
};
