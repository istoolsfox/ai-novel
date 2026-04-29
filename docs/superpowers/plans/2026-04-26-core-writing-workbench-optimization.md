# Core Writing Workbench Optimization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the five highest-value writing modules into dedicated novel-writing workflows: chapter generation, character cards, outline board, editable relationship graph, and style-aware generation.

**Architecture:** Keep the existing `App.tsx` orchestration and `api.ts` client. Add focused React components under `frontend/src/components/`, introduce shared front-end-only types and AI result UI helpers, and store structured module data in existing generic record APIs through `payload` while preserving `title/category/content/status`.

**Tech Stack:** React 19, TypeScript, Vite, Vitest, Testing Library, lucide-react, @xyflow/react, FastAPI-compatible existing API.

---

## File Structure

- Create: `frontend/src/components/AIResultCard.tsx`
  - Shared fixed-height AI result card used by chapters, characters, outline, graph, and style flows.
- Create: `frontend/src/components/CharacterWorkbench.tsx`
  - Dedicated character list, character card editor, and AI assist panel.
- Create: `frontend/src/components/OutlineWorkbench.tsx`
  - Dedicated volume/chapter outline tree, structured outline editor, and AI outline candidate panel.
- Create: `frontend/src/components/RelationshipGraphWorkbench.tsx`
  - Dedicated graph page with add character, add relationship, edit node, edit edge, and AI extraction controls.
- Modify: `frontend/src/components/NovelEditorPage.tsx`
  - Replace local AI result card with shared AI result card, wire one-click draft generation, continuation, selected-text revision, insertion, replacement, and save-as-version actions.
- Modify: `frontend/src/components/StyleLearningPanel.tsx`
  - Add selected style profile handoff readiness: saved profile cards expose usable style metadata labels.
- Modify: `frontend/src/App.tsx`
  - Add state and handlers for character, outline, relationship records and AI workflows; route `characters`, `outline`, and `graph` tabs to dedicated components.
- Modify: `frontend/src/api.ts`
  - Add front-end types for structured character, outline, relationship, and AI result card data. Keep endpoints using existing generic record and AI methods.
- Modify: `frontend/src/styles.css`
  - Add fixed result-card scroll styles and dedicated workbench layouts.
- Modify: `frontend/src/App.test.tsx`
  - Add tests for dedicated workbenches and AI result controls.

## Shared Data Shapes

Use these TypeScript shapes in `frontend/src/api.ts`.

```ts
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

export type OutlinePayload = {
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

export type RelationshipPayload = {
  source_character: string;
  target_character: string;
  relationship_type: string;
  strength: number;
  conflict: string;
  change_history: string;
  related_chapters: string;
};

export type WorkbenchAIResult = {
  id: string;
  title: string;
  content: string;
  status?: 'ready' | 'loading' | 'error';
  error?: string;
  sourceWorkflow?: string;
};
```

## Task 1: Shared AI Result Card And Fixed Scroll Contract

**Files:**
- Create: `frontend/src/components/AIResultCard.tsx`
- Modify: `frontend/src/styles.css`
- Test: `frontend/src/App.test.tsx`

- [ ] **Step 1: Add failing test for fixed AI result UI**

Add this test to `frontend/src/App.test.tsx`.

```ts
test('renders fixed AI result actions in the chapter editor', () => {
  render(<App />);
  expect(screen.getByText('AI 创作副驾驶')).toBeInTheDocument();
  expect(screen.getByText('插入正文')).toBeInTheDocument();
  expect(screen.getByText('替换选中内容')).toBeInTheDocument();
  expect(screen.getByText('保存为版本')).toBeInTheDocument();
  expect(screen.getByText('收藏到灵感库')).toBeInTheDocument();
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend; npm test -- App.test.tsx`

Expected: FAIL because `保存为版本` is not rendered by the current chapter AI result card.

- [ ] **Step 3: Create shared result component**

Create `frontend/src/components/AIResultCard.tsx` with this component.

