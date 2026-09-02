import { useNavigate, useParams } from 'react-router-dom';
import { Map, Sparkles, Plus, Star } from 'lucide-react';
import { useChapters, useProject } from '../shell/useProject';

export function Outline() {
  const { projectId } = useParams();
  const navigate = useNavigate();
  const { project } = useProject(projectId);
  const { chapters } = useChapters(projectId);

  return (
    <div>
      <div style={{ alignItems: 'center', display: 'flex', gap: '1rem', justifyContent: 'space-between' }}>
        <div>
          <h1>Outline</h1>
          <p className="os-page-sub">{project?.title ?? ''} · 分卷章节树与剧情板</p>
        </div>
        <div style={{ display: 'flex', gap: '0.5rem' }}>
          <button className="os-tabs" style={{ border: 'none', margin: 0 }}><button className="active">Board</button><button>List</button><button>Timeline</button></button>
          <button className="os-btn ai"><Sparkles size={14} /> AI Generate</button>
          <button className="os-btn"><Plus size={15} /> Add</button>
        </div>
      </div>

      <div className="os-grid" style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))' }}>
        {chapters.map((ch) => (
          <button
            key={ch.id}
            className="os-card"
            style={{ alignItems: 'flex-start', display: 'flex', flexDirection: 'column', gap: '0.4rem', textAlign: 'left' }}
            onClick={() => navigate(`/projects/${projectId}/writing/${ch.id}`)}
          >
            <small style={{ color: 'var(--n-muted)' }}>CH {String(ch.chapter_number).padStart(2, '0')}</small>
            <strong style={{ fontSize: '0.95rem' }}>{ch.title || '未命名章'}</strong>
            <small style={{ color: 'var(--n-text-2)', minHeight: '2.4em' }}>{ch.brief || '暂无梗概'}</small>
            <div style={{ alignItems: 'center', display: 'flex', gap: '0.4rem', width: '100%' }}>
              <Map size={13} />
              <small style={{ flex: 1 }}>{ch.status === 'final' ? 'Completed' : 'Editing'}</small>
              <Star size={13} style={{ color: 'var(--ai-accent)' }} />
              <Star size={13} style={{ color: 'var(--ai-accent)' }} />
              <Star size={13} style={{ color: 'var(--ai-accent)' }} />
            </div>
          </button>
        ))}
        {chapters.length === 0 && <div className="os-empty">暂无章节，去 Writing 创建。</div>}
      </div>
    </div>
  );
}
