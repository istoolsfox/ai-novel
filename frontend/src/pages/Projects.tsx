import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { FolderOpen, Pencil, Plus } from 'lucide-react';
import { useWorkspace } from '../shell/workspace';
import { EmptyState, PageHeader } from '../ui/basics';
import { ProjectsManagerModal } from '../components/ProjectsManagerModal';

export function Projects() {
  const navigate = useNavigate();
  const { projects, projectsLoading } = useWorkspace();
  const [managing, setManaging] = useState(false);

  return (
    <div className="page-inner">
      <PageHeader
        title="项目库"
        sub="所有小说项目。点击卡片进入项目总览；编辑与删除在管理面板中完成。"
        actions={
          <>
            <button className="btn" onClick={() => setManaging(true)}>
              <Pencil size={14} /> 管理
            </button>
            <button className="btn btn-primary" onClick={() => setManaging(true)}>
              <Plus size={14} /> 新建项目
            </button>
          </>
        }
      />
      {projectsLoading ? (
        <p className="muted">加载中…</p>
      ) : projects.length === 0 ? (
        <EmptyState
          icon={<FolderOpen size={26} />}
          title="还没有项目"
          hint="项目是故事的容器：世界观、人物、关系、大纲与章节都归属其中。"
          action={
            <button className="btn btn-primary" onClick={() => setManaging(true)}>
              <Plus size={14} /> 新建项目
            </button>
          }
        />
      ) : (
        <div className="grid" style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(270px, 1fr))' }}>
          {projects.map((project) => (
            <div key={project.id} className="card card-click" role="link" tabIndex={0}
              onClick={() => navigate(`/projects/${project.id}/overview`)}
              onKeyDown={(event) => event.key === 'Enter' && navigate(`/projects/${project.id}/overview`)}
            >
              <div className="row-flex" style={{ marginBottom: 12 }}>
                <span className="avatar accent">{project.title.slice(0, 1)}</span>
                <span className="grow ellip">
                  <b style={{ fontFamily: 'var(--serif)', fontSize: 15.5 }}>{project.title}</b>
                  <small className="muted" style={{ display: 'block', fontSize: 11.5 }}>
                    {project.genre || '未设类型'}{project.target_chapter_count ? ` · 目标 ${project.target_chapter_count} 章` : ''}
                  </small>
                </span>
              </div>
              <p
                className="muted"
                style={{
                  fontSize: 12.5,
                  lineHeight: 1.65,
                  minHeight: 36,
                  display: '-webkit-box',
                  WebkitBoxOrient: 'vertical',
                  WebkitLineClamp: 3,
                  overflow: 'hidden',
                }}
              >
                {project.topic || project.synopsis?.slice(0, 120) || '暂无简介'}
              </p>
            </div>
          ))}
        </div>
      )}

      {managing && <ProjectsManagerModal onClose={() => setManaging(false)} />}
    </div>
  );
}