```tsx
import { Copy, RefreshCw, Save, Sparkles } from 'lucide-react';
import { WorkbenchAIResult } from '../api';

type AIResultCardProps = {
  result: WorkbenchAIResult;
  canInsert?: boolean;
  canReplace?: boolean;
  canApply?: boolean;
  canSaveVersion?: boolean;
  canFavorite?: boolean;
  loading?: boolean;
  onInsert?: () => void;
  onReplace?: () => void;
  onApply?: () => void;
  onSaveVersion?: () => void;
  onFavorite?: () => void;
  onRegenerate?: () => void;
};

export function AIResultCard({
  result,
  canInsert = false,
  canReplace = false,
  canApply = false,
  canSaveVersion = false,
  canFavorite = false,
  loading = false,
  onInsert,
  onReplace,
  onApply,
  onSaveVersion,
  onFavorite,
  onRegenerate,
}: AIResultCardProps) {
  return (
    <article className={`ai-result-card fixed-result-card ${result.status === 'error' ? 'error' : ''}`}>
      <header>
        <span><Sparkles size={14} /> AI 结果</span>
        <strong>{result.title}</strong>
      </header>
      {result.error && <p className="ai-error-text">远程模型调用失败，已回退到本地占位结果：{result.error}</p>}
      <div className="ai-result-scroll" aria-label={`${result.title} 结果内容`}>
        {loading ? '生成中...' : result.content}
      </div>
      <div className="compact-actions">
        {canInsert && <button onClick={onInsert}>插入正文</button>}
        {canReplace && <button onClick={onReplace}>替换选中内容</button>}
        {canApply && <button onClick={onApply}>应用到当前表单</button>}
        {canSaveVersion && <button onClick={onSaveVersion}><Save size={14} />保存为版本</button>}
        {canFavorite && <button onClick={onFavorite}>收藏到灵感库</button>}
        <button onClick={() => navigator.clipboard?.writeText(result.content)}><Copy size={14} />复制</button>
        <button onClick={onRegenerate}><RefreshCw size={14} />重新生成</button>
      </div>
    </article>
  );
}
```

- [ ] **Step 4: Add fixed result styles**

Add these rules to `frontend/src/styles.css`.

```css
.fixed-result-card {
  max-height: 320px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.fixed-result-card header {
  display: grid;
  gap: 0.35rem;
  flex: 0 0 auto;
}

.fixed-result-card header span {
  color: var(--muted);
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  font-size: 0.76rem;
}

.ai-result-scroll {
  min-height: 92px;
  max-height: 178px;
  overflow-y: auto;
  white-space: pre-wrap;
  line-height: 1.75;
  padding: 0.85rem;
  border: 1px solid var(--line);
  border-radius: 16px;
  background: rgba(7, 12, 24, 0.56);
}

.ai-error-text {
  color: #f3b6a4;
  border: 1px solid rgba(248, 113, 113, 0.28);
  background: rgba(127, 29, 29, 0.18);
  border-radius: 14px;
  padding: 0.65rem 0.75rem;
}
```

- [ ] **Step 5: Add types**

Add `WorkbenchAIResult` from the shared data shapes section to `frontend/src/api.ts`.

- [ ] **Step 6: Run test to verify it passes after Task 2 wires it**

Run after Task 2 implementation: `cd frontend; npm test -- App.test.tsx`

Expected: PASS.

- [ ] **Step 7: Commit**

Run after the test passes:

```bash
git add frontend/src/components/AIResultCard.tsx frontend/src/styles.css frontend/src/api.ts frontend/src/App.test.tsx
git commit -m "feat: add shared AI result card"
```

## Task 2: Chapter Editor Real AI Generation Flow

**Files:**
- Modify: `frontend/src/components/NovelEditorPage.tsx`
- Modify: `frontend/src/App.tsx`
- Test: `frontend/src/App.test.tsx`

- [ ] **Step 1: Add failing test for one-click generation**

Add this test to `frontend/src/App.test.tsx`.

```ts
test('chapter editor exposes real generation and version actions', () => {
  render(<App />);
  expect(screen.getByText('一键生成本章正文')).toBeInTheDocument();
  expect(screen.getByText('续写当前章节')).toBeInTheDocument();
  expect(screen.getByText('保存为版本')).toBeInTheDocument();
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend; npm test -- App.test.tsx`

Expected: FAIL because `一键生成本章正文` is not rendered.

- [ ] **Step 3: Extend `NovelEditorPageProps`**

In `frontend/src/components/NovelEditorPage.tsx`, add these props.

```ts
  onGenerateChapterDraft: (payload: {
    prompt: string;
    tone: string;
    style: string;
    length: string;
    viewpoint: string;
    selectedText: string;
    mode: 'draft' | 'continue' | 'revise';
  }) => Promise<string>;
  onSaveAiResultAsVersion: (title: string, content: string) => Promise<void>;
```

- [ ] **Step 4: Replace local AI result type**

Import `WorkbenchAIResult` and shared card.

```ts
import { Chapter, ChapterVersion, Project, WorkbenchAIResult } from '../api';
import { AIResultCard } from './AIResultCard';
```

Change local state to:

```ts
const [aiResults, setAiResults] = useState<WorkbenchAIResult[]>([
  {
    id: 'local-preview',
    title: 'AI 续写建议',
    content: '她合上古籍时，窗外的雨声忽然停了。不是雨停了，而是整座城像被某种看不见的手按住了呼吸。',
    status: 'ready',
  },
]);
```

- [ ] **Step 5: Replace local fake generation with API-backed generation**

Replace `createAiResult` with:

