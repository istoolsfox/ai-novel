import { useState } from 'react';
import { useParams } from 'react-router-dom';
import { Plus, Pencil, Trash2, Globe } from 'lucide-react';
import { useRecords } from '../shell/useRecords';
import { GenericRecord } from '../api';

const CATEGORIES = ['Locations', 'Organizations', 'Companies', 'Families', 'Countries', 'Rules', 'Objects'];

export function World() {
  const { projectId } = useParams();
  const { records, create, update, remove } = useRecords(projectId, 'world-settings');
  const [editing, setEditing] = useState<{ id?: string; title: string; category: string; content: string }>({ title: '', category: 'Locations', content: '' });
  const [open, setOpen] = useState(false);

  const save = async () => {
    if (!editing.title.trim()) return;
    const payload: Partial<GenericRecord> = { title: editing.title, category: editing.category, content: editing.content, status: 'active' };
    if (editing.id) await update(editing.id, payload);
    else await create(payload);
    setOpen(false);
    setEditing({ title: '', category: 'Locations', content: '' });
  };

  return (
    <div>
      <div style={{ alignItems: 'center', display: 'flex', justifyContent: 'space-between' }}>
        <div>
          <h1>World</h1>
          <p className="os-page-sub">世界观实体：地点 / 组织 / 公司 / 家族 / 国家 / 规则 / 物品</p>
        </div>
        <button className="os-btn os-btn-primary" onClick={() => { setEditing({ title: '', category: 'Locations', content: '' }); setOpen(true); }}>
          <Plus size={15} /> Add Entity
        </button>
      </div>

      <div className="os-grid" style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(240px, 1fr))', marginTop: '0.5rem' }}>
        {CATEGORIES.filter((cat) => records.some((r) => r.category === cat)).map((cat) => (
          <section className="os-card" key={cat}>
            <div className="os-card-header"><strong>{cat}</strong><small>{records.filter((r) => r.category === cat).length}</small></div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.3rem', fontSize: '0.85rem' }}>
              {records.filter((r) => r.category === cat).map((r) => (
                <div key={r.id} style={{ alignItems: 'center', display: 'flex', gap: '0.4rem', padding: '0.3rem 0' }}>
                  <Globe size={14} style={{ color: 'var(--n-muted)' }} />
                  <button className="os-nav-item" style={{ flex: 1, padding: '0.1rem 0.2rem' }} onClick={() => { setEditing({ id: r.id, title: r.title, category: r.category, content: r.content }); setOpen(true); }}>
                    <span>{r.title}</span>
                  </button>
                  <button className="os-icon-btn" title="删除" onClick={() => remove(r.id)}><Trash2 size={14} /></button>
                </div>
              ))}
            </div>
          </section>
        ))}
        {records.length === 0 && <div className="os-empty">还没有世界观实体，点击上方 Add Entity。</div>}
      </div>

      {open && (
        <div className="project-modal-backdrop" onClick={() => setOpen(false)}>
          <div className="project-modal" style={{ maxWidth: '460px' }} role="dialog" aria-label="编辑世界观实体" onClick={(e) => e.stopPropagation()}>
            <div className="project-modal-head">
              <strong>{editing.id ? '编辑实体' : '新增实体'}</strong>
              <button className="project-modal-close" onClick={() => setOpen(false)}>✕</button>
            </div>
            <div className="project-modal-body">
              <label><span>名称</span><input value={editing.title} onChange={(e) => setEditing({ ...editing, title: e.target.value })} autoFocus /></label>
              <label>
                <span>类别</span>
                <select value={editing.category} onChange={(e) => setEditing({ ...editing, category: e.target.value })}>
                  {CATEGORIES.map((c) => <option key={c} value={c}>{c}</option>)}
                </select>
              </label>
              <label><span>说明</span><textarea value={editing.content} onChange={(e) => setEditing({ ...editing, content: e.target.value })} rows={4} /></label>
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
