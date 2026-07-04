<script setup lang="ts">
import { ref, computed, onMounted } from "vue";
import { useRoute } from "vue-router";
import {
  NCard, NGrid, NGridItem, NStatistic, NSpace, NTag, NEmpty, NButton,
  NText, NCollapse, NCollapseItem, NDescriptions, NDescriptionsItem,
  NProgress,
} from "naive-ui";
import { jobApi, emotionApi, chapterApi } from "../api";
import type { GenerationJob, StepRecord, Chapter, ChapterBridge, ChapterQualityScore } from "../api/types";

const route = useRoute();
const projectId = computed(() => route.params.projectId as string);
const jobId = computed(() => route.params.jobId as string);

const job = ref<GenerationJob | null>(null);
const steps = ref<StepRecord[]>([]);
const chapters = ref<Chapter[]>([]);
const bridges = ref<ChapterBridge[]>([]);
const qualityScores = ref<Record<string, ChapterQualityScore | null>>({});

onMounted(async () => {
  job.value = await jobApi.get(projectId.value, jobId.value);
  steps.value = await jobApi.listSteps(projectId.value, jobId.value);
  chapters.value = await chapterApi.list(projectId.value);
  bridges.value = await emotionApi.listBridges(projectId.value);
  const scoreEntries = await Promise.all(
    chapters.value.map(async (chapter) => {
      const scores = await chapterApi.listQualityScores(projectId.value, chapter.id);
      return [chapter.id, scores[0] || null] as const;
    }),
  );
  qualityScores.value = Object.fromEntries(scoreEntries);
});

const totalWords = computed(() =>
  chapters.value.reduce((sum, c) => sum + (c.word_count || 0), 0),
);

const completedSteps = computed(() =>
  steps.value.filter((s) => s.step_status === "completed" || s.status === "done"),
);

const stepDurations = computed(() => {
  const map: Record<string, number> = {};
  for (const s of steps.value) {
    if ((s.step_status === "completed" || s.status === "done") && s.duration_ms) {
      map[s.step_name] = (map[s.step_name] || 0) + s.duration_ms;
    }
  }
  return map;
});

const averageQualityScore = computed(() => {
  const scored = chapters.value.filter((chapter) => chapter.quality_score > 0);
  if (!scored.length) return 0;
  return Math.round(scored.reduce((sum, chapter) => sum + chapter.quality_score, 0) / scored.length);
});

function qualityTagType(score?: number) {
  if (!score) return "default";
  if (score >= 85) return "success";
  if (score >= 70) return "warning";
  return "error";
}

function qualityIssues(score?: ChapterQualityScore | null) {
  const issues = score?.payload?.issues;
  return Array.isArray(issues) ? issues : [];
}
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

    <!-- 自动质量报告 -->
    <NCard title="章节质量报告" style="margin-bottom: 16px">
      <NEmpty v-if="chapters.length === 0" description="暂无章节" />
      <div v-else>
        <NSpace align="center" style="margin-bottom: 14px">
          <NText depth="3">平均质量分</NText>
          <NProgress
            type="line"
            :percentage="averageQualityScore"
            :status="averageQualityScore >= 85 ? 'success' : averageQualityScore >= 70 ? 'warning' : 'error'"
            style="width: 220px"
          />
        </NSpace>
        <NCollapse>
          <NCollapseItem
            v-for="chapter in chapters"
            :key="chapter.id"
            :title="`第 ${chapter.chapter_number} 章 · ${chapter.title || '未命名'} · ${chapter.quality_score || 0} 分`"
            :name="chapter.id"
          >
            <NSpace vertical size="small">
              <NSpace align="center">
                <NTag :type="qualityTagType(chapter.quality_score)" size="small">
                  {{ chapter.quality_score || 0 }} 分
                </NTag>
                <NTag
                  v-if="qualityScores[chapter.id]?.payload?.metrics?.is_final_chapter"
                  type="info"
                  size="small"
                >
                  终章
                </NTag>
                <NTag
                  v-if="qualityScores[chapter.id]?.payload?.metrics?.open_hook_count"
                  type="warning"
                  size="small"
                >
                  未回收钩子 {{ qualityScores[chapter.id]?.payload?.metrics?.open_hook_count }}
                </NTag>
              </NSpace>
              <NDescriptions :column="3" size="small" label-placement="left">
                <NDescriptionsItem label="字数">{{ chapter.word_count }}</NDescriptionsItem>
                <NDescriptionsItem label="重复片段">
                  {{ qualityScores[chapter.id]?.payload?.metrics?.repeated_fragment_count ?? 0 }}
                </NDescriptionsItem>
                <NDescriptionsItem label="报告状态">
                  {{ qualityScores[chapter.id]?.payload?.ok ? "通过" : "需关注" }}
                </NDescriptionsItem>
              </NDescriptions>
              <div v-if="qualityIssues(qualityScores[chapter.id]).length" class="issue-list">
                <NTag
                  v-for="issue in qualityIssues(qualityScores[chapter.id])"
                  :key="issue"
                  type="error"
                  size="small"
                >
                  {{ issue }}
                </NTag>
              </div>
              <NText v-else depth="3">没有发现明显烂尾、占位符或正文结构风险。</NText>
            </NSpace>
          </NCollapseItem>
        </NCollapse>
      </div>
    </NCard>

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
