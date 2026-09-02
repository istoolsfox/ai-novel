import { useParams } from 'react-router-dom';
import { TriangleAlert, CheckCircle2, Sparkles, X, Check } from 'lucide-react';
import { useRecords } from '../shell/useRecords';

export function Consistency() {
  const { projectId } = useParams();
  const { records: foreshadowings, update } = useRecords(projectId, 'foreshadowings');

  const openIssues = foreshadowings.filter((f) => (f.status ?? 'open') !== 'resolved')
    .map((f) => ({ id: f.id, title: '未回收伏笔', detail: f.title, from: 'Foreshadowing' }));

  const groups = [
    { label: 'Foreshadowing', count: openIssues.length, issues: openIssues, tone: 'warn' },
    { label: 'World', count: 0, issues: [], tone: 'ok' },
    { label: 'Plot', count: 0, issues: [], tone: 'ok' },
  ];

  const total = foreshadowings.length;
  const unresolved = openIssues.length;
  const ok = total === 0 ? 100 : total > 0 ? Math.max(0, 100 - Math.round((unresolved / total) * 100)) : 100;

  return (
    <div>
      <h1>Consistency Center</h1>
      <p className="os-page-sub">故事一致性体检：角色 / 时间线 / 世界 / 剧情 / 伏笔</p>

      <section className="os-card" style={{ maxWidth: '420px' }}>
        <div className="os-card-header"><strong>Overall Health</strong><strong style={{ color: 'var(--ai-accent)' }}>{ok}%</strong></div>
        <div className="os-progress"><span style={{ width: `${ok}%` }} /></div>
      </section>

      <div className="os-grid" style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(260px, 1fr))', marginTop: '1rem' }}>
        {groups.map((g) => (
          <section className="os-card" key={g.label}>
            <div className="os-card-header">
              <strong>{g.label}</strong>
              <small style={{ color: g.tone === 'warn' ? '#d97706' : '#1a7f37' }}>{g.count > 0 ? `⚠ ${g.count}` : '✓ No Issues'}</small>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem', fontSize: '0.82rem' }}>
              {g.issues.map((issue) => (
                <div key={issue.id} style={{ border: '1px solid var(--n-border)', borderRadius: '8px', padding: '0.5rem 0.6rem' }}>
                  <div style={{ alignItems: 'center', display: 'flex', gap: '0.4rem' }}>
                    <TriangleAlert size={14} style={{ color: '#d97706' }} />
                    <strong style={{ flex: 1 }}>{issue.title}</strong>
                    <button className="os-icon-btn" title="忽略" onClick={() => update(issue.id, { status: 'resolved' })}><X size={14} /></button>
                  </div>
                  <small style={{ color: 'var(--n-text-2)', display: 'block', margin: '0.3rem 0' }}>{issue.detail}</small>
                  <div style={{ display: 'flex', gap: '0.4rem' }}>
                    <button className="os-btn ai" style={{ fontSize: '0.74rem', padding: '0.2rem 0.45rem' }}><Sparkles size={12} /> AI 修复</button>
                    <button className="os-btn" style={{ fontSize: '0.74rem', padding: '0.2rem 0.45rem' }}><Check size={12} /> 已解决</button>
                  </div>
                </div>
              ))}
              {g.issues.length === 0 && <div className="os-empty" style={{ padding: 0 }}>无问题</div>}
            </div>
          </section>
        ))}
      </div>
    </div>
  );
}
