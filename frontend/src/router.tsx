import { createBrowserRouter, Navigate } from 'react-router-dom';
import { AppShell } from './shell/AppShell';
import { Dashboard } from './pages/Dashboard';
import { Projects } from './pages/Projects';
import { ProjectOverview } from './pages/ProjectOverview';
import { Characters } from './pages/Characters';
import { Outline } from './pages/Outline';
import { Writing } from './pages/Writing';
import { CommandPage } from './pages/Command';
import { Placeholder } from './pages/Placeholder';

function ProjectOutlet() {
  return <Placeholder title="Project" desc="正在进行。" />;
}

export const router = createBrowserRouter([
  {
    path: '/',
    element: <AppShell />,
    children: [
      { index: true, element: <Navigate to="/dashboard" replace /> },
      { path: 'dashboard', element: <Dashboard /> },
      { path: 'projects', element: <Projects /> },
      { path: 'projects/new', element: <Placeholder title="New Project" desc="创建向导将在后续实现。" /> },
      {
        path: 'projects/:projectId',
        children: [
          { index: true, element: <Navigate to="overview" replace /> },
          { path: 'overview', element: <ProjectOverview /> },
          { path: 'story', element: <Placeholder title="Story" desc="故事圣经与 Story State。" /> },
          { path: 'outline', element: <Outline /> },
          { path: 'characters', element: <Characters /> },
          { path: 'world', element: <Placeholder title="World" desc="世界观实体管理。" /> },
          { path: 'relations', element: <Placeholder title="Relations" desc="关系图。" /> },
          { path: 'timeline', element: <Placeholder title="Timeline" desc="横向时间轴。" /> },
          { path: 'writing', element: <Writing /> },
          { path: 'writing/:chapterId', element: <Writing /> },
          { path: 'ai', element: <Placeholder title="AI Studio" desc="AI 生成工作台。" /> },
          { path: 'consistency', element: <Placeholder title="Consistency Center" desc="一致性中心。" /> },
          { path: 'assets', element: <Placeholder title="Assets" desc="素材库。" /> },
          { path: 'analytics', element: <Placeholder title="Analytics" desc="创作分析。" /> },
        ],
      },
      { path: 'command', element: <CommandPage /> },
      { path: 'settings', element: <Placeholder title="Settings" desc="设置中心。" /> },
    ],
  },
]);
