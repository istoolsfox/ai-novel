import { useNavigate, useParams } from 'react-router-dom';
import { Check, Sparkles, TriangleAlert, X } from 'lucide-react';
import { useRecords } from '../shell/useRecords';
import { EmptyState, PageHeader } from '../ui/basics';

export function Consistency() {
  const navigate = useNavigate();
  const { projectId } = useParams();
  const { records: foreshadowings, update, reload } = useRecords(projectId, 'foreshadowings');

  const openIssues = foreshadowings.filter((item) => item.status !== 'resolved');
  const resolved = foreshadowings.length - openIssues.length;
  const health = foreshadowings.length === 0 ? 100 : Math.round((resolved / foreshadowings.length) * 100);

  const groups = [
    { label: '伏笔未回收', icon: TriangleAlert, issues: openIssues },
    { label: '已回收 / 已忽略', icon: Check, issues: foreshadowings.filter((item) => item.status === 'resolved') },
  ];

  return (
    <div className="page-inner">
      <PageHeader
        title="一致性体检"
        sub="当前基于伏笔台账评估故事健康度：未回收的伏笔是读者眼里最大的不一致。"
      />

      <div className="grid" style={{ gridTemplateColumns: 'repeat(3, minmax(0, 1fr))' }}>
        <div className="card">
          <div className="card-head"><b>故事健康度</b></div>
          <div className="stat-value" style={{ color: health >= 80 ? 'var(--ok)' : health >= 50 ? 'var(--warn)' : 'var(--danger)' }}>{health}%</div>
          <div className="progress" style={{ marginTop: 10 }}>
            <span style={{ width: `${health}%`, background: health >= 80 ? 'var(--ok)' : health >= 50 ? 'var(--warn)' : 'var(--danger)' }} />
          </div>
        </div>
        <div className="card">
          <div className="card-head"><b>伏笔台账</b></div>
          <div className="stat-value">{foreshadowings.length}</div>
          <div className="stat-label">共 {resolved} 条已回收 · {openIssues.length} 条待处理</div>
        </div>
        <div className="card">
          <div className="card-head"><b>深入体检</b></div>
          <p className="muted" style={{ fontSize: 12.5, lineHeight: 1.7 }}>
            连续性检查、时间线与知识边界校验由自动托管流程在每章定稿时运行。
          </p>
          <button className="btn" style={{ marginTop: 10 }} onClick={() => navigate(`/projects/${projectId}/ai`)}>
            <Sparkles size={13} /> 前往 AI 工作室
          </button>
        </div>
      </div>

      <section className="section">
        {foreshadowings.length === 0 ? (
          <EmptyState
            icon={<Sparkles size={26} />}
            title="还没有可体检的伏笔数据"
            hint="伏笔会在章节定稿与记忆编译时自动提取，也可以在 AI 工作室生成。"
          />
        ) : (
          <div className="grid" style={{ gridTemplateColumns: '1fr 1fr' }}>
            {groups.map((group) => {
              const Icon = group.icon;
              return (
                <section className="card" key={group.label}>
                  <div className="card-head">
                    <b style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}><Icon size={14} /> {group.label}</b>
                    <span className={group.label.includes('未回收') ? 'badge warn' : 'badge ok'}>{group.issues.length}</span>
                  </div>
                  <div className="stack" style={{ gap: 8 }}>
                    {group.issues.map((issue) => (
                      <div key={issue.id} style={{ border: '1px solid var(--line)', borderRadius: 10, padding: '12px 14px' }}>
                        <div className="row-flex">
                          <b style={{ flex: 1, fontSize: 13 }}>{issue.title}</b>
                          {group.label.includes('未回收') ? (
                            <>
                              <button className="btn" style={{ fontSize: 12, padding: '4px 10px' }}
                                onClick={() => void update(issue.id, { title: issue.title, category: issue.category, content: issue.content, payload: issue.payload, status: 'resolved' }).then(reload)}>
                                <Check size={12} /> 标记回收
                              </button>
                              <button className="icon-btn" aria-label="忽略" onClick={() => void update(issue.id, { title: issue.title, category: issue.category, content: issue.content, payload: issue.payload, status: 'ignored' }).then(reload)}>
                                <X size={13} />
                              </button>
                            </>
                          ) : (
                            <span className="badge ok">{issue.status === 'resolved' ? '已回收' : '已忽略'}</span>
                          )}
                        </div>
                        {issue.content && <p className="muted" style={{ fontSize: 12.5, marginTop: 6, lineHeight: 1.7 }}>{issue.content.slice(0, 120)}</p>}
                      </div>
                    ))}
                    {group.issues.length === 0 && <p className="muted" style={{ fontSize: 12.5 }}>暂无</p>}
                  </div>
                </section>
              );
            })}
          </div>
        )}
      </section>
    </div>
  );
}
