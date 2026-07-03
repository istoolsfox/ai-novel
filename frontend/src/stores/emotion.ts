import { defineStore } from "pinia";
import { ref } from "vue";
import { emotionApi } from "../api";
import type {
  EmotionSeed,
  Archaeology,
  EmotionalLead,
  ImageGrowth,
  ChapterBridge,
} from "../api/types";

export const useEmotionStore = defineStore("emotion", () => {
  const seed = ref<EmotionSeed | null>(null);
  const archaeologyList = ref<Archaeology[]>([]);
  const emotionalLeads = ref<EmotionalLead[]>([]);
  const imageGrowth = ref<ImageGrowth[]>([]);
  const bridges = ref<ChapterBridge[]>([]);
  const currentBridge = ref<ChapterBridge | null>(null);
  const loading = ref(false);

  async function fetchSeed(projectId: string, chapterId: string) {
    const data = await emotionApi.getSeed(projectId, chapterId);
    seed.value = (Object.keys(data).length > 0 ? data : null) as EmotionSeed | null;
  }

  async function fetchArchaeology(projectId: string, chapterId: string) {
    archaeologyList.value = await emotionApi.listArchaeology(projectId, chapterId);
  }

  async function fetchEmotionalLeads(projectId: string, status?: string) {
    emotionalLeads.value = await emotionApi.listEmotionalLeads(projectId, status);
  }

  async function fetchImageGrowth(projectId: string, imageName?: string) {
    imageGrowth.value = await emotionApi.listImageGrowth(projectId, imageName);
  }

  async function fetchBridge(projectId: string, chapterId: string) {
    const data = await emotionApi.getBridge(projectId, chapterId);
    currentBridge.value = (Object.keys(data).length > 0 ? data : null) as ChapterBridge | null;
  }

  async function fetchBridges(projectId: string) {
    bridges.value = await emotionApi.listBridges(projectId);
  }

  function clear() {
    seed.value = null;
    archaeologyList.value = [];
    emotionalLeads.value = [];
    imageGrowth.value = [];
    currentBridge.value = null;
  }

  return {
    seed,
    archaeologyList,
    emotionalLeads,
    imageGrowth,
    bridges,
    currentBridge,
    loading,
    fetchSeed,
    fetchArchaeology,
    fetchEmotionalLeads,
    fetchImageGrowth,
    fetchBridge,
    fetchBridges,
    clear,
  };
});
