import { useEffect, useRef, useState } from 'react';
import {
  BookMarked,
  BookOpen,
  Brain,
  CheckCircle2,
  Cloud,
  CloudOff,
  Download,
  FileText,
  GitBranch,
  Library,
  LoaderCircle,
  LogOut,
  Network,
  PenLine,
  Plus,
  Save,
  Settings,
  ShieldAlert,
  Sparkles,
  Star,
  Trash2,
  Wifi,
  Eye,
  EyeOff,
  UserCircle,
} from 'lucide-react';
import {
  api,
  AuthStatus,
  Chapter,
  ChapterVersion,
  CharacterProfilePayload,
  ForeshadowingPayload,
  GenericRecord,
  KnowledgeDocumentPayload,
  OutlinePayload,
  Project,
  RelationshipPayload,
  TabooRulePayload,
  TimelineEventPayload,
  WorkbenchAIResult,
} from './api';
import { CharacterWorkbench } from './components/CharacterWorkbench';
import {
  ForeshadowingWorkbench,
  KnowledgeWikiWorkbench,
  TabooRulesWorkbench,
  TimelineWorkbench,
} from './components/MemoryWorkbenches';
import { NovelEditorPage } from './components/NovelEditorPage';
import { OutlineWorkbench } from './components/OutlineWorkbench';
import { RelationshipGraphWorkbench } from './components/RelationshipGraphWorkbench';
import { StyleLearningPanel } from './components/StyleLearningPanel';

type TabKey =
  | 'chapters'
  | 'outline'
  | 'characters'
  | 'graph'
  | 'timeline'
  | 'foreshadowing'
  | 'style'
  | 'taboo'
  | 'knowledge'
  | 'wiki'
  | 'settings'
  | 'export';

type SettingsSection = 'account' | 'models' | 'routes' | 'privacy' | 'status';

const tabs: Array<{ key: TabKey; label: string; icon: typeof BookOpen; description: string }> = [
  { key: 'chapters', label: '章节编辑器', icon: PenLine, description: '正文写作、AI 续写、章节版本与定稿' },
  { key: 'outline', label: '大纲', icon: BookMarked, description: '分卷章节树、剧情板与 AI 多章大纲' },
  { key: 'characters', label: '故事圣经', icon: BookOpen, description: '沉淀角色、世界观、设定与核心规则' },
  { key: 'graph', label: '角色关系图', icon: Network, description: '查看人物关系、同盟、冲突与变化' },
  { key: 'timeline', label: '时间线', icon: GitBranch, description: '梳理事件顺序、因果与剧情节奏' },
  { key: 'foreshadowing', label: '伏笔管理', icon: Sparkles, description: '记录埋线、回收节点与悬念提醒' },
  { key: 'style', label: '风格学习', icon: Star, description: '保存样本文风，让 AI 模仿写作语气' },
  { key: 'taboo', label: '雷点控制', icon: ShieldAlert, description: '列出禁写内容、读者雷点与避坑规则' },
  { key: 'knowledge', label: '知识库', icon: Library, description: '管理素材、资料、参考文档与灵感来源' },
  { key: 'wiki', label: 'llmwiki 记忆', icon: Brain, description: '长篇记忆、章节摘要与 Wiki 语义页面' },
  { key: 'export', label: '导出', icon: Download, description: '按当前项目导出 Markdown、TXT、DOCX 等' },
];

const resourceMap: Record<TabKey, string | null> = {
  chapters: null,
  outline: 'outlines',
  characters: 'character-profiles',
  graph: 'character-relationships',
  timeline: 'timeline-events',
  foreshadowing: 'foreshadowings',
  style: 'style-profiles',
  taboo: 'taboo-rules',
  knowledge: 'knowledge-documents',
  wiki: null,
  settings: null,
  export: null,
};

const providerOptions = [
  'OpenAI',
  'DeepSeek',
  'Claude Compatible',
  'Gemini Compatible',
  'Ollama',
  '自定义 OpenAI-compatible',
];

const workflowOptions = [
  { key: 'generate_chapter_variants', label: '章节正文生成' },
  { key: 'generate_chapter_draft', label: '章节草稿生成' },
  { key: 'generate_outline', label: '多章大纲生成' },
  { key: 'generate_chapter_brief', label: '章节梗概扩展' },
  { key: 'score_chapter', label: '章节评分' },
  { key: 'summarize_chapter', label: '章节摘要' },
  { key: 'extract_memory', label: '记忆提取' },
  { key: 'check_consistency', label: '一致性检查' },
  { key: 'analyze_style_sample', label: '风格分析' },
];

const settingsSections: Array<{ key: SettingsSection; title: string; description: string }> = [
  { key: 'account', title: '账户与同步', description: '本地模式、OAuth 登录和同步边界' },
  { key: 'models', title: '模型配置', description: '管理 OpenAI-compatible 模型' },
  { key: 'routes', title: '任务路由', description: '为不同 AI 任务选择模型' },
  { key: 'privacy', title: '隐私模式', description: '确认本地优先和上传边界' },
  { key: 'status', title: '调用状态', description: '查看 API、fallback 和本地占位状态' },
];

const settingsTitleMap = settingsSections.reduce<Record<SettingsSection, string>>((acc, item) => {
  acc[item.key] = item.title;
  return acc;
}, {} as Record<SettingsSection, string>);

type ModelPayload = {
  provider: string;
  api_key: string;
  base_url: string;
  model_name: string;
  temperature: number;
  max_tokens: number;
  is_default: boolean;
};

type ExecutionStatus = {
  state: 'idle' | 'running' | 'success' | 'error';
  title: string;
  detail: string;
};

type GenerateChapterDraftPayload = {
  prompt: string;
  tone: string;
  style: string;
  length: string;
  viewpoint: string;
  selectedText: string;
  mode: 'draft' | 'continue' | 'revise';
};

type ModelForm = {
  id?: string;
  title: string;
} & ModelPayload;

const emptyModelForm: ModelForm = {
  title: '',
  provider: 'OpenAI',
  api_key: '',
  base_url: 'https://api.openai.com/v1',
  model_name: '',
  temperature: 0.7,
  max_tokens: 4000,
  is_default: false,
};

const emptyCharacterForm: CharacterProfilePayload = {
  name: '',
  role: '',
  faction: '',
  appearance: '',
  traits: '',
  desire: '',
  fear: '',
  mainline_relation: '',
  arc: '',
  voice: '',
  related_chapters: '',
  notes: '',
};

const emptyOutlineForm: OutlinePayload = {
  chapter_id: '',
  chapter_number: '',
  volume: '',
  chapter_title: '',
  chapter_goal: '',
  main_conflict: '',
  key_events: '',
  emotional_rhythm: '',
  foreshadowing: '',
  hook: '',
  related_characters: '',
  completion_status: '',
};

const emptyRelationshipForm: RelationshipPayload = {
  source_character: '',
  target_character: '',
  relationship_type: '朋友',
  strength: 50,
  conflict: '',
  change_history: '',
  related_chapters: '',
};

const emptyTimelineForm: TimelineEventPayload = {
  event_time: '',
  chapter: '',
  characters: '',
  cause: '',
  status: '待确认',
  consequence: '',
};

const emptyForeshadowingForm: ForeshadowingPayload = {
  setup_chapter: '',
  payoff_chapter: '',
  status: 'open',
  related_characters: '',
  hint: '',
  payoff_plan: '',
};

const emptyTabooRuleForm: TabooRulePayload = {
  rule: '',
  severity: 'medium',
  scope: '全书',
  response: '生成前提醒，生成后只提示风险，不自动覆盖正文。',
};

const emptyKnowledgeForm: KnowledgeDocumentPayload = {
  source_type: 'reference',
  tags: '',
  content: '',
  wiki_path: 'knowledge/source.md',
};

const localAuthStatus: AuthStatus = {
  mode: 'local',
  authenticated: false,
  user: null,
  sync_enabled: false,
  message: '本地模式：无需登录即可完整使用项目、章节、记忆、导出和本地 API 配置。',
};

