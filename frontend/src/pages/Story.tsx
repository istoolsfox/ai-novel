import { useNavigate, useParams } from 'react-router-dom';
import { ArrowRight, Globe, Library, Map, Network, ScrollText, Sparkles, Users } from 'lucide-react';
import { useRecords } from '../shell/useRecords';
import { useWorkspace } from '../shell/workspace';
import { EmptyState, PageHeader } from '../ui/basics';

export function Story() {
  const { projectId } = useParams();
  const navigate = useNavigate();
  const { project } = useWorkspace();
  const { records: characters } = useRecords(projectId, 'character-profiles');
  const { records: worlds } = useRecords(projectId, 'world-settings');
  const { records: relationships } = useRecords(projectId, 'character-relationships');
  const { records: outlines } = useRecords(projectId, 'outlines');
  const { records: foreshadowings } = useRecords(projectId, 'foreshadowings');

  const blocks = [
    { to: 'characters', label: '人物', icon: Users, count: characters.length, sample: characters[0]?.content },
    { to: 'world', label: '世界观', icon: Globe, count: worlds.length, sample: worlds[0]?.content },
    { to: 'relations', label: '人物关系', icon: Network, count: relationships.length, sample: relationships[0]?.content },
    { to: 'outline', label: '章节大纲', icon: Map, count: outlines.length, sample: outlines[0]?.content },
  ];

  return (
    <div className="page-inner">
      <PageHeader title="故事圣经" sub="一个故事世界的全部基石。逐块补全它们，AI 续写时会自动引用。" />

      <section className="card" style={{ display: 'flex', gap: 20, alignItems: 'flex-start' }}>
        <span className="avatar accent" style={{ width: 44, height: 44, fontSize: 20 }}>{project?.title.slice(0, 1) ?? '书'}</span>
        <div className="grow">
          <b style={{ fontFamily: 'var(--serif)', fontSize: 19 }}>{project?.title ?? '未选择项目'}</b>
          <p className="muted" style={{ fontSize: 12.5, marginTop: 2 }}>{project?.genre || '未设类型'}{project?.tone ? ` · ${project.tone}` : ''}</p>
          {project?.synopsis ? (
            <p style={{ fontSize: 13.5, lineHeight: 1.8, marginTop: 10 }}>{project.synopsis}</p>
          ) : (
            <p className="muted" style={{ fontSize: 12.5, marginTop: 10 }}>还没有简介——在「管理项目」中补充一句话简介与故事梗概。</p>
          )}
        </div>
      </section>

      <section className="section">
        <h2 className="section-title">基石 <small>STORY BIBLE</small></h2>
        <div className="grid" style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(240px, 1fr))' }}>
          {blocks.map((block) => {
            const Icon = block.icon;
            return (
              <button key={block.to} className="card card-click" style={{ display: 'flex', flexDirection: 'column', gap: 10, alignItems: 'flex-start' }}
                onClick={() => navigate(`/projects/${projectId}/${block.to}`)}>
                <div className="row-flex" style={{ width: '100%' }}>
                  <Icon size={15} style={{ color: 'var(--accent)' }} />
                  <b style={{ flex: 1 }}>{block.label}</b>
                  <span className="badge">{block.count}</span>
                  <ArrowRight size={13} className="muted" />
                </div>
                <p className="muted" style={{ fontSize: 12, lineHeight: 1.65, minHeight: 32 }}>
                  {block.sample ? block.sample.slice(0, 64) : '暂无内容'}
                </p>
              </button>
            );
          })}
        </div>
      </section>

      <section className="section">
        <h2 className="section-title">
          <ScrollText size={15} /> 伏笔台账 <small>{foreshadowings.length} 条</small>
          <span className="spacer" />
          <button className="btn btn-ghost" onClick={() => navigate(`/projects/${projectId}/consistency`)}>一致性体检</button>
        </h2>
        {foreshadowings.length === 0 ? (
          <EmptyState title="暂无伏笔记录" hint="伏笔可在 AI 工作室管线中生成，或由章节定稿流程自动提取。" />
        ) : (
          <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: 4, padding: 12 }}>
            {foreshadowings.map((record) => (
              <div key={record.id} className="row">
                <span className={record.status === 'resolved' ? 'badge ok' : 'badge warn'}>{record.status === 'resolved' ? '已回收' : '未回收'}</span>
                <span className="grow ellip" style={{ fontSize: 13 }}>{record.title}</span>
                <small className="muted ellip" style={{ maxWidth: '40%' }}>{record.content.slice(0, 60)}</small>
              </div>
            ))}
          </div>
        )}
      </section>

      <section className="section">
        <div className="card" style={{ display: 'flex', gap: 14, alignItems: 'flex-start', background: 'var(--ai-wash)', borderColor: 'rgba(109,90,205,0.25)' }}>
          <span className="avatar ai"><Sparkles size={14} /></span>
          <div>
            <b style={{ fontSize: 13.5 }}>用 AI 工作室补全故事圣经</b>
            <p className="muted" style={{ fontSize: 12.5, marginTop: 4, lineHeight: 1.7 }}>
              一句话概念 → 故事概念 → 人物 → 世界 → 章节大纲，每一步都可以修改、回退后再继续。
            </p>
            <button className="btn btn-ai" style={{ marginTop: 10 }} onClick={() => navigate(`/projects/${projectId}/ai`)}>
              <Sparkles size={13} /> 打开 AI 工作室
            </button>
          </div>
        </div>
      </section>
    </div>
  );
}