```ts
async function createAiResult(action: string, mode: 'draft' | 'continue' | 'revise' = 'continue') {
  setIsGenerating(true);
  try {
    const content = await onGenerateChapterDraft({
      prompt: prompt || action,
      tone,
      style,
      length,
      viewpoint,
      selectedText,
      mode,
    });
    setAiResults((items) => [
      { id: `${Date.now()}`, title: action, content, status: 'ready', sourceWorkflow: mode === 'revise' ? 'revise_selection' : 'generate_chapter_draft' },
      ...items,
    ]);
  } catch (error) {
    setAiResults((items) => [
      {
        id: `${Date.now()}`,
        title: action,
        content: '本地占位结果：请检查模型配置后重试。当前结果没有写入正式正文。',
        status: 'error',
        error: error instanceof Error ? error.message : '未知错误',
      },
      ...items,
    ]);
  } finally {
    setIsGenerating(false);
  }
}
```

- [ ] **Step 6: Update AI action labels**

In `AIAssistantPanel`, set actions to:

```ts
const actions = ['一键生成本章正文', '续写当前章节', '润色选中文本', '生成下一段剧情', '生成人物对话', '制造剧情冲突', '优化节奏', '检查逻辑漏洞', '伏笔回收建议'];
```

Use this click mapping:

```tsx
onClick={() => {
  if (action === '一键生成本章正文') void onAction(action, 'draft');
  else if (action === '润色选中文本') void onAction(action, 'revise');
  else if (action === '续写当前章节') void onAction(action, 'continue');
  else void onAction(action, 'continue');
}}
```

Update `onAction` prop type to accept the `mode` argument.

- [ ] **Step 7: Render shared result card with save version**

Replace the local `AIResultCard` usage with:

```tsx
<AIResultCard
  key={result.id}
  result={result}
  canInsert
  canReplace={Boolean(selectedText)}
  canSaveVersion
  canFavorite
  loading={isGenerating && result.status === 'loading'}
  onInsert={() => onInsert(result.content)}
  onReplace={() => onReplace(result.content)}
  onSaveVersion={() => void onSaveAiResultAsVersion(result.title, result.content)}
  onFavorite={() => onFavorite(result.id)}
  onRegenerate={() => void onAction(result.title, result.sourceWorkflow === 'revise_selection' ? 'revise' : 'continue') }
/>
```

Remove the local `AIResultCard` function from `NovelEditorPage.tsx`.

- [ ] **Step 8: Add App handlers**

In `frontend/src/App.tsx`, add:

```ts
async function generateChapterDraftFromAI(payload: {
  prompt: string;
  tone: string;
  style: string;
  length: string;
  viewpoint: string;
  selectedText: string;
  mode: 'draft' | 'continue' | 'revise';
}) {
  if (!selectedProject || !selectedChapter) return '请先选择项目和章节。';
  const workflow = payload.mode === 'revise' ? 'revise_selection' : 'generate_chapter_draft';
  const result = await api.runAi(selectedProject.id, workflow, {
    chapter_id: selectedChapter.id,
    chapter_title: selectedChapter.title,
    current_draft: draft,
    selected_text: payload.selectedText,
    prompt: payload.prompt,
    tone: payload.tone,
    style: payload.style,
    length: payload.length,
    viewpoint: payload.viewpoint,
    mode: payload.mode,
    style_profiles: records.filter((record) => record.category === 'style'),
  });
  setLog(formatAiLog(result));
  return result.text;
}

async function saveAiResultAsVersion(title: string, content: string) {
  if (!selectedProject || !selectedChapter) return;
  await api.createVersion(selectedProject.id, selectedChapter.id, title, content);
  await loadVersions(selectedProject.id, selectedChapter.id);
  setLog('AI 结果已保存为候选版本。');
}
```

Pass both handlers into `NovelEditorPage`.

- [ ] **Step 9: Run tests and build**

Run:

```bash
cd frontend
npm test -- App.test.tsx
npm run build
```

Expected: tests PASS and build succeeds.

- [ ] **Step 10: Commit**

```bash
git add frontend/src/components/NovelEditorPage.tsx frontend/src/App.tsx frontend/src/App.test.tsx
git commit -m "feat: wire chapter AI generation flow"
```

## Task 3: Character Workbench

