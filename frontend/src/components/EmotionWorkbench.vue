<script setup lang="ts">
import { ref, computed, onMounted, watch } from "vue";
import { useRoute } from "vue-router";
import {
  NCard, NSelect, NSpace, NTabs, NTabPane, NEmpty, NTag, NText,
  NCollapse, NCollapseItem, NDescriptions, NDescriptionsItem, NSpin,
} from "naive-ui";
import { useEmotionStore } from "../stores/emotion";
import { useChapterStore } from "../stores/chapter";

const route = useRoute();
const emotionStore = useEmotionStore();
const chapterStore = useChapterStore();

const projectId = computed(() => route.params.projectId as string);
const selectedChapterId = ref<string | null>(null);
const activeTab = ref("archaeology");

onMounted(async () => {
  await chapterStore.fetchChapters(projectId.value);
  if (chapterStore.chapters.length > 0) {
    selectedChapterId.value = chapterStore.chapters[0].id;
  }
});

watch(selectedChapterId, async (chapterId) => {
  if (!chapterId) return;
  emotionStore.clear();
  await Promise.all([
    emotionStore.fetchSeed(projectId.value, chapterId),
    emotionStore.fetchArchaeology(projectId.value, chapterId),
    emotionStore.fetchBridge(projectId.value, chapterId),
  ]);
});

const chapterOptions = computed(() =>
  chapterStore.chapters.map((ch) => ({
    label: `第 ${ch.chapter_number} 章 · ${ch.title || "未命名"}`,
    value: ch.id,
  })),
);

const currentArchaeology = computed(() =>
  emotionStore.archaeologyList[0] || null,
);

const FIVE_LAYERS = [
  { key: "surface_layer", label: "表层", icon: "🌊" },
  { key: "emotional_layer", label: "情感层", icon: "💗" },
  { key: "intention_layer", label: "意层", icon: "🎯" },
  { key: "subconscious_layer", label: "潜层", icon: "🌀" },
  { key: "resonance_layer", label: "韵层", icon: "🎵" },
] as const;
</script>

<template>
  <div class="emotion-page">
    <h2 style="margin-bottom: 16px">情感工作台</h2>

    <NCard style="margin-bottom: 16px">
      <NSpace align="center">
        <NText>选择章节：</NText>
        <NSelect
          v-model:value="selectedChapterId"
          :options="chapterOptions"
          style="width: 300px"
          placeholder="选择章节"
        />
      </NSpace>
    </NCard>

    <NEmpty v-if="!selectedChapterId" description="请选择章节" style="margin-top: 60px" />

    <div v-else>
      <NTabs v-model:value="activeTab" type="line" animated>
        <!-- 五层考古 -->
        <NTabPane name="archaeology" tab="五层考古">
          <NSpin v-if="emotionStore.loading" />
          <NEmpty v-else-if="!currentArchaeology" description="该章节暂无考古记录" />
          <NCollapse v-else accordion>
            <NCollapseItem
              v-for="layer in FIVE_LAYERS"
              :key="layer.key"
              :title="`${layer.icon} ${layer.label}`"
              :name="layer.key"
            >
              <div class="layer-content">
                {{ (currentArchaeology as any)[layer.key] || "（无数据）" }}
              </div>
            </NCollapseItem>
          </NCollapse>

          <NCard v-if="currentArchaeology" title="考古发现" size="small" style="margin-top: 16px">
            <NDescriptions :column="1" size="small" label-placement="left">
              <NDescriptionsItem label="潜意识线索">{{ currentArchaeology.subconscious_leads || "—" }}</NDescriptionsItem>
              <NDescriptionsItem label="母题回响">{{ currentArchaeology.motif_echoes || "—" }}</NDescriptionsItem>
              <NDescriptionsItem label="读者体感">{{ currentArchaeology.reader_felt || "—" }}</NDescriptionsItem>
            </NDescriptions>
          </NCard>
        </NTabPane>

        <!-- 情感种子 -->
        <NTabPane name="seed" tab="情感种子">
          <NEmpty v-if="!emotionStore.seed" description="暂无情感种子" />
          <NCard v-else>
            <div class="seed-content">{{ emotionStore.seed.emotion_seed }}</div>
          </NCard>
        </NTabPane>

        <!-- 章节衔接包 -->
        <NTabPane name="bridge" tab="衔接包">
          <NEmpty v-if="!emotionStore.currentBridge" description="暂无衔接包" />
          <NDescriptions v-else :column="1" size="small" label-placement="left" bordered>
            <NDescriptionsItem label="结尾状态">{{ emotionStore.currentBridge.ending_state || "—" }}</NDescriptionsItem>
            <NDescriptionsItem label="开篇钩子">{{ emotionStore.currentBridge.opening_hook || "—" }}</NDescriptionsItem>
            <NDescriptionsItem label="遗留细节">{{ emotionStore.currentBridge.carry_over_details || "—" }}</NDescriptionsItem>
            <NDescriptionsItem label="情感余韵">{{ emotionStore.currentBridge.emotional_residue || "—" }}</NDescriptionsItem>
            <NDescriptionsItem label="悬念线索">{{ emotionStore.currentBridge.pending_threads || "—" }}</NDescriptionsItem>
          </NDescriptions>
        </NTabPane>
      </NTabs>
    </div>
  </div>
</template>

<style scoped>
.emotion-page { max-width: 800px; }
.layer-content {
  white-space: pre-wrap;
  line-height: 1.8;
  padding: 8px 0;
  color: #555;
}
.seed-content {
  white-space: pre-wrap;
  line-height: 2;
  font-size: 15px;
}
</style>
