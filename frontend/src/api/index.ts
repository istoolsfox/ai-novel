// ===== API 模块：按资源组织全部 API 调用 =====

import { api, subscribeSSE, downloadFile } from "./client";
import type {
  Project,
  ProjectInput,
  Chapter,
  ChapterInput,
  ChapterVersion,
  ChapterQualityScore,
  VersionInput,
  Blueprint,
  BlueprintInput,
  GenerationJob,
  JobStartInput,
  StepRecord,
  EmotionSeed,
  Archaeology,
  EmotionalLead,
  ImageGrowth,
  ChapterBridge,
  AiWorkflowInput,
  AiWorkflowOutput,
  GenericRecord,
  GenericInput,
  AuthStatus,
} from "./types";

// ===== 认证 =====
export const authApi = {
  status: () => api.get<AuthStatus>("/api/auth/status"),
  logout: () => api.post<AuthStatus>("/api/auth/logout"),
};

// ===== 项目 =====
export const projectApi = {
  list: () => api.get<Project[]>("/api/projects"),
  get: (id: string) => api.get<Project>(`/api/projects/${id}`),
  create: (data: ProjectInput) => api.post<Project>("/api/projects", data),
  update: (id: string, data: ProjectInput) =>
    api.patch<Project>(`/api/projects/${id}`, data),
  delete: (id: string, password: string) =>
    api.delete<{ ok: boolean }>(`/api/projects/${id}`, { password }),
};

// ===== 章节 =====
export const chapterApi = {
  list: (projectId: string) =>
    api.get<Chapter[]>(`/api/projects/${projectId}/chapters`),
  get: (projectId: string, chapterId: string) =>
    api.get<Chapter>(`/api/projects/${projectId}/chapters/${chapterId}`),
  create: (projectId: string, data: ChapterInput) =>
    api.post<Chapter>(`/api/projects/${projectId}/chapters`, data),
  update: (projectId: string, chapterId: string, data: ChapterInput) =>
    api.patch<Chapter>(`/api/projects/${projectId}/chapters/${chapterId}`, data),
  delete: (projectId: string, chapterId: string) =>
    api.delete<{ ok: boolean }>(`/api/projects/${projectId}/chapters/${chapterId}`),
  finalize: (projectId: string, chapterId: string) =>
    api.post<Chapter>(`/api/projects/${projectId}/chapters/${chapterId}/finalize`),
  listQualityScores: (projectId: string, chapterId: string) =>
    api.get<ChapterQualityScore[]>(
      `/api/projects/${projectId}/chapters/${chapterId}/quality-scores`,
    ),
  // 版本管理
  listVersions: (projectId: string, chapterId: string) =>
    api.get<ChapterVersion[]>(
      `/api/projects/${projectId}/chapters/${chapterId}/versions`,
    ),
  createVersion: (projectId: string, chapterId: string, data: VersionInput) =>
    api.post<ChapterVersion>(
      `/api/projects/${projectId}/chapters/${chapterId}/versions`,
      data,
    ),
  selectVersion: (projectId: string, chapterId: string, versionId: string) =>
    api.post<Chapter>(
      `/api/projects/${projectId}/chapters/${chapterId}/versions/${versionId}/select`,
    ),
};

// ===== 蓝图 =====
export const blueprintApi = {
  list: (projectId: string) =>
    api.get<Blueprint[]>(`/api/projects/${projectId}/blueprints`),
  get: (projectId: string, blueprintId: string) =>
    api.get<Blueprint>(`/api/projects/${projectId}/blueprints/${blueprintId}`),
  create: (projectId: string, data: BlueprintInput) =>
    api.post<Blueprint>(`/api/projects/${projectId}/blueprints`, data),
  update: (projectId: string, blueprintId: string, data: BlueprintInput) =>
    api.patch<Blueprint>(
      `/api/projects/${projectId}/blueprints/${blueprintId}`,
      data,
    ),
  delete: (projectId: string, blueprintId: string) =>
    api.delete<{ ok: boolean }>(
      `/api/projects/${projectId}/blueprints/${blueprintId}`,
    ),
  approve: (projectId: string, blueprintId: string) =>
    api.post<Blueprint>(
      `/api/projects/${projectId}/blueprints/${blueprintId}/approve`,
    ),
  autoGenerate: (projectId: string, volumeNumber: number) =>
    api.post<Blueprint>(
      `/api/projects/${projectId}/blueprints/auto-generate`,
      { volume_number: volumeNumber },
    ),
};

