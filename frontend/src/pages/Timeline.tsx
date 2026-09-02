import { useState } from 'react';
import { useParams } from 'react-router-dom';
import { BookMarked, History, Pencil, Plus, Trash2 } from 'lucide-react';
import { GenericRecord } from '../api';
import { useRecords } from '../shell/useRecords';
import { ConfirmDialog, EmptyState, PageHeader } from '../ui/basics';
import { HistoryDrawer } from '../components/HistoryDrawer';
import { FieldDef, RecordFormModal } from '../components/RecordFormModal';

const RESOURCE = 'timeline-events';

const EVENT_FIELDS: FieldDef[] = [
  { key: 'title', label: '时间标记', required: true, placeholder: '如：元年冬 / 第 12 章夜 / 三年后' },
  { key: 'content', label: '事件', type: 'textarea', rows: 3, required: true, placeholder: '发生了什么？' },
  { key: 'payload.consequence', label: '后果 / 影响', type: 'textarea', rows: 2, placeholder: '这件事如何影响后续剧情？' },
];

export function Timeline() {
  const { projectId } = useParams();
  const { records, create, update, remove, reload } = useRecords(projectId, RESOURCE);
  const [formOpen, setFormOpen] = useState(false);
  const [editing, setEditing] = useState<GenericRecord | null>(null);
  const [historyFor, setHistoryFor] = useState<GenericRecord | null>(null);
  const [deleting, setDeleting] = useState<GenericRecord | null>(null);

  const sorted = [...records].sort((left, right) => left.title.localeCompare(right.title, 'zh'));

  return (
    <div className="page-inner">
      <PageHeader
        title="时间线"
        sub="事件顺序与因果链。时间标记按字典序排列，建议使用「第 N 章」或「卷一章名」作为前缀。"
        actions={
          <button className="btn btn-primary" onClick={() => { setEditing(null); setFormOpen(true); }}>
            <Plus size={14} /> 新建事件
          </button>
        }
      />

      {sorted.length === 0 ? (
        <EmptyState
          icon={<BookMarked size={26} />}
          title="还没有时间线事件"
          hint="把关键事件按顺序排好，AI 生成正文时会参考因果链，避免前后矛盾。"
        />
      ) : (
        <div className="timeline" style={{ marginTop: 8 }}>
          {sorted.map((record, index) => {
            const consequence = typeof record.payload?.consequence === 'string' ? record.payload.consequence : '';
            return (
              <div className="timeline-item" key={record.id}>
                <div className="timeline-when">{record.title}</div>
                <div className="timeline-axis">
                  <span className="timeline-dot" />
                  {index < sorted.length - 1 && <span className="timeline-line" />}
                </div>
                <article className="card timeline-card">
                  <div className="row-flex">
                    <b style={{ flex: 1, fontSize: 13.5 }}>{record.content?.split('\n')[0] || '（无内容）'}</b>
                    <button className="icon-btn" aria-label="编辑事件" onClick={() => { setEditing(record); setFormOpen(true); }}>
                      <Pencil size={13} />
                    </button>
                    <button className="icon-btn" aria-label="事件历史" onClick={() => setHistoryFor(record)}>
                      <History size={13} />
                    </button>
                    <button className="icon-btn" aria-label="删除事件" onClick={() => setDeleting(record)}>
                      <Trash2 size={13} />
                    </button>
                  </div>
                  {record.content?.includes('\n') && (
                    <p className="muted" style={{ fontSize: 12.5, lineHeight: 1.75, marginTop: 8, whiteSpace: 'pre-wrap' }}>
                      {record.content.split('\n').slice(1).join('\n').trim()}
                    </p>
                  )}
                  {consequence && (
                    <p style={{ fontSize: 12.5, lineHeight: 1.75, marginTop: 8 }}>
                      <span className="badge warn" style={{ marginRight: 8 }}>后果</span>
                      {consequence}
                    </p>
                  )}
                </article>
              </div>
            );
          })}
        </div>
      )}

      {formOpen && (
        <RecordFormModal
          modalTitle={editing ? '编辑事件' : '新建事件'}
          fields={EVENT_FIELDS}
          record={editing}
          onClose={() => setFormOpen(false)}
          onSave={async (values) => {
            const payload = { ...(values.payload ?? {}) };
            if (values.id) await update(String(values.id), { ...values, category: 'timeline', status: 'active', payload });
            else await create({ ...values, category: 'timeline', status: 'active' });
          }}
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
          title="删除事件"
          danger
          confirmLabel="删除"
          message={<>将删除事件「<b>{deleting.title}</b>」及其历史版本。</>}
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
