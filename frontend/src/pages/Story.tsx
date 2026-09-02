import { useParams } from 'react-router-dom';
import { Users, Map, ScrollText } from 'lucide-react';
import { useRecords } from '../shell/useRecords';

export function Story() {
  const { projectId } = useParams();
  const { records: characters } = useRecords(projectId, 'character-profiles');
  const { records: outlines } = useRecords(projectId, 'outlines');
  const { records: foreshadowings } = useRecords(projectId, 'foreshadowings');

  return (
    <div>
      <h1>Story</h1>
      <p className="os-page-sub">故事圣经：角色档案、大纲、伏笔与世界观核心</p>

      <div className="os-grid" style={{ gridTemplateColumns: '1fr 1fr' }}>
        <section className="os-card">
          <div className="os-card-header"><strong style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}><Users size={14} /> Character Bible</strong><small>{characters.length}</small></div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem' }}>
            {characters.map((c) => (
              <div key={c.id} style={{ border: '1px solid var(--n-border)', borderRadius: '8px', padding: '0.5rem 0.6rem' }}>
                <strong style={{ fontSize: '0.9rem' }}>{c.title}</strong>
                {c.content && <small style={{ color: 'var(--n-text-2)', display: 'block', marginTop: '0.2rem' }}>{c.content.slice(0, 90)}{c.content.length > 90 ? '…' : ''}</small>}
              </div>
            ))}
            {characters.length === 0 && <div className="os-empty">暂无角色档案</div>}
          </div>
        </section>

        <section className="os-card">
          <div className="os-card-header"><strong style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}><Map size={14} /> Outline</strong><small>{outlines.length}</small></div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem' }}>
            {outlines.map((o) => (
              <div key={o.id} style={{ border: '1px solid var(--n-border)', borderRadius: '8px', padding: '0.5rem 0.6rem' }}>
                <strong style={{ fontSize: '0.9rem' }}>{o.title}</strong>
                {o.content && <small style={{ color: 'var(--n-text-2)', display: 'block', marginTop: '0.2rem' }}>{o.content.slice(0, 90)}{o.content.length > 90 ? '…' : ''}</small>}
              </div>
            ))}
            {outlines.length === 0 && <div className="os-empty">暂无大纲</div>}
          </div>
        </section>

        <section className="os-card" style={{ gridColumn: '1 / -1' }}>
          <div className="os-card-header"><strong style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}><ScrollText size={14} /> Foreshadowings</strong><small>{foreshadowings.length}</small></div>
          <div className="os-ai-chip-list">
            {foreshadowings.map((f) => <span key={f.id} className="os-ai-chip ai">{f.title}</span>)}
            {foreshadowings.length === 0 && <span className="os-empty" style={{ padding: 0 }}>暂无伏笔</span>}
          </div>
        </section>
      </div>
    </div>
  );
}
