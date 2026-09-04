import { useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { ArrowRight, Check, Globe, LoaderCircle, Map, Sparkles, Users } from 'lucide-react';
import { AiResult, api } from '../api';
import { useWorkspace } from '../shell/workspace';
import { useRecords } from '../shell/useRecords';
import { PageHeader } from '../ui/basics';

type StepKey = 'characters' | 'world' | 'outline';

const STEP_LIST: Array<{ key: StepKey; label: string; desc: string; icon: typeof Sparkles }> = [
  { key: 'characters', label: '人物', desc: '主角与关键配角', icon: Users },
  { key: 'world', label: '世界观', desc: '地点 / 组织 / 规则', icon: Globe },
  { key: 'outline', label: '第一章大纲', desc: '章节梗概与钩子', icon: Map },
];

type StepState = {
  status: 'idle' | 'running' | 'done' | 'error';
  result?: AiResult;
  accepted?: boolean;
};

export function AIStudio() {
  const navigate = useNavigate();
  const { projectId } = useParams();
  const { project } = useWorkspace();
  const { reload: reloadCharacters, records: characters } = useRecords(projectId, 'character-profiles');
  const { reload: reloadWorlds, records: worlds } = useRecords(projectId, 'world-settings');
  const [concept, setConcept] = useState(project?.topic ?? '');
  const [steps, setSteps] = useState<Record<StepKey, StepState>>({
    characters: { status: 'idle' },
    world: { status: 'idle' },
    outline: { status: 'idle' },
  });
  const [busy, setBusy] = useState(false);
  const [conceptSaving, setConceptSaving] = useState(false);
  const [conceptSaved, setConceptSaved] = useState(false);

  const setStep = (key: StepKey, patch: Partial<StepState>) =>
    setSteps((prev) => ({ ...prev, [key]: { ...prev[key], ...patch } }));

  const workflowFor = (key: StepKey) => (key === 'characters' ? 'generate_characters' : key === 'world' ? 'generate_setting' : 'generate_outline');

  const payloadFor = (key: StepKey, prompt: string): Record<string, unknown> => {
    const base = { prompt, logline: concept };
    if (key === 'characters') {
      return { ...base, mode: 'new', existing_characters: characters.map((item) => ({ title: item.title, payload: item.payload })) };
    }
    if (key === 'world') {
      return { ...base, existing_world: worlds.map((item) => ({ title: item.title, category: item.category })) };
    }
    return {
      ...base,
      scope: 'chapter',
      chapter_number: 1,
      characters: characters.map((item) => item.title),
      world: worlds.map((item) => item.title),
    };
  };

  const runStep = async (key: StepKey) => {
    if (!projectId || busy) return;
    setBusy(true);
    setStep(key, { status: 'running' });
    try {
      const result = await api.runAi(projectId, workflowFor(key), payloadFor(key, ''));
      setStep(key, { status: 'done', result, accepted: false });
    } catch {
      setStep(key, { status: 'error' });
    } finally {
      setBusy(false);
    }
  };

  const acceptStep = async (key: StepKey) => {
    if (!projectId) return;
    const step = steps[key];
    if (!step.result) return;
    const items = parseItems(step.result);
    for (const item of items) {
      const payload = (item.payload ?? {}) as Record<string, unknown>;
      if (key === 'characters') {
        await api.createRecord(projectId, 'character-profiles', {
          title: item.title,
          category: typeof payload.role === 'string' ? payload.role : '配角',
          content: item.content,
          payload,
          status: 'active',
        });
      } else if (key === 'world') {
        await api.createRecord(projectId, 'world-settings', {
          title: item.title,
          category: typeof payload.category === 'string' ? payload.category : 'Locations',
          content: item.content,
          payload,
          status: 'active',
        });
      } else {
        await api.createRecord(projectId, 'outlines', {
          title: item.title,
          category: 'chapter_outline',
          content: item.content,
          payload,
          status: 'active',
        });
      }
    }
    if (key === 'characters') await reloadCharacters();
    if (key === 'world') await reloadWorlds();
    setStep(key, { accepted: true });
  };

  return (
    <div className="page-inner">
      <PageHeader
        title="AI 工作室"
        sub="一句话概念，逐步生成人物、世界观与大纲。每一步的产物都会落库，可随时修改和回退版本。"
      />

      <section className="card">
        <div className="card-head">
          <b>故事概念</b>
          <small>一句话说清你想写什么</small>
        </div>
        <textarea
          value={concept}
          onChange={(event) => setConcept(event.target.value)}
          rows={3}
          placeholder="例：一个被流放的前朝公主，发现能改写记忆的古籍，踏上复仇与救赎之路。"
        />
        <div className="row-flex" style={{ marginTop: 12, justifyContent: 'flex-end' }}>
          {conceptSaved && <span className="badge ok">已存入项目</span>}
          <button
            className="btn"
            disabled={!concept.trim() || conceptSaving}
            onClick={() => {
              if (!projectId) return;
              setConceptSaving(true);
              api
                .updateProject(projectId, {
                  title: project?.title ?? '未命名项目',
                  topic: concept,
                  genre: project?.genre ?? '',
                  audience: project?.audience ?? '',
                  tone: project?.tone ?? '',
                  target_chapter_count: project?.target_chapter_count ?? 0,
                  synopsis: project?.synopsis ?? '',
                })
                .then(() => setConceptSaved(true))
                .finally(() => setConceptSaving(false));
            }}
          >
            {conceptSaving ? '保存中…' : '把概念存入项目'}
          </button>
        </div>
      </section>

      <section className="section">
        <h2 className="section-title">
          生成管线 <small>PIPELINE</small>
        </h2>
        <div className="grid" style={{ gridTemplateColumns: `repeat(${STEP_LIST.length}, minmax(0, 1fr))` }}>
          {STEP_LIST.map((step, index) => {
            const state = steps[step.key];
            const Icon = step.icon;
            return (
              <div key={step.key} className="card" style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                <div className="row-flex">
                  <Icon size={15} style={{ color: 'var(--ai)' }} />
                  <b style={{ flex: 1, fontSize: 13.5 }}>
                    {index + 1}. {step.label}
                  </b>
                  <StepBadge state={state} />
                </div>
                <p className="muted" style={{ fontSize: 12 }}>{step.desc}</p>
                {state.result?.text && (
                  <p className="muted" style={{ fontSize: 12, lineHeight: 1.7, maxHeight: 92, overflow: 'hidden' }}>
                    {state.result.text.slice(0, 130)}{state.result.text.length > 130 ? '…' : ''}
                  </p>
                )}
                <div className="row-flex" style={{ marginTop: 'auto' }}>
                  <button className="btn grow" onClick={() => void runStep(step.key)} disabled={busy || !concept.trim()}>
                    {state.status === 'running' ? <LoaderCircle size={12} className="spin" /> : <Sparkles size={12} />}
                    {state.status === 'done' ? '重新生成' : '生成'}
                  </button>
                  {state.result && !state.accepted && (
                    <button className="btn btn-ai" onClick={() => void acceptStep(step.key)}>
                      <Check size={12} /> 接受
                    </button>
                  )}
                  {state.accepted && (
                    <button className="btn btn-ghost" style={{ color: 'var(--ok)' }}>
                      <Check size={12} /> 已保存
                    </button>
                  )}
                </div>
              </div>
            );
          })}
        </div>
        {!concept.trim() && <p className="muted" style={{ fontSize: 12.5, marginTop: 10 }}>先在上方填写故事概念，再依次运行生成。</p>}
      </section>

      <section className="section">
        <div className="card" style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
          <span className="avatar accent"><ArrowRight size={15} /></span>
          <div style={{ flex: 1 }}>
            <b style={{ fontSize: 13.5 }}>基础设定就绪后，去写作页开始第一章</b>
            <p className="muted" style={{ fontSize: 12.5, marginTop: 4 }}>写作页的 AI Copilot 会引用人物、世界观与大纲作为上下文。</p>
          </div>
          <button className="btn btn-primary" onClick={() => navigate(`/projects/${projectId}/writing`)}>
            进入写作
          </button>
        </div>
      </section>
    </div>
  );
}

function StepBadge({ state }: { state: StepState }) {
  if (state.status === 'running') return <span className="badge ai">生成中</span>;
  if (state.status === 'error') return <span className="badge" style={{ background: 'var(--accent-wash)', color: 'var(--danger)' }}>失败</span>;
  if (state.accepted) return <span className="badge ok">已保存</span>;
  if (state.status === 'done') return <span className="badge accent">待接受</span>;
  return <span className="badge">待运行</span>;
}

function parseItems(result: AiResult): Array<{ title: string; content: string; payload?: Record<string, unknown> }> {
  const structured = result.structured;
  const normalize = (item: unknown, index: number) => {
    if (item && typeof item === 'object') {
      const record = item as Record<string, unknown>;
      const title = [record.name, record.title, record.chapter_title].find((value) => typeof value === 'string' && value.trim()) ?? `条目 ${index + 1}`;
      const content =
        [record.description, record.chapter_goal, record.summary, record.content].find((value) => typeof value === 'string' && value.trim()) ??
        (Object.entries(record)
          .filter(([key, value]) => !['name', 'title', 'chapter_title'].includes(key) && typeof value === 'string' && value.trim())
          .map(([, value]) => String(value).trim())
          .join('\n') || result.text.trim());
      return { title: String(title), content: String(content), payload: record };
    }
    return { title: `条目 ${index + 1}`, content: String(item ?? '') };
  };
  if (Array.isArray(structured)) return structured.map(normalize);
  const match = result.text.match(/\[[\s\S]*\]/);
  if (match) {
    try {
      const parsed = JSON.parse(match[0]) as unknown;
      if (Array.isArray(parsed)) return parsed.map(normalize);
    } catch {
      /* fallthrough */
    }
  }
  return [{ title: 'AI 结果', content: result.text.trim() }];
}
