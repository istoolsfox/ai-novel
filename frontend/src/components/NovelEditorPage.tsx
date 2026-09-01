import { ReactNode, SyntheticEvent, useMemo, useState } from 'react';
import {
  BookMarked,
  BookOpen,
  Brain,
  Check,
  ChevronLeft,
  ChevronRight,
  Eye,
  Feather,
  FileDown,
  GitBranch,
  History,
  Library,
  PenLine,
  Plus,
  RefreshCw,
  Save,
  Search,
  Sparkles,
  Trash2,
  Wand2,
} from 'lucide-react';
import { Chapter, ChapterVersion, Project, WorkbenchAIResult } from '../api';
import { AIResultCard } from './AIResultCard';

type GenerateChapterDraftPayload = {
  workflow?: string;
  prompt: string;
  tone: string;
  style: string;
  length: string;
  viewpoint: string;
  selectedText: string;
  emotionalIntent?: string;
  mode: 'draft' | 'continue' | 'revise';
};

type SelectionRange = {
  start: number;
  end: number;
  text: string;
  draftSnapshot: string;
};

const floatingSelectionActions = new Set([
  '润色',
  '扩写',
  '缩写',
  '改写风格',
  '生成对话',
  '检查逻辑',
  '加强冲突',
  '潜台词藏回',
  '情感加深',
  '去AI味',
]);
const toneOptions = ['悬疑', '克制', '热血', '暗黑', '轻松', '治愈', '紧张', '压抑', '浪漫', '诡秘', '燃向', '冷幽默', '悲壮', '荒诞', '温柔'];
const styleOptions = ['网文爽感', '文学化表达', '电影感', '古风权谋', '都市悬疑', '群像史诗', '赛博朋克', '新怪谈', '意识流', '轻小说', '历史正剧', '黑色幽默', '悬疑推理', '成长流', '公路片'];
const assistantActionGroups = [
  {
    label: '起草',
    description: '从空白页推进到可编辑正文',
    actions: ['一键生成本章正文', '续写当前章节', '生成下一段剧情'],
  },
  {
    label: '修改',
    description: '围绕现有段落增强表达',
    actions: ['润色选中文本', '生成人物对话', '制造剧情冲突', '优化节奏'],
  },
  {
    label: '检查',
    description: '回看逻辑、伏笔与章节质量',
    actions: ['检查逻辑漏洞', '伏笔回收建议'],
  },
  {
    label: '情感增强',
    description: '提取情感种子、潜台词和追读债务',
    actions: ['生成情感种子', '五层情感考古', '潜台词藏回', '追读力检查', '情感加深', '去AI味'],
  },
];

function chapterDisplayTitle(chapter: Chapter) {
  const cleaned = (chapter.title || '未命名章节').replace(/^第\s*\d+\s*章\s*[·：:、-]?\s*/, '').trim();
  return cleaned || '未命名章节';
}

function firstStringValue(value: unknown, keys: string[]): string {
  if (!value || typeof value !== 'object') return '';
  const record = value as Record<string, unknown>;
  for (const key of keys) {
    const candidate = record[key];
    if (typeof candidate === 'string' && candidate.trim()) return candidate;
  }
  return '';
}

