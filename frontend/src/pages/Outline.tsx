import { useMemo, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { BookOpen, Feather, Layers, Map, Pencil, Plus, Sparkles, Trash2 } from 'lucide-react';
import { Chapter, GenericRecord } from '../api';
import { useChapters } from '../shell/useProject';
import { useRecords } from '../shell/useRecords';
import { useWorkspace } from '../shell/workspace';
import { ConfirmDialog, EmptyState, Modal, PageHeader } from '../ui/basics';
import { AIGenerateModal } from '../components/AIGenerateModal';
import { FieldDef, RecordFormModal } from '../components/RecordFormModal';
import { api } from '../api';

type ChapterForm = { id?: string; title: string; brief: string; summary: string };
type TabKey = 'book' | 'volume' | 'chapter';

const TABS: Array<{ key: TabKey; label: string; icon: typeof BookOpen }> = [
  { key: 'book', label: '全书大纲', icon: BookOpen },
  { key: 'volume', label: '卷大纲', icon: Layers },
  { key: 'chapter', label: '章节大纲', icon: Map },
];

const BOOK_FIELDS: FieldDef[] = [
  { key: 'title', label: '名称', required: true },
  { key: 'payload.premise', label: '一句话故事', type: 'textarea', rows: 2 },
  { key: 'payload.core_conflict', label: '核心冲突', type: 'textarea', rows: 2 },
  { key: 'payload.main_arc', label: '主线走向（起承转合）', type: 'textarea', rows: 4 },
  { key: 'payload.ending_direction', label: '结局方向', type: 'textarea', rows: 2 },
  { key: 'content', label: '补充说明', type: 'textarea', rows: 3 },
];

const VOLUME_FIELDS: FieldDef[] = [
  { key: 'title', label: '卷名', required: true, placeholder: '如：第一卷 · 灰雾之城' },
  { key: 'payload.volume_number', label: '卷号' },
  { key: 'payload.start_chapter', label: '起始章号' },
  { key: 'payload.end_chapter', label: '结束章号' },
  { key: 'payload.volume_goal', label: '本卷目标', type: 'textarea', rows: 3 },
  { key: 'payload.key_turns', label: '关键转折', type: 'textarea', rows: 3 },
  { key: 'payload.ending_state', label: '卷末状态', type: 'textarea', rows: 2 },
];

function str(value: unknown): string {
  return typeof value === 'string' ? value : '';
}

function numberOf(value: unknown, fallback: number): number {
  const parsed = Number(value);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : fallback;
}

export function Outline() {
  const navigate = useNavigate();
  const { projectId } = useParams();
  const { project } = useWorkspace();
  const { chapters, reload } = useChapters(projectId);
  const { records: outlineRecords, create, update, remove: removeRecord, reload: reloadOutlines } = useRecords(projectId, 'outlines');
  const [tab, setTab] = useState<TabKey>('book');
  const [form, setForm] = useState<ChapterForm | null>(null);
  const [saving, setSaving] = useState(false);
  const [deleting, setDeleting] = useState<Chapter | null>(null);
  const [aiOpen, setAiOpen] = useState(false);
  const [bookFormOpen, setBookFormOpen] = useState(false);
  const [editingBook, setEditingBook] = useState<GenericRecord | null>(null);
  const [volumeFormOpen, setVolumeFormOpen] = useState(false);
  const [editingVolume, setEditingVolume] = useState<GenericRecord | null>(null);
  const [deletingVolume, setDeletingVolume] = useState<GenericRecord | null>(null);

  const sorted = [...chapters].sort((left, right) => left.chapter_number - right.chapter_number);
  const totalWords = chapters.reduce((sum, chapter) => sum + (chapter.draft?.length ?? 0), 0);
  const nextChapterNumber = chapters.reduce((max, chapter) => Math.max(max, chapter.chapter_number), 0) + 1;

  const bookOutline = outlineRecords.find((record) => str(record.category) === 'book_outline') ?? null;
  const volumes = useMemo(
    () =>
      outlineRecords
        .filter((record) => str(record.category) === 'volume_outline')
        .sort((left, right) => {
          const leftPayload = (left.payload ?? {}) as Record<string, unknown>;
          const rightPayload = (right.payload ?? {}) as Record<string, unknown>;
          return numberOf(leftPayload.start_chapter, 9999) - numberOf(rightPayload.start_chapter, 9999);
        }),
    [outlineRecords],
  );

  const volumeOfChapter = (chapter: Chapter): GenericRecord | null =>
    volumes.find((volume) => {
      const payload = (volume.payload ?? {}) as Record<string, unknown>;
      const start = numberOf(payload.start_chapter, 1);
      const end = numberOf(payload.end_chapter, start);
      return chapter.chapter_number >= start && chapter.chapter_number <= end;
    }) ?? null;

  const openCreateForm = () => setForm({ title: `第 ${nextChapterNumber} 章`, brief: '', summary: '' });

  const saveChapter = async () => {
    if (!form || !projectId || saving) return;
    setSaving(true);
    try {
      if (form.id) {
        await api.updateChapter(projectId, form.id, { title: form.title, brief: form.brief, summary: form.summary });
      } else {
        await api.createChapter(projectId, {
          chapter_number: nextChapterNumber,
          title: form.title || `第 ${nextChapterNumber} 章`,
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

  const saveBookOutline = async (values: Partial<GenericRecord>) => {
    if (values.id) {
      await update(String(values.id), values);
      return;
    }
    await create({ ...values, category: 'book_outline', status: 'active' });
  };

  const saveVolumeOutline = async (values: Partial<GenericRecord>) => {
    const payload = (values.payload ?? {}) as Record<string, unknown>;
    const normalized: Partial<GenericRecord> = {
      ...values,
      category: 'volume_outline',
      status: 'active',
      payload: {
        ...payload,
        volume_number: numberOf(payload.volume_number, volumes.length + 1),
        start_chapter: numberOf(payload.start_chapter, 1),
        end_chapter: numberOf(payload.end_chapter, numberOf(payload.start_chapter, 1)),
      },
    };
    if (values.id) {
      await update(String(values.id), normalized);
      return;
    }
    await create(normalized);
  };

  const nextVolumeNumber = volumes.length + 1;
  const nextVolumeStart = (() => {
    const last = volumes[volumes.length - 1];
    const lastPayload = (last?.payload ?? {}) as Record<string, unknown>;
    return last ? numberOf(lastPayload.end_chapter, 0) + 1 : 1;
  })();

  return (
    <div className="page-inner wide">
      <PageHeader
        title="大纲"
        sub={project ? `${project.title} · ${chapters.length} 章 · 共 ${totalWords.toLocaleString()} 字` : '全书 → 卷 → 章，逐层拆解故事'}
      />

      <div className="row-flex" style={{ gap: 8, marginBottom: 16 }}>
        {TABS.map((item) => (
          <button
            key={item.key}
            className={tab === item.key ? 'btn btn-primary' : 'btn'}
            onClick={() => setTab(item.key)}
          >
            <item.icon size={14} /> {item.label}
            {item.key === 'volume' && volumes.length > 0 ? <small style={{ marginLeft: 4 }}>{volumes.length}</small> : null}
          </button>
        ))}
      </div>

      {tab === 'book' && (
        bookOutline ? (
          <section className="card" style={{ padding: 20, maxWidth: 760 }}>
            <div className="card-head">
              <b style={{ fontFamily: 'var(--serif)', fontSize: 17 }}>{bookOutline.title || '全书大纲'}</b>
              <div className="row-flex">
                <button className="btn" onClick={() => { setEditingBook(bookOutline); setBookFormOpen(true); }}>
                  <Pencil size={13} /> 编辑
                </button>
              </div>
            </div>
            {(() => {
              const payload = (bookOutline.payload ?? {}) as Record<string, unknown>;
              const rows = [
                { label: '一句话故事', value: str(payload.premise) },
                { label: '核心冲突', value: str(payload.core_conflict) },
                { label: '主线走向', value: str(payload.main_arc) },
                { label: '结局方向', value: str(payload.ending_direction) },
              ].filter((row) => row.value);
              const extra = str(bookOutline.content);
              return (
                <>
                  {rows.length > 0 ? (
                    <dl className="kv">
                      {rows.map((row) => (
                        <div className="kv-row" key={row.label}>
                          <dt>{row.label}</dt>
                          <dd style={{ whiteSpace: 'pre-line' }}>{row.value}</dd>
                        </div>
                      ))}
                    </dl>
                  ) : (
                    <p style={{ fontSize: 13.5, lineHeight: 1.8, color: 'var(--ink-2)', whiteSpace: 'pre-line' }}>{extra || '暂无内容'}</p>
                  )}
                  {rows.length > 0 && extra && extra !== rows.map((row) => row.value).join('\n') && (
                    <p style={{ fontSize: 13, lineHeight: 1.8, color: 'var(--ink-2)', marginTop: 14, whiteSpace: 'pre-line' }}>{extra}</p>
                  )}
                </>
              );
            })()}
          </section>
        ) : (
          <EmptyState
            icon={<BookOpen size={26} />}
            title="还没有全书大纲"
            hint="先用一段话定下核心冲突与主线走向，卷和章都从这里拆出来。"
            action={
              <div className="row-flex" style={{ gap: 8 }}>
                <button className="btn" onClick={() => { setEditingBook(null); setBookFormOpen(true); }}>
                  <Plus size={14} /> 手动创建
                </button>
                {projectId && (
                  <button className="btn btn-ai" onClick={() => setAiOpen(true)}>
                    <Sparkles size={14} /> AI 生成全书大纲
                  </button>
                )}
              </div>
            }
          />
        )
      )}

      {tab === 'volume' && (
        volumes.length === 0 ? (
          <EmptyState
            icon={<Layers size={26} />}
            title="还没有卷大纲"
            hint="把主线切成几卷：每卷有自己的目标、转折和卷末状态。"
            action={
              <>
                <button className="btn" onClick={() => { setEditingVolume(null); setVolumeFormOpen(true); }}>
                  <Plus size={14} /> 新建卷
                </button>
                {projectId && (
                  <button className="btn btn-ai" onClick={() => setAiOpen(true)}>
                    <Sparkles size={14} /> AI 生成卷大纲
                  </button>
                )}
              </>
            }
          />
        ) : (
          <div className="grid" style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))' }}>
            {volumes.map((volume) => {
              const payload = (volume.payload ?? {}) as Record<string, unknown>;
              const start = numberOf(payload.start_chapter, 1);
              const end = numberOf(payload.end_chapter, start);
              const chapterCount = sorted.filter((chapter) => chapter.chapter_number >= start && chapter.chapter_number <= end).length;
              return (
                <article key={volume.id} className="card" style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                  <div className="row-flex">
                    <span className="badge accent">第 {numberOf(payload.volume_number, 1)} 卷</span>
                    <span className="muted" style={{ fontSize: 12 }}>CH {start}–{end} · {chapterCount} 章</span>
                    <span className="spacer" style={{ flex: 1 }} />
                    <button className="icon-btn" aria-label="编辑卷" onClick={() => { setEditingVolume(volume); setVolumeFormOpen(true); }}>
                      <Pencil size={13} />
                    </button>
                    <button className="icon-btn" aria-label="删除卷" onClick={() => setDeletingVolume(volume)}>
                      <Trash2 size={13} />
                    </button>
                  </div>
                  <b style={{ fontFamily: 'var(--serif)', fontSize: 15.5 }}>{volume.title || '未命名卷'}</b>
                  <p className="muted" style={{ fontSize: 12.5, lineHeight: 1.7, flex: 1, whiteSpace: 'pre-line' }}>
                    {str(payload.volume_goal) || volume.content || '暂无本卷目标'}
                  </p>
                  {str(payload.key_turns) && (
                    <p className="muted" style={{ fontSize: 12, lineHeight: 1.7, whiteSpace: 'pre-line' }}>
                      <span style={{ fontWeight: 700 }}>转折 · </span>{str(payload.key_turns)}
                    </p>
                  )}
                </article>
              );
            })}
            <div style={{ display: 'flex', gap: 8, alignItems: 'center', justifyContent: 'center', border: '1px dashed var(--line-strong)', borderRadius: 10, minHeight: 120 }}>
              <button className="btn" onClick={() => { setEditingVolume(null); setVolumeFormOpen(true); }}>
                <Plus size={14} /> 新建卷
              </button>
              {projectId && (
                <button className="btn btn-ai" onClick={() => setAiOpen(true)}>
                  <Sparkles size={14} /> AI 生成
                </button>
              )}
            </div>
          </div>
        )
      )}

      {tab === 'chapter' && (
        sorted.length === 0 ? (
          <EmptyState
            icon={<Map size={26} />}
            title="还没有章节"
            hint="手动创建章节，或让 AI 根据人物与世界观生成第一章大纲。"
            action={
              <button className="btn" onClick={openCreateForm}>
                <Plus size={14} /> 新建章节
              </button>
            }
          />
        ) : (
          (() => {
            const grouped = sorted.reduce<Array<{ label: string; chapters: Chapter[] }>>((groups, chapter) => {
              const volume = volumeOfChapter(chapter);
              const label = volume ? volume.title || `第 ${numberOf((volume.payload as Record<string, unknown>).volume_number, 1)} 卷` : '未分卷';
              const last = groups[groups.length - 1];
              if (last && last.label === label) last.chapters.push(chapter);
              else groups.push({ label, chapters: [chapter] });
              return groups;
            }, []);
            return (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 22 }}>
                {grouped.map((group) => (
                  <section key={group.label}>
                    <h2 className="section-title" style={{ marginBottom: 10 }}>
                      {group.label} <small>{group.chapters.length} 章</small>
                    </h2>
                    <div className="grid" style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))' }}>
                      {group.chapters.map((chapter) => (
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
                          <b
                            style={{ fontFamily: 'var(--serif)', fontSize: 15.5, cursor: 'pointer' }}
                            title="点击编辑本章梗概"
                            onClick={() => setForm({ id: chapter.id, title: chapter.title, brief: chapter.brief, summary: chapter.summary })}
                          >
                            {chapter.title || '未命名章'}
                          </b>
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
                  </section>
                ))}
              </div>
            );
          })()
        )
      )}

      {tab === 'chapter' && sorted.length > 0 && (
        <div className="row-flex" style={{ marginTop: 18, gap: 8 }}>
          <button className="btn" onClick={openCreateForm}>
            <Plus size={14} /> 新建章节
          </button>
          <button className="btn btn-ai" onClick={() => setAiOpen(true)}>
            <Sparkles size={14} /> AI 生成章节
          </button>
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

      {bookFormOpen && (
        <RecordFormModal
          modalTitle={editingBook ? '编辑全书大纲' : '新建全书大纲'}
          fields={BOOK_FIELDS}
          record={editingBook}
          extraValues={editingBook ? undefined : { title: '全书大纲' }}
          onClose={() => setBookFormOpen(false)}
          onSave={saveBookOutline}
        />
      )}

      {volumeFormOpen && (
        <RecordFormModal
          modalTitle={editingVolume ? '编辑卷大纲' : '新建卷大纲'}
          fields={VOLUME_FIELDS}
          record={editingVolume}
          extraValues={
            editingVolume
              ? undefined
              : {
                  title: `第 ${nextVolumeNumber} 卷`,
                  payload: { volume_number: String(nextVolumeNumber), start_chapter: String(nextVolumeStart), end_chapter: String(nextVolumeStart + 9) },
                }
          }
          onClose={() => setVolumeFormOpen(false)}
          onSave={saveVolumeOutline}
        />
      )}

      {aiOpen && projectId && (
        <AIGenerateModal
          projectId={projectId}
          title={tab === 'book' ? 'AI 生成全书大纲' : tab === 'volume' ? 'AI 生成卷大纲' : 'AI 生成新章节'}
          intro={
            tab === 'book'
              ? 'AI 会基于故事概念与现有人物、世界观，生成统摄全书的总大纲。'
              : tab === 'volume'
                ? 'AI 会承接全书大纲与已有卷，生成本卷的目标、转折与卷末状态。'
                : 'AI 会基于现有人物、世界观和最近章节生成新的一章梗概并创建章节。'
          }
          workflow={tab === 'book' ? 'generate_book_outline' : tab === 'volume' ? 'generate_volume_outline' : 'generate_outline'}
          buildPayload={(prompt) => {
            if (tab === 'book') return { prompt };
            if (tab === 'volume') {
              return {
                prompt,
                volume_number: nextVolumeNumber,
                start_chapter: nextVolumeStart,
                end_chapter: nextVolumeStart + 9,
              };
            }
            return {
              scope: 'chapter',
              chapter_number: nextChapterNumber,
              prompt,
            };
          }}
          saveLabel={tab === 'book' ? '保存全书大纲' : tab === 'volume' ? '保存卷大纲' : '创建章节'}
          onSave={async (items) => {
            const item = items[0];
            const payload = (item?.payload ?? {}) as Record<string, unknown>;
            if (tab === 'book') {
              const values = {
                title: '全书大纲',
                category: 'book_outline',
                content: item?.content ?? '',
                payload,
                status: 'active',
              };
              if (bookOutline) await update(bookOutline.id, { id: bookOutline.id, ...values });
              else await create(values);
              await reloadOutlines();
              setTab('book');
              return;
            }
            if (tab === 'volume') {
              await create({
                title: item?.title || `第 ${nextVolumeNumber} 卷大纲`,
                category: 'volume_outline',
                content: item?.content ?? '',
                payload: {
                  ...payload,
                  volume_number: numberOf(payload.volume_number, nextVolumeNumber),
                  start_chapter: numberOf(payload.start_chapter, nextVolumeStart),
                  end_chapter: numberOf(payload.end_chapter, nextVolumeStart + 9),
                },
                status: 'active',
              });
              await reloadOutlines();
              setTab('volume');
              return;
            }
            const goal = typeof payload.chapter_goal === 'string' ? payload.chapter_goal : item?.content ?? '';
            const keyEvents = typeof payload.key_events === 'string' ? `\n\n关键事件：${payload.key_events}` : '';
            await api.createChapter(projectId, {
              chapter_number: nextChapterNumber,
              title: item?.title || `第 ${nextChapterNumber} 章`,
              brief: `${goal}${keyEvents}`,
              summary: '',
              draft: '',
            });
            await reload();
            setTab('chapter');
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

      {deletingVolume && (
        <ConfirmDialog
          title="删除卷大纲"
          danger
          confirmLabel="删除"
          message={<>将删除「<b>{deletingVolume.title || '未命名卷'}</b>」。章节正文不受影响，但对应章号会回到未分卷。</>}
          onConfirm={() => {
            void removeRecord(deletingVolume.id).then(reloadOutlines);
            setDeletingVolume(null);
          }}
          onCancel={() => setDeletingVolume(null)}
        />
      )}
    </div>
  );
}
