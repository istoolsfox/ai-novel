import { useState } from 'react';
import { useParams } from 'react-router-dom';
import { Plus, Pencil, Trash2, Network, Sparkles } from 'lucide-react';
import { useRecords } from '../shell/useRecords';
import { GenericRecord } from '../api';

function relPayload(r: GenericRecord) {
  return {
    source: (r.payload?.source_character as string) ?? r.content?.split('→')[0]?.trim() ?? '',
    target: (r.payload?.target_character as string) ?? r.content?.split('→')[1]?.trim() ?? '',
    type: (r.payload?.relationship_type as string) ?? r.category ?? '朋友',
    strength: (r.payload?.strength as number) ?? 50,
  };
}

export function Relations() {
  const { projectId } = useParams();
  const { records, create, update, remove } = useRecords(projectId, 'character-relationships');
  const [editing, setEditing] = useState<{ id?: string; source: string; target: string; type: string; strength: number }>({ source: '', target: '', type: '朋友', strength: 50 });
  const [open, setOpen] = useState(false);

  const save = async () => {
    if (!editing.source.trim() || !editing.target.trim()) return;
    const payload: Partial<GenericRecord> = {
      title: `${editing.source} → ${editing.target}`,
      category: editing.type,
      content: `${editing.source} → ${editing.target}`,
      status: 'active',
      payload: { source_character: editing.source, target_character: editing.target, relationship_type: editing.type, strength: editing.strength },
    };
    if (editing.id) await update(editing.id, payload);
    else await create(payload);
    setOpen(false);
    setEditing({ source: '', target: '', type: '朋友', strength: 50 });
  };

  return (
    <div>
      <div style={{ alignItems: 'center', display: 'flex', justifyContent: 'space-between' }}>
        <div>
          <h1>Relations</h1>
          <p className="os-page-sub">人物关系、同盟、冲突与变化</p>
        </div>
        <div style={{ display: 'flex', gap: '0.5rem' }}>
          <button className="os-btn">Auto Layout</button>
          <button className="os-btn ai"><Sparkles size={14} /> AI Analyze</button>
          <button className="os-btn os-btn-primary" onClick={() => { setEditing({ source: '', target: '', type: '朋友', strength: 50 }); setOpen(true); }}>
            <Plus size={15} /> Add Relation
          </button>
        </div>
      </div>

      <div className="os-grid" style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(240px, 1fr))', marginTop: '0.5rem' }}>
        {records.map((r) => {
          const p = relPayload(r);
          return (
            <div className="os-card" key={r.id} style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
              <div style={{ alignItems: 'center', display: 'flex', gap: '0.4rem' }}>
                <Network size={15} style={{ color: 'var(--ai-accent)' }} />
                <strong style={{ flex: 1 }}>{p.source} ↔ {p.target}</strong>
                <button className="os-icon-btn" title="编辑" onClick={() => { setEditing({ id: r.id, ...p }); setOpen(true); }}><Pencil size={14} /></button>
                <button className="os-icon-btn" title="删除" onClick={() => remove(r.id)}><Trash2 size={14} /></button>
              </div>
              <span className={`os-badge ${p.type === 'Romance' ? 'editing' : 'done'}`}>{p.type}</span>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <div className="os-progress" style={{ flex: 1 }}><span style={{ width: `${p.strength}%` }} /></div>
                <small style={{ color: 'var(--n-text-2)' }}>{p.strength}%</small>
              </div>
            </div>
          );
        })}
        {records.length === 0 && <div className="os-empty">暂无关系，点击 Add Relation。</div>}
      </div>

      {open && (
        <div className="project-modal-backdrop" onClick={() => setOpen(false)}>
          <div className="project-modal" role="dialog" aria-label="编辑关系" onClick={(e) => e.stopPropagation()}>
            <div className="project-modal-head">
              <strong>{editing.id ? '编辑关系' : '新增关系'}</strong>
              <button className="project-modal-close" onClick={() => setOpen(false)}>✕</button>
            </div>
            <div className="project-modal-body">
              <label><span>角色 A</span><input value={editing.source} onChange={(e) => setEditing({ ...editing, source: e.target.value })} autoFocus /></label>
              <label><span>角色 B</span><input value={editing.target} onChange={(e) => setEditing({ ...editing, target: e.target.value })} /></label>
              <label>
                <span>关系类型</span>
                <select value={editing.type} onChange={(e) => setEditing({ ...editing, type: e.target.value })}>
                  {['朋友', '爱人', '仇敌', '盟友', 'Romance', 'Rival', 'Family', '同事'].map((t) => <option key={t} value={t}>{t}</option>)}
                </select>
              </label>
              <label>
                <span>强度 {editing.strength}%</span>
                <input type="range" min="0" max="100" value={editing.strength} onChange={(e) => setEditing({ ...editing, strength: Number(e.target.value) })} />
              </label>
            </div>
            <div className="project-modal-actions">
              <span />
              <div className="project-modal-action-right">
                <button onClick={() => setOpen(false)}>取消</button>
                <button className="primary-action" onClick={() => void save()} disabled={!editing.source.trim() || !editing.target.trim()}>{editing.id ? '保存' : '创建'}</button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
