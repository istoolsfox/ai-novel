import { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { Compass, Feather, Globe, Network, Pencil, Sparkles, Users } from 'lucide-react';
import { api } from '../api';
import { useChapters } from '../shell/useProject';
import { useWorkspace } from '../shell/workspace';
import { EmptyState, PageHeader } from '../ui/basics';
import { ProjectsManagerModal } from '../components/ProjectsManagerModal';

export function ProjectOverview() {
  const navigate = useNavigate();
  const { projectId } = useParams();
  const { project } = useWorkspace();
  const { chapters } = useChapters(projectId);
  const [counts, setCounts] = useState({ characters: 0, worlds: 0, relationships: 0 });
  const [managing, setManaging] = useState(false);

  useEffect(() => {
    if (!projectId) return;
    let alive = true;
    Promise.all([
      api.listRecords(projectId, 'character-profiles').catch(() => []),
      api.listRecords(projectId, 'world-settings').catch(() => []),
      api.listRecords(projectId, 'character-relationships').catch(() => []),
    ]).then(([characters, worlds, relationships]) => {
      if (alive) setCounts({ characters: characters.length, worlds: worlds.length, relationships: relationships.length });
    });
    return () => {
      alive = false;
    };
  }, [projectId]);

  const totalWords = chapters.reduce((sum, chapter) => sum + (chapter.draft?.length ?? 0), 0);
  const finalized = chapters.filter((chapter) => chapter.status === 'final').length;
  const target = project?.target_chapter_count ?? 0;
  const pct = target ? Math.min(100, Math.round((chapters.length / target) * 100)) : 0;

  const metrics = [
    { icon: Users, label: '人物', value: counts.characters, to: 'characters' },
    { icon: Globe, label: '世界观', value: counts.worlds, to: 'world' },
    { icon: Network, label: '关系', value: counts.relationships, to: 'relations' },
    { icon: Feather, label: '章节', value: chapters.length, to: 'writing' },
  ];

  if (!project) {
    return (
      <div className="page-inner">
        <EmptyState icon={<Compass size={26} />} title="项目不存在或已删除" hint="请从项目库重新选择。" />
      </div>
    );
  }

  return (
    <div className="page-inner">
      <PageHeader
        title={project.title}
        sub={[project.genre || '未设类型', project.topic].filter(Boolean).join(' · ') || '还没有核心创意'}
        actions={
          <>
            <button className="btn" onClick={() => setManaging(true)}>
              <Pencil size={13} /> 编辑项目
            </button>
            <button className="btn btn-ai" onClick={() => navigate(`/projects/${projectId}/ai`)}>
              <Sparkles size={14} /> AI 工作室
            </button>
            <button className="btn btn-primary" onClick={() => navigate(`/projects/${projectId}/writing`)}>
              <Feather size={14} /> 继续写作
            </button>
          </>
        }
      />

      <div className="grid" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))' }}>
        {metrics.map((metric) => {
          const Icon = metric.icon;
          return (
            <button key={metric.label} className="card card-click" style={{ display: 'flex', flexDirection: 'column', gap: 6, alignItems: 'flex-start' }}
              onClick={() => navigate(`/projects/${projectId}/${metric.to}`)}>
              <Icon size={15} style={{ color: 'var(--accent)' }} />
              <span className="stat-value">{metric.value}</span>
              <span className="stat-label">{metric.label}</span>
            </button>
          );
        })}
      </div>

      <div className="grid" style={{ gridTemplateColumns: '3fr 2fr', marginTop: 16 }}>
        <section className="card">
          <div className="card-head">
            <b>写作进度</b>
            <small>{chapters.length}{target ? ` / ${target}` : ''} 章 · {totalWords.toLocaleString()} 字</small>
          </div>
          <div className="progress" style={{ marginBottom: 8 }}><span style={{ width: `${pct}%` }} /></div>
          <p className="muted" style={{ fontSize: 12.5 }}>{target ? `完成 ${pct}%，其中 ${finalized} 章已定稿` : `已写 ${chapters.length} 章，其中 ${finalized} 章已定稿（可在管理项目中设定目标章节数）`}</p>
        </section>

        <section className="card">
          <div className="card-head"><b>故事简介</b></div>
          {project.synopsis ? (
            <p style={{ fontSize: 13, lineHeight: 1.8 }}>{project.synopsis}</p>
          ) : (
            <p className="muted" style={{ fontSize: 12.5, lineHeight: 1.7 }}>还没有简介。点击「编辑项目」补充梗概，AI 生成时会引用。</p>
          )}
        </section>
      </div>

      <section className="section">
        <h2 className="section-title">最近章节 <small>RECENT CHAPTERS</small></h2>
        {chapters.length === 0 ? (
          <EmptyState
            title="还没有章节"
            hint="去「大纲」创建章节，或让 AI 生成第一章。"
            action={
              <button className="btn btn-primary" onClick={() => navigate(`/projects/${projectId}/outline`)}>
                前往大纲
              </button>
            }
          />
        ) : (
          <div className="card" style={{ padding: 10 }}>
            {[...chapters].sort((left, right) => right.chapter_number - left.chapter_number).slice(0, 6).map((chapter) => (
              <button key={chapter.id} className="row" onClick={() => navigate(`/projects/${projectId}/writing/${chapter.id}`)}>
                <span className="muted" style={{ width: 30, fontSize: 12 }}>{String(chapter.chapter_number).padStart(2, '0')}</span>
                <span className="grow ellip" style={{ fontSize: 13.5 }}>{chapter.title || '未命名章'}</span>
                <small className="muted">{(chapter.draft?.length ?? 0).toLocaleString()} 字</small>
                <span className={chapter.status === 'final' ? 'badge ok' : 'badge'}>{chapter.status === 'final' ? '已定稿' : '草稿'}</span>
              </button>
            ))}
          </div>
        )}
      </section>

      {managing && <ProjectsManagerModal onClose={() => setManaging(false)} />}
    </div>
  );
}
