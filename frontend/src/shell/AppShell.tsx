import { NavLink, Outlet, useLocation, useNavigate, useParams } from 'react-router-dom';
import {
  BookMarked,
  Compass,
  Feather,
  Globe,
  HeartPulse,
  Library,
  Map,
  Network,
  Search,
  Settings,
  Sparkles,
  Users,
} from 'lucide-react';
import { WorkspaceProvider, useWorkspace } from './workspace';
import { ProjectSwitcher } from '../components/ProjectSwitcher';

const PROJECT_NAV = [
  { to: 'overview', label: '总览', icon: Compass },
  { to: 'story', label: '故事圣经', icon: Library },
  { to: 'outline', label: '大纲', icon: Map },
  { to: 'characters', label: '人物', icon: Users },
  { to: 'world', label: '世界观', icon: Globe },
  { to: 'relations', label: '人物关系', icon: Network },
  { to: 'timeline', label: '时间线', icon: BookMarked },
  { to: 'writing', label: '写作', icon: Feather },
  { to: 'consistency', label: '一致性', icon: HeartPulse },
];

const PAGE_TITLES: Record<string, string> = {
  dashboard: '工作台',
  projects: '项目库',
  overview: '总览',
  story: '故事圣经',
  outline: '大纲',
  characters: '人物',
  world: '世界观',
  relations: '人物关系',
  timeline: '时间线',
  writing: '写作',
  ai: 'AI 工作室',
  consistency: '一致性',
  settings: '设置',
  command: '命令',
};

function ShellFrame() {
  const location = useLocation();
  const navigate = useNavigate();
  const params = useParams();
  const { project, immersive } = useWorkspace();
  const projectId = params.projectId;

  const segments = location.pathname.split('/').filter(Boolean);
  const pageTitle = PAGE_TITLES[segments[segments.length - 1] ?? ''] ?? '';

  if (immersive) {
    return (
      <div className="immersive-shell">
        <Outlet />
      </div>
    );
  }

  return (
    <div className="shell">
      <header className="topbar">
        <div className="topbar-crumbs">
          <span>项目库</span>
          {project && (
            <>
              <span>/</span>
              <b>{project.title}</b>
            </>
          )}
          {pageTitle && (
            <>
              <span>/</span>
              <span>{pageTitle}</span>
            </>
          )}
        </div>
        <div className="topbar-spacer" />
        <button className="topbar-search" onClick={() => navigate('/command')} aria-label="打开命令面板">
          <Search size={13} />
          <span style={{ flex: 1, textAlign: 'left' }}>搜索或执行命令</span>
          <kbd>⌘K</kbd>
        </button>
      </header>
      <div className="shell-body">
        <aside className="sidebar">
          <div className="brand">
            <span className="brand-mark"><Feather size={15} /></span>
            <span className="brand-name">Novel OS</span>
          </div>

          <ProjectSwitcher />

          <nav className="nav-group">
            <div className="nav-label">工作台</div>
            <NavLink to="/dashboard" className={({ isActive }) => `nav-item${isActive ? ' active' : ''}`}>
              <Compass size={15} />
              <span>总览面板</span>
            </NavLink>
            <NavLink to="/projects" className={({ isActive }) => `nav-item${isActive ? ' active' : ''}`} end>
              <Library size={15} />
              <span>项目库</span>
            </NavLink>
          </nav>

          <hr className="nav-sep" />

          <nav className="nav-group">
            <div className="nav-label">当前项目</div>
            {PROJECT_NAV.map((item) => {
              const Icon = item.icon;
              return (
                <NavLink
                  key={item.to}
                  className={({ isActive }) => `nav-item${isActive ? ' active' : ''}`}
                  to={projectId ? `/projects/${projectId}/${item.to}` : '/projects'}
                >
                  <Icon size={15} />
                  <span>{item.label}</span>
                </NavLink>
              );
            })}
          </nav>

          <hr className="nav-sep" />

          <nav className="nav-group">
            <div className="nav-label">AI</div>
            <button
              className="nav-item ai"
              onClick={() => navigate(projectId ? `/projects/${projectId}/ai` : '/projects')}
            >
              <Sparkles size={15} />
              <span>AI 工作室</span>
            </button>
          </nav>

          <nav className="nav-group" style={{ marginTop: 'auto' }}>
            <button className="nav-item" onClick={() => navigate('/settings')}>
              <Settings size={15} />
              <span>设置</span>
            </button>
          </nav>
        </aside>
        <main className="page">
          <Outlet />
        </main>
      </div>
    </div>
  );
}

export function AppShell() {
  const params = useParams();
  return (
    <WorkspaceProvider projectId={params.projectId}>
      <ShellFrame />
    </WorkspaceProvider>
  );
}
