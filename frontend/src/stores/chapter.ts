import { defineStore } from "pinia";
import { ref } from "vue";
import { chapterApi } from "../api";
import type { Chapter, ChapterInput, ChapterVersion, VersionInput } from "../api/types";

export const useChapterStore = defineStore("chapter", () => {
  const chapters = ref<Chapter[]>([]);
  const currentChapter = ref<Chapter | null>(null);
  const versions = ref<ChapterVersion[]>([]);
  const loading = ref(false);

  async function fetchChapters(projectId: string) {
    loading.value = true;
    try {
      chapters.value = await chapterApi.list(projectId);
    } finally {
      loading.value = false;
    }
  }

  async function fetchChapter(projectId: string, chapterId: string) {
    currentChapter.value = await chapterApi.get(projectId, chapterId);
  }

  async function createChapter(projectId: string, data: ChapterInput) {
    const chapter = await chapterApi.create(projectId, data);
    chapters.value.push(chapter);
    chapters.value.sort((a, b) => a.chapter_number - b.chapter_number);
    return chapter;
  }

  async function updateChapter(
    projectId: string,
    chapterId: string,
    data: ChapterInput,
  ) {
    const updated = await chapterApi.update(projectId, chapterId, data);
    const idx = chapters.value.findIndex((c) => c.id === chapterId);
    if (idx >= 0) chapters.value[idx] = updated;
    if (currentChapter.value?.id === chapterId) currentChapter.value = updated;
    return updated;
  }

  async function deleteChapter(projectId: string, chapterId: string) {
    await chapterApi.delete(projectId, chapterId);
    chapters.value = chapters.value.filter((c) => c.id !== chapterId);
  }

  async function finalizeChapter(projectId: string, chapterId: string) {
    const chapter = await chapterApi.finalize(projectId, chapterId);
    const idx = chapters.value.findIndex((c) => c.id === chapterId);
    if (idx >= 0) chapters.value[idx] = chapter;
    return chapter;
  }

  async function fetchVersions(projectId: string, chapterId: string) {
    versions.value = await chapterApi.listVersions(projectId, chapterId);
  }

  async function createVersion(
    projectId: string,
    chapterId: string,
    data: VersionInput,
  ) {
    const version = await chapterApi.createVersion(projectId, chapterId, data);
    versions.value.unshift(version);
    return version;
  }

  async function selectVersion(
    projectId: string,
    chapterId: string,
    versionId: string,
  ) {
    const chapter = await chapterApi.selectVersion(projectId, chapterId, versionId);
    const idx = chapters.value.findIndex((c) => c.id === chapterId);
    if (idx >= 0) chapters.value[idx] = chapter;
    if (currentChapter.value?.id === chapterId) currentChapter.value = chapter;
    return chapter;
  }

  return {
    chapters,
    currentChapter,
    versions,
    loading,
    fetchChapters,
    fetchChapter,
    createChapter,
    updateChapter,
    deleteChapter,
    finalizeChapter,
    fetchVersions,
    createVersion,
    selectVersion,
  };
});
