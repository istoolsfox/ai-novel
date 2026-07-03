// ===== 后端 API 类型定义 =====

export interface Project {
  id: string;
  title: string;
  topic: string;
  genre: string;
  audience: string;
  tone: string;
  target_chapter_count: number;
  target_words_per_chapter: number;
  logline: string;
  synopsis: string;
  global_summary: string;
  status: string;
  privacy_mode: number;
  project_root_path: string;
  created_at: string;
  updated_at: string;
}

export interface ProjectInput {
  title: string;
  topic?: string;
  genre?: string;
  audience?: string;
  tone?: string;
  target_chapter_count?: number;
  target_words_per_chapter?: number;
  logline?: string;
  synopsis?: string;
  global_summary?: string;
  privacy_mode?: boolean;
}

export interface Chapter {
  id: string;
  project_id: string;
  outline_id: string;
  chapter_number: number;
  title: string;
  brief: string;
  draft: string;
  summary: string;
  word_count: number;
  status: string;
  selected_version_id: string;
  created_at: string;
  updated_at: string;
}

export interface ChapterInput {
  outline_id?: string;
  chapter_number: number;
  title?: string;
  brief?: string;
  draft?: string;
  summary?: string;
  status?: string;
}

export interface ChapterVersion {
  id: string;
  project_id: string;
  chapter_id: string;
  label: string;
  content: string;
  model: string;
  context_summary: string;
  created_at: string;
}

export interface Blueprint {
  id: string;
  project_id: string;
  volume_number: number;
  volume_title: string;
  volume_arc: string;
  chapter_range: { start: number; end: number };
  emotional_climate: Record<string, any>;
  key_foreshadowings: any[];
  character_arcs: any[];
  recurring_motifs: string[];
  taboo_list: string[];
  generation_params: Record<string, any>;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface BlueprintInput {
  volume_number?: number;
  volume_title?: string;
  volume_arc?: string;
  chapter_range?: { start: number; end: number };
  emotional_climate?: Record<string, any>;
  key_foreshadowings?: any[];
  character_arcs?: any[];
  recurring_motifs?: string[];
  taboo_list?: string[];
  generation_params?: Record<string, any>;
}

export interface GenerationJob {
  id: string;
  project_id: string;
  volume_blueprint_id?: string;
  blueprint_id?: string;
  start_chapter_number?: number;
  start_chapter?: number;
  target_chapter_count: number;
  current_chapter_number?: number;
  completed_chapter_count?: number;
  current_step?: string;
  status: string;
  checkpoint_strategy: string;
  auto_finalize: boolean | number;
  params_json?: string;
  params?: Record<string, any>;
  pause_reason?: string;
  pause_detail?: string;
  error_message: string;
  created_at: string;
  updated_at: string;
}

export interface JobStartInput {
  blueprint_id?: string;
  start_chapter?: number;
  count?: number;
  checkpoint_strategy?: string;
  auto_finalize?: boolean;
  params?: Record<string, any>;
}

export interface StepRecord {
  id: string;
  job_id: string;
  project_id?: string;
  chapter_id: string;
  chapter_number?: number;
  step_name: string;
  step_status?: string;
  status?: string;
  step_output?: string;
  output_text?: string;
  error_message: string;
  duration_ms?: number;
  started_at?: string;
  completed_at?: string;
  created_at: string;
}

export interface SSEEvent {
  type: string;
  [key: string]: any;
}

export interface EmotionSeed {
  id: string;
  project_id: string;
  chapter_id: string;
  emotion_seed: string;
  created_at: string;
}

export interface Archaeology {
  id: string;
  project_id: string;
  chapter_id: string;
  view_mode: string;
  surface_layer: string;
  emotional_layer: string;
  intention_layer: string;
  subconscious_layer: string;
  resonance_layer: string;
  subconscious_leads: string;
  motif_echoes: string;
  reader_felt: string;
  created_at: string;
}

export interface EmotionalLead {
  id: string;
  project_id: string;
  chapter_id: string;
  lead_text: string;
  status: string;
  deepened_chapters: string;
  created_at: string;
}

export interface ImageGrowth {
  id: string;
  project_id: string;
  image: string;
  chapter_id: string;
  chapter_number: number;
  context: string;
  felt_meaning_hint: string;
  is_new: boolean;
  created_at: string;
}

export interface ChapterBridge {
  id: string;
  project_id: string;
  chapter_id: string;
  chapter_number: number;
  ending_state: string;
  opening_hook: string;
  carry_over_details: string;
  emotional_residue: string;
  pending_threads: string;
  created_at: string;
}

export interface ReaderPullReport {
  id: string;
  project_id: string;
  chapter_id: string;
  hook_strength: number;
  emotional_debt: string;
  pull_score: number;
  report_json: string;
  created_at: string;
}

export interface AiWorkflowInput {
  chapter_id?: string;
  prompt?: string;
  content?: string;
  count?: number;
  payload?: Record<string, any>;
}

export interface AiWorkflowOutput {
  text: string;
  model: string;
  status: string;
  error: string;
  structured?: Record<string, any>;
  context?: Record<string, any>;
  score?: number;
}

export interface GenericRecord {
  id: string;
  project_id: string;
  title: string;
  category: string;
  content: string;
  payload: Record<string, any>;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface GenericInput {
  title?: string;
  category?: string;
  content?: string;
  payload?: Record<string, any>;
  status?: string;
}

export interface VersionInput {
  label?: string;
  content: string;
  model?: string;
  context_summary?: string;
}

export interface AuthStatus {
  mode: string;
  authenticated: boolean;
  user: any;
  sync_enabled: boolean;
  message: string;
}
