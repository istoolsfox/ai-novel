import { useState } from 'react';
import { useParams } from 'react-router-dom';
import { Plus, Pencil, Trash2, Clock } from 'lucide-react';
import { useRecords } from '../shell/useRecords';
import { GenericRecord } from '../api';

function eventTime(r: GenericRecord) {
  return (r.payload && typeof r.payload.event_time === 'string') ? r.payload.event_time : r.title;
}

export function Timeline() {
  const { projectId } = useParams();
  const { records, create, update, remove } = useRecords(projectId, 'timeline-events');
  const [editing, setEditing] = useState<{ id?: string; title: string; content: string }>({ title: '', content: '' });
  const [open, setOpen] = useState(false);
  const sorted = [...records].sort((a, b) => a.title.localeCompare(b.title, 'zh'));

  const save = async () => {
    if (!editing.title.trim()) return;
    const payload: Partial<GenericRecord> = { title: editing.title, category: 'timeline', content: editing.content, status: 'active' };
    if (editing.id) await update(editing.id, payload);
    else await create(payload);
    setOpen(false);
    setEditing({ title: '', content: '' });
  };

  return (
    <div>
      <div style={{ alignItems: 'center', display: 'flex', justifyContent: 'space-between' }}>
        <div>
          <h1>Timeline</h1>
          <p className="os-page-sub">事件顺序、因果与剧情节奏</p>
        </div>
        <button className="os-btn os-btn-primary" onClick={() => { setEditing({ title: '', content: '' }); setOpen(true); }}>
          <Plus size={15} /> Add Event
        </button>
      </div>

      <div style={{ overflowX: 'auto', padding: '1.5rem 0 0.5rem' }}>
        <div style={{ alignItems: 'center', display: 'flex', gap: '0', minWidth: 'max-content', position: 'relative' }}>
          <div style={{ position: 'absolute', top: '18px', left: '0', right: '0', height: '2px', background: 'var(--n-border)' }} />
          {sorted.map((r, i) => (
            <div key={r.id} style={{ alignItems: 'center', display: 'flex', flexDirection: 'column', gap: '0.5rem', minWidth: '130px', position: 'relative', zIndex: 1 }}>
              <div style={{ background: 'var(--ai-accent)', border: '3px solid var(--n-surface)', borderRadius: '50%', height: '16px', width: '16px' }} />
              <small style={{ color: 'var(--n-text-2)', textAlign: 'center' }}>{eventTime(r)}</small>
              <div style={{ alignItems: 'center', display: 'flex', gap: '0.3rem' }}>
                <button className="os-btn os-btn-ghost" style={{ fontSize: '0.78rem', padding: '0.15rem 0.3rem' }} onClick={() => { setEditing({ id: r.id, title: r.title, content: r.content }); setOpen(true); }}>{r.content || r.title}</button>
                <button className="os-icon-btn" title="删除" style={{ height: 24, width: 24 }} onClick={() => remove(r.id)}><Trash2 size={13} /></button>
              </div>
            </div>
          ))}
          {records.length === 0 && <div className="os-empty" style={{ position: 'static' }}>暂无时间线事件</div>}
        </div>
      </div>

      {open && (
        <div className="project-modal-backdrop" onClick={() => setOpen(false)}>
          <div className="project-modal" role="dialog" aria-label="编辑时间线事件" onClick={(e) => e.stopPropagation()}>
            <div className="project-modal-head">
              <strong>{editing.id ? '编辑事件' : '新增事件'}</strong>
              <button className="project-modal-close" onClick={() => setOpen(false)}>✕</button>
            </div>
            <div className="project-modal-body">
              <label><span>时间 / 标记</span><input value={editing.title} onChange={(e) => setEditing({ ...editing, title: e.target.value })} autoFocus placeholder="如：2025 / CH12" /></label>
              <label><span>事件</span><textarea value={editing.content} onChange={(e) => setEditing({ ...editing, content: e.target.value })} rows={3} /></label>
            </div>
            <div className="project-modal-actions">
              <span />
              <div className="project-modal-action-right">
                <button onClick={() => setOpen(false)}>取消</button>
                <button className="primary-action" onClick={() => void save()} disabled={!editing.title.trim()}>{editing.id ? '保存' : '创建'}</button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
