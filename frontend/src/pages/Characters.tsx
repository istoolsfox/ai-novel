import { useState } from 'react';
import { useParams } from 'react-router-dom';
import { History, Pencil, Plus, Sparkles, Trash2, Users } from 'lucide-react';
import { GenericRecord } from '../api';
import { useRecords } from '../shell/useRecords';
import { ConfirmDialog, EmptyState, PageHeader } from '../ui/basics';
import { AIGenerateModal } from '../components/AIGenerateModal';
import { HistoryDrawer } from '../components/HistoryDrawer';
import { FieldDef, RecordFormModal } from '../components/RecordFormModal';
import { readableContent } from '../utils/text';

const RESOURCE = 'character-profiles';

const CHARACTER_FIELDS: FieldDef[] = [
  { key: 'title', label: '姓名', required: true, placeholder: '如：沈照夜' },
  { key: 'category', label: '定位', type: 'select', options: ['主角', '重要配角', '配角', '反派', '龙套'] },
  { key: 'payload.role', label: '身份 / 职业', placeholder: '如：前朝公主' },
  { key: 'payload.appearance', label: '外貌', type: 'textarea', rows: 2 },
  { key: 'payload.traits', label: '性格特质', placeholder: '冷静、警惕、重诺' },
  { key: 'payload.desire', label: '欲望（想要什么）', type: 'textarea', rows: 2 },
  { key: 'payload.fear', label: '恐惧（害怕什么）', type: 'textarea', rows: 2 },
  { key: 'payload.arc', label: '人物弧光', type: 'textarea', rows: 2 },
  { key: 'payload.voice', label: '语言风格' },
  { key: 'content', label: '简介 / 备注', type: 'textarea', rows: 3 },
];

