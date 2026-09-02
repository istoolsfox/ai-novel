import { useState } from 'react';
import { useParams } from 'react-router-dom';
import { History, Network, Pencil, Plus, Sparkles, Trash2 } from 'lucide-react';
import { GenericRecord } from '../api';
import { useRecords } from '../shell/useRecords';
import { ConfirmDialog, EmptyState, PageHeader } from '../ui/basics';
import { AIGenerateModal } from '../components/AIGenerateModal';
import { HistoryDrawer } from '../components/HistoryDrawer';
import { FieldDef, RecordFormModal } from '../components/RecordFormModal';

const RESOURCE = 'character-relationships';

const RELATION_TYPES = ['盟友', '爱人', '亲情', '师徒', '仇敌', '对手', '竞争', '上下级', '陌路'];

const RELATION_FIELDS: FieldDef[] = [
  { key: 'payload.source_character', label: '角色 A', required: true, placeholder: '角色名' },
  { key: 'payload.target_character', label: '角色 B', required: true, placeholder: '角色名' },
  { key: 'payload.relationship_type', label: '关系类型', type: 'select', options: RELATION_TYPES },
  { key: 'payload.strength', label: '关系强度（0-100）', type: 'range' },
  { key: 'payload.conflict', label: '张力 / 冲突', type: 'textarea', rows: 2, placeholder: '两人之间未解决的是什么？' },
  { key: 'payload.change_history', label: '关系变化', type: 'textarea', rows: 2, placeholder: '从什么变成什么？因什么事件？' },
];

type RelPayload = {
  source_character?: string;
  target_character?: string;
  relationship_type?: string;
  strength?: number | string;
  conflict?: string;
  change_history?: string;
};

function relPayload(record: GenericRecord): RelPayload {
  return (record.payload ?? {}) as RelPayload;
}

export function Relations() {
  const { projectId } = useParams();
  const { records, create, update, remove, reload } = useRecords(projectId, RESOURCE);
  const [formOpen, setFormOpen] = useState(false);
  const [editing, setEditing] = useState<GenericRecord | null>(null);
  const [aiOpen, setAiOpen] = useState(false);
  const [historyFor, setHistoryFor] = useState<GenericRecord | null>(null);
  const [deleting, setDeleting] = useState<GenericRecord | null>(null);

  const saveForm = async (values: Partial<GenericRecord>) => {
    const payload = (values.payload ?? {}) as RelPayload;
    const complete = {
      ...values,
      title: `${payload.source_character ?? ''} → ${payload.target_character ?? ''}`,
      content: `${payload.source_character ?? ''} → ${payload.target_character ?? ''}`,
      category: payload.relationship_type ?? '',
      status: 'active',
    };
    if (values.id) {
      await update(String(values.id), complete);
      return;
    }
    await create(complete);
  };

  return (
    <div className="page-inner wide">
      <PageHeader
        title="人物关系"
        sub="关系是剧情的发动机：记录同盟、冲突、亲疏与变化，AI 正文生成会引用这些设定。"
        actions={
          <>
            <button className="btn" onClick={() => { setEditing(null); setFormOpen(true); }}>
              <Plus size={14} /> 新建关系
            </button>
            <button className="btn btn-ai" onClick={() => setAiOpen(true)}>
              <Sparkles size={14} /> AI 梳理关系
            </button>
          </>
        }
      />

      {records.length === 0 ? (
        <EmptyState
          icon={<Network size={26} />}
          title="还没有人物关系"
          hint="先创建人物，再在这里把人物两两连接起来。"
          action={
            <button className="btn btn-ai" onClick={() => setAiOpen(true)}>
              <Sparkles size={14} /> AI 梳理关系
            </button>
          }
        />
      ) : (
        <div className="grid" style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))' }}>
          {records.map((record) => {
            const payload = relPayload(record);
            const strength = Number(payload.strength ?? 50);
            return (
              <article key={record.id} className="card" style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                <div className="row-flex">
                  <b style={{ fontFamily: 'var(--serif)', fontSize: 15.5, flex: 1 }}>
                    {payload.source_character || '?'} <span className="muted" style={{ fontWeight: 400 }}>与</span> {payload.target_character || '?'}
                  </b>
                  <button className="icon-btn" aria-label="编辑关系" onClick={() => { setEditing(record); setFormOpen(true); }}>
                    <Pencil size={13} />
                  </button>
                  <button className="icon-btn" aria-label="关系历史" onClick={() => setHistoryFor(record)}>
                    <History size={13} />
                  </button>
                  <button className="icon-btn" aria-label="删除关系" onClick={() => setDeleting(record)}>
                    <Trash2 size={13} />
                  </button>
                </div>
                <div className="row-flex">
                  <span className="badge accent">{payload.relationship_type || record.category || '关系'}</span>
                  <div className="progress grow"><span style={{ width: `${Math.max(0, Math.min(100, strength))}%` }} /></div>
                  <small className="muted" style={{ width: 34, textAlign: 'right' }}>{strength}%</small>
                </div>
                {payload.conflict && (
                  <p style={{ fontSize: 12.5, lineHeight: 1.7 }}>
                    <span className="muted">张力 · </span>{payload.conflict}
                  </p>
                )}
                {payload.change_history && (
                  <p className="muted" style={{ fontSize: 12.5, lineHeight: 1.7 }}>
                    <span>变化 · </span>{payload.change_history}
                  </p>
                )}
              </article>
            );
          })}
        </div>
      )}

      {formOpen && (
        <RecordFormModal
          modalTitle={editing ? '编辑关系' : '新建关系'}
          fields={RELATION_FIELDS}
          record={editing}
          extraValues={editing ? undefined : { payload: { relationship_type: '盟友', strength: '50' } }}
          onClose={() => setFormOpen(false)}
          onSave={saveForm}
        />
      )}

      {aiOpen && projectId && (
        <AIGenerateModal
          projectId={projectId}
          title="AI 梳理人物关系"
          intro="AI 会基于现有人物档案提出关系建议，保存后仍可修改。"
          workflow="extract_relationships"
          buildPayload={(prompt) => ({ prompt, content: prompt })}
          onSave={async (items) => {
            for (const item of items) {
              const payload = (item.payload ?? {}) as RelPayload;
              await create({
                title: `${payload.source_character ?? item.title} → ${payload.target_character ?? ''}`,
                category: payload.relationship_type ?? '',
                content: item.content,
                payload: payload as Record<string, unknown>,
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
          title="删除关系"
          danger
          confirmLabel="删除"
          message={<>将删除这条关系及其历史版本。</>}
          onConfirm={() => {
            void remove(deleting.id);
            setDeleting(null);
          }}
          onCancel={() => setDeleting(null)}
        />
      )}
    </div>
  );
}
