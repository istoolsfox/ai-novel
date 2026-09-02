import { createContext, ReactNode, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import { api, Project } from '../api';

type WorkspaceValue = {
  projects: Project[];
  projectsLoading: boolean;
  reloadProjects: () => Promise<void>;
  projectId?: string;
  project: Project | null;
  immersive: boolean;
  setImmersive: (value: boolean) => void;
};

const WorkspaceContext = createContext<WorkspaceValue | null>(null);

export function WorkspaceProvider({ projectId, children }: { projectId?: string; children: ReactNode }) {
  const [projects, setProjects] = useState<Project[]>([]);
  const [projectsLoading, setProjectsLoading] = useState(true);
  const [immersive, setImmersive] = useState(false);

  const reloadProjects = useCallback(async () => {
    try {
      const items = await api.listProjects();
      setProjects(items);
    } catch {
      setProjects([]);
    } finally {
      setProjectsLoading(false);
    }
  }, []);

  useEffect(() => {
    void reloadProjects();
  }, [reloadProjects]);

  useEffect(() => {
    if (!immersive) return;
    const onKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setImmersive(false);
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [immersive, setImmersive]);

  const project = useMemo(() => projects.find((item) => item.id === projectId) ?? null, [projects, projectId]);

  return (
    <WorkspaceContext.Provider
      value={{ projects, projectsLoading, reloadProjects, projectId, project, immersive, setImmersive }}
    >
      {children}
    </WorkspaceContext.Provider>
  );
}

export function useWorkspace(): WorkspaceValue {
  const value = useContext(WorkspaceContext);
  if (!value) throw new Error('useWorkspace 必须在 WorkspaceProvider 内使用');
  return value;
}
