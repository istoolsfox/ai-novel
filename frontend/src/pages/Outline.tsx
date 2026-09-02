import { useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { Feather, Map, Pencil, Plus, Sparkles, Trash2 } from 'lucide-react';
import { Chapter } from '../api';
import { useChapters } from '../shell/useProject';
import { useWorkspace } from '../shell/workspace';
import { ConfirmDialog, EmptyState, Modal, PageHeader } from '../ui/basics';
import { AIGenerateModal } from '../components/AIGenerateModal';
import { api } from '../api';

type ChapterForm = { id?: string; title: string; brief: string; summary: string };

export function Outline() {
  const navigate = useNavigate();
  const { projectId } = useParams();
  const { project } = useWorkspace();
  const { chapters, reload } = useChapters(projectId);
  const [form, setForm] = useState<ChapterForm | null>(null);
  const [saving, setSaving] = useState(false);
  const [deleting, setDeleting] = useState<Chapter | null>(null);
  const [aiOpen, setAiOpen] = useState(false);

  const sorted = [...chapters].sort((left, right) => left.chapter_number - right.chapter_number);
  const totalWords = chapters.reduce((sum, chapter) => sum + (chapter.draft?.length ?? 0), 0);

  const saveChapter = async () => {
    if (!form || !projectId || saving) return;
    setSaving(true);
    try {
      if (form.id) {
        await api.updateChapter(projectId, form.id, { title: form.title, brief: form.brief, summary: form.summary });
      } else {
        const nextNumber = chapters.reduce((max, chapter) => Math.max(max, chapter.chapter_number), 0) + 1;
        await api.createChapter(projectId, {
          chapter_number: nextNumber,
          title: form.title || `第 ${nextNumber} 章`,
          brief: form.brief,
          summary: form.summary,
          draft: '',
        });
      }
      await reload();
      setForm(null);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="page-inner wide">
      <PageHeader
        title="大纲"
        sub={project ? `${project.title} · ${chapters.length} 章 · 共 ${totalWords.toLocaleString()} 字` : '章节板：梗概、状态与入口'}
        actions={
          <>
            <button className="btn" onClick={() => { setForm({ title: '', brief: '', summary: '' }); }}>
              <Plus size={14} /> 新建章节
            </button>
            <button className="btn btn-ai" onClick={() => setAiOpen(true)}>
              <Sparkles size={14} /> AI 生成章节
            </button>
          </>
        }
      />

      {sorted.length === 0 ? (
        <EmptyState
          icon={<Map size={26} />}
          title="还没有章节"
          hint="手动创建章节，或让 AI 根据人物与世界观生成第一章大纲。"
          action={
            <button className="btn" onClick={() => setForm({ title: '', brief: '', summary: '' })}>
              <Plus size={14} /> 新建章节
            </button>
          }
        />
      ) : (
        <div className="grid" style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))' }}>
          {sorted.map((chapter) => (
            <article key={chapter.id} className="card" style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
              <div className="row-flex">
                <span className="muted" style={{ fontSize: 11, letterSpacing: '0.1em', fontWeight: 700 }}>
                  CH {String(chapter.chapter_number).padStart(2, '0')}
                </span>
                <span className={chapter.status === 'final' ? 'badge ok' : 'badge'}>
                  {chapter.status === 'final' ? '已定稿' : '草稿'}
                </span>
                <span className="spacer" style={{ flex: 1 }} />
                <button className="icon-btn" aria-label="编辑章节" onClick={() => setForm({ id: chapter.id, title: chapter.title, brief: chapter.brief, summary: chapter.summary })}>
                  <Pencil size={13} />
                </button>
                <button className="icon-btn" aria-label="删除章节" onClick={() => setDeleting(chapter)}>
                  <Trash2 size={13} />
                </button>
              </div>
              <b style={{ fontFamily: 'var(--serif)', fontSize: 15.5 }}>{chapter.title || '未命名章'}</b>
              <p className="muted" style={{ fontSize: 12.5, lineHeight: 1.7, flex: 1, minHeight: 38 }}>
                {chapter.brief || chapter.summary || '暂无梗概'}
              </p>
              <div className="row-flex">
                <span className="badge">{(chapter.draft?.length ?? 0).toLocaleString()} 字</span>
                <span className="spacer" style={{ flex: 1 }} />
                <button className="btn" style={{ fontSize: 12.5, padding: '5px 11px' }} onClick={() => navigate(`/projects/${projectId}/writing/${chapter.id}`)}>
                  <Feather size={12} /> 写作
                </button>
              </div>
            </article>
          ))}
        </div>
      )}

      {form && (
        <Modal
          title={form.id ? '编辑章节' : '新建章节'}
          onClose={() => setForm(null)}
          footer={
            <>
              <span className="spacer" />
              <button className="btn" onClick={() => setForm(null)}>取消</button>
              <button className="btn btn-primary" onClick={() => void saveChapter()} disabled={saving || !form.title.trim()}>
                {saving ? '保存中…' : form.id ? '保存' : '创建章节'}
              </button>
            </>
          }
        >
          <label className="field">
            <span>章节标题 *</span>
            <input value={form.title} onChange={(event) => setForm({ ...form, title: event.target.value })} autoFocus placeholder="如：第 1 章 · 暴雨夜" />
          </label>
          <label className="field">
            <span>章节梗概（AI 生成的依据）</span>
            <textarea value={form.brief} onChange={(event) => setForm({ ...form, brief: event.target.value })} rows={4} placeholder="这一章要发生什么？" />
          </label>
          <label className="field">
            <span>内容摘要（写完后再补）</span>
            <textarea value={form.summary} onChange={(event) => setForm({ ...form, summary: event.target.value })} rows={3} />
          </label>
        </Modal>
      )}

      {aiOpen && projectId && (
        <AIGenerateModal
          projectId={projectId}
          title="AI 生成新章节"
          intro="AI 会基于现有人物、世界观和最近章节生成新的一章梗概并创建章节；接受后可在大纲中继续编辑。"
          workflow="generate_outline"
          buildPayload={(prompt) => ({
            scope: 'chapter',
            chapter_number: chapters.reduce((max, chapter) => Math.max(max, chapter.chapter_number), 0) + 1,
            prompt,
          })}
          saveLabel="创建章节"
          onSave={async (items) => {
            const nextNumber = chapters.reduce((max, chapter) => Math.max(max, chapter.chapter_number), 0) + 1;
            const item = items[0];
            const payload = (item?.payload ?? {}) as Record<string, unknown>;
            const goal = typeof payload.chapter_goal === 'string' ? payload.chapter_goal : item?.content ?? '';
            const keyEvents = typeof payload.key_events === 'string' ? `\n\n关键事件：${payload.key_events}` : '';
            await api.createChapter(projectId, {
              chapter_number: nextNumber,
              title: item?.title || `第 ${nextNumber} 章`,
              brief: `${goal}${keyEvents}`,
              summary: '',
              draft: '',
            });
            await reload();
          }}
          onClose={() => setAiOpen(false)}
        />
      )}

      {deleting && projectId && (
        <ConfirmDialog
          title="删除章节"
          danger
          confirmLabel="删除章节"
          message={<>将删除第 {deleting.chapter_number} 章「<b>{deleting.title || '未命名'}</b>」及其全部版本与正文。</>}
          onConfirm={() => {
            void api.deleteChapter(projectId, deleting.id).then(reload);
            setDeleting(null);
          }}
          onCancel={() => setDeleting(null)}
        />
      )}
    </div>
  );
}
