import { useEffect, useState } from 'react';
import { api, Chapter, Project } from '../api';

export function useProjects() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    api.listProjects().then((items) => {
      setProjects(items);
      setLoading(false);
    }).catch(() => setLoading(false));
  }, []);
  return { projects, loading };
}

export function useProject(projectId?: string) {
  const { projects, loading } = useProjects();
  const project = projects.find((p) => p.id === projectId) ?? null;
  return { project, loading };
}

export function useChapters(projectId?: string) {
  const [chapters, setChapters] = useState<Chapter[]>([]);
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    if (!projectId) return;
    setLoading(true);
    api.listChapters(projectId).then((items) => {
      setChapters(items);
      setLoading(false);
    }).catch(() => setLoading(false));
  }, [projectId]);
  return { chapters, loading };
}