function normalizeGeneratedProse(raw: string) {
  const trimmed = raw.trim();
  if (!trimmed) return raw;
  try {
    const parsed = JSON.parse(trimmed) as unknown;
    if (Array.isArray(parsed)) {
      const first = parsed[0];
      return firstStringValue(first, ['content', 'draft', 'text', 'body']) || raw;
    }
    if (parsed && typeof parsed === 'object') {
      const record = parsed as Record<string, unknown>;
      const drafts = record.drafts;
      if (Array.isArray(drafts) && drafts.length > 0) {
        return firstStringValue(drafts[0], ['content', 'draft', 'text', 'body']) || raw;
      }
      return firstStringValue(record, ['content', 'draft', 'text', 'body']) || raw;
    }
  } catch {
    // Plain prose is the preferred output for chapter writing.
  }
  return raw.replace(/\\n/g, '\n').replace(/\\"/g, '"').trim();
}

type NovelEditorPageProps = {
  project: Project | null;
  chapters: Chapter[];
  selectedChapter: Chapter | null;
  versions: ChapterVersion[];
  styleProfiles?: Array<{ id: string; title: string }>;
  selectedStyleProfileId?: string;
  draft: string;
  log: string;
  modelLabel: string;
  wikiPageCount: number;
  onCreateChapter: () => void;
  onDeleteChapter: (chapter: Chapter) => void;
  onSelectChapter: (chapter: Chapter) => void;
  onDraftChange: (draft: string) => void;
  onChapterTitleChange: (title: string) => void;
  onSaveChapter: () => void;
  onGenerateVariant: () => void;
  onGenerateChapterDraft: (payload: GenerateChapterDraftPayload) => Promise<string>;
  onStyleProfileChange?: (id: string) => void;
  onSaveAiResultAsVersion: (title: string, content: string) => Promise<void>;
  onScoreChapter: () => void;
  onFinalizeChapter: () => void;
  onSelectVersion: (versionId: string) => void;
  onOpenResource: (resource: 'characters' | 'outline' | 'knowledge') => void;
  onLog: (message: string) => void;
};

export function NovelEditorPage({
  project,
  chapters,
  selectedChapter,
  versions,
  styleProfiles = [],
  selectedStyleProfileId = '',
  draft,
  log,
  modelLabel,
  wikiPageCount,
  onCreateChapter,
  onDeleteChapter,
  onSelectChapter,
  onDraftChange,
  onChapterTitleChange,
  onSaveChapter,
  onGenerateVariant,
  onGenerateChapterDraft,
  onStyleProfileChange = () => undefined,
  onSaveAiResultAsVersion,
  onScoreChapter,
  onFinalizeChapter,
  onSelectVersion,
  onOpenResource,
  onLog,
}: NovelEditorPageProps) {
  const [leftCollapsed, setLeftCollapsed] = useState(false);
  const [rightCollapsed, setRightCollapsed] = useState(false);
  const [chapterOrder, setChapterOrder] = useState<'asc' | 'desc'>('asc');
  const [chapterSearch, setChapterSearch] = useState('');
  const [selectedRange, setSelectedRange] = useState<SelectionRange | null>(null);
  const [prompt, setPrompt] = useState('');
  const [tone, setTone] = useState('悬疑');
  const [style, setStyle] = useState('网文爽感');
  const [length, setLength] = useState('中等');
  const [viewpoint, setViewpoint] = useState('第三人称');
  const [aiResults, setAiResults] = useState<WorkbenchAIResult[]>([
    {
      id: 'local-preview',
      title: 'AI 续写建议',
      content: '她合上古籍时，窗外的雨声忽然停了。不是雨停了，而是整座城像被某种看不见的手按住了呼吸。',
      status: 'ready',
      sourceWorkflow: 'generate_chapter_draft',
    },
  ]);
  const [isGenerating, setIsGenerating] = useState(false);

  const wordCount = draft.trim().length;
  const readMinutes = Math.max(1, Math.ceil(wordCount / 500));
  const completion = selectedChapter?.status === 'final' ? 100 : Math.min(96, Math.max(12, Math.round(wordCount / 30)));
  const todayWords = Math.min(wordCount, 1260);
  const aiEditCount = versions.length;
  const selectedText = selectedRange?.text ?? '';
  const hasSelectedRange = Boolean(selectedRange && selectedRange.end > selectedRange.start);

  const visibleChapters = useMemo(() => {
    return [...chapters]
      .filter((chapter) => {
        const keyword = chapterSearch.trim();
        if (!keyword) return true;
        return `${chapter.chapter_number} ${chapter.title} ${chapter.brief}`.includes(keyword);
      })
      .sort((left, right) =>
        chapterOrder === 'asc'
          ? left.chapter_number - right.chapter_number
          : right.chapter_number - left.chapter_number
      );
  }, [chapters, chapterOrder, chapterSearch]);

  function modeForAction(action: string): GenerateChapterDraftPayload['mode'] {
    if (action === '一键生成本章正文') return 'draft';
    if (action === '润色选中文本') return 'revise';
    if (floatingSelectionActions.has(action)) return 'revise';
    return 'continue';
  }

  function workflowForAction(action: string) {
    if (action === '生成情感种子') return 'generate_emotion_seed';
    if (action === '五层情感考古') return 'emotion_archaeology';
    if (action === '潜台词藏回') return 'dialogue_subtext_excavation';
    if (action === '追读力检查') return 'analyze_reader_pull';
    if (action === '情感加深') return 'deepen_and_bury';
    if (action === '去AI味') return 'anti_ai_polish';
    const mode = modeForAction(action);
    return mode === 'revise' ? 'revise_selection' : 'generate_chapter_draft';
  }

  async function createAiResult(action: string) {
    setIsGenerating(true);
    const mode = modeForAction(action);
    const sourceWorkflow = workflowForAction(action);
    const isEmotionalWorkflow = !['generate_chapter_draft', 'revise_selection'].includes(sourceWorkflow);
    try {
      const content = await onGenerateChapterDraft({
        workflow: sourceWorkflow,
        prompt: prompt || action,
        tone,
        style,
        length,
        viewpoint,
        selectedText: selectedRange?.text.trim() ?? '',
        emotionalIntent: isEmotionalWorkflow ? action : undefined,
        mode,
      });
      const cleanContent = normalizeGeneratedProse(content);
      setAiResults((items) => [
        { id: `${Date.now()}`, title: action, content: cleanContent, status: 'ready', sourceWorkflow },
        ...items,
      ]);
    } catch (error) {
      const message =
        error instanceof Error
          ? error.message
          : '本地占位结果：请检查模型配置后重试。当前结果没有写入正式正文。';
      setAiResults((items) => [
        {
          id: `${Date.now()}`,
          title: action,
          content: message,
          status: 'error',
          sourceWorkflow,
        },
        ...items,
      ]);
      onLog(message);
    } finally {
      setIsGenerating(false);
    }
  }

  function insertResult(content: string, logMessage = 'AI 结果已插入正文。') {
    handleDraftChange(`${draft}${draft ? '\n\n' : ''}${content}`);
    onLog(logMessage);
  }

  function replaceSelection(content: string) {
    if (!selectedRange || selectedRange.end <= selectedRange.start) {
      insertResult(content);
      return;
    }
    const rangeMatchesDraft =
      selectedRange.draftSnapshot === draft &&
      selectedRange.start >= 0 &&
      selectedRange.end <= draft.length &&
      draft.slice(selectedRange.start, selectedRange.end) === selectedRange.text;
    if (!rangeMatchesDraft) {
      setSelectedRange(null);
      insertResult(content, '选区已失效，AI 结果已追加到正文。');
      return;
    }
    onDraftChange(`${draft.slice(0, selectedRange.start)}${content}${draft.slice(selectedRange.end)}`);
    setSelectedRange(null);
    onLog('已替换选中文本。');
  }

  function handleDraftChange(nextDraft: string) {
    setSelectedRange(null);
    onDraftChange(nextDraft);
  }

  function favoriteResult(id: string) {
    setAiResults((items) => items.map((item) => (item.id === id ? { ...item } : item)));
    onLog('AI 结果已收藏到灵感库。');
  }

  function deleteAiResult(id: string) {
    setAiResults((items) => items.filter((item) => item.id !== id));
    onLog('AI 结果已删除。');
  }

  return (
    <EditorLayout leftCollapsed={leftCollapsed} rightCollapsed={rightCollapsed}>
      <NovelSidebar
        collapsed={leftCollapsed}
        project={project}
        chapters={visibleChapters}
        selectedChapter={selectedChapter}
        chapterSearch={chapterSearch}
        chapterOrder={chapterOrder}
        onToggle={() => setLeftCollapsed(!leftCollapsed)}
        onSearch={setChapterSearch}
        onOrderChange={setChapterOrder}
        onSelectChapter={onSelectChapter}
        onCreateChapter={onCreateChapter}
        onDeleteChapter={onDeleteChapter}
        onOpenResource={onOpenResource}
      />

      <main className="novel-editor-main">
          <EditorHeader
            project={project}
            selectedChapter={selectedChapter}
            wordCount={wordCount}
            onTitleChange={onChapterTitleChange}
            onSave={onSaveChapter}
            onExport={onFinalizeChapter}
            onScore={onScoreChapter}
          />
        <WritingEditor
          selectedChapter={selectedChapter}
          draft={draft}
          selectedText={selectedText}
          hasSelectedRange={hasSelectedRange}
          onDraftChange={handleDraftChange}
          onTextSelection={setSelectedRange}
          onAiAction={createAiResult}
        />
        <WritingStatusBar
          wordCount={wordCount}
          readMinutes={readMinutes}
          todayWords={todayWords}
          aiEditCount={aiEditCount}
          completion={completion}
          log={log}
        />
      </main>

      <AIAssistantPanel
        collapsed={rightCollapsed}
        project={project}
        selectedChapter={selectedChapter}
        wordCount={wordCount}
        prompt={prompt}
        tone={tone}
        style={style}
        length={length}
        viewpoint={viewpoint}
        styleProfiles={styleProfiles}
        selectedStyleProfileId={selectedStyleProfileId}
        isGenerating={isGenerating}
        aiResults={aiResults}
        hasSelectedRange={hasSelectedRange}
        versions={versions}
        modelLabel={modelLabel}
        wikiPageCount={wikiPageCount}
        onToggle={() => setRightCollapsed(!rightCollapsed)}
        onPromptChange={setPrompt}
        onToneChange={setTone}
        onStyleChange={setStyle}
        onStyleProfileChange={onStyleProfileChange}
        onLengthChange={setLength}
        onViewpointChange={setViewpoint}
        onAction={createAiResult}
        onGenerateVariant={onGenerateVariant}
        onScoreChapter={onScoreChapter}
        onInsert={insertResult}
        onReplace={replaceSelection}
        onRegenerate={createAiResult}
        onSaveVersion={onSaveAiResultAsVersion}
        onFavorite={favoriteResult}
        onDeleteResult={deleteAiResult}
        onSelectVersion={onSelectVersion}
      />
    </EditorLayout>
  );
}

function EditorLayout({
  children,
  leftCollapsed,
  rightCollapsed,
}: {
  children: ReactNode;
  leftCollapsed: boolean;
  rightCollapsed: boolean;
}) {
  const className = [
    'novel-editor-page',
    leftCollapsed ? 'left-collapsed' : '',
    rightCollapsed ? 'right-collapsed' : '',
  ].join(' ');
  return <section className={className}>{children}</section>;
}

function NovelSidebar({
  collapsed,
  project,
  chapters,
  selectedChapter,
  chapterSearch,
  chapterOrder,
  onToggle,
  onSearch,
  onOrderChange,
  onSelectChapter,
  onCreateChapter,
  onDeleteChapter,
  onOpenResource,
}: {
  collapsed: boolean;
  project: Project | null;
  chapters: Chapter[];
  selectedChapter: Chapter | null;
  chapterSearch: string;
  chapterOrder: 'asc' | 'desc';
  onToggle: () => void;
  onSearch: (value: string) => void;
  onOrderChange: (value: 'asc' | 'desc') => void;
  onSelectChapter: (chapter: Chapter) => void;
  onCreateChapter: () => void;
  onDeleteChapter: (chapter: Chapter) => void;
  onOpenResource: (resource: 'characters' | 'outline' | 'knowledge') => void;
}) {
  return (
    <aside className="novel-sidebar">
      <button className="rail-toggle" onClick={onToggle} title={collapsed ? '展开左侧栏' : '折叠左侧栏'}>
        {collapsed ? <ChevronRight size={16} /> : <ChevronLeft size={16} />}
      </button>
      {!collapsed && (
        <>
          <div className="novel-sidebar-head">
            <span>Novel Editor</span>
            <h3>{project?.title ?? '未选择小说'}</h3>
            <small>连载中 / 本地优先 / 私有工作室</small>
          </div>
          <div className="novel-search">
            <Search size={15} />
            <input
              aria-label="章节搜索"
              value={chapterSearch}
              onChange={(event) => onSearch(event.target.value)}
              placeholder="搜索章节、分卷、关键词"
            />
          </div>
          <div className="chapter-select-row">
            <label>
              章节选择
              <select
                aria-label="章节选择"
                value={selectedChapter?.id ?? ''}
                onChange={(event) => {
                  const next = chapters.find((chapter) => chapter.id === event.target.value);
                  if (next) onSelectChapter(next);
                }}
              >
                <option value="">选择章节</option>
                {chapters.map((chapter) => (
                  <option key={chapter.id} value={chapter.id}>
                    第 {chapter.chapter_number} 章 · {chapterDisplayTitle(chapter)}
                  </option>
                ))}
              </select>
            </label>
            <label>
              章节顺序
              <select
                aria-label="章节顺序"
                value={chapterOrder}
                onChange={(event) => onOrderChange(event.target.value as 'asc' | 'desc')}
              >
                <option value="asc">正序</option>
                <option value="desc">倒序</option>
              </select>
            </label>
          </div>
          <ChapterTree
            chapters={chapters}
            selectedChapter={selectedChapter}
            onSelectChapter={onSelectChapter}
            onCreateChapter={onCreateChapter}
            onDeleteChapter={onDeleteChapter}
          />
          <div className="novel-resource-links">
            <button onClick={() => onOpenResource('characters')}><BookOpen size={15} />角色</button>
            <button onClick={() => onOpenResource('knowledge')}><GitBranch size={15} />世界观</button>
            <button onClick={() => onOpenResource('outline')}><BookMarked size={15} />大纲</button>
            <button onClick={() => onOpenResource('knowledge')}><Library size={15} />灵感库</button>
          </div>
          <div className="recent-edits">
            <span>最近编辑</span>
            <p>{selectedChapter ? `刚刚更新：第 ${selectedChapter.chapter_number} 章` : '还没有编辑记录'}</p>
          </div>
        </>
      )}
    </aside>
  );
}

function ChapterTree({
  chapters,
  selectedChapter,
  onSelectChapter,
  onCreateChapter,
  onDeleteChapter,
}: {
  chapters: Chapter[];
  selectedChapter: Chapter | null;
  onSelectChapter: (chapter: Chapter) => void;
  onCreateChapter: () => void;
  onDeleteChapter: (chapter: Chapter) => void;
}) {
  return (
    <div className="chapter-tree">
      <div className="volume-header">
        <span>第一卷 · 记忆古籍</span>
        <button onClick={onCreateChapter}><Plus size={14} />新增章节</button>
      </div>
      <div className="chapter-tree-list">
        {chapters.map((chapter) => (
          <ChapterItem
            chapter={chapter}
            selected={chapter.id === selectedChapter?.id}
            key={chapter.id}
            onSelect={() => onSelectChapter(chapter)}
            onDelete={() => {
              if (window.confirm(`确定删除第 ${chapter.chapter_number} 章《${chapter.title || '未命名章节'}》吗？此操作会删除本章版本。`)) {
                onDeleteChapter(chapter);
              }
            }}
          />
        ))}
        {chapters.length === 0 && <p className="empty-state">暂无章节，创建后会自动进入编辑。</p>}
      </div>
    </div>
  );
}

function ChapterItem({
  chapter,
  selected,
  onSelect,
  onDelete,
}: {
  chapter: Chapter;
  selected: boolean;
  onSelect: () => void;
  onDelete: () => void;
}) {
  const wordCount = chapter.draft?.length ?? 0;
  const status = chapter.status === 'final' ? '已完成' : wordCount > 800 ? '待修改' : '草稿';
  return (
    <article className={selected ? 'chapter-item active' : 'chapter-item'}>
      <button className="chapter-item-main" onClick={onSelect}>
        <span>第 {chapter.chapter_number} 章</span>
        <strong>{chapterDisplayTitle(chapter)}</strong>
        <small>{wordCount} 字 · {status}</small>
      </button>
      <button className="chapter-delete-button" aria-label={`删除章节 第 ${chapter.chapter_number} 章`} onClick={onDelete}>
        <Trash2 size={14} />
      </button>
    </article>
  );
}

function EditorHeader({
  project,
  selectedChapter,
  wordCount,
  onTitleChange,
  onSave,
  onExport,
  onScore,
}: {
  project: Project | null;
  selectedChapter: Chapter | null;
  wordCount: number;
  onTitleChange: (title: string) => void;
  onSave: () => void;
  onExport: () => void;
  onScore: () => void;
}) {
  return (
    <header className="editor-header">
      <div>
        <span className="eyebrow">沉浸式小说创作空间</span>
        <input
          className="editor-title-input"
          value={selectedChapter?.title ?? ''}
          onChange={(event) => onTitleChange(event.target.value)}
          placeholder="请选择章节或输入章节标题"
          disabled={!selectedChapter}
        />
        <p>{project?.title ?? '未选择作品'} · 已自动保存 · {wordCount} 字</p>
      </div>
      <div className="editor-header-actions">
        <button className="toolbar-button primary-toolbar" onClick={onSave} disabled={!selectedChapter} title="保存正文 (Cmd+S)">
          <Save size={15} />
          <span>保存</span>
        </button>
        <button className="toolbar-button" onClick={onExport} disabled={!selectedChapter} title="发布 / 导出">
          <FileDown size={16} />
          <span className="toolbar-tip">导出</span>
        </button>
        <button className="toolbar-button" onClick={onScore} disabled={!selectedChapter} title="检查逻辑与评分">
          <Check size={16} />
          <span className="toolbar-tip">评分</span>
        </button>
      </div>
    </header>
  );
}

function WritingEditor({
  selectedChapter,
  draft,
  selectedText,
  hasSelectedRange,
  onDraftChange,
  onTextSelection,
  onAiAction,
}: {
  selectedChapter: Chapter | null;
  draft: string;
  selectedText: string;
  hasSelectedRange: boolean;
  onDraftChange: (draft: string) => void;
  onTextSelection: (range: SelectionRange | null) => void;
  onAiAction: (action: string) => void;
}) {
  function captureSelection(event: SyntheticEvent<HTMLTextAreaElement>) {
    const target = event.currentTarget;
    const start = target.selectionStart;
    const end = target.selectionEnd;
    const text = target.value.slice(start, end);
    onTextSelection(end > start ? { start, end, text, draftSnapshot: target.value } : null);
  }

  return (
    <div className="writing-editor-wrap">
      <textarea
        className="writing-editor"
        value={draft}
        onChange={(event) => onDraftChange(event.target.value)}
        onMouseUp={captureSelection}
        onKeyUp={captureSelection}
        placeholder={selectedChapter ? '在这里写下这一章...' : '请先创建或选择章节'}
      />
      <FloatingAIToolbar visible={hasSelectedRange} selectedText={selectedText} onAction={onAiAction} />
    </div>
  );
}

function FloatingAIToolbar({
  visible,
  selectedText,
  onAction,
}: {
  visible: boolean;
  selectedText: string;
  onAction: (action: string) => void;
}) {
  if (!visible) return null;
  return (
    <div className="floating-ai-toolbar" aria-label={`AI 操作：${selectedText}`}>
      {['润色', '扩写', '缩写', '改写风格', '生成对话', '检查逻辑', '加强冲突'].map((action) => (
        <button key={action} onClick={() => onAction(action)}>{action}</button>
      ))}
    </div>
  );
}

function WritingStatusBar({
  wordCount,
  readMinutes,
  todayWords,
  aiEditCount,
  completion,
  log,
}: {
  wordCount: number;
  readMinutes: number;
  todayWords: number;
  aiEditCount: number;
  completion: number;
  log: string;
}) {
  return (
    <footer className="writing-status-bar">
      <span>本章 {wordCount} 字</span>
      <span>预计阅读 {readMinutes} 分钟</span>
      <span>今日新增 {todayWords} 字</span>
      <span>AI 修改 {aiEditCount} 次</span>
      <span>完成度 {completion}%</span>
      <strong>{log}</strong>
    </footer>
  );
}

function AIAssistantPanel({
  collapsed,
  project,
  selectedChapter,
  wordCount,
  prompt,
  tone,
  style,
  length,
  viewpoint,
  styleProfiles,
  selectedStyleProfileId,
  isGenerating,
  aiResults,
  hasSelectedRange,
  versions,
  modelLabel,
  wikiPageCount,
  onToggle,
  onPromptChange,
  onToneChange,
  onStyleChange,
  onStyleProfileChange,
  onLengthChange,
  onViewpointChange,
  onAction,
  onGenerateVariant,
  onScoreChapter,
  onInsert,
  onReplace,
  onRegenerate,
  onSaveVersion,
  onFavorite,
  onDeleteResult,
  onSelectVersion,
}: {
  collapsed: boolean;
  project: Project | null;
  selectedChapter: Chapter | null;
  wordCount: number;
  prompt: string;
  tone: string;
  style: string;
  length: string;
  viewpoint: string;
  styleProfiles: Array<{ id: string; title: string }>;
  selectedStyleProfileId: string;
  isGenerating: boolean;
  aiResults: WorkbenchAIResult[];
  hasSelectedRange: boolean;
  versions: ChapterVersion[];
  modelLabel: string;
  wikiPageCount: number;
  onToggle: () => void;
  onPromptChange: (value: string) => void;
  onToneChange: (value: string) => void;
  onStyleChange: (value: string) => void;
  onStyleProfileChange: (id: string) => void;
  onLengthChange: (value: string) => void;
  onViewpointChange: (value: string) => void;
  onAction: (action: string) => void;
  onGenerateVariant: () => void;
  onScoreChapter: () => void;
  onInsert: (content: string) => void;
  onReplace: (content: string) => void;
  onRegenerate: (action: string) => void;
  onSaveVersion: (title: string, content: string) => Promise<void>;
  onFavorite: (id: string) => void;
  onDeleteResult: (id: string) => void;
  onSelectVersion: (versionId: string) => void;
}) {
  return (
    <aside className="ai-assistant-panel">
      <button className="rail-toggle right" onClick={onToggle} title={collapsed ? '展开 AI 助手' : '折叠 AI 助手'}>
        {collapsed ? <ChevronLeft size={16} /> : <ChevronRight size={16} />}
      </button>
      {!collapsed && (
        <>
          <div className="ai-panel-head">
            <span>AI Copilot</span>
            <h3>AI 创作副驾驶</h3>
            <small>{modelLabel}</small>
          </div>
          <ContextPropertiesPanel project={project} selectedChapter={selectedChapter} wordCount={wordCount} versionCount={versions.length} />
          <div className="ai-action-groups">
            {assistantActionGroups.map((group) => (
              <section className="ai-action-group" key={group.label}>
                <div className="ai-action-group-head">
                  <strong>{group.label}</strong>
                  <span>{group.description}</span>
                </div>
                <div className="ai-action-grid">
                  {group.actions.map((action) => (
                    <AIActionCard
                      key={action}
                      title={action}
                      disabled={isGenerating}
                      onClick={() => onAction(action)}
                    />
                  ))}
                </div>
              </section>
            ))}
          </div>
          <PromptInputBox
            prompt={prompt}
            tone={tone}
            style={style}
            length={length}
            viewpoint={viewpoint}
            styleProfiles={styleProfiles}
            selectedStyleProfileId={selectedStyleProfileId}
            loading={isGenerating}
            onPromptChange={onPromptChange}
            onToneChange={onToneChange}
            onStyleChange={onStyleChange}
            onStyleProfileChange={onStyleProfileChange}
            onLengthChange={onLengthChange}
            onViewpointChange={onViewpointChange}
            onSubmit={() => onAction('自定义正文结果')}
          />
          <div className="ai-result-list">
            {aiResults.map((result) => (
              <AIResultCard
                key={result.id}
                result={result}
                canInsert
                canReplace={hasSelectedRange}
                canSaveVersion
                canFavorite
                loading={isGenerating}
                onInsert={() => onInsert(result.content)}
                onReplace={() => onReplace(result.content)}
                onRegenerate={() => onRegenerate(result.title)}
                onSaveVersion={() => void onSaveVersion(result.title, result.content)}
                onFavorite={() => onFavorite(result.id)}
                onDelete={() => onDeleteResult(result.id)}
              />
            ))}
            {versions.slice(0, 2).map((version) => (
              <article className="ai-result-card" key={version.id}>
                <strong>{version.label}</strong>
                <p>{version.content.slice(0, 120)}</p>
                <button onClick={() => onSelectVersion(version.id)}>设为当前正文</button>
              </article>
            ))}
          </div>
          <ContextReferencePanel wikiPageCount={wikiPageCount} />
          <button className="secondary-action" onClick={onGenerateVariant}>
            <Feather size={15} />
            生成候选版本
          </button>
          <button className="secondary-action" onClick={onScoreChapter}>
            <Brain size={15} />
            检查逻辑与评分
          </button>
        </>
      )}
    </aside>
  );
}

function AIActionCard({ title, disabled, onClick }: { title: string; disabled: boolean; onClick: () => void }) {
  return (
    <button className="ai-action-card" disabled={disabled} onClick={onClick}>
      <Wand2 size={15} />
      {title}
    </button>
  );
}

function PromptInputBox({
  prompt,
  tone,
  style,
  length,
  viewpoint,
  styleProfiles,
  selectedStyleProfileId,
  loading,
  onPromptChange,
  onToneChange,
  onStyleChange,
  onStyleProfileChange,
  onLengthChange,
  onViewpointChange,
  onSubmit,
}: {
  prompt: string;
  tone: string;
  style: string;
  length: string;
  viewpoint: string;
  styleProfiles: Array<{ id: string; title: string }>;
  selectedStyleProfileId: string;
  loading: boolean;
  onPromptChange: (value: string) => void;
  onToneChange: (value: string) => void;
  onStyleChange: (value: string) => void;
  onStyleProfileChange: (id: string) => void;
  onLengthChange: (value: string) => void;
  onViewpointChange: (value: string) => void;
  onSubmit: () => void;
}) {
  return (
    <div className="prompt-box">
      <textarea
        value={prompt}
        onChange={(event) => onPromptChange(event.target.value)}
        placeholder="帮我续写这一章，但保持悬疑感，并加入主角的心理变化"
      />
      <div className="prompt-controls">
        <select aria-label="语气" value={tone} onChange={(event) => onToneChange(event.target.value)}>
          {toneOptions.map((option) => (
            <option key={option}>{option}</option>
          ))}
        </select>
        <select aria-label="表达风格" value={style} onChange={(event) => onStyleChange(event.target.value)}>
          {styleOptions.map((option) => (
            <option key={option}>{option}</option>
          ))}
        </select>
        <select
          aria-label="写作风格档案"
          value={selectedStyleProfileId}
          onChange={(event) => onStyleProfileChange(event.target.value)}
        >
          <option value="">不指定风格档案</option>
          {styleProfiles.map((profile) => (
            <option key={profile.id} value={profile.id}>
              {profile.title}
            </option>
          ))}
        </select>
        <select value={length} onChange={(event) => onLengthChange(event.target.value)}>
          <option>短</option>
          <option>中等</option>
          <option>长</option>
        </select>
        <select value={viewpoint} onChange={(event) => onViewpointChange(event.target.value)}>
          <option>第三人称</option>
          <option>第一人称</option>
          <option>多视角</option>
        </select>
      </div>
      <button className="primary-action" disabled={loading} onClick={onSubmit}>
        {loading ? <RefreshCw size={15} /> : <Sparkles size={15} />}
        {loading ? '生成中' : '生成正文结果'}
      </button>
    </div>
  );
}

function ContextReferencePanel({ wikiPageCount }: { wikiPageCount: number }) {
  const references = ['当前章节', '角色设定', '世界观规则', '剧情大纲', '最近三章摘要', `llmwiki 记忆 · ${wikiPageCount} 页`];
  return (
    <div className="context-reference-panel">
      <div>
        <Eye size={15} />
        <strong>上下文引用</strong>
      </div>
      {references.map((item) => (
        <span key={item}>{item}</span>
      ))}
    </div>
  );
}

function ContextPropertiesPanel({
  project,
  selectedChapter,
  wordCount,
  versionCount,
}: {
  project: Project | null;
  selectedChapter: Chapter | null;
  wordCount: number;
  versionCount: number;
}) {
  const rows: Array<{ label: string; value: string }> = [
    { label: '状态', value: selectedChapter?.status === 'final' ? '已完成' : selectedChapter ? '草稿' : '—' },
    { label: '字数', value: `${wordCount}` },
    { label: '章节', value: selectedChapter ? `第 ${selectedChapter.chapter_number} 章` : '—' },
    { label: '版本', value: `${versionCount}` },
    { label: '作品', value: project?.title ?? '—' },
  ];
  return (
    <div className="context-properties">
      <div className="context-properties-head">
        <span>属性</span>
        <small>{project ? '当前作品' : '未选择作品'}</small>
      </div>
      <dl>
        {rows.map((row) => (
          <div key={row.label}>
            <dt>{row.label}</dt>
            <dd>{row.value}</dd>
          </div>
        ))}
      </dl>
    </div>
  );
}
