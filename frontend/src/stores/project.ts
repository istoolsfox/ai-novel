import { defineStore } from "pinia";
import { ref } from "vue";
import { projectApi } from "../api";
import type { Project, ProjectInput } from "../api/types";

export const useProjectStore = defineStore("project", () => {
  const projects = ref<Project[]>([]);
  const currentProject = ref<Project | null>(null);
  const loading = ref(false);

  async function fetchProjects() {
    loading.value = true;
    try {
      projects.value = await projectApi.list();
    } finally {
      loading.value = false;
    }
  }

  async function fetchProject(id: string) {
    loading.value = true;
    try {
      currentProject.value = await projectApi.get(id);
    } finally {
      loading.value = false;
    }
  }

  async function createProject(data: ProjectInput): Promise<Project> {
    const project = await projectApi.create(data);
    projects.value.unshift(project);
    return project;
  }

  async function updateProject(id: string, data: ProjectInput) {
    const updated = await projectApi.update(id, data);
    const idx = projects.value.findIndex((p) => p.id === id);
    if (idx >= 0) projects.value[idx] = updated;
    if (currentProject.value?.id === id) currentProject.value = updated;
    return updated;
  }

  async function deleteProject(id: string, password: string) {
    await projectApi.delete(id, password);
    projects.value = projects.value.filter((p) => p.id !== id);
  }

  return {
    projects,
    currentProject,
    loading,
    fetchProjects,
    fetchProject,
    createProject,
    updateProject,
    deleteProject,
  };
});