// ===== 托管任务 =====
export const jobApi = {
  start: (projectId: string, data: JobStartInput) =>
    api.post<GenerationJob>(`/api/projects/${projectId}/jobs`, data),
  startAutopilot: (projectId: string, data: JobStartInput & { generation_mode?: string }) =>
    api.post<{ job: GenerationJob; blueprint: Blueprint; prepared: Record<string, number> }>(
      `/api/projects/${projectId}/jobs/autopilot`,
      data,
    ),
  list: (projectId: string) =>
    api.get<GenerationJob[]>(`/api/projects/${projectId}/jobs`),
  get: (projectId: string, jobId: string) =>
    api.get<GenerationJob>(`/api/projects/${projectId}/jobs/${jobId}`),
  pause: (projectId: string, jobId: string) =>
    api.post<GenerationJob>(`/api/projects/${projectId}/jobs/${jobId}/pause`),
  resume: (projectId: string, jobId: string) =>
    api.post<GenerationJob>(`/api/projects/${projectId}/jobs/${jobId}/resume`),
  abort: (projectId: string, jobId: string) =>
    api.post<GenerationJob>(`/api/projects/${projectId}/jobs/${jobId}/abort`),
  continueCheckpoint: (projectId: string, jobId: string) =>
    api.post<GenerationJob>(
      `/api/projects/${projectId}/jobs/${jobId}/checkpoint/continue`,
    ),
  listSteps: (projectId: string, jobId: string) =>
    api.get<StepRecord[]>(`/api/projects/${projectId}/jobs/${jobId}/steps`),
  // SSE 订阅
  subscribe: (
    projectId: string,
    jobId: string,
    onEvent: (data: any) => void,
    onError?: (err: Event) => void,
  ) =>
    subscribeSSE(
      `/api/projects/${projectId}/jobs/${jobId}/stream`,
      onEvent,
      onError,
    ),
};

// ===== 情感深度 =====
export const emotionApi = {
  getSeed: (projectId: string, chapterId: string) =>
    api.get<EmotionSeed | {}>(
      `/api/projects/${projectId}/chapters/${chapterId}/emotion-seed`,
    ),
  listArchaeology: (projectId: string, chapterId: string) =>
    api.get<Archaeology[]>(
      `/api/projects/${projectId}/chapters/${chapterId}/archaeology`,
    ),
  getArchaeology: (projectId: string, chapterId: string, archId: string) =>
    api.get<Archaeology>(
      `/api/projects/${projectId}/chapters/${chapterId}/archaeology/${archId}`,
    ),
  listEmotionalLeads: (projectId: string, status?: string) =>
    api.get<EmotionalLead[]>(
      `/api/projects/${projectId}/emotional-leads${status ? `?status=${status}` : ""}`,
    ),
  listImageGrowth: (projectId: string, imageName?: string) =>
    api.get<ImageGrowth[]>(
      `/api/projects/${projectId}/image-growth${imageName ? `?image_name=${imageName}` : ""}`,
    ),
  getBridge: (projectId: string, chapterId: string) =>
    api.get<ChapterBridge | {}>(
      `/api/projects/${projectId}/chapters/${chapterId}/bridge`,
    ),
  listBridges: (projectId: string) =>
    api.get<ChapterBridge[]>(`/api/projects/${projectId}/bridges`),
};

// ===== AI 工作流 =====
export const aiApi = {
  run: (projectId: string, workflow: string, data: AiWorkflowInput) =>
    api.post<AiWorkflowOutput>(
      `/api/projects/${projectId}/ai/${workflow}`,
      data,
    ),
  testConnection: (projectId: string, data: any) =>
    api.post<any>(`/api/projects/${projectId}/ai/test-connection`, data),
};

// ===== 通用资源 =====
export const resourceApi = {
  list: (projectId: string, resource: string) =>
    api.get<GenericRecord[]>(`/api/projects/${projectId}/${resource}`),
  create: (projectId: string, resource: string, data: GenericInput) =>
    api.post<GenericRecord>(`/api/projects/${projectId}/${resource}`, data),
  update: (
    projectId: string,
    resource: string,
    recordId: string,
    data: GenericInput,
  ) =>
    api.patch<GenericRecord>(
      `/api/projects/${projectId}/${resource}/${recordId}`,
      data,
    ),
  delete: (projectId: string, resource: string, recordId: string) =>
    api.delete<{ ok: boolean }>(
      `/api/projects/${projectId}/${resource}/${recordId}`,
    ),
};

// ===== 导出 =====
export const exportApi = {
  markdown: (projectId: string) =>
    downloadFile(`/api/projects/${projectId}/export/markdown`, "novel.md"),
  txt: (projectId: string) =>
    downloadFile(`/api/projects/${projectId}/export/txt`, "novel.txt"),
  docx: (projectId: string) =>
    downloadFile(`/api/projects/${projectId}/export/docx`, "novel.docx"),
  pdf: (projectId: string) =>
    downloadFile(`/api/projects/${projectId}/export/pdf`, "novel.pdf"),
  epub: (projectId: string) =>
    downloadFile(`/api/projects/${projectId}/export/epub`, "novel.epub"),
};

// ===== Wiki =====
export const wikiApi = {
  search: (projectId: string, q: string) =>
    api.get<any[]>(
      `/api/projects/${projectId}/wiki/search${q ? `?q=${encodeURIComponent(q)}` : ""}`,
    ),
  count: (projectId: string) =>
    api.get<{ count: number }>(`/api/projects/${projectId}/wiki/count`),
  lint: (projectId: string) =>
    api.get<any>(`/api/projects/${projectId}/wiki/lint`),
};
