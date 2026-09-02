import { createBrowserRouter, Navigate } from 'react-router-dom';
import { AppShell } from './shell/AppShell';
import { Dashboard } from './pages/Dashboard';
import { Projects } from './pages/Projects';
import { ProjectOverview } from './pages/ProjectOverview';
import { Characters } from './pages/Characters';
import { Outline } from './pages/Outline';
import { Writing } from './pages/Writing';
import { World } from './pages/World';
import { Relations } from './pages/Relations';
import { Timeline } from './pages/Timeline';
import { Story } from './pages/Story';
import { Consistency } from './pages/Consistency';
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
          { path: 'story', element: <Story /> },
          { path: 'outline', element: <Outline /> },
          { path: 'characters', element: <Characters /> },
          { path: 'world', element: <World /> },
          { path: 'relations', element: <Relations /> },
          { path: 'timeline', element: <Timeline /> },
          { path: 'writing', element: <Writing /> },
          { path: 'writing/:chapterId', element: <Writing /> },
          { path: 'ai', element: <Placeholder title="AI Studio" desc="AI 生成工作台。" /> },
          { path: 'consistency', element: <Consistency /> },
          { path: 'assets', element: <Placeholder title="Assets" desc="素材库。" /> },
          { path: 'analytics', element: <Placeholder title="Analytics" desc="创作分析。" /> },
        ],
      },
      { path: 'command', element: <CommandPage /> },
      { path: 'settings', element: <Placeholder title="Settings" desc="设置中心。" /> },
    ],
  },
]);
