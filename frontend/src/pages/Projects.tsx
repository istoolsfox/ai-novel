import { useNavigate } from 'react-router-dom';
import { Plus, FolderOpen } from 'lucide-react';
import { useProjects } from '../shell/useProject';

export function Projects() {
  const navigate = useNavigate();
  const { projects } = useProjects();
  return (
    <div>
      <div style={{ alignItems: 'center', display: 'flex', justifyContent: 'space-between' }}>
        <div>
          <h1>Projects</h1>
          <p className="os-page-sub">你的小说与短剧项目</p>
        </div>
        <button className="os-btn os-btn-primary" onClick={() => navigate('/projects/new')}><Plus size={16} /> New Project</button>
      </div>
      <div className="os-grid" style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(240px, 1fr))' }}>
        {projects.map((p) => (
          <button key={p.id} className="os-card" style={{ alignItems: 'flex-start', display: 'flex', flexDirection: 'column', gap: '0.6rem', textAlign: 'left' }} onClick={() => navigate(`/projects/${p.id}/overview`)}>
            <FolderOpen size={16} />
            <strong style={{ fontSize: '0.95rem' }}>{p.title}</strong>
            <small style={{ color: 'var(--n-text-2)' }}>{p.genre || 'Novel'}</small>
          </button>
        ))}
        {projects.length === 0 && <div className="os-empty">暂无项目</div>}
      </div>
    </div>
  );
}
