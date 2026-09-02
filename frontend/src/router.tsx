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
import { AIStudio } from './pages/AIStudio';
import { CommandPage } from './pages/Command';
import { Placeholder } from './pages/Placeholder';

export const router = createBrowserRouter([
  {
    path: '/',
    element: <AppShell />,
    children: [
      { index: true, element: <Navigate to="/dashboard" replace /> },
      { path: 'dashboard', element: <Dashboard /> },
      { path: 'projects', element: <Projects /> },
      { path: 'projects/new', element: <Navigate to="/projects" replace /> },
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
          { path: 'ai', element: <AIStudio /> },
          { path: 'consistency', element: <Consistency /> },
          { path: 'assets', element: <Placeholder title="素材库" desc="灵感、素材与知识库将在后续阶段上线。" /> },
          { path: 'analytics', element: <Placeholder title="创作分析" desc="产出与质量分析将在后续阶段上线。" /> },
        ],
      },
      { path: 'command', element: <CommandPage /> },
      { path: 'settings', element: <Placeholder title="设置" desc="模型配置、安全与备份管理可通过 API 访问，图形界面将在后续阶段上线。" /> },
    ],
  },
]);
