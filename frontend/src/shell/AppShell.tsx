import { useState } from 'react';
import { NavLink, Outlet, useLocation, useNavigate, useParams } from 'react-router-dom';
import {
  Activity,
  Bell,
  Brain,
  ChevronLeft,
  ChevronRight,
  FileText,
  FolderOpen,
  Globe,
  HeartPulse,
  Home,
  Library,
  Map,
  Network,
  RefreshCw,
  Search,
  Settings,
  Sparkles,
  Users,
} from 'lucide-react';
import './shell.css';

const CURRENT_PROJECT_NAV = [
  { to: 'overview', label: 'Overview', icon: Home },
  { to: 'story', label: 'Story', icon: Library },
  { to: 'outline', label: 'Outline', icon: Map },
  { to: 'characters', label: 'Characters', icon: Users },
  { to: 'world', label: 'World', icon: Globe },
  { to: 'relations', label: 'Relations', icon: Network },
  { to: 'timeline', label: 'Timeline', icon: FileText },
  { to: 'writing', label: 'Writing', icon: FileText },
  { to: 'consistency', label: 'Consistency', icon: HeartPulse },
];

export function AppShell() {
  const [collapsed, setCollapsed] = useState(false);
  const [aiOpen, setAiOpen] = useState(true);
  const location = useLocation();
  const navigate = useNavigate();
  const params = useParams();
  const projectId = params.projectId;
  const projectTitle = params.projectId ? '小说项目' : 'Notion Saves';

  const isEditor = /\/(writing|editor)/.test(location.pathname);
  const showAi = aiOpen && !isEditor;

  const bodyClass = [
    'os-body',
    collapsed ? 'sidebar-collapsed' : '',
    showAi ? 'with-ai' : '',
  ].join(' ').replace(/\s+/g, ' ').trim();

  return (
    <div className="os-shell">
      <header className="os-topbar">
        <button className="os-sidebar-brand" onClick={() => navigate('/')} title="回到首页" style={{ border: 'none', background: 'none', padding: 0 }}>
          <span className="os-logo"><Brain size={16} /></span>
        </button>
        <div className="os-breadcrumb">
          <span>Projects</span>
          <ChevronRight size={14} />
          <span>{projectId ? '雨夜玫瑰' : 'Dashboard'}</span>
          {isEditor && (<><ChevronRight size={14} /><span>Chapter 38</span></>)}
        </div>
        <button className="os-topbar-search" onClick={() => navigate('/command')} aria-label="打开命令面板">
          <Search size={14} />
          <span>搜索或执行命令</span>
          <kbd>⌘K</kbd>
        </button>
        <div className="os-topbar-right">
          <button className="os-icon-btn" title="通知"><Bell size={16} /></button>
          <button className="os-icon-btn" title="设置" onClick={() => navigate('/settings')}><Settings size={16} /></button>
        </div>
      </header>
      <div className={bodyClass}>
        <aside className={collapsed ? 'os-sidebar os-sidebar-collapsed' : 'os-sidebar'}>
          <div className="os-sidebar-brand">
            <button className="os-logo" onClick={() => navigate('/dashboard')} title="Novel OS"><Brain size={16} /></button>
            <strong>Novel OS</strong>
          </div>
          <button className="os-collapse" onClick={() => setCollapsed(!collapsed)} title="折叠侧栏 (⌘B)">
            {collapsed ? <ChevronRight size={16} /> : <ChevronLeft size={16} />}
            <span>折叠</span>
          </button>

          <nav className="os-nav-group">
            <div className="os-nav-group-label">Workspace</div>
            <NavLink className={({ isActive }) => `os-nav-item${isActive ? ' active' : ''}`} to="/dashboard">
              <Home size={16} />
              <span>Dashboard</span>
            </NavLink>
            <NavLink className={({ isActive }) => `os-nav-item${isActive ? ' active' : ''}`} to="/projects">
              <FolderOpen size={16} />
              <span>Projects</span>
            </NavLink>
          </nav>

          <div className="os-nav-divider" />

          <nav className="os-nav-group">
            <div className="os-nav-group-label">Current Project</div>
            {CURRENT_PROJECT_NAV.map((item) => {
              const Icon = item.icon;
              return (
                <NavLink key={item.to} className={({ isActive }) => `os-nav-item${isActive ? ' active' : ''}`} to={projectId ? `/projects/${projectId}/${item.to}` : '/projects'}>
                  <Icon size={16} />
                  <span>{item.label}</span>
                </NavLink>
              );
            })}
          </nav>

          <div className="os-nav-divider" />

          <nav className="os-nav-group">
            <div className="os-nav-group-label">AI</div>
            <button className="os-nav-item" onClick={() => { if (projectId) navigate(`/projects/${projectId}/ai`); }}>
              <Sparkles size={16} className="os-ai-indicator" />
              <span>AI Studio</span>
            </button>
          </nav>

          <nav className="os-nav-group">
            <div className="os-nav-group-label">Data</div>
            <button className="os-nav-item" onClick={() => navigate(projectId ? `/projects/${projectId}/analytics` : '/dashboard')}>
              <Activity size={16} />
              <span>Analytics</span>
            </button>
          </nav>

          <div className="os-sidebar-footer">
            <button className="os-nav-item" onClick={() => setAiOpen(!aiOpen)} title="AI 面板 (⌘J)">
              <Sparkles size={16} className="os-ai-indicator" />
              <span>{aiOpen ? '收起 AI 面板' : '展开 AI 面板'}</span>
            </button>
          </div>
        </aside>
        <main className="os-page">
          <Outlet />
        </main>
        {showAi && <AIPanel active />}
      </div>
    </div>
  );
}

function AIPanel({ active }: { active?: boolean }) {
  return (
    <aside className="os-ai-panel">
      <div className="os-ai-panel-head">
        <strong><Sparkles size={15} /> AI Copilot</strong>
        <span className="os-ai-chip">Context · 14 sources</span>
      </div>
      <div className="os-ai-section">
        <h4>Current Chapter</h4>
        <div className="os-ai-chip-list">
          <span className="os-ai-chip">38 · 暴雨</span>
        </div>
      </div>
      <div className="os-ai-section">
        <h4>Characters</h4>
        <div className="os-ai-chip-list">
          <span className="os-ai-chip">林默</span>
          <span className="os-ai-chip">苏晚</span>
        </div>
      </div>
      <div className="os-ai-section">
        <h4>Active Plotlines</h4>
        <div className="os-ai-chip-list">
          <span className="os-ai-chip ai">Identity Reveal</span>
          <span className="os-ai-chip ai">Romance</span>
        </div>
      </div>
      <div className="os-ai-section">
        <h4>Foreshadowings</h4>
        <div className="os-ai-chip-list">
          <span className="os-ai-chip">Mysterious Ring</span>
          <span className="os-ai-chip">Father's Death</span>
        </div>
      </div>
      <div className="os-ai-section">
        <h4>Quick Actions</h4>
        <div className="os-ai-actions">
          <button className="os-ai-action"><FileText size={14} /> Continue</button>
          <button className="os-ai-action"><RefreshCw size={14} /> Rewrite</button>
          <button className="os-ai-action"><Sparkles size={14} /> Expand</button>
          <button className="os-ai-action"><Sparkles size={14} /> Polish</button>
        </div>
      </div>
    </aside>
  );
}
