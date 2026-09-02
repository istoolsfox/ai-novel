import { useParams } from 'react-router-dom';
import { Sparkles } from 'lucide-react';
import { useProjects, useChapters } from '../shell/useProject';

export function Characters() {
  const { projectId } = useParams();
  const { chapters } = useChapters(projectId);
  const { projects } = useProjects();
  const project = projects.find((p) => p.id === projectId);

  return (
    <div>
      <h1>Characters</h1>
      <p className="os-page-sub">{project?.title ?? '角色管理'} · 沉淀每个角色的设定、状态与弧线</p>
      <div className="os-grid" style={{ gridTemplateColumns: '280px 1fr' }}>
        <section className="os-card">
          <div className="os-card-header"><strong>角色列表</strong></div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.15rem', fontSize: '0.85rem' }}>
            <div className="os-nav-group-label">MAIN</div>
            {['林默', '苏晚', '顾辰'].map((n) => (
              <button key={n} className="os-nav-item">{n}</button>
            ))}
            <div className="os-nav-group-label" style={{ marginTop: '0.6rem' }}>SUPPORTING</div>
            {['沈妍', '周野', '李秘书'].map((n) => (
              <button key={n} className="os-nav-item">{n}</button>
            ))}
          </div>
        </section>
        <section className="os-card">
          <div className="os-card-header">
            <strong>林默</strong>
            <div style={{ display: 'flex', gap: '0.4rem' }}>
              <button className="os-btn">Edit</button>
              <button className="os-btn ai"><Sparkles size={14} /> AI</button>
            </div>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.8rem', fontSize: '0.85rem' }}>
            <small style={{ color: 'var(--n-text-2)' }}>Male · 28 · Protagonist</small>
            <Field label="Role" value="Business heir" />
            <Field label="Personality" value="Calm · Controlled · Possessive" />
            <Field label="Current State" value="Location: Shanghai · Emotion: Angry · Health: Injured" />
            <Field label="Goal" value="Protect Su Wan" />
            <Field label="Character Arc" value="Cold → Trust → Love → Sacrifice" />
          </div>
        </section>
      </div>
    </div>
  );
}

function Field({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <small style={{ color: 'var(--n-muted)', display: 'block', fontWeight: 700 }}>{label}</small>
      <span>{value}</span>
    </div>
  );
}
