import { FormEvent, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { FolderOpen, Pencil, Plus, Trash2 } from 'lucide-react';
import { api, Project } from '../api';
import { useWorkspace } from '../shell/workspace';
import { ConfirmDialog, Modal } from '../ui/basics';

type FormState = {
  id?: string;
  title: string;
  genre: string;
  topic: string;
  audience: string;
  tone: string;
  target_chapter_count: string;
  synopsis: string;
};

const EMPTY_FORM: FormState = {
  title: '',
  genre: '',
  topic: '',
  audience: '',
  tone: '',
  target_chapter_count: '',
  synopsis: '',
};

function formFromProject(project: Project): FormState {
  return {
    id: project.id,
    title: project.title ?? '',
    genre: project.genre ?? '',
    topic: project.topic ?? '',
    audience: project.audience ?? '',
    tone: project.tone ?? '',
    target_chapter_count: project.target_chapter_count ? String(project.target_chapter_count) : '',
    synopsis: project.synopsis ?? '',
  };
}

export function ProjectsManagerModal({ onClose }: { onClose: () => void }) {
  const navigate = useNavigate();
  const { projects, reloadProjects, projectId } = useWorkspace();
  const [form, setForm] = useState<FormState | null>(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [deleting, setDeleting] = useState<Project | null>(null);

  const set = (patch: Partial<FormState>) => setForm((prev) => (prev ? { ...prev, ...patch } : prev));

  const save = async (event: FormEvent) => {
    event.preventDefault();
    if (!form || !form.title.trim() || saving) return;
    setSaving(true);
    setError('');
    const payload = {
      title: form.title.trim(),
      genre: form.genre.trim(),
      topic: form.topic.trim(),
      audience: form.audience.trim(),
      tone: form.tone.trim(),
      target_chapter_count: Number(form.target_chapter_count) || 0,
      synopsis: form.synopsis,
    };
    try {
      if (form.id) {
        await api.updateProject(form.id, payload);
      } else {
        const created = await api.createProject(payload);
        await reloadProjects();
        setForm(null);
        navigate(`/projects/${created.id}/overview`);
        onClose();
        return;
      }
      await reloadProjects();
      setForm(null);
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : '保存失败');
    } finally {
      setSaving(false);
    }
  };

  const remove = async () => {
    if (!deleting) return;
    try {
      await api.deleteProject(deleting.id, deleting.title);
      const wasCurrent = deleting.id === projectId;
      await reloadProjects();
      setDeleting(null);
      if (wasCurrent) navigate('/projects');
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : '删除失败');
      setDeleting(null);
    }
  };

  return (
    <>
      <Modal
        title="管理项目"
        wide
        onClose={onClose}
        footer={
          <>
            <span className="spacer">{error}</span>
            <button className="btn" onClick={onClose}>完成</button>
            <button className="btn btn-primary" onClick={() => setForm({ ...EMPTY_FORM })}>
              <Plus size={14} /> 新建项目
            </button>
          </>
        }
      >
        {form ? (
          <form onSubmit={save} style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
            <label className="field">
              <span>项目名称 *</span>
              <input value={form.title} onChange={(event) => set({ title: event.target.value })} autoFocus placeholder="如：雨夜玫瑰" />
            </label>
            <div style={{ display: 'grid', gap: 14, gridTemplateColumns: '1fr 1fr' }}>
              <label className="field">
                <span>类型</span>
                <input value={form.genre} onChange={(event) => set({ genre: event.target.value })} placeholder="悬疑 / 古风 / 都市…" />
              </label>
              <label className="field">
                <span>目标章节数</span>
                <input
                  type="number"
                  min={0}
                  value={form.target_chapter_count}
                  onChange={(event) => set({ target_chapter_count: event.target.value })}
                  placeholder="24"
                />
              </label>
            </div>
            <label className="field">
              <span>核心创意（一句话）</span>
              <input value={form.topic} onChange={(event) => set({ topic: event.target.value })} placeholder="一个关于记忆改写的复仇故事" />
            </label>
            <div style={{ display: 'grid', gap: 14, gridTemplateColumns: '1fr 1fr' }}>
              <label className="field">
                <span>目标读者</span>
                <input value={form.audience} onChange={(event) => set({ audience: event.target.value })} placeholder="网文读者" />
              </label>
              <label className="field">
                <span>基调</span>
                <input value={form.tone} onChange={(event) => set({ tone: event.target.value })} placeholder="克制、悬疑" />
              </label>
            </div>
            <label className="field">
              <span>简介</span>
              <textarea value={form.synopsis} onChange={(event) => set({ synopsis: event.target.value })} rows={3} placeholder="故事梗概…" />
            </label>
            <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
              <button type="button" className="btn" onClick={() => setForm(null)}>返回列表</button>
              <button type="submit" className="btn btn-primary" disabled={!form.title.trim() || saving}>
                {saving ? '保存中…' : form.id ? '保存修改' : '创建项目'}
              </button>
            </div>
          </form>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
            {projects.map((project) => (
              <div key={project.id} className="row" style={{ border: '1px solid var(--line)', borderRadius: 10, marginBottom: 6 }}>
                <span className="avatar" aria-hidden>
                  <FolderOpen size={14} />
                </span>
                <span className="grow ellip">
                  <b>{project.title}</b>
                  <small style={{ display: 'block' }}>
                    {[project.genre || '未设类型', project.target_chapter_count ? `目标 ${project.target_chapter_count} 章` : ''].filter(Boolean).join(' · ') || ' '}
                  </small>
                </span>
                {project.id === projectId && <span className="badge accent">当前</span>}
                <button className="icon-btn" aria-label={`编辑 ${project.title}`} onClick={() => setForm(formFromProject(project))}>
                  <Pencil size={14} />
                </button>
                <button className="icon-btn" aria-label={`删除 ${project.title}`} onClick={() => setDeleting(project)}>
                  <Trash2 size={14} />
                </button>
              </div>
            ))}
            {projects.length === 0 && <p className="muted">还没有项目，点击下方「新建项目」开始。</p>}
          </div>
        )}
      </Modal>

      {deleting && (
        <ConfirmDialog
          title="删除项目"
          danger
          confirmLabel="永久删除"
          message={
            <>
              将删除项目「<b>{deleting.title}</b>」及其全部章节、设定与版本历史，此操作不可恢复。
            </>
          }
          inputHint={`输入项目名称「${deleting.title}」以确认删除`}
          expectedValue={deleting.title}
          onConfirm={() => void remove()}
          onCancel={() => setDeleting(null)}
        />
      )}
    </>
  );
}
