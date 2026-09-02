import { useState } from 'react';
import { useParams } from 'react-router-dom';
import { Sparkles, Play, Pause, Square, Check, RefreshCw, Users, Globe, Map, Library } from 'lucide-react';
import { api, AiResult } from '../api';
import { useProject } from '../shell/useProject';
import { useRecords } from '../shell/useRecords';

type StepKey = 'concept' | 'bible' | 'characters' | 'world' | 'outline';
const STEP_LIST: Array<{ key: StepKey; label: string; icon: typeof Sparkles }> = [
  { key: 'concept', label: 'Story Concept', icon: Sparkles },
  { key: 'bible', label: 'Story Bible', icon: Library },
  { key: 'characters', label: 'Characters', icon: Users },
  { key: 'world', label: 'World', icon: Globe },
  { key: 'outline', label: 'Outline', icon: Map },
];

export function AIStudio() {
  const { projectId } = useParams();
  const { project } = useProject(projectId);
  const { records: characters, create: createCharacter } = useRecords(projectId, 'character-profiles');
  const { records: outlines, create: createOutline } = useRecords(projectId, 'outlines');
  const { records: worlds, create: createWorld } = useRecords(projectId, 'world-settings');
  const [concept, setConcept] = useState('一个被流放的前朝公主，发现能改写记忆的古籍，踏上复仇与救赎之路。');
  const [steps, setSteps] = useState<Array<{ key: StepKey; status: 'idle' | 'running' | 'done' | 'error'; result?: AiResult; accepted?: boolean }>>(
    STEP_LIST.map((s) => ({ key: s.key, status: 'idle' })),
  );
  const [running, setRunning] = useState(false);

  const setStatus = (key: StepKey, status: 'idle' | 'running' | 'done' | 'error', result?: AiResult) =>
    setSteps((prev) => prev.map((s) => (s.key === key ? { ...s, status, result: result ?? s.result } : s)));

  const runStep = async (key: StepKey) => {
    if (!projectId) return;
    setStatus(key, 'running');
    setRunning(true);
    try {
      let workflow = '';
      let payload: Record<string, unknown> = {};
      if (key === 'characters') {
        workflow = 'generate_characters';
        payload = { mode: 'new', existing_characters: characters.map((c) => c.title), logline: project?.topic ?? concept, genre: project?.genre ?? '', audience: project?.audience ?? '', tone: project?.tone ?? '', world: [], timeline: [], foreshadowings: [] };
      } else if (key === 'outline') {
        workflow = 'generate_outline';
        payload = { scope: 'chapter', chapter_number: 1, chapter_title: '第 1 章', target_chapter_count: project?.target_chapter_count ?? 5, genre: project?.genre ?? '', audience: project?.audience ?? '', tone: project?.tone ?? '', logline: project?.topic ?? concept, characters: [], world: [], timeline: [], foreshadowings: [], style: '' };
      } else {
        setStatus(key, 'done', { workflow: key, text: promptForStep(key, concept, project), score: 0, items: [] });
        setRunning(false);
        return;
      }
      const result = await api.runAi(projectId, workflow, payload);
      setStatus(key, 'done', result);
    } catch (error) {
      setStatus(key, 'error');
    } finally {
      setRunning(false);
    }
  };

  const accept = async (key: StepKey) => {
    const step = steps.find((s) => s.key === key);
    if (!step?.result?.text || !projectId) return;
    try {
      if (key === 'characters') {
        const items = extractJson(step.result.text);
        for (const item of items) {
          await createCharacter({ title: (item.name ?? item.title ?? '角色').toString(), category: 'character-profiles', content: JSON.stringify(item, null, 2), status: 'active' });
        }
      } else if (key === 'outline') {
        const items = extractJson(step.result.text);
        for (const item of items) {
          await createOutline({ title: (item.chapter_title ?? item.title ?? '章节大纲').toString(), category: 'outlines', content: JSON.stringify(item, null, 2), status: 'active' });
        }
      } else if (key === 'world') {
        const items = extractJson(step.result.text);
        for (const item of items) {
          await createWorld({ title: (item.name ?? item.title ?? '实体').toString(), category: 'Locations', content: JSON.stringify(item, null, 2), status: 'active' });
        }
      }
      setSteps((prev) => prev.map((s) => (s.key === key ? { ...s, accepted: true } : s)));
    } catch {
      /* ignore */
    }
  };

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h1>AI Studio</h1>
          <p className="os-page-sub">What do you want to create?</p>
        </div>
        <button className="os-btn ai"><Sparkles size={14} /> {project?.title ?? 'AI 创作'}</button>
      </div>

      <section className="os-card">
        <div className="os-card-header"><strong>故事概念</strong><small>描述你的故事</small></div>
        <textarea
          value={concept}
          onChange={(e) => setConcept(e.target.value)}
          rows={4}
          placeholder="描述你想创作的故事…"
        />
        <div style={{ display: 'flex', gap: '0.5rem', marginTop: '0.6rem' }}>
          {['Romance', 'CEO', 'Revenge'].map((g) => (
            <button key={g} className="os-ai-chip ai" style={{ border: '1px solid var(--n-border)', cursor: 'pointer' }}>{g}</button>
          ))}
          <button className="os-btn" style={{ marginLeft: 'auto' }}><Play size={14} /> Run All</button>
        </div>
      </section>

      <section className="os-card" style={{ marginTop: '1rem' }}>
        <div className="os-card-header"><strong>生成管线</strong><small>序列：概念 → 设定 → 角色 → 世界 → 大纲</small></div>
        <div className="os-grid" style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(210px, 1fr))' }}>
          {steps.map((s) => {
            const meta = STEP_LIST.find((x) => x.key === s.key)!;
            const Icon = meta.icon;
            return (
              <div key={s.key} className="os-card" style={{ padding: '0.7rem', display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                <div style={{ alignItems: 'center', display: 'flex', gap: '0.5rem' }}>
                  <Icon size={15} style={{ color: 'var(--ai-accent)' }} />
                  <strong style={{ flex: 1, fontSize: '0.86rem' }}>{meta.label}</strong>
                  <StepBadge status={s.status} />
                </div>
                {s.result?.text && (
                  <small style={{ color: 'var(--n-text-2)', maxHeight: '52px', overflow: 'hidden' }}>{s.result.text.slice(0, 90)}{s.result.text.length > 90 ? '…' : ''}</small>
                )}
                <div style={{ display: 'flex', gap: '0.35rem', marginTop: 'auto' }}>
                  <button className="os-btn" style={{ fontSize: '0.74rem', padding: '0.25rem 0.45rem', flex: 1 }} onClick={() => void runStep(s.key)} disabled={running || s.accepted}>
                    {s.status === 'running' ? <Pause size={12} /> : s.accepted ? <Check size={12} /> : <Play size={12} />}
                    {s.accepted ? '已保存' : s.status === 'done' ? '重新生成' : '运行'}
                  </button>
                  {s.result?.text && !s.accepted && (
                    <button className="os-btn ai" style={{ fontSize: '0.74rem', padding: '0.25rem 0.45rem' }} onClick={() => void accept(s.key)} title="保存到项目">
                      <Check size={12} /> 接受
                    </button>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </section>
    </div>
  );
}

function StepBadge({ status }: { status: string }) {
  if (status === 'running') return <span className="os-ai-chip ai"><Pause size={10} /> 生成中</span>;
  if (status === 'done') return <span className="os-ai-chip ai"><Check size={10} /> 完成</span>;
  if (status === 'error') return <span className="os-ai-chip" style={{ color: '#c9564f' }}>失败</span>;
  return <span className="os-ai-chip">待运行</span>;
}

function promptForStep(key: StepKey, concept: string, project?: { title?: string; genre?: string; audience?: string; tone?: string } | null) {
  return `【${project?.title ?? '新故事'}】\n类型：${project?.genre ?? '奇幻'} · 受众：${project?.audience ?? '网文读者'} · 基调：${project?.tone ?? '克制、悬疑'}\n概念：${concept}\n\n请围绕以上概念展开，输出结构化内容。`;
}

function extractJson(text: string): Array<Record<string, unknown>> {
  try {
    const raw = text.match(/\[[\s\S]*\]/);
    if (raw) return JSON.parse(raw[0]);
  } catch {
    /* ignore */
  }
  return [];
}
