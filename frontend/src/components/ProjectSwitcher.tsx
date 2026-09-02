import { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { BookMarked, ChevronDown, Settings2 } from 'lucide-react';
import { useWorkspace } from '../shell/workspace';
import { ProjectsManagerModal } from './ProjectsManagerModal';

export function ProjectSwitcher() {
  const navigate = useNavigate();
  const { projects, projectId, project } = useWorkspace();
  const [open, setOpen] = useState(false);
  const [managing, setManaging] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const onDown = (event: MouseEvent) => {
      if (rootRef.current && !rootRef.current.contains(event.target as Node)) setOpen(false);
    };
    const onKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setOpen(false);
    };
    document.addEventListener('mousedown', onDown);
    document.addEventListener('keydown', onKey);
    return () => {
      document.removeEventListener('mousedown', onDown);
      document.removeEventListener('keydown', onKey);
    };
  }, [open]);

  return (
    <div className="project-switcher" ref={rootRef}>
      <button
        className={open ? 'project-switcher-main open' : 'project-switcher-main'}
        onClick={() => setOpen(!open)}
        aria-label="切换项目"
        aria-expanded={open}
      >
        <span className="project-switcher-title">
          <small>当前项目</small>
          <b>{project?.title ?? '未选择项目'}</b>
        </span>
        <span className="project-switcher-badge">
          <ChevronDown size={13} style={{ transform: open ? 'rotate(180deg)' : undefined, transition: 'transform 160ms ease' }} />
        </span>
      </button>

      {open && (
        <div className="project-menu">
          <div className="project-menu-head">全部项目 · {projects.length}</div>
          {projects.map((item) => (
            <button
              key={item.id}
              className={item.id === projectId ? 'project-menu-item current' : 'project-menu-item'}
              onClick={() => {
                setOpen(false);
                navigate(`/projects/${item.id}/overview`);
              }}
            >
              <BookMarked size={14} style={{ color: 'var(--ink-3)', flexShrink: 0 }} />
              <b>{item.title}</b>
              <small>{item.genre || '小说'}</small>
            </button>
          ))}
          {projects.length === 0 && <div className="project-menu-head" style={{ paddingTop: 2 }}>还没有项目</div>}
          <div className="project-menu-actions">
            <button className="btn" onClick={() => { setOpen(false); setManaging(true); }}>
              <Settings2 size={13} /> 管理
            </button>
            <button className="btn btn-primary" onClick={() => { setOpen(false); setManaging(true); }}>
              新建项目
            </button>
          </div>
        </div>
      )}

      {managing && <ProjectsManagerModal onClose={() => setManaging(false)} />}
    </div>
  );
}
