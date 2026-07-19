import { api } from './api';

let preferredProjectId = '';
let installed = false;
let restoreBridge: (() => void) | null = null;
const listeners = new Set<(projectId: string) => void>();

function publish(projectId: string) {
  if (!projectId) return;
  preferredProjectId = projectId;
  listeners.forEach((listener) => listener(projectId));
}

export function setPreferredProjectId(projectId: string) {
  preferredProjectId = projectId;
}

export function getPreferredProjectId() {
  return preferredProjectId;
}

export function subscribeProjectSelection(listener: (projectId: string) => void) {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}

export function resetProjectSelectionBridge() {
  restoreBridge?.();
}

export function installProjectSelectionBridge() {
  if (installed) return restoreBridge ?? (() => undefined);

  const originalListProjects = api.listProjects;
  const originalListChapters = api.listChapters;

  api.listProjects = async () => {
    const projects = await originalListProjects();
    if (!preferredProjectId) return projects;
    const preferred = projects.find((project) => project.id === preferredProjectId);
    if (!preferred) return projects;
    return [preferred, ...projects.filter((project) => project.id !== preferredProjectId)];
  };

  api.listChapters = async (projectId: string) => {
    publish(projectId);
    return originalListChapters(projectId);
  };

  installed = true;
  restoreBridge = () => {
    if (!installed) return;
    api.listProjects = originalListProjects;
    api.listChapters = originalListChapters;
    installed = false;
    restoreBridge = null;
    listeners.clear();
    preferredProjectId = '';
  };
  return restoreBridge;
}