**Files:**
- Create: `frontend/src/components/CharacterWorkbench.tsx`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/api.ts`
- Modify: `frontend/src/styles.css`
- Test: `frontend/src/App.test.tsx`

- [ ] **Step 1: Add failing test**

Add this test to `frontend/src/App.test.tsx`.

```ts
test('renders dedicated character workbench', () => {
  render(<App />);
  fireEvent.click(screen.getByRole('button', { name: /故事圣经/ }));
  expect(screen.getByText('角色工作台')).toBeInTheDocument();
  expect(screen.getByLabelText('姓名')).toBeInTheDocument();
  expect(screen.getByLabelText('欲望目标')).toBeInTheDocument();
  expect(screen.getByText('AI 生成新角色')).toBeInTheDocument();
  expect(screen.getByText('AI 补全角色')).toBeInTheDocument();
  expect(screen.getByText('生成角色对白')).toBeInTheDocument();
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend; npm test -- App.test.tsx`

Expected: FAIL because the generic record form is still used for `故事圣经`.

- [ ] **Step 3: Add character type to `api.ts`**

Add `CharacterProfilePayload` from the shared data shapes section to `frontend/src/api.ts`.

- [ ] **Step 4: Create `CharacterWorkbench.tsx`**

Create a component with this public API.

```tsx
import { Sparkles, UserPlus } from 'lucide-react';
import { CharacterProfilePayload, GenericRecord, WorkbenchAIResult } from '../api';
import { AIResultCard } from './AIResultCard';

type CharacterWorkbenchProps = {
  records: GenericRecord[];
  form: CharacterProfilePayload;
  aiResults: WorkbenchAIResult[];
  modelLabel: string;
  onFormChange: (form: CharacterProfilePayload) => void;
  onSave: () => void;
  onGenerate: (mode: 'new' | 'complete' | 'dialogue' | 'consistency') => void;
  onApplyResult: (content: string) => void;
};

const fields: Array<{ key: keyof CharacterProfilePayload; label: string; multiline?: boolean }> = [
  { key: 'name', label: '姓名' },
  { key: 'role', label: '身份' },
  { key: 'faction', label: '阵营' },
  { key: 'appearance', label: '年龄 / 外貌', multiline: true },
  { key: 'traits', label: '性格关键词' },
  { key: 'desire', label: '欲望目标', multiline: true },
  { key: 'fear', label: '恐惧 / 弱点', multiline: true },
  { key: 'mainline_relation', label: '与主线关系', multiline: true },
  { key: 'arc', label: '人物弧光', multiline: true },
  { key: 'voice', label: '口癖 / 说话方式', multiline: true },
  { key: 'related_chapters', label: '相关章节' },
  { key: 'notes', label: '备注', multiline: true },
];

export function CharacterWorkbench({
  records,
  form,
  aiResults,
  modelLabel,
  onFormChange,
  onSave,
  onGenerate,
  onApplyResult,
}: CharacterWorkbenchProps) {
  return (
    <section className="special-workbench character-workbench">
      <aside className="workbench-side-list">
        <div className="workbench-panel-head">
          <span>Story Bible</span>
          <h3>角色工作台</h3>
          <small>{records.length} 个角色档案</small>
        </div>
        <button className="primary-action" onClick={() => onGenerate('new')}><UserPlus size={15} />AI 生成新角色</button>
        <div className="entity-list">
          {records.map((record) => <button key={record.id}>{record.title}</button>)}
          {records.length === 0 && <p className="empty-state">还没有角色，先生成或手动创建一个角色。</p>}
        </div>
      </aside>
      <main className="structured-editor-panel">
        <div className="workbench-panel-head">
          <span>Character Card</span>
          <h3>可编辑角色卡</h3>
          <small>{modelLabel}</small>
        </div>
        <div className="structured-grid">
          {fields.map((field) => (
            <label key={field.key}>
              {field.label}
              {field.multiline ? (
                <textarea aria-label={field.label} value={form[field.key]} onChange={(event) => onFormChange({ ...form, [field.key]: event.target.value })} />
              ) : (
                <input aria-label={field.label} value={form[field.key]} onChange={(event) => onFormChange({ ...form, [field.key]: event.target.value })} />
              )}
            </label>
          ))}
        </div>
        <button className="primary-action" onClick={onSave}>保存角色卡</button>
      </main>
      <aside className="workbench-ai-panel">
        <div className="workbench-panel-head">
          <span>AI Character Lab</span>
          <h3>角色生成与一致性</h3>
        </div>
        <div className="ai-action-grid compact">
          <button onClick={() => onGenerate('complete')}><Sparkles size={15} />AI 补全角色</button>
          <button onClick={() => onGenerate('dialogue')}>生成角色对白</button>
          <button onClick={() => onGenerate('consistency')}>检查人物一致性</button>
        </div>
        <div className="workbench-result-list">
          {aiResults.map((result) => (
            <AIResultCard key={result.id} result={result} canApply canFavorite onApply={() => onApplyResult(result.content)} />
          ))}
        </div>
      </aside>
    </section>
  );
}
```

- [ ] **Step 5: Add App state and handlers**

In `frontend/src/App.tsx`, add:

```ts
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

const [characterForm, setCharacterForm] = useState<CharacterProfilePayload>(emptyCharacterForm);
const [characterAiResults, setCharacterAiResults] = useState<WorkbenchAIResult[]>([]);
```

Add:

```ts
async function saveCharacterProfile() {
  if (!selectedProject) return;
  await api.createRecord(selectedProject.id, 'character-profiles', {
    title: characterForm.name || '未命名角色',
    category: 'character',
    content: `${characterForm.name}\n${characterForm.role}\n${characterForm.desire}`,
    payload: characterForm,
    status: 'active',
  });
  await loadTabData('characters', selectedProject.id);
  setLog('角色卡已保存到当前项目。');
}

async function generateCharacter(mode: 'new' | 'complete' | 'dialogue' | 'consistency') {
  if (!selectedProject) return;
  const workflow = mode === 'consistency' ? 'check_consistency' : 'generate_characters';
  const result = await api.runAi(selectedProject.id, workflow, { mode, character: characterForm });
  setCharacterAiResults((items) => [
    { id: `${Date.now()}`, title: mode === 'dialogue' ? '角色对白' : '角色生成结果', content: formatAiLog(result), status: 'ready' },
    ...items,
  ]);
}

function applyCharacterAiResult(content: string) {
  setCharacterForm((current) => ({ ...current, notes: `${current.notes ? `${current.notes}\n\n` : ''}${content}` }));
  setLog('AI 结果已应用到角色备注。');
}
```

- [ ] **Step 6: Route Story Bible tab to component**

When `activeTab === 'characters'`, render:

```tsx
<CharacterWorkbench
  records={records}
  form={characterForm}
  aiResults={characterAiResults}
  modelLabel={modelLabel(modelForWorkflow('generate_characters'))}
  onFormChange={setCharacterForm}
  onSave={() => void saveCharacterProfile()}
  onGenerate={(mode) => void generateCharacter(mode)}
  onApplyResult={applyCharacterAiResult}
/>
```

Exclude `characters` from the generic records layout condition.

- [ ] **Step 7: Add styles**

Add shared workbench styles from Task 6 before running tests.

- [ ] **Step 8: Run tests and commit**

Run:

```bash
cd frontend
npm test -- App.test.tsx
npm run build
```

Expected: PASS.

Commit:

```bash
git add frontend/src/components/CharacterWorkbench.tsx frontend/src/App.tsx frontend/src/api.ts frontend/src/styles.css frontend/src/App.test.tsx
git commit -m "feat: add character workbench"
```

## Task 4: Outline Workbench

**Files:**
- Create: `frontend/src/components/OutlineWorkbench.tsx`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/api.ts`
- Modify: `frontend/src/App.test.tsx`
- Modify: `frontend/src/styles.css`

- [ ] **Step 1: Add failing test**

Add:

```ts
test('renders dedicated outline workbench', () => {
  render(<App />);
  fireEvent.click(screen.getByRole('button', { name: /大纲/ }));
  expect(screen.getByText('大纲工作台')).toBeInTheDocument();
  expect(screen.getByLabelText('本章目标')).toBeInTheDocument();
  expect(screen.getByLabelText('主要冲突')).toBeInTheDocument();
  expect(screen.getByText('生成 10 章大纲')).toBeInTheDocument();
  expect(screen.getByText('扩展本章梗概')).toBeInTheDocument();
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend; npm test -- App.test.tsx`

Expected: FAIL because generic records layout is still used.

- [ ] **Step 3: Add outline type**

Add `OutlinePayload` from shared data shapes to `frontend/src/api.ts`.

- [ ] **Step 4: Create `OutlineWorkbench.tsx`**

Public API:

```tsx
import { BookMarked, GitBranch, Sparkles } from 'lucide-react';
import { GenericRecord, OutlinePayload, WorkbenchAIResult } from '../api';
import { AIResultCard } from './AIResultCard';

type OutlineWorkbenchProps = {
  records: GenericRecord[];
  form: OutlinePayload;
  aiResults: WorkbenchAIResult[];
  modelLabel: string;
  onFormChange: (form: OutlinePayload) => void;
  onSave: () => void;
  onGenerate: (mode: 'five' | 'ten' | 'twenty' | 'expand' | 'rhythm') => void;
  onApplyResult: (content: string) => void;
};
```

The component must render:

- Heading text `大纲工作台`
- Left tree title `分卷与章节`
- Inputs with labels: `分卷`, `章节标题`, `本章目标`, `主要冲突`, `关键事件`, `情绪节奏`, `伏笔`, `结尾钩子`, `关联角色`, `完成状态`
- Buttons: `生成 5 章大纲`, `生成 10 章大纲`, `生成 20 章大纲`, `扩展本章梗概`, `检查节奏断点`
- AI results using shared `AIResultCard` with `canApply` and `canFavorite`.

- [ ] **Step 5: Add App state and handlers**

Add:

```ts
const emptyOutlineForm: OutlinePayload = {
  volume: '第一卷',
  chapter_title: '',
  chapter_goal: '',
  main_conflict: '',
  key_events: '',
  emotional_rhythm: '',
  foreshadowing: '',
  hook: '',
  related_characters: '',
  completion_status: '草稿',
};

const [outlineForm, setOutlineForm] = useState<OutlinePayload>(emptyOutlineForm);
const [outlineAiResults, setOutlineAiResults] = useState<WorkbenchAIResult[]>([]);
```

Add:

```ts
async function saveOutlineRecord() {
  if (!selectedProject) return;
  await api.createRecord(selectedProject.id, 'outlines', {
    title: outlineForm.chapter_title || `${outlineForm.volume}大纲`,
    category: 'outline',
    content: `${outlineForm.chapter_goal}\n${outlineForm.main_conflict}\n${outlineForm.key_events}`,
    payload: outlineForm,
    status: outlineForm.completion_status,
  });
  await loadTabData('outline', selectedProject.id);
  setLog('大纲已保存到当前项目。');
}

async function generateOutline(mode: 'five' | 'ten' | 'twenty' | 'expand' | 'rhythm') {
  if (!selectedProject) return;
  const workflow = mode === 'rhythm' ? 'check_consistency' : mode === 'expand' ? 'generate_chapter_brief' : 'generate_outline';
  const result = await api.runAi(selectedProject.id, workflow, { mode, outline: outlineForm, chapters });
  setOutlineAiResults((items) => [
    { id: `${Date.now()}`, title: '大纲生成结果', content: formatAiLog(result), status: 'ready' },
    ...items,
  ]);
}

function applyOutlineAiResult(content: string) {
  setOutlineForm((current) => ({ ...current, key_events: `${current.key_events ? `${current.key_events}\n\n` : ''}${content}` }));
  setLog('AI 大纲结果已加入关键事件。');
}
```

- [ ] **Step 6: Route outline tab**

Render `OutlineWorkbench` when `activeTab === 'outline'`, and exclude `outline` from the generic records layout.

- [ ] **Step 7: Run tests and commit**

Run:

```bash
cd frontend
npm test -- App.test.tsx
npm run build
```

Expected: PASS.

Commit:

```bash
git add frontend/src/components/OutlineWorkbench.tsx frontend/src/App.tsx frontend/src/api.ts frontend/src/styles.css frontend/src/App.test.tsx
git commit -m "feat: add outline workbench"
```

## Task 5: Relationship Graph Workbench With Add/Edit Controls

**Files:**
- Create: `frontend/src/components/RelationshipGraphWorkbench.tsx`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/api.ts`
- Modify: `frontend/src/App.test.tsx`
- Modify: `frontend/src/styles.css`

- [ ] **Step 1: Add failing test**

Add:

```ts
test('relationship graph supports adding characters and relationships', () => {
  render(<App />);
  fireEvent.click(screen.getByRole('button', { name: /角色关系图/ }));
  expect(screen.getByText('关系图工作台')).toBeInTheDocument();
  expect(screen.getByText('新增角色')).toBeInTheDocument();
  expect(screen.getByText('新增关系')).toBeInTheDocument();
  expect(screen.getByLabelText('关系类型')).toBeInTheDocument();
  expect(screen.getByLabelText('关系强度')).toBeInTheDocument();
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend; npm test -- App.test.tsx`

Expected: FAIL because the graph page only renders display controls.

- [ ] **Step 3: Add relationship type**

Add `RelationshipPayload` from shared data shapes to `frontend/src/api.ts`.

- [ ] **Step 4: Create `RelationshipGraphWorkbench.tsx`**

Public API:

```tsx
import { Background, Controls, ReactFlow } from '@xyflow/react';
import { GitBranch, Plus, Sparkles } from 'lucide-react';
import { GenericRecord, RelationshipPayload, WorkbenchAIResult } from '../api';
import { AIResultCard } from './AIResultCard';

type RelationshipGraphWorkbenchProps = {
  relationships: GenericRecord[];
  characters: GenericRecord[];
  form: RelationshipPayload;
  aiResults: WorkbenchAIResult[];
  modelLabel: string;
  onFormChange: (form: RelationshipPayload) => void;
  onSaveRelationship: () => void;
  onCreateCharacter: () => void;
  onGenerate: (mode: 'extract' | 'conflict' | 'consistency') => void;
  onApplyResult: (content: string) => void;
};
```

The component must render:

- Heading `关系图工作台`
- Buttons `新增角色`, `新增关系`, `AI 提取关系`
- Form labels `来源角色`, `目标角色`, `关系类型`, `关系强度`, `冲突说明`, `关系变化记录`, `相关章节`
- Relationship type select options: `朋友`, `敌人`, `亲属`, `师徒`, `暧昧`, `利用`, `背叛`, `同盟`
- React Flow graph using character records as nodes and relationship records as edges.
- Shared `AIResultCard` list with `canApply`.

- [ ] **Step 5: Add App state and handlers**

Add:

```ts
const emptyRelationshipForm: RelationshipPayload = {
  source_character: '',
  target_character: '',
  relationship_type: '同盟',
  strength: 3,
  conflict: '',
  change_history: '',
  related_chapters: '',
};

const [relationshipForm, setRelationshipForm] = useState<RelationshipPayload>(emptyRelationshipForm);
const [relationshipAiResults, setRelationshipAiResults] = useState<WorkbenchAIResult[]>([]);
```

Add:

```ts
async function saveRelationshipRecord() {
  if (!selectedProject) return;
  await api.createRecord(selectedProject.id, 'character-relationships', {
    title: `${relationshipForm.source_character || '未知角色'} → ${relationshipForm.target_character || '未知角色'}`,
    category: relationshipForm.relationship_type,
    content: relationshipForm.conflict || relationshipForm.change_history,
    payload: relationshipForm,
    status: 'active',
  });
  await loadTabData('graph', selectedProject.id);
  setLog('角色关系已保存。');
}

async function createGraphCharacter() {
  if (!selectedProject) return;
  await api.createRecord(selectedProject.id, 'character-profiles', {
    title: '新角色',
    category: 'character',
    content: '请在角色工作台完善这个角色。',
    payload: emptyCharacterForm,
    status: 'draft',
  });
  setLog('已创建新角色，可在角色工作台继续完善。');
}

async function generateRelationship(mode: 'extract' | 'conflict' | 'consistency') {
  if (!selectedProject) return;
  const workflow = mode === 'extract' ? 'extract_relationships' : 'check_consistency';
  const result = await api.runAi(selectedProject.id, workflow, {
    mode,
    relationship: relationshipForm,
    characters: records,
    chapter: selectedChapter,
    draft,
  });
  setRelationshipAiResults((items) => [
    { id: `${Date.now()}`, title: '关系分析结果', content: formatAiLog(result), status: 'ready' },
    ...items,
  ]);
}

function applyRelationshipAiResult(content: string) {
  setRelationshipForm((current) => ({ ...current, change_history: `${current.change_history ? `${current.change_history}\n\n` : ''}${content}` }));
  setLog('AI 关系分析已加入变化记录。');
}
```

- [ ] **Step 6: Render dedicated graph component**

When `activeTab === 'graph'`, render `RelationshipGraphWorkbench`.

Pass character records using a separate state loaded from `character-profiles`. If keeping one `records` state, call `api.listRecords(selectedProject.id, 'character-profiles')` inside a `loadGraphSupportingData(projectId)` helper and store it in `graphCharacters`.

- [ ] **Step 7: Run tests and commit**

Run:

```bash
cd frontend
npm test -- App.test.tsx
npm run build
```

Expected: PASS.

Commit:

```bash
git add frontend/src/components/RelationshipGraphWorkbench.tsx frontend/src/App.tsx frontend/src/api.ts frontend/src/styles.css frontend/src/App.test.tsx
git commit -m "feat: add editable relationship graph workbench"
```

## Task 6: Shared Workbench Styling

**Files:**
- Modify: `frontend/src/styles.css`

- [ ] **Step 1: Add styles used by Character, Outline, and Graph workbenches**

Add:

```css
.special-workbench {
  display: grid;
  grid-template-columns: minmax(220px, 0.72fr) minmax(420px, 1.45fr) minmax(280px, 0.9fr);
  gap: 1rem;
  align-items: stretch;
}

.workbench-side-list,
.structured-editor-panel,
.workbench-ai-panel {
  border: 1px solid var(--line);
  background: rgba(8, 13, 26, 0.74);
  border-radius: 24px;
  padding: 1rem;
  box-shadow: var(--shadow-soft);
  min-width: 0;
}

.workbench-panel-head {
  display: grid;
  gap: 0.35rem;
  margin-bottom: 1rem;
}

.workbench-panel-head span {
  color: var(--accent-amber);
  font-size: 0.76rem;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

.workbench-panel-head h3 {
  margin: 0;
}

.structured-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.85rem;
}

.structured-grid label {
  display: grid;
  gap: 0.45rem;
  color: var(--muted);
  font-size: 0.88rem;
}

.structured-grid textarea {
  min-height: 94px;
}

.entity-list,
.workbench-result-list {
  display: grid;
  gap: 0.65rem;
  max-height: calc(100vh - 260px);
  overflow-y: auto;
  padding-right: 0.25rem;
}

.entity-list button {
  text-align: left;
  border: 1px solid var(--line);
  border-radius: 16px;
  padding: 0.75rem;
  background: rgba(255, 255, 255, 0.035);
  color: var(--text);
}

.relationship-graph-workbench .graph-stage {
  height: 520px;
  border: 1px solid var(--line);
  border-radius: 22px;
  overflow: hidden;
  background: rgba(4, 8, 18, 0.62);
}

@media (max-width: 1180px) {
  .special-workbench {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 720px) {
  .structured-grid {
    grid-template-columns: 1fr;
  }
}
```

- [ ] **Step 2: Run visual safety build**

Run:

```bash
cd frontend
npm run build
```

Expected: build succeeds and CSS compiles.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/styles.css
git commit -m "style: add workbench layout styles"
```

## Task 7: Style Profile Handoff To Chapter Generation

**Files:**
- Modify: `frontend/src/components/StyleLearningPanel.tsx`
- Modify: `frontend/src/components/NovelEditorPage.tsx`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/App.test.tsx`

- [ ] **Step 1: Add failing test**

Add:

```ts
test('style learning exposes style profile handoff for generation', () => {
  render(<App />);
  fireEvent.click(screen.getByRole('button', { name: /风格学习/ }));
  expect(screen.getByText('章节生成时可调用')).toBeInTheDocument();
  fireEvent.click(screen.getByRole('button', { name: /章节编辑器/ }));
  expect(screen.getByLabelText('写作风格档案')).toBeInTheDocument();
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend; npm test -- App.test.tsx`

Expected: FAIL because chapter editor has no style profile selector.

- [ ] **Step 3: Add style profile selector prop**

In `NovelEditorPageProps`, add:

```ts
styleProfiles: Array<{ id: string; title: string }>;
selectedStyleProfileId: string;
onStyleProfileChange: (id: string) => void;
```

Render this select in `PromptInputBox`:

```tsx
<select aria-label="写作风格档案" value={selectedStyleProfileId} onChange={(event) => onStyleProfileChange(event.target.value)}>
  <option value="">不指定风格档案</option>
  {styleProfiles.map((profile) => <option key={profile.id} value={profile.id}>{profile.title}</option>)}
</select>
```

- [ ] **Step 4: Store selected style profile in App**

Add:

```ts
const [selectedStyleProfileId, setSelectedStyleProfileId] = useState('');
```

Pass:

```tsx
styleProfiles={records.filter((record) => record.category === 'style').map((record) => ({ id: record.id, title: record.title }))}
selectedStyleProfileId={selectedStyleProfileId}
onStyleProfileChange={setSelectedStyleProfileId}
```

Update `generateChapterDraftFromAI` payload:

```ts
style_profile_id: selectedStyleProfileId,
style_profile: records.find((record) => record.id === selectedStyleProfileId),
```

- [ ] **Step 5: Add style handoff copy**

In `StyleLearningPanel.tsx`, render `章节生成时可调用` near saved style profiles.

- [ ] **Step 6: Run tests and commit**

Run:

```bash
cd frontend
npm test -- App.test.tsx
npm run build
```

Expected: PASS.

Commit:

```bash
git add frontend/src/components/StyleLearningPanel.tsx frontend/src/components/NovelEditorPage.tsx frontend/src/App.tsx frontend/src/App.test.tsx
git commit -m "feat: connect style profiles to chapter generation"
```

## Task 8: Full Verification

**Files:**
- Test only unless a previous task fails.

- [ ] **Step 1: Run frontend tests**

Run:

```bash
cd frontend
npm test
```

Expected: all tests PASS.

- [ ] **Step 2: Run frontend build**

Run:

```bash
cd frontend
npm run build
```

Expected: Vite build succeeds.

- [ ] **Step 3: Run backend tests**

Run:

```bash
python -m pytest backend/tests/test_mvp.py -q
```

Expected: all backend tests PASS.

- [ ] **Step 4: Manual browser verification**

Start services if they are not already running:

```powershell
Start-Process -FilePath python -ArgumentList '-m','uvicorn','backend.app.main:app','--host','127.0.0.1','--port','8000' -WorkingDirectory 'G:\ai小说' -WindowStyle Hidden
Start-Process -FilePath npm.cmd -ArgumentList 'run','dev','--','--host','127.0.0.1' -WorkingDirectory 'G:\ai小说\frontend' -WindowStyle Hidden
```

Open `http://127.0.0.1:5173` and verify:

- Chapter editor shows one-click generation and fixed AI result cards.
- Character workbench renders role-specific fields.
- Outline workbench renders structural fields.
- Relationship graph has add character and add relationship controls.
- Style learning shows style profile handoff text.

- [ ] **Step 5: Commit verification-only fixes**

If verification required small fixes:

```bash
git add frontend/src backend/tests frontend/src/App.test.tsx
git commit -m "fix: stabilize core workbench verification"
```

If no fixes were needed, do not create an empty commit.

## Self-Review

- Spec coverage: The plan covers chapter AI generation, character workbench, outline workbench, relationship graph creation/editing, style profile handoff, fixed AI result containers, and tests.
- Placeholder scan: No `TBD`, `TODO`, or deferred implementation steps are present.
- Type consistency: `CharacterProfilePayload`, `OutlinePayload`, `RelationshipPayload`, and `WorkbenchAIResult` are defined in `api.ts` before component tasks use them.
- Scope check: The plan does not rewrite worldbuilding, timeline, foreshadowing, taboo, knowledge base, wiki, export, auth, or backend architecture. It focuses on the approved first-stage core writing chain.
