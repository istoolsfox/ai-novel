import { useNavigate, useParams } from 'react-router-dom';
import { Sparkles, Users, Globe, Map, TriangleAlert, CheckCircle2, ArrowLeft } from 'lucide-react';
import { useChapters, useProject } from '../shell/useProject';

export function ProjectOverview() {
  const { projectId } = useParams();
  const navigate = useNavigate();
  const { project } = useProject(projectId);
  const { chapters } = useChapters(projectId);
  const total = project?.target_chapter_count ?? 0;
  const pct = total ? Math.min(100, Math.round((chapters.length / total) * 100)) : 0;

  return (
    <div>
      <button className="os-btn os-btn-ghost" onClick={() => navigate('/projects')} style={{ marginBottom: '1rem' }}>
        <ArrowLeft size={15} /> Projects
      </button>
      <h1>{project?.title ?? '未命名项目'}</h1>
      <p className="os-page-sub">{project?.genre || 'Novel'} · {project?.topic || ''}</p>
      <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1.5rem' }}>
        <button className="os-btn os-btn-primary" onClick={() => navigate(`/projects/${projectId}/writing`)}>Continue Writing</button>
        <button className="os-btn" onClick={() => navigate(`/projects/${projectId}/ai`)}>AI Create</button>
      </div>

      <div className="os-grid" style={{ gridTemplateColumns: '1fr 1fr' }}>
        <section className="os-card">
          <div className="os-card-header"><strong>Story Progress</strong><small>{pct}%</small></div>
          <div className="os-progress" style={{ marginBottom: '0.5rem' }}><span style={{ width: `${pct}%` }} /></div>
          <small style={{ color: 'var(--n-text-2)' }}>{chapters.length} / {total} Chapters</small>
        </section>

        <section className="os-card">
          <div className="os-card-header"><strong>Four Metrics</strong></div>
          <div className="os-grid" style={{ gridTemplateColumns: 'repeat(2, minmax(0,1fr))', gap: '0.6rem' }}>
            <div><Users size={16} /><small>Characters<br /><strong style={{ fontSize: '1.1rem' }}>12</strong></small></div>
            <div><Globe size={16} /><small>World<br /><strong style={{ fontSize: '1.1rem' }}>34</strong></small></div>
            <div><Map size={16} /><small>Plotlines<br /><strong style={{ fontSize: '1.1rem' }}>4</strong></small></div>
            <div><Sparkles size={16} /><small>Foreshadowings<br /><strong style={{ fontSize: '1.1rem' }}>17</strong></small></div>
          </div>
        </section>
      </div>

      <div className="os-grid" style={{ gridTemplateColumns: '1fr 1fr', marginTop: '1rem' }}>
        <section className="os-card">
          <div className="os-card-header"><strong>Recent Chapters</strong></div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.2rem', fontSize: '0.84rem' }}>
            {chapters.slice(-6).reverse().map((ch) => (
              <div key={ch.id} style={{ alignItems: 'center', display: 'flex', gap: '0.6rem', padding: '0.3rem 0' }}>
                <span style={{ color: 'var(--n-muted)', width: '2rem' }}>{String(ch.chapter_number).padStart(2, '0')}</span>
                <span style={{ flex: 1 }}>{ch.title || '未命名'}</span>
                <span className={`os-badge ${ch.status === 'final' ? 'done' : 'editing'}`}>{ch.status === 'final' ? 'Completed' : 'Editing'}</span>
              </div>
            ))}
            {chapters.length === 0 && <div className="os-empty">暂无章节</div>}
          </div>
        </section>

        <section className="os-card">
          <div className="os-card-header"><strong>Story Health</strong></div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', fontSize: '0.8rem' }}>
            <Row label="Character Consistency" value={94} />
            <Row label="Timeline Consistency" value={98} />
            <Row label="Plot Continuity" value={91} />
            <Row label="Foreshadowing" value={87} />
            <div style={{ borderTop: '1px solid var(--n-border)', display: 'flex', justifyContent: 'space-between', marginTop: '0.4rem', paddingTop: '0.5rem' }}>
              <strong>Overall</strong><strong style={{ color: 'var(--ai-accent)' }}>93%</strong>
            </div>
          </div>
        </section>
      </div>
    </div>
  );
}

function Row({ label, value }: { label: string; value: number }) {
  return (
    <div style={{ alignItems: 'center', display: 'flex', gap: '0.6rem' }}>
      <span style={{ flex: 1 }}>{label}</span>
      <div className="os-progress" style={{ flex: 1, maxWidth: '120px' }}><span style={{ width: `${value}%` }} /></div>
      <span style={{ color: 'var(--n-text-2)', width: '2.2rem' }}>{value}%</span>
    </div>
  );
}
