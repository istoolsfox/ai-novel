import { useNavigate } from 'react-router-dom';
import { FolderOpen, Plus, Sparkles, TriangleAlert, CheckCircle2 } from 'lucide-react';
import { useProjects } from '../shell/useProject';

function progress(p: { target_chapter_count?: number }) {
  return p?.target_chapter_count ? Math.min(100, 100) : 0;
}

export function Dashboard() {
  const navigate = useNavigate();
  const { projects } = useProjects();

  return (
    <div>
      <h1>Good afternoon.</h1>
      <p className="os-page-sub">欢迎回来，继续你的故事。</p>
      <button className="os-btn os-btn-primary" onClick={() => navigate('/projects/new')}>
        <Plus size={16} /> New Project
      </button>

      <div className="os-grid" style={{ marginTop: '1.5rem' }}>
        <section className="os-card">
          <div className="os-card-header">
            <strong>Recent Projects</strong>
            <small>{projects.length} 个项目</small>
          </div>
          <div className="os-grid" style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(240px, 1fr))' }}>
            {projects.slice(0, 6).map((p) => (
              <button
                key={p.id}
                className="os-card"
                style={{ alignItems: 'flex-start', display: 'flex', flexDirection: 'column', gap: '0.6rem', textAlign: 'left' }}
                onClick={() => navigate(`/projects/${p.id}/overview`)}
              >
                <span style={{ display: 'flex', gap: '0.4rem' }}>
                  <FolderOpen size={16} />
                  <strong style={{ fontSize: '0.95rem' }}>{p.title}</strong>
                </span>
                <small style={{ color: 'var(--n-text-2)' }}>{p.genre || 'Novel'}</small>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', width: '100%' }}>
                  <div className="os-progress" style={{ flex: 1 }}>
                    <span style={{ width: `${progress(p)}%` }} />
                  </div>
                  <small style={{ color: 'var(--n-muted)' }}>{progress(p)}%</small>
                </div>
              </button>
            ))}
            {projects.length === 0 && <div className="os-empty">还没有项目，点击上方 New Project 创建。</div>}
          </div>
        </section>

        <div className="os-grid" style={{ gridTemplateColumns: '2fr 1fr' }}>
          <section className="os-card">
            <div className="os-card-header">
              <strong>Today</strong>
              <small>今日创作</small>
            </div>
            <div className="os-grid" style={{ gridTemplateColumns: 'repeat(3, minmax(0,1fr))' }}>
              <div><h2 style={{ fontSize: '1.6rem', margin: '0' }}>0</h2><small style={{ color: 'var(--n-text-2)' }}>Words</small></div>
              <div><h2 style={{ fontSize: '1.6rem', margin: '0' }}>0</h2><small style={{ color: 'var(--n-text-2)' }}>Chapters</small></div>
              <div><h2 style={{ fontSize: '1.6rem', margin: '0' }}>0</h2><small style={{ color: 'var(--n-text-2)' }}>Writing Time</small></div>
            </div>
          </section>

          <section className="os-card">
            <div className="os-card-header">
              <strong style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}><Sparkles size={14} /> AI Insights</strong>
              <small>consistency</small>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem', fontSize: '0.8rem' }}>
              <span style={{ color: 'var(--n-text-2)' }}><TriangleAlert size={13} style={{ marginRight: '0.3rem' }} />角色冲突待处理</span>
              <span style={{ color: 'var(--n-text-2)' }}><TriangleAlert size={13} style={{ marginRight: '0.3rem' }} />未尽伏笔</span>
              <span style={{ color: '#1a7f37' }}><CheckCircle2 size={13} style={{ marginRight: '0.3rem' }} />世界一致性 94%</span>
              <span style={{ color: '#1a7f37' }}><CheckCircle2 size={13} style={{ marginRight: '0.3rem' }} />时间线一致性 98%</span>
            </div>
          </section>
        </div>
      </div>
    </div>
  );
}
