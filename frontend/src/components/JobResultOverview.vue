<script setup lang="ts">
import { ref, computed, onMounted } from "vue";
import { useRoute } from "vue-router";
import {
  NCard, NGrid, NGridItem, NStatistic, NSpace, NTag, NEmpty, NButton,
  NText, NCollapse, NCollapseItem, NDescriptions, NDescriptionsItem,
} from "naive-ui";
import { jobApi, emotionApi, chapterApi } from "../api";
import type { GenerationJob, StepRecord, Chapter, ChapterBridge } from "../api/types";

const route = useRoute();
const projectId = computed(() => route.params.projectId as string);
const jobId = computed(() => route.params.jobId as string);

const job = ref<GenerationJob | null>(null);
const steps = ref<StepRecord[]>([]);
const chapters = ref<Chapter[]>([]);
const bridges = ref<ChapterBridge[]>([]);

onMounted(async () => {
  job.value = await jobApi.get(projectId.value, jobId.value);
  steps.value = await jobApi.listSteps(projectId.value, jobId.value);
  chapters.value = await chapterApi.list(projectId.value);
  bridges.value = await emotionApi.listBridges(projectId.value);
});

const totalWords = computed(() =>
  chapters.value.reduce((sum, c) => sum + (c.word_count || 0), 0),
);

const completedSteps = computed(() =>
  steps.value.filter((s) => s.status === "done"),
);

const stepDurations = computed(() => {
  const map: Record<string, number> = {};
  for (const s of steps.value) {
    if (s.status === "done" && s.duration_ms) {
      map[s.step_name] = (map[s.step_name] || 0) + s.duration_ms;
    }
  }
  return map;
});
</script>

<template>
  <div class="results-page">
    <h2 style="margin-bottom: 20px">生成结果总览</h2>

    <NGrid :cols="4" :x-gap="16" :y-gap="16" style="margin-bottom: 16px">
      <NGridItem>
        <NCard>
          <NStatistic label="完成章节" :value="job?.completed_chapter_count || 0" />
        </NCard>
      </NGridItem>
      <NGridItem>
        <NCard>
          <NStatistic label="目标章节" :value="job?.target_chapter_count || 0" />
        </NCard>
      </NGridItem>
      <NGridItem>
        <NCard>
          <NStatistic label="总字数" :value="totalWords" />
        </NCard>
      </NGridItem>
      <NGridItem>
        <NCard>
          <NStatistic label="总步骤" :value="completedSteps.length" />
        </NCard>
      </NGridItem>
    </NGrid>

    <!-- 衔接包链 -->
    <NCard title="衔接包链" style="margin-bottom: 16px">
      <NEmpty v-if="bridges.length === 0" description="暂无衔接包" />
      <NCollapse v-else accordion>
        <NCollapseItem
          v-for="bridge in bridges"
          :key="bridge.id"
          :title="`第 ${bridge.chapter_number} 章 → 下一章`"
          :name="bridge.id"
        >
          <NDescriptions :column="1" size="small" label-placement="left">
            <NDescriptionsItem label="结尾状态">{{ bridge.ending_state || "—" }}</NDescriptionsItem>
            <NDescriptionsItem label="开篇钩子">{{ bridge.opening_hook || "—" }}</NDescriptionsItem>
            <NDescriptionsItem label="遗留细节">{{ bridge.carry_over_details || "—" }}</NDescriptionsItem>
            <NDescriptionsItem label="情感余韵">{{ bridge.emotional_residue || "—" }}</NDescriptionsItem>
            <NDescriptionsItem label="悬念线索">{{ bridge.pending_threads || "—" }}</NDescriptionsItem>
          </NDescriptions>
        </NCollapseItem>
      </NCollapse>
    </NCard>

    <!-- 步骤耗时统计 -->
    <NCard title="步骤耗时统计">
      <NEmpty v-if="Object.keys(stepDurations).length === 0" description="暂无数据" />
      <div v-else class="duration-list">
        <div v-for="(ms, name) in stepDurations" :key="name" class="duration-item">
          <NText>{{ name }}</NText>
          <div class="duration-bar">
            <div
              class="duration-fill"
              :style="{ width: `${Math.min((ms / Math.max(...Object.values(stepDurations))) * 100, 100)}%` }"
            />
          </div>
          <NText depth="3" style="font-size: 12px; min-width: 60px; text-align: right">
            {{ (ms / 1000).toFixed(1) }}s
          </NText>
        </div>
      </div>
    </NCard>
  </div>
</template>

<style scoped>
.results-page { max-width: 800px; }
.duration-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.duration-item {
  display: flex;
  align-items: center;
  gap: 12px;
}
.duration-bar {
  flex: 1;
  height: 8px;
  border-radius: 4px;
  background: rgba(128, 128, 128, 0.1);
  overflow: hidden;
}
.duration-fill {
  height: 100%;
  background: #2080f0;
  border-radius: 4px;
  transition: width 0.3s;
}
</style>