export default function App() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [selectedProject, setSelectedProject] = useState<Project | null>(null);
  const [chapters, setChapters] = useState<Chapter[]>([]);
  const [selectedChapter, setSelectedChapter] = useState<Chapter | null>(null);
  const [versions, setVersions] = useState<ChapterVersion[]>([]);
  const [records, setRecords] = useState<GenericRecord[]>([]);
  const [styleProfileRecords, setStyleProfileRecords] = useState<GenericRecord[]>([]);
  const [selectedStyleProfileId, setSelectedStyleProfileId] = useState('');
  const [modelConfigs, setModelConfigs] = useState<GenericRecord[]>([]);
  const [taskRoutes, setTaskRoutes] = useState<GenericRecord[]>([]);
  const [wikiPages, setWikiPages] = useState<Array<{ path: string; content: string }>>([]);
  const [wikiPageCount, setWikiPageCount] = useState(0);
  const [activeTab, setActiveTab] = useState<TabKey>('chapters');
  const [log, setLog] = useState('准备就绪');
  const [executionStatus, setExecutionStatus] = useState<ExecutionStatus>({
    state: 'idle',
    title: '准备就绪',
    detail: '等待下一步操作',
  });
  const [projectTitle, setProjectTitle] = useState('前朝公主');
  const [recordTitle, setRecordTitle] = useState('');
  const [recordContent, setRecordContent] = useState('');
  const [modelForm, setModelForm] = useState<ModelForm>(emptyModelForm);
  const [showApiKey, setShowApiKey] = useState(false);
  const [privacyMode, setPrivacyMode] = useState(true);
  const [settingsSection, setSettingsSection] = useState<SettingsSection>('account');
  const [authStatus, setAuthStatus] = useState<AuthStatus>(localAuthStatus);
  const [deleteProjectTarget, setDeleteProjectTarget] = useState<Project | null>(null);
  const [deleteProjectPassword, setDeleteProjectPassword] = useState('');
  const [styleSampleTitle, setStyleSampleTitle] = useState('未命名风格样本');
  const [styleSampleText, setStyleSampleText] = useState('');
  const [styleWritingGoal, setStyleWritingGoal] = useState('');
  const [styleAnalysis, setStyleAnalysis] = useState('');
  const [styleImitation, setStyleImitation] = useState('');
  const [characterForm, setCharacterForm] = useState<CharacterProfilePayload>(emptyCharacterForm);
  const [editingCharacterId, setEditingCharacterId] = useState('');
  const [characterAiResults, setCharacterAiResults] = useState<WorkbenchAIResult[]>([]);
  const [characterSaveStatus, setCharacterSaveStatus] = useState('');
  const [outlineForm, setOutlineForm] = useState<OutlinePayload>(emptyOutlineForm);
  const [outlineScope, setOutlineScope] = useState<'global' | 'chapter'>('chapter');
  const [editingOutlineId, setEditingOutlineId] = useState('');
  const [outlineAiResults, setOutlineAiResults] = useState<WorkbenchAIResult[]>([]);
  const [relationshipForm, setRelationshipForm] = useState<RelationshipPayload>(emptyRelationshipForm);
  const [editingRelationshipId, setEditingRelationshipId] = useState('');
  const [relationshipAiResults, setRelationshipAiResults] = useState<WorkbenchAIResult[]>([]);
  const [timelineForm, setTimelineForm] = useState<TimelineEventPayload>(emptyTimelineForm);
  const [editingTimelineId, setEditingTimelineId] = useState('');
  const [timelineAiResults, setTimelineAiResults] = useState<WorkbenchAIResult[]>([]);
  const [foreshadowingForm, setForeshadowingForm] = useState<ForeshadowingPayload>(emptyForeshadowingForm);
  const [editingForeshadowingId, setEditingForeshadowingId] = useState('');
  const [foreshadowingAiResults, setForeshadowingAiResults] = useState<WorkbenchAIResult[]>([]);
  const [tabooRuleForm, setTabooRuleForm] = useState<TabooRulePayload>(emptyTabooRuleForm);
  const [editingTabooRuleId, setEditingTabooRuleId] = useState('');
  const [tabooAiResults, setTabooAiResults] = useState<WorkbenchAIResult[]>([]);
  const [knowledgeForm, setKnowledgeForm] = useState<KnowledgeDocumentPayload>(emptyKnowledgeForm);
  const [editingKnowledgeId, setEditingKnowledgeId] = useState('');
  const [graphCharacters, setGraphCharacters] = useState<GenericRecord[]>([]);
  const [draft, setDraft] = useState('');
  const activeTabRef = useRef<TabKey>('chapters');
  const tabLoadSeq = useRef(0);
  const selectedProjectRef = useRef<Project | null>(null);
  const styleProfileLoadSeq = useRef(0);

  function startExecution(title: string, detail: string) {
    setExecutionStatus({ state: 'running', title, detail });
    setLog(detail);
  }

  function finishExecution(title: string, detail: string) {
    setExecutionStatus({ state: 'success', title, detail });
    setLog(detail);
  }

  function failExecution(title: string, detail: string) {
    setExecutionStatus({ state: 'error', title, detail });
    setLog(detail);
  }

  async function executeTask<T>(
    title: string,
    detail: string,
    task: () => Promise<T>,
    successDetail: string,
  ): Promise<T | undefined> {
    startExecution(title, detail);
    try {
      const result = await task();
      finishExecution(title, successDetail);
      return result;
    } catch (error) {
      failExecution(title, `${title}失败：${error instanceof Error ? error.message : '未知错误'}`);
      return undefined;
    }
  }

  useEffect(() => {
    void loadProjects();
    void loadAuthStatus();
  }, []);

  useEffect(() => {
    selectedProjectRef.current = selectedProject;
  }, [selectedProject]);

  useEffect(() => {
    activeTabRef.current = activeTab;
  }, [activeTab]);

  useEffect(() => {
    if (selectedProject) {
      void loadChapters(selectedProject.id);
      void loadWikiPageCount(selectedProject.id);
      void loadTabData(activeTab, selectedProject.id);
      void loadSettingsData(selectedProject.id);
      setPrivacyMode(Boolean(selectedProject.privacy_mode ?? true));
    } else {
      styleProfileLoadSeq.current += 1;
      setStyleProfileRecords([]);
      setSelectedStyleProfileId('');
      setWikiPageCount(0);
    }
  }, [selectedProject, activeTab]);

  useEffect(() => {
    if (selectedProject) {
      void loadStyleProfileRecords(selectedProject.id);
    }
  }, [selectedProject]);

  useEffect(() => {
    const chapterBelongsToProject = Boolean(
      selectedProject && selectedChapter && selectedChapter.project_id === selectedProject.id,
    );
    setDraft(chapterBelongsToProject ? selectedChapter?.draft ?? '' : '');
    if (selectedProject && selectedChapter && chapterBelongsToProject) {
      void loadVersions(selectedProject.id, selectedChapter.id);
    }
  }, [selectedChapter, selectedProject]);

  async function loadProjects() {
    try {
      const result = await api.listProjects();
      setProjects(result);
      setSelectedProject((current) => current ?? result[0] ?? null);
    } catch {
      setLog('后端未启动时，界面会保持空状态。');
    }
  }

  async function loadAuthStatus() {
    try {
      setAuthStatus(await api.authStatus());
    } catch {
      setAuthStatus(localAuthStatus);
    }
  }

  async function loadChapters(projectId: string) {
    const result = await api.listChapters(projectId);
    setChapters(result);
    setSelectedChapter((current) => {
      if (current && result.some((chapter) => chapter.id === current.id)) return current;
      return result[0] ?? null;
    });
  }

  async function loadVersions(projectId: string, chapterId: string) {
    setVersions(await api.listVersions(projectId, chapterId));
  }

  async function loadWikiPageCount(projectId: string) {
    const result = await api.wikiCount(projectId).catch(() => ({ count: 0 }));
    if (isFreshProjectLoad(projectId)) {
      setWikiPageCount(result.count);
    }
  }

  async function loadStyleProfileRecords(projectId: string) {
    if (selectedProjectRef.current?.id !== projectId) return;
    const seq = ++styleProfileLoadSeq.current;
    setStyleProfileRecords([]);
    setSelectedStyleProfileId('');
    const result = await api.listRecords(projectId, 'style-profiles');
    if (seq === styleProfileLoadSeq.current && selectedProjectRef.current?.id === projectId) {
      setStyleProfileRecords(result);
      setSelectedStyleProfileId((current) => (current && result.some((record) => record.id === current) ? current : ''));
    }
  }

  async function loadTabData(tab: TabKey, projectId: string) {
    const seq = ++tabLoadSeq.current;
    if (tab === 'wiki') {
      const pages = await api.wikiSearch(projectId);
      if (seq === tabLoadSeq.current && tab === activeTabRef.current && isFreshProjectLoad(projectId)) {
        setWikiPages(pages);
        setWikiPageCount(pages.length);
      }
      return;
    }
    if (tab === 'knowledge') {
      const [nextRecords, pages] = await Promise.all([
        api.listRecords(projectId, 'knowledge-documents'),
        api.wikiSearch(projectId).catch(() => []),
      ]);
      if (seq === tabLoadSeq.current && tab === activeTabRef.current && isFreshProjectLoad(projectId)) {
        setRecords(nextRecords);
        setWikiPages(pages);
        setWikiPageCount(pages.length);
      }
      return;
    }
    if (tab === 'graph') {
      const { relationships, characters } = await loadGraphSupportingData(projectId);
      if (seq === tabLoadSeq.current && tab === activeTabRef.current && isFreshProjectLoad(projectId)) {
        setRecords(relationships);
        setGraphCharacters(characters);
      }
      return;
    }
    const resource = resourceMap[tab];
    if (resource) {
      const nextRecords = await api.listRecords(projectId, resource);
      if (seq === tabLoadSeq.current && tab === activeTabRef.current && isFreshProjectLoad(projectId)) {
        setRecords(nextRecords);
      }
    }
  }

  function isFreshProjectLoad(projectId: string) {
    return !selectedProjectRef.current || selectedProjectRef.current.id === projectId;
  }

  async function loadGraphSupportingData(projectId: string) {
    const [relationships, characters] = await Promise.all([
      api.listRecords(projectId, 'character-relationships'),
      api.listRecords(projectId, 'character-profiles'),
    ]);
    return { relationships, characters };
  }

  async function loadSettingsData(projectId: string) {
    const [models, routes] = await Promise.all([
      api.listRecords(projectId, 'model-configs'),
      api.listRecords(projectId, 'model-task-routes'),
    ]);
    setModelConfigs(models);
    setTaskRoutes(routes);
  }

  async function createProject() {
    const project = await executeTask(
      '新建项目',
      '正在创建本地小说项目目录与数据库记录...',
      () =>
        api.createProject({
          title: projectTitle,
          topic: '一个被流放的前朝公主发现能改写记忆的古籍',
          genre: '奇幻',
          audience: '网文读者',
          tone: '克制、悬疑',
          target_chapter_count: 5,
          target_words_per_chapter: 3000,
        }),
      `已创建项目：${projectTitle}`,
    );
    if (!project) return;
    setProjects([project, ...projects]);
    setSelectedProject(project);
  }

  async function deleteProject() {
    if (!deleteProjectTarget) return;
    const executionTitle = '删除项目';
    startExecution(executionTitle, `正在删除项目：${deleteProjectTarget.title}...`);
    try {
      await api.deleteProject(deleteProjectTarget.id, deleteProjectPassword);
      const nextProjects = projects.filter((project) => project.id !== deleteProjectTarget.id);
      setProjects(nextProjects);
      if (selectedProject?.id === deleteProjectTarget.id) {
        setSelectedProject(nextProjects[0] ?? null);
        if (nextProjects.length === 0) {
          setChapters([]);
          setSelectedChapter(null);
          setVersions([]);
          setRecords([]);
          setWikiPages([]);
          setWikiPageCount(0);
        }
      }
      setDeleteProjectTarget(null);
      setDeleteProjectPassword('');
      finishExecution(executionTitle, `项目已删除：${deleteProjectTarget.title}`);
    } catch (error) {
      failExecution(executionTitle, `删除失败：${error instanceof Error ? error.message : '请检查删除密码'}`);
    }
  }

  async function createChapter() {
    if (!selectedProject) return;
    const chapterNumber = chapters.length + 1;
    const chapter = await executeTask(
      '新增章节',
      `正在创建第 ${chapterNumber} 章，并归属到当前项目...`,
      () =>
        api.createChapter(selectedProject.id, {
          chapter_number: chapterNumber,
          title: `第 ${chapterNumber} 章`,
          brief: '本章目标：推进主角发现古籍代价。',
          draft: '',
        }),
      `第 ${chapterNumber} 章已创建，并自动跳转到对应章节。`,
    );
    if (!chapter) return;
    setChapters([...chapters, chapter]);
    setSelectedChapter(chapter);
  }

  async function deleteChapter(chapter: Chapter) {
    if (!selectedProject) return;
    const deleted = await executeTask(
      '删除章节',
      `正在删除第 ${chapter.chapter_number} 章及其候选版本...`,
      () => api.deleteChapter(selectedProject.id, chapter.id),
      `已删除第 ${chapter.chapter_number} 章，并移除本章候选版本。`,
    );
    if (!deleted) return;
    const nextChapters = chapters.filter((item) => item.id !== chapter.id);
    setChapters(nextChapters);
    if (selectedChapter?.id === chapter.id) {
      const nextSelectedChapter = nextChapters[0] ?? null;
      setSelectedChapter(nextSelectedChapter);
      setDraft(nextSelectedChapter?.draft ?? '');
      setVersions([]);
    }
    await loadChapters(selectedProject.id);
  }

  async function saveChapter() {
    if (!selectedProject || !selectedChapter) return;
    const updated = await executeTask(
      '保存章节正文',
      `正在保存第 ${selectedChapter.chapter_number} 章标题、正文快照，并同步章节大纲...`,
      () =>
        api.updateChapter(selectedProject.id, selectedChapter.id, {
          ...selectedChapter,
          draft,
        }),
      '章节标题和正文已保存。',
    );
    if (!updated) return;
    setSelectedChapter(updated);
    setChapters((items) => items.map((chapter) => (chapter.id === updated.id ? updated : chapter)));
    await syncChapterTitleToOutline(updated);
    await loadChapters(selectedProject.id);
  }

  function updateChapterTitle(title: string) {
    setSelectedChapter((current) => (current ? { ...current, title } : current));
    setChapters((items) =>
      items.map((chapter) => (chapter.id === selectedChapter?.id ? { ...chapter, title } : chapter)),
    );
    if (outlineScope === 'chapter' && selectedChapter?.id === outlineForm.chapter_id) {
      setOutlineForm((current) => ({ ...current, chapter_title: title }));
    }
  }

  async function syncChapterTitleToOutline(chapter: Chapter) {
    if (!selectedProject) return;
    try {
      const outlineRecords = await api.listRecords(selectedProject.id, 'outlines');
      const matched = outlineRecords.find((record) => {
        if (record.category === 'global_outline') return false;
        const payload = record.payload ?? {};
        return (
          payload.chapter_id === chapter.id ||
          String(payload.chapter_number ?? '') === String(chapter.chapter_number)
        );
      });
      const payload = {
        title: chapter.title || `第 ${chapter.chapter_number} 章`,
        category: 'chapter_outline',
        content: chapter.brief || matched?.content || '由章节标题同步创建的章节大纲，请继续完善本章目标、冲突和关键事件。',
        payload: {
          ...(matched?.payload ?? {}),
          chapter_id: chapter.id,
          chapter_number: String(chapter.chapter_number),
          chapter_title: chapter.title,
          chapter_goal: String(matched?.payload?.chapter_goal ?? chapter.brief ?? ''),
        },
        status: matched?.status || 'draft',
      };
      if (matched) {
        await api.updateRecord(selectedProject.id, 'outlines', matched.id, payload);
      } else {
        await api.createRecord(selectedProject.id, 'outlines', payload);
      }
      if (activeTabRef.current === 'outline') {
        await loadTabData('outline', selectedProject.id);
      }
    } catch (error) {
      setLog(`章节标题已保存，但同步大纲失败：${error instanceof Error ? error.message : '未知错误'}`);
    }
  }

  async function generateVariant() {
    if (!selectedProject || !selectedChapter) return;
    const result = await executeTask(
      '生成候选版本',
      '正在读取当前章节上下文并生成候选版本...',
      () =>
        api.runAi(selectedProject.id, 'generate_chapter_variants', {
          chapter_id: selectedChapter.id,
          prompt: selectedChapter.brief,
          count: 2,
        }),
      '候选版本生成完成，已写入版本列表。',
    );
    if (!result) return;
    await loadVersions(selectedProject.id, selectedChapter.id);
    setLog(formatAiLog(result));
  }

  async function generateChapterDraftFromAI(payload: GenerateChapterDraftPayload) {
    if (!selectedProject || !selectedChapter) {
      return '请先选择项目和章节，再生成正文结果。';
    }
    const workflow = payload.mode === 'revise' ? 'revise_selection' : 'generate_chapter_draft';
    const executionTitle = payload.mode === 'revise' ? '改写选中文本' : '生成本章正文';
    startExecution(executionTitle, '正在请求后端读取章节、大纲、角色和 llmwiki 上下文...');
    const selectedStyleProfile = styleProfileRecords.find((record) => record.id === selectedStyleProfileId);
    const validStyleProfileId = selectedStyleProfile ? selectedStyleProfile.id : '';
    try {
      startExecution(executionTitle, '后端将统一压缩写作资产并调用章节正文模型...');
      const result = await api.runAi(selectedProject.id, workflow, {
        chapter_id: selectedChapter.id,
        chapter_number: selectedChapter.chapter_number,
        chapter_title: selectedChapter.title,
        current_draft: draft,
        selected_text: payload.selectedText,
        prompt: payload.prompt,
        generation_contract: {
          output: 'single_chapter_prose',
          use_llmwiki: true,
          avoid_multiple_drafts: true,
          instruction:
            `只生成当前第 ${selectedChapter.chapter_number} 章《${selectedChapter.title}》的单篇中文小说正文。` +
            '不要输出 JSON、chapter_id、drafts 数组、多个版本或章节标题；必须参考后端提供的角色、大纲、时间线、伏笔、雷点、知识库和 llmwiki 页面。',
        },
        tone: payload.tone,
        style: payload.style,
        length: payload.length,
        viewpoint: payload.viewpoint,
        mode: payload.mode,
        style_profile_id: validStyleProfileId,
        style_profile: selectedStyleProfile ?? null,
        style_profiles: styleProfileRecords.map(({ id, title }) => ({ id, title })),
      });
      const message = formatAiLog(result);
      const isLegacyPlaceholder = result.text.includes('本地 MVP 的可编辑 AI 占位结果');
      if (result.status === 'fallback' || (result.status === 'local' && isLegacyPlaceholder)) {
        failExecution(executionTitle, message);
        throw new Error(message);
      }
      finishExecution(executionTitle, '模型已返回正文结果，可以插入正文、保存为版本或重新生成。');
      return result.text;
    } catch (error) {
      const message = error instanceof Error ? error.message : 'AI 生成失败，请检查模型配置和后端服务。';
      failExecution(executionTitle, message);
      throw error;
    }
  }

  async function saveAiResultAsVersion(title: string, content: string) {
    if (!selectedProject || !selectedChapter) return;
    const saved = await executeTask(
      '保存 AI 结果为版本',
      '正在把 AI 结果写入当前章节候选版本...',
      () => api.createVersion(selectedProject.id, selectedChapter.id, title, content),
      'AI 结果已保存为候选版本。',
    );
    if (!saved) return;
    await loadVersions(selectedProject.id, selectedChapter.id);
  }

  async function scoreChapter() {
    if (!selectedProject || !selectedChapter) return;
    const result = await executeTask(
      '章节评分',
      '正在调用评分任务，评分结果只写入报告，不会覆盖正文...',
      () =>
        api.runAi(selectedProject.id, 'score_chapter', {
          chapter_id: selectedChapter.id,
          content: draft,
        }),
      '章节评分完成。',
    );
    if (!result) return;
    setLog(formatAiLog(result, `章节评分：${result.score}。`));
  }

  async function finalizeChapter() {
    if (!selectedProject || !selectedChapter) return;
    const updated = await executeTask(
      '章节定稿',
      '正在定稿章节、生成摘要并同步 llmwiki 记忆...',
      () => api.finalizeChapter(selectedProject.id, selectedChapter.id),
      '章节已定稿，摘要已进入结构化记忆和 llmwiki 页面。',
    );
    if (!updated) return;
    setSelectedChapter(updated);
    await loadWikiPageCount(selectedProject.id);
    if (activeTabRef.current === 'wiki') {
      await loadTabData('wiki', selectedProject.id);
    }
  }

  async function selectVersion(versionId: string) {
    if (!selectedProject || !selectedChapter) return;
    const updated = await executeTask(
      '切换候选版本',
      '正在把候选版本设为当前正文...',
      () => api.selectVersion(selectedProject.id, selectedChapter.id, versionId),
      '已将候选版本设为当前正文。',
    );
    if (!updated) return;
    setSelectedChapter(updated);
    setDraft(updated.draft);
  }

  async function createRecord() {
    if (!selectedProject) return;
    const resource = resourceMap[activeTab];
    if (!resource) return;
    const saved = await executeTask(
      '保存资料',
      '正在保存资料并同步项目记忆层...',
      () =>
        api.createRecord(selectedProject.id, resource, {
          title: recordTitle || '未命名资料',
          content: recordContent,
          category: activeTab,
        }),
      '资料已保存到当前项目。',
    );
    if (!saved) return;
    setRecordTitle('');
    setRecordContent('');
    await loadWikiPageCount(selectedProject.id);
    await loadTabData(activeTab, selectedProject.id);
  }

  function payloadValue(record: GenericRecord, key: string) {
    return record.payload?.[key];
  }

  function structuredText(value: unknown, joiner = '\n'): string {
    if (value === undefined || value === null) return '';
    if (typeof value === 'string') return value;
    if (typeof value === 'number' || typeof value === 'boolean') return String(value);
    if (Array.isArray(value)) {
      return value
        .map((item) => structuredText(item, '；'))
        .map((item) => item.trim())
        .filter(Boolean)
        .join(joiner);
    }
    if (typeof value === 'object') {
      const record = value as Record<string, unknown>;
      const title: string = structuredText(record.title ?? record.name ?? record.stage ?? record.event ?? record.label, '；').trim();
      const body: string = structuredText(
        record.summary ??
          record.content ??
          record.description ??
          record.detail ??
          record.role ??
          record.identity ??
          record.goal ??
          record.purpose,
        '；',
      ).trim();
      if (title && body && title !== body) return `${title}：${body}`;
      if (title || body) return title || body;
      return Object.entries(record)
        .map(([key, item]) => {
          const text: string = structuredText(item, '；').trim();
          return text ? `${key}：${text}` : '';
        })
        .filter(Boolean)
        .join('；');
    }
    return String(value);
  }

  function payloadText(record: GenericRecord, key: string, fallback = '') {
    const value = payloadValue(record, key);
    if (value === undefined || value === null) return fallback;
    const inlineKeys = ['related_characters', 'related_chapters', 'characters', 'tags'];
    return structuredText(value, inlineKeys.includes(key) ? '、' : '\n') || fallback;
  }

  function selectCharacterRecord(record: GenericRecord) {
    setEditingCharacterId(record.id);
    setCharacterSaveStatus('编辑模式：保存后会替换当前角色卡，并同步 llmwiki。');
    setCharacterForm({
      name: payloadText(record, 'name', record.title),
      role: payloadText(record, 'role'),
      faction: payloadText(record, 'faction'),
      appearance: payloadText(record, 'appearance'),
      traits: payloadText(record, 'traits'),
      desire: payloadText(record, 'desire'),
      fear: payloadText(record, 'fear'),
      mainline_relation: payloadText(record, 'mainline_relation'),
      arc: payloadText(record, 'arc'),
      voice: payloadText(record, 'voice'),
      related_chapters: payloadText(record, 'related_chapters'),
      notes: payloadText(record, 'notes', record.content),
    });
    setLog(`正在编辑角色卡：${record.title || '未命名角色'}`);
  }

  function selectOutlineRecord(record: GenericRecord) {
    setEditingOutlineId(record.id);
    setOutlineScope(record.category === 'global_outline' ? 'global' : 'chapter');
    setOutlineForm({
      chapter_id: payloadText(record, 'chapter_id'),
      chapter_number: payloadText(record, 'chapter_number'),
      volume: payloadText(record, 'volume'),
      chapter_title: payloadText(record, 'chapter_title', record.title),
      chapter_goal: payloadText(record, 'chapter_goal', record.content),
      main_conflict: payloadText(record, 'main_conflict'),
      key_events: payloadText(record, 'key_events'),
      emotional_rhythm: payloadText(record, 'emotional_rhythm'),
      foreshadowing: payloadText(record, 'foreshadowing'),
      hook: payloadText(record, 'hook'),
      related_characters: payloadText(record, 'related_characters'),
      completion_status: payloadText(record, 'completion_status', record.status || 'draft'),
    });
    setLog(`正在编辑大纲：${record.title || '未命名大纲'}`);
  }

  function selectRelationshipRecord(record: GenericRecord) {
    setEditingRelationshipId(record.id);
    setRelationshipForm({
      source_character: payloadText(record, 'source_character'),
      target_character: payloadText(record, 'target_character'),
      relationship_type: payloadText(record, 'relationship_type', record.category || '朋友'),
      strength: Number(payloadValue(record, 'strength') ?? 50),
      conflict: payloadText(record, 'conflict', record.content),
      change_history: payloadText(record, 'change_history'),
      related_chapters: payloadText(record, 'related_chapters'),
    });
    setLog(`正在编辑关系：${record.title || '未命名关系'}`);
  }

  function selectTimelineRecord(record: GenericRecord) {
    setEditingTimelineId(record.id);
    setTimelineForm({
      event_time: payloadText(record, 'event_time', record.title),
      chapter: payloadText(record, 'chapter'),
      characters: payloadText(record, 'characters'),
      cause: payloadText(record, 'cause', record.content),
      status: payloadText(record, 'status', record.status || '待确认'),
      consequence: payloadText(record, 'consequence'),
    });
    setLog(`正在编辑时间线事件：${record.title || '未命名事件'}`);
  }

  function selectForeshadowingRecord(record: GenericRecord) {
    setEditingForeshadowingId(record.id);
    setForeshadowingForm({
      setup_chapter: payloadText(record, 'setup_chapter'),
      payoff_chapter: payloadText(record, 'payoff_chapter'),
      status: payloadText(record, 'status', record.status || 'open'),
      related_characters: payloadText(record, 'related_characters'),
      hint: payloadText(record, 'hint', record.title),
      payoff_plan: payloadText(record, 'payoff_plan', record.content),
    });
    setLog(`正在编辑伏笔：${record.title || '未命名伏笔'}`);
  }

  function selectTabooRuleRecord(record: GenericRecord) {
    setEditingTabooRuleId(record.id);
    setTabooRuleForm({
      rule: payloadText(record, 'rule', record.title),
      severity: payloadText(record, 'severity', record.category || 'medium'),
      scope: payloadText(record, 'scope'),
      response: payloadText(record, 'response', record.content),
    });
    setLog(`正在编辑雷点规则：${record.title || '未命名规则'}`);
  }

  function selectKnowledgeRecord(record: GenericRecord) {
    setEditingKnowledgeId(record.id);
    setKnowledgeForm({
      source_type: payloadText(record, 'source_type', record.category || 'reference'),
      tags: payloadText(record, 'tags'),
      content: payloadText(record, 'content', record.content),
      wiki_path: payloadText(record, 'wiki_path', record.title),
    });
    setLog(`正在编辑知识库资料：${record.title || '未命名资料'}`);
  }

  function cancelCharacterEdit() {
    setEditingCharacterId('');
    setCharacterForm(emptyCharacterForm);
    setCharacterSaveStatus('已退出编辑模式，可以新建角色卡。');
  }

  function cancelOutlineEdit() {
    setEditingOutlineId('');
    setOutlineForm(emptyOutlineForm);
    setOutlineScope('chapter');
    setLog('已退出大纲编辑模式。');
  }

  function cancelRelationshipEdit() {
    setEditingRelationshipId('');
    setRelationshipForm(emptyRelationshipForm);
    setLog('已退出关系编辑模式。');
  }

  function cancelTimelineEdit() {
    setEditingTimelineId('');
    setTimelineForm(emptyTimelineForm);
    setLog('已退出时间线编辑模式。');
  }

  function cancelForeshadowingEdit() {
    setEditingForeshadowingId('');
    setForeshadowingForm(emptyForeshadowingForm);
    setLog('已退出伏笔编辑模式。');
  }

  function cancelTabooRuleEdit() {
    setEditingTabooRuleId('');
    setTabooRuleForm(emptyTabooRuleForm);
    setLog('已退出雷点规则编辑模式。');
  }

  function cancelKnowledgeEdit() {
    setEditingKnowledgeId('');
    setKnowledgeForm(emptyKnowledgeForm);
    setLog('已退出知识库编辑模式。');
  }

  async function saveCharacterProfile() {
    if (!selectedProject) return;
    const executionTitle = editingCharacterId ? '更新角色卡' : '保存角色卡';
    startExecution(executionTitle, editingCharacterId ? '正在替换角色卡并同步 llmwiki...' : '正在写入角色卡、关系图和 llmwiki...');
    setCharacterSaveStatus(editingCharacterId ? '更新中：正在替换角色卡并同步 llmwiki...' : '保存中：正在写入角色卡、关系图和 llmwiki...');
    const payload = {
      title: characterForm.name || '未命名角色',
      category: 'character',
      content: `${characterForm.name}\n${characterForm.role}\n${characterForm.desire}`,
      payload: { ...characterForm },
      status: 'active',
    };
    try {
      if (editingCharacterId) {
        await api.updateRecord(selectedProject.id, 'character-profiles', editingCharacterId, payload);
      } else {
        await api.createRecord(selectedProject.id, 'character-profiles', payload);
      }
      const relationshipNote = characterForm.mainline_relation || characterForm.role;
      if (!editingCharacterId && characterForm.name && relationshipNote) {
        await api.createRecord(selectedProject.id, 'character-relationships', {
          title: `${characterForm.name} → 主线剧情`,
          category: '主线关联',
          content: relationshipNote,
          payload: {
            source_character: characterForm.name,
            target_character: '主线剧情',
            relationship_type: '主线关联',
            strength: 70,
            conflict: relationshipNote,
            change_history: `由角色卡保存自动创建：${relationshipNote}`,
            related_chapters: characterForm.related_chapters,
          },
          status: 'active',
        });
      }
      await loadTabData('characters', selectedProject.id);
      setCharacterSaveStatus(editingCharacterId ? '更新成功：角色卡和 llmwiki 已替换同步。' : '保存成功：角色卡、关系图和 llmwiki 已同步。');
      finishExecution(executionTitle, editingCharacterId ? '角色卡已更新，并替换同步到 llmwiki。' : '角色卡已保存到当前项目，并同步到关系图与 llmwiki。');
      setEditingCharacterId('');
    } catch (error) {
      const message = error instanceof Error ? error.message : '未知错误';
      setCharacterSaveStatus(`保存失败：${message}`);
      failExecution(executionTitle, `角色卡保存失败：${message}`);
    }
  }

  async function saveOutlineRecord() {
    if (!selectedProject) return;
    const normalizedOutlineForm: OutlinePayload = {
      ...outlineForm,
      chapter_id: outlineScope === 'chapter' ? outlineForm.chapter_id || selectedChapter?.id || '' : '',
      chapter_number:
        outlineScope === 'chapter'
          ? outlineForm.chapter_number || String(selectedChapter?.chapter_number ?? '')
          : '',
    };
    const payload = {
      title:
        outlineScope === 'global'
          ? outlineForm.chapter_title || '全书总纲 / 主线轨道'
          : outlineForm.chapter_title || `${outlineForm.volume}大纲`,
      category: outlineScope === 'global' ? 'global_outline' : 'chapter_outline',
      content: `${outlineForm.chapter_goal}\n${outlineForm.main_conflict}\n${outlineForm.key_events}`.trim(),
      payload: { ...normalizedOutlineForm, scope: outlineScope },
      status: outlineForm.completion_status || (outlineScope === 'global' ? 'active' : 'draft'),
    };
    const saved = await executeTask(
      editingOutlineId ? '更新大纲' : '保存大纲',
      '正在保存大纲，并同步到 llmwiki 大纲页...',
      async () =>
        editingOutlineId
          ? api.updateRecord(selectedProject.id, 'outlines', editingOutlineId, payload)
          : api.createRecord(selectedProject.id, 'outlines', payload),
      editingOutlineId ? '大纲已更新，并替换同步到 llmwiki。' : '大纲已保存到当前项目。',
    );
    if (!saved) return;
    setEditingOutlineId('');
    setOutlineScope('chapter');
    await loadTabData('outline', selectedProject.id);
  }

  async function saveOutlineCandidate(content: string) {
    if (!selectedProject) return;
    const structured = structuredFromAi({ text: content });
    if (!structured) {
      applyOutlineAiResult(content);
      return;
    }
    const candidate = normalizeOutlinePayload(structured);
    const title = candidate.chapter_title || '未命名章节大纲';
    const saved = await executeTask(
      '保存 AI 章节大纲',
      `正在把《${title}》保存为独立章节大纲，并同步 llmwiki...`,
      () =>
        api.createRecord(selectedProject.id, 'outlines', {
          title,
          category: 'chapter_outline',
          content: [candidate.chapter_goal, candidate.main_conflict, candidate.key_events].filter(Boolean).join('\n'),
          payload: { ...candidate, scope: 'chapter' },
          status: candidate.completion_status || 'draft',
        }),
      `已保存章节大纲：${title}`,
    );
    if (!saved) return;
    await loadTabData('outline', selectedProject.id);
  }

  async function deleteOutlineRecord(recordId: string) {
    if (!selectedProject) return;
    const deleted = await executeTask(
      '删除大纲',
      '正在删除大纲记录，并清理 llmwiki 中的同步大纲页...',
      () => api.deleteRecord(selectedProject.id, 'outlines', recordId),
      '大纲已删除，llmwiki 大纲索引已刷新。',
    );
    if (!deleted) return;
    if (editingOutlineId === recordId) {
      cancelOutlineEdit();
    }
    await loadTabData('outline', selectedProject.id);
  }

  function createGlobalOutlineDraft() {
    setOutlineScope('global');
    setEditingOutlineId('');
    setOutlineForm({
      ...emptyOutlineForm,
      chapter_title: '全书总纲 / 主线轨道',
      chapter_goal: selectedProject?.synopsis || selectedProject?.topic || '写下全书核心主线、主题承诺和最终走向。',
      main_conflict: '主角长期目标与核心阻力。',
      key_events: '开端；中段转折；低谷；高潮；结局。',
      emotional_rhythm: '整体情绪曲线与读者期待管理。',
      foreshadowing: '贯穿全书的大伏笔与回收节点。',
      hook: '全书最终悬念或主题落点。',
      completion_status: 'active',
    });
    setLog('已切换到全书总纲编辑模式。');
  }

  async function saveRelationshipRecord() {
    if (!selectedProject) return;
    const payload = {
      title: `${relationshipForm.source_character || '未知角色'} → ${relationshipForm.target_character || '未知角色'}`,
      category: relationshipForm.relationship_type,
      content: relationshipForm.conflict || relationshipForm.change_history,
      payload: { ...relationshipForm },
      status: 'active',
    };
    const saved = await executeTask(
      editingRelationshipId ? '更新角色关系' : '保存角色关系',
      '正在保存角色关系，并同步 relationships.md...',
      async () =>
        editingRelationshipId
          ? api.updateRecord(selectedProject.id, 'character-relationships', editingRelationshipId, payload)
          : api.createRecord(selectedProject.id, 'character-relationships', payload),
      editingRelationshipId ? '角色关系已更新，并替换同步到 llmwiki。' : '角色关系已保存。',
    );
    if (!saved) return;
    setEditingRelationshipId('');
    await loadTabData('graph', selectedProject.id);
  }

  async function createGraphCharacter() {
    if (!selectedProject) return;
    const saved = await executeTask(
      '新增关系图角色',
      '正在创建角色节点，并同步到角色资料...',
      () =>
        api.createRecord(selectedProject.id, 'character-profiles', {
          title: '新角色',
          category: 'character',
          content: '请在角色工作台完善这个角色。',
          payload: { ...emptyCharacterForm },
          status: 'draft',
        }),
      '已创建新角色，可在角色工作台继续完善。',
    );
    if (!saved) return;
    await loadTabData('graph', selectedProject.id);
  }

  function structuredRecord(value: unknown) {
    if (value && typeof value === 'object' && !Array.isArray(value)) return value as Record<string, unknown>;
    return null;
  }

  function structuredArrayFirst(value: unknown) {
    if (Array.isArray(value)) return structuredRecord(value[0]);
    const record = structuredRecord(value);
    if (!record) return null;
    for (const key of ['characters', 'character', 'outlines', 'outline', 'items', 'results']) {
      const nested = record[key];
      if (Array.isArray(nested)) {
        const first = structuredRecord(nested[0]);
        if (first) return first;
      }
      const nestedRecord = structuredRecord(nested);
      if (nestedRecord) return nestedRecord;
    }
    return record;
  }

  function structuredArrayFrom(value: unknown): Array<Record<string, unknown>> {
    if (Array.isArray(value)) return value.map(structuredRecord).filter(Boolean) as Array<Record<string, unknown>>;
    const record = structuredRecord(value);
    if (!record) return [];
    for (const key of ['chapter_outlines', 'chapterOutlines', 'outlines', 'chapters', 'items', 'results']) {
      const nested = record[key];
      if (Array.isArray(nested)) {
        return nested.map(structuredRecord).filter(Boolean) as Array<Record<string, unknown>>;
      }
    }
    return [record];
  }

  function parseJsonObjectFromText(text: string): unknown {
    const trimmed = text.trim();
    const fenced = trimmed.match(/^```(?:json)?\s*([\s\S]*?)\s*```$/i);
    const candidate = fenced?.[1]?.trim() || trimmed;
    try {
      return JSON.parse(candidate);
    } catch {
      const start = candidate.indexOf('{');
      const end = candidate.lastIndexOf('}');
      if (start >= 0 && end > start) {
        return JSON.parse(candidate.slice(start, end + 1));
      }
      throw new Error('No JSON object found');
    }
  }

  function parseStructuredText(text: string) {
    try {
      return structuredArrayFirst(parseJsonObjectFromText(text));
    } catch {
      return null;
    }
  }

  function structuredFromAi(result: { structured?: unknown; text: string }) {
    return structuredArrayFirst(result.structured) ?? parseStructuredText(result.text);
  }

  function structuredArrayFromAi(result: { structured?: unknown; text: string }) {
    const fromStructured = structuredArrayFrom(result.structured);
    if (fromStructured.length) return fromStructured;
    try {
      return structuredArrayFrom(parseJsonObjectFromText(result.text));
    } catch {
      return [];
    }
  }

  function mergeStringFields<T extends Record<string, string | undefined>>(current: T, source: Record<string, unknown>, keys: Array<keyof T>) {
    return keys.reduce<T>((next, key) => {
      const value = source[String(key)];
      const text = structuredText(value);
      return text ? { ...next, [key]: text } : next;
    }, current);
  }

  function normalizeCharacterPayload(source: Record<string, unknown>) {
    const aliases: Record<keyof CharacterProfilePayload, string[]> = {
      name: ['name', 'title', '姓名', '角色名'],
      role: ['role', 'identity', '身份', '定位'],
      faction: ['faction', 'camp', 'affiliation', '阵营', '势力'],
      appearance: ['appearance', 'age_appearance', 'look', '外貌', '年龄外貌'],
      traits: ['traits', 'personality', 'keywords', '性格', '性格关键词'],
      desire: ['desire', 'goal', 'motivation', 'want', '欲望目标', '目标'],
      fear: ['fear', 'weakness', 'wound', '恐惧', '弱点'],
      mainline_relation: ['mainline_relation', 'plot_relation', 'story_role', '与主线关系', '主线关系'],
      arc: ['arc', 'character_arc', 'growth', '人物弧光'],
      voice: ['voice', 'speech_style', 'dialogue_style', '口癖', '说话方式'],
      related_chapters: ['related_chapters', 'chapters', '关联章节', '相关章节'],
      notes: ['notes', 'background', 'memo', '备注', '补充'],
    };
    return (Object.keys(aliases) as Array<keyof CharacterProfilePayload>).reduce<Partial<CharacterProfilePayload>>(
      (payload, field) => {
        const foundKey = aliases[field].find((key) => source[key] !== undefined && source[key] !== null);
        if (!foundKey) return payload;
        const value = source[foundKey];
        const text = structuredText(value, field === 'related_chapters' ? '、' : '\n');
        return text ? { ...payload, [field]: text } : payload;
      },
      {},
    );
  }

  function normalizeOutlinePayload(source: Record<string, unknown>): OutlinePayload {
    const aliases: Record<keyof OutlinePayload, string[]> = {
      chapter_id: ['chapter_id', 'chapterId', '章节ID'],
      chapter_number: ['chapter_number', 'chapterNumber', 'index', '章节序号', '第几章'],
      volume: ['volume', '卷名', '分卷'],
      chapter_title: ['chapter_title', 'title', '章节标题', '标题'],
      chapter_goal: ['chapter_goal', 'goal', '本章目标', '目标', 'summary', '摘要'],
      main_conflict: ['main_conflict', 'conflict', '主要冲突', '冲突'],
      key_events: ['key_events', 'events', '关键事件', '事件'],
      emotional_rhythm: ['emotional_rhythm', 'rhythm', '情绪节奏', '节奏'],
      foreshadowing: ['foreshadowing', '伏笔', '埋线'],
      hook: ['hook', '结尾钩子', '悬念'],
      related_characters: ['related_characters', 'characters', '关联角色', '角色'],
      completion_status: ['completion_status', 'status', '状态'],
    };
    return (Object.keys(aliases) as Array<keyof OutlinePayload>).reduce<OutlinePayload>((payload, field) => {
      const foundKey = aliases[field].find((key) => source[key] !== undefined && source[key] !== null);
      if (!foundKey) return payload;
      const value = source[foundKey];
      const text = structuredText(value, field === 'related_characters' ? '、' : '\n');
      return text ? { ...payload, [field]: text } : payload;
    }, { ...emptyOutlineForm });
  }

  function chapterNumberValue(value: unknown) {
    const match = String(value || '').match(/\d+/);
    return match ? Number(match[0]) : Number.POSITIVE_INFINITY;
  }

  function stripChapterNumberPrefix(value: string) {
    return value.replace(/^第\s*[\d一二三四五六七八九十百千万〇零两]+\s*章\s*[·：:、-]?\s*/, '').trim();
  }

  function displayChapterTitle(chapter: Chapter) {
    return stripChapterNumberPrefix(chapter.title || '') || '未命名章节';
  }

  function chapterTitleWithNumber(title: string, chapterNumber: string) {
    const trimmedTitle = title.trim();
    const trimmedNumber = chapterNumber.trim();
    if (!trimmedNumber) return trimmedTitle;
    if (/^第\s*[\d一二三四五六七八九十百千万〇零两]+\s*章/.test(trimmedTitle)) return trimmedTitle;
    const bareTitle = stripChapterNumberPrefix(trimmedTitle);
    return bareTitle ? `第 ${trimmedNumber} 章 · ${bareTitle}` : `第 ${trimmedNumber} 章`;
  }

  function outlineCandidateForChapter(source: Record<string, unknown>) {
    const normalized = normalizeOutlinePayload(source);
    const chapter = chapters.find(
      (item) => String(item.chapter_number) === String(normalized.chapter_number || '').trim(),
    );
    const chapterNumber = normalized.chapter_number || (chapter ? String(chapter.chapter_number) : '');
    const chapterTitle = chapterTitleWithNumber(normalized.chapter_title || chapter?.title || '', chapterNumber);
    return {
      ...normalized,
      chapter_id: normalized.chapter_id || chapter?.id || '',
      chapter_title: chapterTitle,
      chapter_number: chapterNumber,
    };
  }

  function outlineCandidateTitle(candidate: OutlinePayload, index: number) {
    const number = candidate.chapter_number || String(index + 1);
    const title = candidate.chapter_title || `第 ${number} 章大纲`;
    return `第 ${number} 章 · ${title.replace(/^第\s*\d+\s*章\s*[·：:、-]?\s*/, '')}`;
  }

  async function generateCharacter(mode: 'new' | 'complete' | 'dialogue' | 'consistency') {
    if (!selectedProject) return;
    const workflow = mode === 'consistency' ? 'check_consistency' : 'generate_characters';
    const existingCharacterNames = records
      .map((record) => String(record.payload?.name ?? record.title ?? '').trim())
      .filter(Boolean);
    const result = await executeTask(
      mode === 'dialogue' ? '生成角色对白' : 'AI 生成角色',
      '正在读取角色卡、关系图和 llmwiki 记忆，调用角色工作流...',
      () =>
        api.runAi(selectedProject.id, workflow, {
          mode,
          character: characterForm,
          existing_character_names: existingCharacterNames,
          existing_characters: records,
          generation_contract: {
            avoid_duplicate_names: true,
            instruction: `生成新角色时不得使用这些已有角色名：${existingCharacterNames.join('、') || '暂无'}。`,
          },
        }),
      '角色 AI 工作流已完成，结果已显示在右侧。',
    );
    if (!result) return;
    const structured = structuredFromAi(result);
    if (structured && (mode === 'new' || mode === 'complete')) {
      const characterPayload = normalizeCharacterPayload(structured);
      setCharacterForm((current) =>
        ({
          ...current,
          ...characterPayload,
        }),
      );
    }
    setCharacterAiResults((items) => [
      {
        id: `character-ai-${Date.now()}`,
        title: mode === 'dialogue' ? '角色对白' : '角色生成结果',
        content: formatAiLog(result),
        status: 'ready',
        sourceWorkflow: workflow,
      },
      ...items,
    ]);
    setLog(formatAiLog(result));
  }

  async function generateOutline(mode: 'five' | 'ten' | 'twenty' | 'expand' | 'rhythm') {
    if (!selectedProject) return;
    const workflow =
      mode === 'rhythm' ? 'check_consistency' : mode === 'expand' ? 'generate_chapter_brief' : 'generate_outline';
    const chapterCount = mode === 'five' ? 5 : mode === 'ten' ? 10 : mode === 'twenty' ? 20 : 1;
    const targetChapter =
      selectedChapter ??
      chapters.find((chapter) => String(chapter.chapter_number) === String(outlineForm.chapter_number)) ??
      chapters[0] ??
      null;
    const focusChapterTitle =
      outlineForm.chapter_title || targetChapter?.title || (mode === 'expand' ? '当前章节' : '每个目标章节');
    const duplicateInstruction =
      '必须先检查 llmwiki、已有大纲和时间线，避免重复事件；不得复用已有章节已经发生过的剧情节点。';
    const result = await executeTask(
      'AI 生成大纲',
      '正在读取角色、前文摘要和 llmwiki 记忆，生成结构化大纲...',
      () =>
        api.runAi(selectedProject.id, workflow, {
          chapter_id: targetChapter?.id ?? outlineForm.chapter_id ?? '',
          mode,
          chapter_count: chapterCount,
          outline: outlineForm,
          selected_chapter: targetChapter,
          chapters,
          generation_contract: {
            output: mode === 'expand' ? 'single_chapter_outline' : 'multiple_chapter_outlines',
            include_global_outline: true,
            use_llmwiki: true,
            avoid_duplicate_events: true,
            focus_chapter_title: focusChapterTitle,
            instruction:
              mode === 'expand'
                ? `返回当前章节《${focusChapterTitle}》的结构化章节大纲 JSON，chapter_title 必须写成“第 N 章 · 章节名”。${duplicateInstruction}`
                : `返回 ${chapterCount} 个可独立保存的章节大纲数组，每项包含 chapter_number、chapter_title、chapter_goal、main_conflict、key_events、emotional_rhythm、foreshadowing、hook、related_characters。chapter_title 必须写成“第 N 章 · 章节名”，每章必须围绕自己的章节标题展开。${duplicateInstruction}`,
          },
        }),
      '大纲 AI 工作流已完成，结果已显示在右侧。',
    );
    if (!result) return;
    const structuredItems =
      mode === 'rhythm'
        ? []
        : structuredArrayFromAi(result).sort(
            (left, right) =>
              chapterNumberValue(normalizeOutlinePayload(left).chapter_number) -
              chapterNumberValue(normalizeOutlinePayload(right).chapter_number),
          );
    if (structuredItems.length === 1 && mode === 'expand') {
      const normalized = outlineCandidateForChapter(structuredItems[0]);
      setOutlineScope('chapter');
      setOutlineForm((current) => ({ ...current, ...normalized }));
    }
    const resultCards =
      structuredItems.length > 1
        ? structuredItems.map((item, index) => {
            const normalized = outlineCandidateForChapter(item);
            return {
              id: `outline-ai-${Date.now()}-${index}`,
              title: outlineCandidateTitle(normalized, index),
              content: JSON.stringify(normalized, null, 2),
              status: result.status === 'fallback' ? 'error' : 'ready',
              error: result.error,
              sourceWorkflow: workflow,
            } satisfies WorkbenchAIResult;
          })
        : [
            {
              id: `outline-ai-${Date.now()}`,
              title: mode === 'rhythm' ? '节奏检查结果' : '大纲生成结果',
              content: formatAiLog(result),
              status: result.status === 'fallback' ? 'error' : 'ready',
              error: result.error,
              sourceWorkflow: workflow,
            } satisfies WorkbenchAIResult,
          ];
    setOutlineAiResults((items) => [...resultCards, ...items]);
    setLog(formatAiLog(result));
  }

  async function generateRelationship(mode: 'extract' | 'conflict' | 'consistency') {
    if (!selectedProject) return;
    const workflow = mode === 'extract' ? 'extract_relationships' : 'check_consistency';
    const result = await executeTask(
      'AI 分析角色关系',
      '正在读取角色卡和当前章节，提取关系变化...',
      () =>
        api.runAi(selectedProject.id, workflow, {
          mode,
          relationship: relationshipForm,
          characters: graphCharacters,
          chapter: selectedChapter,
          draft,
        }),
      '角色关系分析完成，结果已显示在右侧。',
    );
    if (!result) return;
    setRelationshipAiResults((items) => [
      {
        id: `relationship-ai-${Date.now()}`,
        title: '关系分析结果',
        content: formatAiLog(result),
        status: 'ready',
        sourceWorkflow: workflow,
      },
      ...items,
    ]);
    setLog(formatAiLog(result));
  }

  async function saveTimelineEvent() {
    if (!selectedProject) return;
    const payload = {
      title: timelineForm.event_time || timelineForm.chapter || '未命名事件',
      category: 'timeline',
      content: [timelineForm.cause, timelineForm.consequence].filter(Boolean).join('\n'),
      payload: { ...timelineForm },
      status: timelineForm.status || '待确认',
    };
    const saved = await executeTask(
      editingTimelineId ? '更新时间线事件' : '保存时间线事件',
      '正在保存事件因果，并同步 timeline.md...',
      async () =>
        editingTimelineId
          ? api.updateRecord(selectedProject.id, 'timeline-events', editingTimelineId, payload)
          : api.createRecord(selectedProject.id, 'timeline-events', payload),
      editingTimelineId ? '时间线事件已更新，并替换同步到 llmwiki。' : '时间线事件已保存，并会同步到 llmwiki。',
    );
    if (!saved) return;
    setEditingTimelineId('');
    setTimelineForm(emptyTimelineForm);
    await loadTabData('timeline', selectedProject.id);
  }

  async function extractTimelineEvents() {
    if (!selectedProject) return;
    const result = await executeTask(
      '提取时间线事件',
      '正在从当前章节正文中提取事件、因果和后续影响...',
      () =>
        api.runAi(selectedProject.id, 'extract_timeline_events', {
          chapter_id: selectedChapter?.id,
          chapter_title: selectedChapter?.title,
          draft,
        }),
      '时间线提取完成，结果已显示在右侧。',
    );
    if (!result) return;
    const structured = structuredFromAi(result);
    if (structured && result.status !== 'fallback' && result.status !== 'local') {
      setTimelineForm((current) =>
        mergeStringFields(current, structured, ['event_time', 'chapter', 'characters', 'cause', 'status', 'consequence']),
      );
    }
    setTimelineAiResults((items) => [
      {
        id: `timeline-ai-${Date.now()}`,
        title: '时间线提取结果',
        content: formatAiLog(result),
        status: result.status === 'fallback' || result.status === 'local' ? 'error' : 'ready',
        error: result.error,
        sourceWorkflow: 'extract_timeline_events',
      },
      ...items,
    ]);
    setLog(formatAiLog(result));
  }

  async function saveForeshadowing() {
    if (!selectedProject) return;
    const payload = {
      title: foreshadowingForm.hint || '未命名伏笔',
      category: foreshadowingForm.status,
      content: [foreshadowingForm.hint, foreshadowingForm.payoff_plan].filter(Boolean).join('\n'),
      payload: { ...foreshadowingForm },
      status: foreshadowingForm.status,
    };
    const saved = await executeTask(
      editingForeshadowingId ? '更新伏笔' : '保存伏笔',
      '正在保存伏笔线索，并同步 foreshadowing.md...',
      async () =>
        editingForeshadowingId
          ? api.updateRecord(selectedProject.id, 'foreshadowings', editingForeshadowingId, payload)
          : api.createRecord(selectedProject.id, 'foreshadowings', payload),
      editingForeshadowingId ? '伏笔已更新，并替换同步到 llmwiki。' : '伏笔已保存，并会同步到 llmwiki。',
    );
    if (!saved) return;
    setEditingForeshadowingId('');
    setForeshadowingForm(emptyForeshadowingForm);
    await loadTabData('foreshadowing', selectedProject.id);
  }

  async function extractForeshadowing() {
    if (!selectedProject) return;
    const result = await executeTask(
      '提取伏笔线索',
      '正在从当前章节中提取埋线、回收计划和相关角色...',
      () =>
        api.runAi(selectedProject.id, 'extract_memory', {
          mode: 'foreshadowing',
          chapter_id: selectedChapter?.id,
          chapter_title: selectedChapter?.title,
          draft,
        }),
      '伏笔提取完成，结果已显示在右侧。',
    );
    if (!result) return;
    const structured = structuredFromAi(result);
    if (structured) {
      setForeshadowingForm((current) =>
        mergeStringFields(current, structured, [
          'setup_chapter',
          'payoff_chapter',
          'status',
          'related_characters',
          'hint',
          'payoff_plan',
        ]),
      );
    }
    setForeshadowingAiResults((items) => [
      {
        id: `foreshadowing-ai-${Date.now()}`,
        title: '伏笔提取结果',
        content: formatAiLog(result),
        status: 'ready',
        sourceWorkflow: 'extract_memory',
      },
      ...items,
    ]);
    setLog(formatAiLog(result));
  }

  async function saveTabooRule() {
    if (!selectedProject) return;
    const payload = {
      title: tabooRuleForm.rule || '未命名雷点规则',
      category: tabooRuleForm.severity,
      content: [tabooRuleForm.rule, tabooRuleForm.response].filter(Boolean).join('\n'),
      payload: { ...tabooRuleForm },
      status: 'active',
    };
    const saved = await executeTask(
      editingTabooRuleId ? '更新雷点规则' : '保存雷点规则',
      '正在保存雷点规则，并同步 taboo-rules.md...',
      async () =>
        editingTabooRuleId
          ? api.updateRecord(selectedProject.id, 'taboo-rules', editingTabooRuleId, payload)
          : api.createRecord(selectedProject.id, 'taboo-rules', payload),
      editingTabooRuleId ? '雷点规则已更新，并替换同步到 llmwiki。' : '雷点规则已保存，并会注入后续章节生成上下文。',
    );
    if (!saved) return;
    setEditingTabooRuleId('');
    setTabooRuleForm(emptyTabooRuleForm);
    await loadTabData('taboo', selectedProject.id);
  }

  async function checkTabooRules() {
    if (!selectedProject) return;
    const result = await executeTask(
      '检查雷点规则',
      '正在检查当前正文是否触碰雷点规则...',
      () =>
        api.runAi(selectedProject.id, 'check_taboo_rules', {
          chapter_id: selectedChapter?.id,
          content: draft,
          rule: tabooRuleForm,
        }),
      '雷点检查完成，结果已显示在右侧。',
    );
    if (!result) return;
    setTabooAiResults((items) => [
      {
        id: `taboo-ai-${Date.now()}`,
        title: '雷点检查结果',
        content: formatAiLog(result),
        status: result.status === 'fallback' ? 'error' : 'ready',
        error: result.error,
        sourceWorkflow: 'check_taboo_rules',
      },
      ...items,
    ]);
    setLog(formatAiLog(result));
  }

  async function saveKnowledgeDocument() {
    if (!selectedProject) return;
    const payload = {
      title: knowledgeForm.wiki_path || knowledgeForm.tags || '未命名资料',
      category: knowledgeForm.source_type,
      content: knowledgeForm.content,
      payload: { ...knowledgeForm },
      status: 'active',
    };
    const saved = await executeTask(
      editingKnowledgeId ? '更新知识库资料' : '保存知识库资料',
      '正在保存资料索引，并同步项目 llmwiki 记忆层...',
      async () =>
        editingKnowledgeId
          ? api.updateRecord(selectedProject.id, 'knowledge-documents', editingKnowledgeId, payload)
          : api.createRecord(selectedProject.id, 'knowledge-documents', payload),
      editingKnowledgeId ? '知识库资料已更新，并替换同步到项目 llmwiki。' : '知识库资料已保存，并同步到项目 llmwiki 记忆层。',
    );
    if (!saved) return;
    setEditingKnowledgeId('');
    setKnowledgeForm(emptyKnowledgeForm);
    await Promise.all([
      loadTabData('knowledge', selectedProject.id),
      activeTabRef.current === 'wiki' ? loadTabData('wiki', selectedProject.id) : Promise.resolve(),
      loadWikiPageCount(selectedProject.id),
    ]);
  }

  function applyCharacterAiResult(content: string) {
    const structured = structuredFromAi({ text: content });
    if (structured) {
      const characterPayload = normalizeCharacterPayload(structured);
      if (Object.keys(characterPayload).length > 0) {
        setCharacterForm((current) => ({
          ...current,
          ...characterPayload,
        }));
        setLog('AI 角色结果已拆分填入可编辑角色卡。');
        return;
      }
    }
    setCharacterForm((current) => ({
      ...current,
      notes: [current.notes, content].filter(Boolean).join('\n\n'),
    }));
    setLog('AI 结果已应用到角色备注。');
  }

  function applyOutlineAiResult(content: string) {
    const structured = structuredFromAi({ text: content });
    if (structured) {
      const normalized = normalizeOutlinePayload(structured);
      setOutlineScope('chapter');
      setOutlineForm((current) => ({ ...current, ...normalized }));
      setLog('AI 大纲结果已拆分填入当前章节剧情板。');
      return;
    }
    setOutlineForm((current) => ({
      ...current,
      key_events: [current.key_events, content].filter(Boolean).join('\n\n'),
    }));
    setLog('AI 大纲结果已加入关键事件。');
  }

  function applyRelationshipAiResult(content: string) {
    setRelationshipForm((current) => ({
      ...current,
      change_history: [current.change_history, content].filter(Boolean).join('\n\n'),
    }));
    setLog('AI 关系分析已加入变化记录。');
  }

  function applyTimelineAiResult(content: string) {
    setTimelineForm((current) => ({
      ...current,
      consequence: [current.consequence, content].filter(Boolean).join('\n\n'),
    }));
    setLog('AI 时间线结果已加入后续影响。');
  }

  function applyForeshadowingAiResult(content: string) {
    setForeshadowingForm((current) => ({
      ...current,
      payoff_plan: [current.payoff_plan, content].filter(Boolean).join('\n\n'),
    }));
    setLog('AI 伏笔结果已加入回收计划。');
  }

  function applyTabooAiResult(content: string) {
    setTabooRuleForm((current) => ({
      ...current,
      response: [current.response, content].filter(Boolean).join('\n\n'),
    }));
    setLog('AI 雷点检查已加入处理方式。');
  }

  async function createWikiPage() {
    if (!selectedProject) return;
    const saved = await executeTask(
      '写入 Wiki 页面',
      '正在写入当前项目 memory/wiki 目录...',
      () => api.wikiWrite(selectedProject.id, recordTitle || 'notes/index.md', recordContent || '# 新记忆页'),
      'Wiki 页面已写入当前项目 memory/wiki。',
    );
    if (!saved) return;
    await loadWikiPageCount(selectedProject.id);
    await loadTabData('wiki', selectedProject.id);
  }

  function parseModelPayload(record: GenericRecord): ModelPayload {
    const payload = record.payload ?? {};
    return {
      provider: String(payload.provider ?? record.category ?? 'OpenAI'),
      api_key: String(payload.api_key ?? ''),
      base_url: String(payload.base_url ?? ''),
      model_name: String(payload.model_name ?? record.content ?? ''),
      temperature: Number(payload.temperature ?? 0.7),
      max_tokens: Number(payload.max_tokens ?? 4000),
      is_default: Boolean(payload.is_default),
    };
  }

  function modelLabel(record?: GenericRecord) {
    if (!record) return '当前使用本地占位模型';
    const payload = parseModelPayload(record);
    return `${record.title || payload.model_name || '未命名模型'} · ${payload.model_name || payload.provider}`;
  }

  function modelForWorkflow(workflow: string) {
    const route = taskRoutes.find((item) => item.category === workflow || item.title === workflow);
    const routed = route ? modelConfigs.find((model) => model.id === route.content) : undefined;
    if (routed) return routed;
    return modelConfigs.find((model) => parseModelPayload(model).is_default) ?? modelConfigs[0];
  }

  function formatAiLog(result: { status?: string; error?: string; text: string }, prefix = '') {
    if (result.status === 'local') {
      return `${prefix}当前没有可用于该任务的远程模型，已使用本地占位结果。${result.error ? `原因：${result.error}` : ''}`;
    }
    if (result.status === 'fallback') {
      if (result.error?.includes('仍可能在生成') || result.error?.includes('暂未返回结果')) {
        return `${prefix}远程模型仍可能在生成，当前显示本地占位结果。${result.error ? `说明：${result.error}` : ''}`;
      }
      return `${prefix}远程模型调用失败，已回退到本地占位结果。${result.error ? `错误摘要：${result.error}` : ''}`;
    }
    return `${prefix}${result.text}`;
  }

  async function saveModelConfig() {
    if (!selectedProject) {
      setLog('请先选择项目，再保存模型配置。');
      return;
    }
    const executionTitle = '保存模型配置';
    startExecution(executionTitle, '正在写入当前项目的模型配置...');
    const payload = {
      title: modelForm.title || modelForm.model_name || '未命名模型',
      category: modelForm.provider,
      content: modelForm.model_name,
      payload: {
        provider: modelForm.provider,
        api_key: modelForm.api_key,
        base_url: modelForm.base_url,
        model_name: modelForm.model_name,
        temperature: modelForm.temperature,
        max_tokens: modelForm.max_tokens,
        is_default: modelForm.is_default,
      },
      status: 'active',
    };
    try {
      if (modelForm.id) {
        await api.updateRecord(selectedProject.id, 'model-configs', modelForm.id, payload);
      } else {
        await api.createRecord(selectedProject.id, 'model-configs', payload);
      }
      setModelForm(emptyModelForm);
      await loadSettingsData(selectedProject.id);
      finishExecution(executionTitle, modelForm.id ? '模型配置已更新。' : '模型配置已保存。');
    } catch (error) {
      failExecution(executionTitle, `模型配置保存失败：${error instanceof Error ? error.message : '未知错误'}`);
    }
  }

  async function deleteModelConfig(recordId: string) {
    if (!selectedProject) return;
    await api.deleteRecord(selectedProject.id, 'model-configs', recordId);
    await loadSettingsData(selectedProject.id);
    setLog('模型配置已删除。');
  }

  function editModelConfig(record: GenericRecord) {
    const payload = parseModelPayload(record);
    setModelForm({ id: record.id, title: record.title, ...payload });
  }

  async function saveTaskRoute(workflow: string, modelId: string) {
    if (!selectedProject) return;
    const existing = taskRoutes.find((route) => route.category === workflow || route.title === workflow);
    const payload = {
      title: workflow,
      category: workflow,
      content: modelId,
      payload: { workflow, model_config_id: modelId },
      status: 'active',
    };
    if (existing) {
      await api.updateRecord(selectedProject.id, 'model-task-routes', existing.id, payload);
    } else {
      await api.createRecord(selectedProject.id, 'model-task-routes', payload);
    }
    await loadSettingsData(selectedProject.id);
    setLog('任务路由已保存。');
  }

  async function savePrivacyMode() {
    if (!selectedProject) return;
    const updated = await api.updateProject(selectedProject.id, { ...selectedProject, privacy_mode: privacyMode });
    setSelectedProject(updated);
    setProjects((items) => items.map((item) => (item.id === updated.id ? updated : item)));
    setLog('隐私模式已保存。');
  }

  async function testConnection() {
    if (!selectedProject) {
      setLog('请先选择项目，再测试连接。');
      return;
    }
    const hasFormInput = Boolean(modelForm.id || modelForm.api_key.trim() || modelForm.model_name.trim() || modelForm.title.trim());
    const activeModel = modelForWorkflow('generate_chapter_draft');
    const payload = hasFormInput ? modelForm : activeModel ? parseModelPayload(activeModel) : null;
    if (!payload || !payload.api_key.trim() || !payload.model_name.trim()) {
      setLog('连接测试失败：请先填写 API Key 与 Model Name，或保存一个可用模型并设为默认。');
      return;
    }
    const executionTitle = '测试模型连接';
    startExecution(executionTitle, '正在向远程模型发送最小连接测试请求...');
    try {
      const result = await api.testModelConnection(selectedProject.id, {
        provider: payload.provider,
        api_key: payload.api_key,
        base_url: payload.base_url,
        model_name: payload.model_name,
        temperature: payload.temperature,
        max_tokens: payload.max_tokens,
      });
      finishExecution(
        executionTitle,
        `连接测试成功：${result.message} 当前模型：${result.model}${
          hasFormInput && !modelForm.id ? '。请保存配置并设为默认或配置任务路由，否则正文生成仍会使用本地占位。' : ''
        }`,
      );
    } catch (error) {
      failExecution(executionTitle, `连接测试失败：${error instanceof Error ? error.message : '未知错误'}`);
    }
  }

  async function analyzeStyleSample() {
    if (!selectedProject || !styleSampleText.trim()) return;
    const result = await executeTask(
      '分析写作风格',
      '正在调用 AI 分析样本文风、句式和对白习惯...',
      () =>
        api.runAi(selectedProject.id, 'analyze_style_sample', {
          content: styleSampleText,
          prompt: '请分析这段文本的写作语气、句式节奏、意象偏好、叙述视角、对白习惯和可复用风格规则。',
        }),
      '风格样本已完成 AI 分析。',
    );
    if (!result) return;
    setStyleAnalysis(formatAiLog(result));
  }

  async function imitateStyleSample() {
    if (!selectedProject || !styleSampleText.trim()) return;
    const result = await executeTask(
      '模拟写作语气',
      '正在基于风格样本生成试写片段...',
      () =>
        api.runAi(selectedProject.id, 'analyze_style_sample', {
          content: styleSampleText,
          prompt: `请模仿样本文风写一段新文本。写作要求：${styleWritingGoal || '延续悬疑氛围，并表现人物心理变化。'}`,
        }),
      '已生成风格模拟片段。',
    );
    if (!result) return;
    setStyleImitation(formatAiLog(result));
  }

  async function saveStyleProfile() {
    if (!selectedProject) return;
    const projectId = selectedProject.id;
    const saved = await executeTask(
      '保存风格档案',
      '正在保存风格档案，并同步到项目 llmwiki...',
      () =>
        api.createRecord(projectId, 'style-profiles', {
          title: styleSampleTitle || '未命名风格档案',
          category: 'style',
          content: styleAnalysis || styleSampleText,
          payload: {
            sample: styleSampleText,
            analysis: styleAnalysis,
            imitation: styleImitation,
            writing_goal: styleWritingGoal,
          },
          status: 'active',
        }),
      '风格档案已保存到当前项目。',
    );
    if (!saved) return;
    if (selectedProjectRef.current?.id !== projectId) return;
    await loadTabData('style', projectId);
    await loadStyleProfileRecords(projectId);
  }

  async function continueLocalMode() {
    setAuthStatus(localAuthStatus);
    setLog('已保持本地模式：小说正文、记忆和 API Key 不会因为 OAuth 自动上传。');
  }

  async function startOauthLogin() {
    try {
      const result = await api.startOauth('openai');
      setLog(result.message);
    } catch (error) {
      setLog(`OAuth 登录入口暂不可用：${error instanceof Error ? error.message : '未知错误'}`);
    }
  }

  async function logout() {
    try {
      setAuthStatus(await api.logout());
      setLog('已退出登录，继续本地使用。');
    } catch {
      setAuthStatus(localAuthStatus);
      setLog('已回到本地模式。');
    }
  }

  const activeTabMeta = tabs.find((tab) => tab.key === activeTab);
  const isWritingTab = activeTab === 'chapters';
  const executionBusy = executionStatus.state === 'running';
  const executionLabel =
    executionStatus.state === 'running'
      ? `正在执行：${executionStatus.title}`
      : executionStatus.state === 'success'
        ? `执行完成：${executionStatus.title}`
        : executionStatus.state === 'error'
          ? `执行失败：${executionStatus.title}`
          : executionStatus.title;
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark">
            <Brain size={28} />
          </div>
          <div>
            <h1>AI 小说创作平台</h1>
            <p>本地优先 / 长篇记忆 / 项目隔离</p>
          </div>
        </div>

        <div className="create-project">
          <div className="section-title">
            <span>项目库</span>
            <small>{projects.length} 本小说</small>
          </div>
          <input value={projectTitle} onChange={(event) => setProjectTitle(event.target.value)} aria-label="项目标题" />
          <button className="primary-action" onClick={() => void createProject()}>
            <Plus size={16} />
            新建项目
          </button>
        </div>

        <div className="project-list">
          {projects.map((project) => (
            <article className={project.id === selectedProject?.id ? 'project-card selected' : 'project-card'} key={project.id}>
            <button
              className={project.id === selectedProject?.id ? 'selected' : ''}
              onClick={() => setSelectedProject(project)}
            >
              <strong>{project.title}</strong>
              <span>{project.genre || '本地项目'} · {project.target_chapter_count || 0} 章计划</span>
            </button>
              <button
                className="danger-link"
                onClick={() => {
                  setDeleteProjectTarget(project);
                  setDeleteProjectPassword('');
                }}
              >
                <Trash2 size={14} />
                删除
              </button>
            </article>
          ))}
          {projects.length === 0 && (
            <div className="empty-project">
              <strong>从侧栏创建第一本小说</strong>
              <span>后续章节、记忆、导出都会自动归属这里选中的项目。</span>
            </div>
          )}
        </div>

        {deleteProjectTarget && (
          <div className="delete-project-panel">
            <strong>删除项目：{deleteProjectTarget.title}</strong>
            <p>删除后会移出项目库。请输入删除密码；如果未配置环境变量，请输入项目名称。</p>
            <input
              aria-label="删除项目密码"
              type="password"
              value={deleteProjectPassword}
              onChange={(event) => setDeleteProjectPassword(event.target.value)}
              placeholder="删除密码或项目名称"
            />
            <div className="compact-actions">
              <button onClick={() => {
                setDeleteProjectTarget(null);
                setDeleteProjectPassword('');
              }}>
                取消
              </button>
              <button className="danger-action" onClick={() => void deleteProject()} disabled={!deleteProjectPassword.trim()}>
                确认删除
              </button>
            </div>
          </div>
        )}

        <div className="sidebar-tools">
          <button className={activeTab === 'settings' ? 'selected' : ''} onClick={() => setActiveTab('settings')}>
            <Settings size={16} />
            设置
          </button>
        </div>
      </aside>

      <main className={isWritingTab ? 'workspace writing-workspace' : 'workspace'}>
        {isWritingTab ? (
          <header className="writing-dock">
            <div>
              <span className="eyebrow">写作工作台</span>
              <strong>{selectedProject?.title ?? '还没有项目'}</strong>
              <span>
                {selectedChapter
                  ? `第 ${selectedChapter.chapter_number} 章 · ${displayChapterTitle(selectedChapter)}`
                  : '选择章节后开始写作'}
              </span>
            </div>
            <div className="writing-dock-actions">
              <span>
                <CheckCircle2 size={15} />
                遵循 CLAUDE.md
              </span>
              <span>{authStatus.authenticated ? '云端账户已登录' : '本地优先'}</span>
              <span>{modelLabel(modelForWorkflow('generate_chapter_draft'))}</span>
              <span className={`writing-execution ${executionStatus.state}`} role="status" aria-live="polite">
                {executionStatus.state === 'running' && <LoaderCircle className="execution-spinner" size={15} />}
                {executionLabel}
              </span>
            </div>
          </header>
        ) : (
          <header className="topbar">
            <div>
              <span className="eyebrow">智能创作工作室</span>
              <h2>{selectedProject?.title ?? '还没有项目'}</h2>
              <p className="project-context">
                {selectedProject
                  ? `所有操作写入 ${selectedProject.title} 的项目目录`
                  : '先从左侧项目库创建或选择小说项目'}
              </p>
            </div>
            <div className="topbar-stack">
              <div className="studio-command">
                <Sparkles size={16} />
                <span>/imagine 下一章的悬念、记忆线索与人物暗流</span>
              </div>
              <div className="claude-note">
                <CheckCircle2 size={16} />
                执行计划前读取并遵循 CLAUDE.md
              </div>
              <div className="status-pill">
                <span>{log}</span>
              </div>
              <div className={`execution-status ${executionStatus.state}`} role="status" aria-live="polite">
                {executionStatus.state === 'running' ? (
                  <LoaderCircle className="execution-spinner" size={16} />
                ) : executionStatus.state === 'error' ? (
                  <ShieldAlert size={16} />
                ) : (
                  <CheckCircle2 size={16} />
                )}
                <div>
                  <strong>{executionLabel}</strong>
                  <span>{executionStatus.detail}</span>
                </div>
              </div>
            </div>
          </header>
        )}

        <nav className="tabs">
          {tabs.map((tab) => {
            const Icon = tab.icon;
            return (
              <button
                className={activeTab === tab.key ? 'active' : ''}
                key={tab.key}
                onClick={() => setActiveTab(tab.key)}
                title={`${tab.label}：${tab.description}`}
              >
                <Icon size={16} />
                <span>{tab.label}</span>
                <small>{tab.description}</small>
              </button>
            );
          })}
        </nav>

        {activeTabMeta && !isWritingTab && (
          <section className="feature-explainer" aria-label="当前功能说明">
            <div>
              <span>当前入口说明</span>
              <strong>{activeTabMeta.label}</strong>
            </div>
            <p>{activeTabMeta.description}</p>
          </section>
        )}

        {!isWritingTab && (
          <section className="context-strip" aria-label="工作台状态">
            <div>
              <span>运行模式</span>
              <strong>{authStatus.authenticated ? '云端账户已登录' : '本地优先'}</strong>
            </div>
            <div>
              <span>章节</span>
              <strong>{chapters.length} 章</strong>
            </div>
            <div>
              <span>记忆</span>
              <strong>{wikiPageCount} 个 Wiki 页面</strong>
            </div>
            <div>
              <span>AI 模型</span>
              <strong>{modelLabel(modelForWorkflow('generate_chapter_draft'))}</strong>
            </div>
          </section>
        )}

        {activeTab === 'chapters' && (
          <NovelEditorPage
            project={selectedProject}
            chapters={chapters}
            selectedChapter={selectedChapter}
            versions={versions}
            styleProfiles={styleProfileRecords.map((record) => ({ id: record.id, title: record.title }))}
            selectedStyleProfileId={selectedStyleProfileId}
            draft={draft}
            log={log}
            modelLabel={modelLabel(modelForWorkflow('generate_chapter_draft'))}
            wikiPageCount={wikiPageCount}
            onCreateChapter={() => void createChapter()}
            onDeleteChapter={(chapter) => void deleteChapter(chapter)}
            onSelectChapter={setSelectedChapter}
            onDraftChange={setDraft}
            onChapterTitleChange={updateChapterTitle}
            onSaveChapter={() => void saveChapter()}
            onGenerateVariant={() => void generateVariant()}
            onGenerateChapterDraft={generateChapterDraftFromAI}
            onStyleProfileChange={setSelectedStyleProfileId}
            onSaveAiResultAsVersion={saveAiResultAsVersion}
            onScoreChapter={() => void scoreChapter()}
            onFinalizeChapter={() => void finalizeChapter()}
            onSelectVersion={(versionId) => void selectVersion(versionId)}
            onOpenSettings={() => setActiveTab('settings')}
            onOpenResource={(resource) => setActiveTab(resource)}
            onLog={setLog}
          />
        )}

        {activeTab === 'graph' && (
          <RelationshipGraphWorkbench
            relationships={records}
            characters={graphCharacters}
            form={relationshipForm}
            aiResults={relationshipAiResults}
            modelLabel={modelLabel(modelForWorkflow('extract_relationships'))}
            editingRecordId={editingRelationshipId}
            onFormChange={(field, value) => setRelationshipForm((current) => ({ ...current, [field]: value }))}
            onSaveRelationship={() => void saveRelationshipRecord()}
            onSelectRelationship={selectRelationshipRecord}
            onCancelEdit={cancelRelationshipEdit}
            onCreateCharacter={() => void createGraphCharacter()}
            onGenerate={(mode) => void generateRelationship(mode)}
            onApplyResult={applyRelationshipAiResult}
            onDeleteResult={(id) => setRelationshipAiResults((items) => items.filter((item) => item.id !== id))}
          />
        )}

        {activeTab === 'settings' && (
          <section className="settings-page">
            <aside className="settings-nav">
              <div className="settings-nav-title">
                <span>设置中心</span>
                <small>本地优先配置</small>
              </div>
              {settingsSections.map((section) => (
                <button
                  className={settingsSection === section.key ? 'active' : ''}
                  key={section.key}
                  onClick={() => setSettingsSection(section.key)}
                >
                  <strong>{section.title}</strong>
                  <span>{section.description}</span>
                </button>
              ))}
            </aside>

            <div className="settings-content">
              <div className="settings-content-header">
                <div>
                  <span className="eyebrow">Settings</span>
                  <h3>{settingsTitleMap[settingsSection]}</h3>
                </div>
                <div className="settings-badges">
                  <span>{authStatus.authenticated ? '已登录' : '本地模式'}</span>
                  <span>{modelConfigs.length ? `${modelConfigs.length} 个模型` : '占位模型'}</span>
                </div>
              </div>

              {settingsSection === 'account' && (
                <div className="settings-card account-card">
                  <div className="account-status">
                    <div className={authStatus.authenticated ? 'account-avatar signed-in' : 'account-avatar'}>
                      {authStatus.user?.avatar_url ? (
                        <img src={authStatus.user.avatar_url} alt={authStatus.user.name} />
                      ) : authStatus.authenticated ? (
                        authStatus.user?.name.slice(0, 1) ?? <UserCircle size={22} />
                      ) : (
                        <CloudOff size={22} />
                      )}
                    </div>
                    <div>
                      <strong>{authStatus.authenticated ? '已登录' : '本地模式'}</strong>
                      <p>{authStatus.message}</p>
                    </div>
                  </div>
                  {authStatus.authenticated && authStatus.user ? (
                    <div className="signed-in-profile">
                      <div>
                        <strong>{authStatus.user.name}</strong>
                        <span>{authStatus.user.email}</span>
                        <span>Provider：{authStatus.user.provider}</span>
                      </div>
                      <button onClick={() => void logout()}>
                        <LogOut size={15} />
                        退出登录
                      </button>
                    </div>
                  ) : (
                    <>
                      <div className="action-row account-actions">
                        <button onClick={() => void continueLocalMode()}>
                          <CloudOff size={15} />
                          继续本地使用
                        </button>
                        <button className="primary-action" onClick={() => void startOauthLogin()}>
                          <Cloud size={15} />
                          OAuth 登录
                        </button>
                      </div>
                      <div className="provider-row">
                        <span>OpenAI</span>
                        <span>GitHub</span>
                        <span>Google</span>
                        <span>自定义 Provider</span>
                      </div>
                    </>
                  )}
                  <div className="privacy-list">
                    <p>本地项目默认保存在本机，OAuth 登录不会自动上传小说正文。</p>
                    <p>只有你后续主动开启同步时，才会考虑云端同步。</p>
                    <p>API Key 仍优先保存在当前项目的本地模型配置中，不和 OAuth 账号强绑定。</p>
                  </div>
                </div>
              )}

              {settingsSection === 'models' && (
                <div className="settings-card model-config-card">
                  <div className="section-toolbar">
                    <div>
                      <strong>模型配置</strong>
                      <span>{modelConfigs.length ? `${modelConfigs.length} 个配置` : '还没有模型配置'}</span>
                    </div>
                    <button onClick={() => setModelForm(emptyModelForm)}>新建配置</button>
                  </div>
                  <div className="settings-grid">
                    <label>
                      配置名称
                      <input
                        aria-label="配置名称"
                        value={modelForm.title}
                        onChange={(event) => setModelForm({ ...modelForm, title: event.target.value })}
                        placeholder="例如：DeepSeek 写作模型"
                      />
                    </label>
                    <label>
                      服务商类型
                      <select
                        value={modelForm.provider}
                        onChange={(event) => setModelForm({ ...modelForm, provider: event.target.value })}
                      >
                        {providerOptions.map((provider) => (
                          <option key={provider} value={provider}>
                            {provider}
                          </option>
                        ))}
                      </select>
                    </label>
                    <label className="api-key-field">
                      API Key
                      <span>
                        <input
                          aria-label="API Key"
                          type={showApiKey ? 'text' : 'password'}
                          value={modelForm.api_key}
                          onChange={(event) => setModelForm({ ...modelForm, api_key: event.target.value })}
                          placeholder="sk-..."
                        />
                        <button type="button" onClick={() => setShowApiKey(!showApiKey)}>
                          {showApiKey ? <EyeOff size={15} /> : <Eye size={15} />}
                        </button>
                      </span>
                    </label>
                    <label>
                      Base URL
                      <input
                        value={modelForm.base_url}
                        onChange={(event) => setModelForm({ ...modelForm, base_url: event.target.value })}
                        placeholder="https://api.openai.com/v1"
                      />
                    </label>
                    <label>
                      Model Name
                      <input
                        value={modelForm.model_name}
                        onChange={(event) => setModelForm({ ...modelForm, model_name: event.target.value })}
                        placeholder="gpt-4o-mini"
                      />
                    </label>
                    <label>
                      Temperature
                      <input
                        type="number"
                        step="0.1"
                        min="0"
                        max="2"
                        value={modelForm.temperature}
                        onChange={(event) => setModelForm({ ...modelForm, temperature: Number(event.target.value) })}
                      />
                    </label>
                    <label>
                      Max Tokens
                      <input
                        type="number"
                        min="1"
                        value={modelForm.max_tokens}
                        onChange={(event) => setModelForm({ ...modelForm, max_tokens: Number(event.target.value) })}
                      />
                    </label>
                    <label className="check-row">
                      <input
                        type="checkbox"
                        checked={modelForm.is_default}
                        onChange={(event) => setModelForm({ ...modelForm, is_default: event.target.checked })}
                      />
                      是否默认模型
                    </label>
                  </div>
                  <div className="action-row">
                    <button className="primary-action" onClick={() => void saveModelConfig()} disabled={executionBusy}>
                      {executionBusy && executionStatus.title === '保存模型配置' ? (
                        <LoaderCircle className="execution-spinner" size={15} />
                      ) : (
                        <Save size={15} />
                      )}
                      {executionBusy && executionStatus.title === '保存模型配置' ? '保存中' : '保存配置'}
                    </button>
                    <button onClick={() => void testConnection()} disabled={executionBusy}>
                      <Wifi size={15} />
                      测试连接
                    </button>
                  </div>
                  <div className="model-list">
                    {modelConfigs.map((model) => {
                      const payload = parseModelPayload(model);
                      return (
                        <article key={model.id}>
                          <div>
                            <strong>{model.title}</strong>
                            <span>{payload.provider} / {payload.model_name || '未填写模型名'}</span>
                          </div>
                          <div className="compact-actions">
                            <button onClick={() => editModelConfig(model)}>编辑</button>
                            <button onClick={() => void deleteModelConfig(model.id)}>
                              <Trash2 size={14} />
                              删除
                            </button>
                          </div>
                        </article>
                      );
                    })}
                    {modelConfigs.length === 0 && <p className="empty-state">还没有模型配置，AI 操作会使用本地占位模型。</p>}
                  </div>
                </div>
              )}

              {settingsSection === 'routes' && (
                <div className="settings-card">
                  <div className="section-toolbar">
                    <div>
                      <strong>任务路由</strong>
                      <span>给生成、评分、摘要、记忆提取分配不同模型。</span>
                    </div>
                  </div>
                  <div className="route-list structured">
                    {workflowOptions.map((workflow) => {
                      const selected = modelForWorkflow(workflow.key);
                      return (
                        <label key={workflow.key}>
                          <span>{workflow.label}</span>
                          <select
                            value={selected?.id ?? ''}
                            onChange={(event) => void saveTaskRoute(workflow.key, event.target.value)}
                          >
                            <option value="">本地占位模型</option>
                            {modelConfigs.map((model) => (
                              <option key={model.id} value={model.id}>
                                {modelLabel(model)}
                              </option>
                            ))}
                          </select>
                        </label>
                      );
                    })}
                  </div>
                </div>
              )}

              {settingsSection === 'privacy' && (
                <div className="settings-card">
                  <div className="section-toolbar">
                    <div>
                      <strong>隐私模式</strong>
                      <span>确认哪些数据留在本机，哪些数据可能发给远程模型。</span>
                    </div>
                  </div>
                  <label className="privacy-toggle">
                    <input type="checkbox" checked={privacyMode} onChange={(event) => setPrivacyMode(event.target.checked)} />
                    小说正文、设定、记忆默认保存在本机；调用远程模型时只发送必要上下文。
                  </label>
                  <button onClick={() => void savePrivacyMode()}>保存隐私设置</button>
                  <div className="privacy-list">
                    <p>OAuth 登录不等于云同步，不会自动上传项目。</p>
                    <p>项目、章节、Wiki 和导出文件仍以 project_id 隔离保存在本地。</p>
                    <p>API Key 仍保存在当前项目的模型配置中。</p>
                  </div>
                </div>
              )}

              {settingsSection === 'status' && (
                <div className="settings-card">
                  <div className="section-toolbar">
                    <div>
                      <strong>调用状态</strong>
                      <span>快速判断当前 AI 能力来自远程模型还是本地占位。</span>
                    </div>
                    <button onClick={() => void testConnection()}>
                      <Wifi size={15} />
                      测试连接
                    </button>
                  </div>
                  <div className="status-grid">
                    <div>
                      <span>账户</span>
                      <strong>{authStatus.authenticated ? '已登录' : '本地模式'}</strong>
                    </div>
                    <div>
                      <span>默认模型</span>
                      <strong>{modelLabel(modelForWorkflow('generate_chapter_draft'))}</strong>
                    </div>
                    <div>
                      <span>Fallback</span>
                      <strong>失败时回退到本地占位结果</strong>
                    </div>
                  </div>
                  <div className="api-status">
                    <strong>最近状态</strong>
                    <p>{log}</p>
                  </div>
                </div>
              )}
            </div>
          </section>
        )}

        {activeTab === 'style' && (
          <StyleLearningPanel
            records={records}
            sampleTitle={styleSampleTitle}
            sampleText={styleSampleText}
            writingGoal={styleWritingGoal}
            analysis={styleAnalysis}
            imitation={styleImitation}
            modelLabel={modelLabel(modelForWorkflow('analyze_style_sample'))}
            onSampleTitleChange={setStyleSampleTitle}
            onSampleTextChange={setStyleSampleText}
            onWritingGoalChange={setStyleWritingGoal}
            onImportText={(text, fileName) => {
              setStyleSampleText(text);
              setStyleSampleTitle(fileName.replace(/\.(txt|md)$/i, ''));
              setLog(`已导入风格样本：${fileName}`);
            }}
            onAnalyze={() => void analyzeStyleSample()}
            onImitate={() => void imitateStyleSample()}
            onSaveProfile={() => void saveStyleProfile()}
          />
        )}

        {activeTab === 'characters' && (
          <CharacterWorkbench
            records={records}
            form={characterForm}
            aiResults={characterAiResults}
            modelLabel={modelLabel(modelForWorkflow('generate_characters'))}
            saveStatus={characterSaveStatus}
            editingRecordId={editingCharacterId}
            onFormChange={(field, value) => setCharacterForm((current) => ({ ...current, [field]: value }))}
            onSave={() => void saveCharacterProfile()}
            onSelectRecord={selectCharacterRecord}
            onCancelEdit={cancelCharacterEdit}
            onGenerate={(mode) => void generateCharacter(mode)}
            onApplyResult={applyCharacterAiResult}
            onDeleteResult={(id) => setCharacterAiResults((items) => items.filter((item) => item.id !== id))}
          />
        )}

        {activeTab === 'outline' && (
          <OutlineWorkbench
            records={records}
            chapters={chapters}
            form={outlineForm}
            scope={outlineScope}
            aiResults={outlineAiResults}
            modelLabel={modelLabel(modelForWorkflow('generate_outline'))}
            editingRecordId={editingOutlineId}
            onScopeChange={(scope) => {
              setOutlineScope(scope);
              if (scope === 'global') createGlobalOutlineDraft();
            }}
            onFormChange={(field, value) => setOutlineForm((current) => ({ ...current, [field]: value }))}
            onSave={() => void saveOutlineRecord()}
            onSelectRecord={selectOutlineRecord}
            onCancelEdit={cancelOutlineEdit}
            onGenerate={(mode) => void generateOutline(mode)}
            onApplyResult={applyOutlineAiResult}
            onSaveResult={(content) => void saveOutlineCandidate(content)}
            onCreateGlobalOutline={createGlobalOutlineDraft}
            onDeleteRecord={(recordId) => void deleteOutlineRecord(recordId)}
            onDeleteResult={(id) => setOutlineAiResults((items) => items.filter((item) => item.id !== id))}
          />
        )}

        {activeTab === 'timeline' && (
          <TimelineWorkbench
            records={records}
            form={timelineForm}
            aiResults={timelineAiResults}
            modelLabel={modelLabel(modelForWorkflow('extract_timeline_events'))}
            editingRecordId={editingTimelineId}
            onFormChange={(field, value) => setTimelineForm((current) => ({ ...current, [field]: value }))}
            onSave={() => void saveTimelineEvent()}
            onSelectRecord={selectTimelineRecord}
            onCancelEdit={cancelTimelineEdit}
            onExtract={() => void extractTimelineEvents()}
            onApplyResult={applyTimelineAiResult}
            onDeleteResult={(id) => setTimelineAiResults((items) => items.filter((item) => item.id !== id))}
          />
        )}

        {activeTab === 'foreshadowing' && (
          <ForeshadowingWorkbench
            records={records}
            form={foreshadowingForm}
            aiResults={foreshadowingAiResults}
            modelLabel={modelLabel(modelForWorkflow('extract_memory'))}
            editingRecordId={editingForeshadowingId}
            onFormChange={(field, value) => setForeshadowingForm((current) => ({ ...current, [field]: value }))}
            onSave={() => void saveForeshadowing()}
            onSelectRecord={selectForeshadowingRecord}
            onCancelEdit={cancelForeshadowingEdit}
            onExtract={() => void extractForeshadowing()}
            onApplyResult={applyForeshadowingAiResult}
            onDeleteResult={(id) => setForeshadowingAiResults((items) => items.filter((item) => item.id !== id))}
          />
        )}

        {activeTab === 'taboo' && (
          <TabooRulesWorkbench
            records={records}
            form={tabooRuleForm}
            aiResults={tabooAiResults}
            modelLabel={modelLabel(modelForWorkflow('check_taboo_rules'))}
            editingRecordId={editingTabooRuleId}
            onFormChange={(field, value) => setTabooRuleForm((current) => ({ ...current, [field]: value }))}
            onSave={() => void saveTabooRule()}
            onSelectRecord={selectTabooRuleRecord}
            onCancelEdit={cancelTabooRuleEdit}
            onCheck={() => void checkTabooRules()}
            onApplyResult={applyTabooAiResult}
            onDeleteResult={(id) => setTabooAiResults((items) => items.filter((item) => item.id !== id))}
          />
        )}

        {activeTab === 'knowledge' && (
          <KnowledgeWikiWorkbench
            records={records}
            wikiPages={wikiPages}
            form={knowledgeForm}
            editingRecordId={editingKnowledgeId}
            onFormChange={(field, value) => setKnowledgeForm((current) => ({ ...current, [field]: value }))}
            onSave={() => void saveKnowledgeDocument()}
            onSelectRecord={selectKnowledgeRecord}
            onCancelEdit={cancelKnowledgeEdit}
          />
        )}

        {activeTab !== 'chapters' && activeTab !== 'characters' && activeTab !== 'outline' && activeTab !== 'graph' && activeTab !== 'timeline' && activeTab !== 'foreshadowing' && activeTab !== 'taboo' && activeTab !== 'knowledge' && activeTab !== 'export' && activeTab !== 'wiki' && activeTab !== 'settings' && activeTab !== 'style' && (
          <section className="records-layout">
            <div className="record-form">
              <div className="panel-heading">
                <span>写入资料</span>
                <small>当前项目</small>
              </div>
              <input value={recordTitle} onChange={(event) => setRecordTitle(event.target.value)} placeholder="标题" />
              <textarea value={recordContent} onChange={(event) => setRecordContent(event.target.value)} placeholder="内容" />
              <button onClick={() => void createRecord()}>保存到当前项目</button>
            </div>
            <div className="record-list">
              {records.map((record) => (
                <article key={record.id}>
                  <h3>{record.title}</h3>
                  <p>{record.content}</p>
                  <span>{record.status}</span>
                </article>
              ))}
            </div>
          </section>
        )}

        {activeTab === 'wiki' && (
          <section className="records-layout">
            <div className="record-form">
              <div className="panel-heading">
                <span>Wiki 页面</span>
                <small>memory/wiki</small>
              </div>
              <input value={recordTitle} onChange={(event) => setRecordTitle(event.target.value)} placeholder="characters/heroine.md" />
              <textarea value={recordContent} onChange={(event) => setRecordContent(event.target.value)} placeholder="# Wiki 记忆页" />
              <button onClick={() => void createWikiPage()}>写入 llmwiki 记忆</button>
            </div>
            <div className="record-list">
              {wikiPages.map((page) => (
                <article key={page.path}>
                  <h3>{page.path}</h3>
                  <p>{page.content.slice(0, 260)}</p>
                </article>
              ))}
            </div>
          </section>
        )}

        {activeTab === 'export' && selectedProject && (
          <section className="export-panel">
            <FileText size={42} />
            <h3>导出当前项目</h3>
            <p>导出接口只读取当前项目章节，避免不同小说串稿。</p>
            <div className="action-row">
              <a href={`/api/projects/${selectedProject.id}/export/markdown`}>Markdown</a>
              <a href={`/api/projects/${selectedProject.id}/export/txt`}>TXT</a>
              <a href={`/api/projects/${selectedProject.id}/export/docx`}>DOCX</a>
              <a href={`/api/projects/${selectedProject.id}/export/pdf`}>PDF</a>
              <a href={`/api/projects/${selectedProject.id}/export/epub`}>EPUB</a>
            </div>
          </section>
        )}
      </main>
    </div>
  );
}