export function Characters() {
  const { projectId } = useParams();
  const { records, create, update, remove, reload } = useRecords(projectId, RESOURCE);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [formOpen, setFormOpen] = useState(false);
  const [editing, setEditing] = useState<GenericRecord | null>(null);
  const [aiOpen, setAiOpen] = useState(false);
  const [historyFor, setHistoryFor] = useState<GenericRecord | null>(null);
  const [deleting, setDeleting] = useState<GenericRecord | null>(null);

  const selected = records.find((item) => item.id === selectedId) ?? records[0] ?? null;
  const payload = (selected?.payload ?? {}) as Record<string, unknown>;

  const detailRows: Array<{ label: string; value: string }> = selected
    ? [
        { label: '定位', value: str(selected.category) },
        { label: '身份 / 职业', value: str(payload.role) },
        { label: '外貌', value: str(payload.appearance) },
        { label: '性格特质', value: str(payload.traits) },
        { label: '欲望', value: str(payload.desire) },
        { label: '恐惧', value: str(payload.fear) },
        { label: '人物弧光', value: str(payload.arc) },
        { label: '语言风格', value: str(payload.voice) },
      ].filter((row) => row.value)
    : [];

  const saveForm = async (values: Partial<GenericRecord>) => {
    if (values.id) {
      await update(String(values.id), values);
      return;
    }
    const created = await create(values);
    if (created) setSelectedId(created.id);
  };

  return (
    <div className="page-inner wide">
      <PageHeader
        title="人物"
        sub="角色的身份、欲望、恐惧与弧光——AI 生成后可逐项修改，每次修改都会保留版本。"
        actions={
          <>
            <button className="btn" onClick={() => { setEditing(null); setFormOpen(true); }}>
              <Plus size={14} /> 新建人物
            </button>
            <button className="btn btn-ai" onClick={() => setAiOpen(true)}>
              <Sparkles size={14} /> AI 生成人物
            </button>
          </>
        }
      />

      {records.length === 0 ? (
        <EmptyState
          icon={<Users size={26} />}
          title="还没有人物"
          hint="手动创建，或让 AI 根据故事概念生成一组人物。"
          action={
            <button className="btn btn-ai" onClick={() => setAiOpen(true)}>
              <Sparkles size={14} /> AI 生成人物
            </button>
          }
        />
      ) : (
        <div className="master-detail">
          <aside className="card" style={{ padding: 14 }}>
            <div className="card-head" style={{ marginBottom: 8 }}>
              <b>人物列表</b>
              <small>{records.length}</small>
            </div>
            <div className="master-list">
              {records.map((record) => {
                const recordPayload = (record.payload ?? {}) as Record<string, unknown>;
                return (
                  <button
                    key={record.id}
                    className={selected?.id === record.id ? 'master-item active' : 'master-item'}
                    onClick={() => setSelectedId(record.id)}
                  >
                    <span className="avatar">{str(record.title).slice(0, 1) || '人'}</span>
                    <span className="grow">
                      <b>{record.title}</b>
                      <small>{str(recordPayload.role) || str(record.category) || '人物'}</small>
                    </span>
                  </button>
                );
              })}
            </div>
          </aside>

          {selected && (
            <section className="card">
              <div className="card-head">
                <div className="row-flex">
                  <span className="avatar accent" style={{ width: 38, height: 38, fontSize: 17 }}>
                    {str(selected.title).slice(0, 1) || '人'}
                  </span>
                  <span>
                    <b style={{ fontFamily: 'var(--serif)', fontSize: 18 }}>{selected.title}</b>
                    <small className="muted" style={{ display: 'block', fontSize: 11.5 }}>
                      {str(payload.role) || '人物档案'}
                    </small>
                  </span>
                </div>
                <div className="row-flex">
                  <button className="btn" onClick={() => { setEditing(selected); setFormOpen(true); }}>
                    <Pencil size={13} /> 编辑
                  </button>
                  <button className="btn" onClick={() => setHistoryFor(selected)}>
                    <History size={13} /> 历史
                  </button>
                  <button className="icon-btn" aria-label="删除人物" onClick={() => setDeleting(selected)}>
                    <Trash2 size={14} />
                  </button>
                </div>
              </div>

              {readableContent(selected.content) && (
                <p style={{ fontSize: 13.5, lineHeight: 1.8, color: 'var(--ink-2)', marginBottom: 18, whiteSpace: 'pre-line' }}>
                  {readableContent(selected.content)}
                </p>
              )}

              {detailRows.length > 0 ? (
                <dl className="kv">
                  {detailRows.map((row) => (
                    <div className="kv-row" key={row.label}>
                      <dt>{row.label}</dt>
                      <dd>{row.value}</dd>
                    </div>
                  ))}
                </dl>
              ) : (
                <EmptyState title="此档案还没有结构化字段" hint="点击「编辑」补充身份、欲望、恐惧与人物弧光，AI 生成正文时会引用这些设定。" />
              )}
            </section>
          )}
        </div>
      )}

      {formOpen && (
        <RecordFormModal
          modalTitle={editing ? `编辑人物 · ${editing.title}` : '新建人物'}
          fields={CHARACTER_FIELDS}
          record={editing}
          onClose={() => setFormOpen(false)}
          onSave={saveForm}
        />
      )}

      {aiOpen && projectId && (
        <AIGenerateModal
          projectId={projectId}
          title="AI 生成人物"
          intro="AI 会参考现有人物避免重复。生成结果保存后仍可自由修改、回退。"
          workflow="generate_characters"
          buildPayload={(prompt) => ({
            prompt,
            mode: 'new',
            existing_characters: records.map((record) => ({ title: record.title, payload: record.payload })),
          })}
          onSave={async (items) => {
            for (const item of items) {
              const values = item.payload ?? { name: item.title };
              await create({
                title: item.title,
                category: str((values as Record<string, unknown>).role) || '配角',
                content: item.content,
                payload: values,
                status: 'active',
              });
            }
            await reload();
          }}
          onClose={() => setAiOpen(false)}
        />
      )}

      {historyFor && projectId && (
        <HistoryDrawer
          projectId={projectId}
          resource={RESOURCE}
          record={historyFor}
          onClose={() => setHistoryFor(null)}
          onRestored={(updated) => {
            void reload();
            setHistoryFor((prev) => (prev ? { ...prev, ...updated } : prev));
          }}
        />
      )}

      {deleting && (
        <ConfirmDialog
          title="删除人物"
          danger
          confirmLabel="删除"
          message={<>将删除人物「<b>{deleting.title}</b>」及其全部历史版本。</>}
          onConfirm={() => {
            void remove(deleting.id);
            setDeleting(null);
            if (selected?.id === deleting.id) setSelectedId(null);
          }}
          onCancel={() => setDeleting(null)}
        />
      )}
    </div>
  );
}

function str(value: unknown): string {
  return typeof value === 'string' ? value : '';
}
