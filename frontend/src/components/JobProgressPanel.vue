<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import {
  NCard, NButton, NSpace, NProgress, NTag, NTabs, NTabPane, NEmpty,
  NStatistic, NGrid, NGridItem, NText, NPopconfirm, useMessage,
} from "naive-ui";
import { useJobStore } from "../stores/job";
import { useChapterStore } from "../stores/chapter";
import CheckpointNotification from "./CheckpointNotification.vue";
import ChapterStream from "./ChapterStream.vue";

const route = useRoute();
const router = useRouter();
const message = useMessage();
const jobStore = useJobStore();
const chapterStore = useChapterStore();

const projectId = computed(() => route.params.projectId as string);
const jobId = computed(() => route.params.jobId as string);
const activeTab = ref("steps");

// 九步管线元数据
const STEP_META = [
  { name: "brief", label: "概要", icon: "📋" },
  { name: "seed", label: "情感种子", icon: "🌱" },
  { name: "draft", label: "初稿", icon: "✍️" },
  { name: "dialogue", label: "对话潜台词", icon: "💬" },
  { name: "archaeology", label: "情感考古", icon: "🔍" },
  { name: "reader_pull", label: "追读力", icon: "🎯" },
  { name: "deepen", label: "加深·藏回", icon: "⬇️" },
  { name: "anti_ai", label: "去AI味", icon: "🧹" },
  { name: "finalize", label: "定稿", icon: "✅" },
] as const;

onMounted(async () => {
  await jobStore.fetchJob(projectId.value, jobId.value);
  await jobStore.fetchSteps(projectId.value, jobId.value);
  await chapterStore.fetchChapters(projectId.value);
  jobStore.startStream(projectId.value, jobId.value);
});

onUnmounted(() => {
  jobStore.stopStream();
});

// 步骤状态计算
function getStepStatus(stepName: string): "done" | "active" | "pending" {
  const chapterNumber = displayedChapterNumber.value;
  const persisted = jobStore.steps
    .filter((step) => step.step_name === stepName && (!chapterNumber || step.chapter_number === chapterNumber))
    .pop();
  if (persisted?.step_status === "completed" || persisted?.step_status === "skipped" || persisted?.status === "done") {
    return "done";
  }
  if (persisted?.step_status === "running") {
    return "active";
  }
  const events = jobStore.sseEvents;
  const hasDone = events.some(
    (e) => e.type === "step" && e.step_name === stepName && ["completed", "skipped"].includes(e.status),
  );
  if (hasDone) return "done";
  const hasStart = events.some(
    (e) => e.type === "step" && e.step_name === stepName && e.status === "running",
  );
  if (hasStart) return "active";
  return "pending";
}

// 从 SSE 事件提取日志
const logLines = computed(() =>
  jobStore.sseEvents
    .filter((e) => e.type !== "heartbeat")
    .map((e) => {
      const time = new Date().toLocaleTimeString("zh-CN", { hour12: false });
      switch (e.type) {
        case "chapter_started":
          return `[${time}] 📖 开始生成第 ${e.chapter_number} 章`;
        case "chapter_completed":
          return `[${time}] ✅ 第 ${e.chapter_number} 章完成`;
        case "step":
          if (e.status === "running") return `[${time}] 🔄 ${e.step_name} 开始`;
          if (e.status === "completed") return `[${time}] ✅ ${e.step_name} 完成`;
          if (e.status === "skipped") return `[${time}] ⏭️ ${e.step_name} 跳过`;
          if (e.status === "failed") return `[${time}] ❌ ${e.step_name} 失败`;
          return `[${time}] ${e.step_name}: ${e.status}`;
        case "checkpoint":
          return `[${time}] ⚠️ 检查点触发: ${e.reason}`;
        case "smart_stop":
          return `[${time}] ⚠️ 智能停: ${e.reason}`;
        case "error":
          return `[${time}] ❌ 错误: ${e.message}`;
        case "auto_export_completed":
          return `[${time}] 📦 自动导出完成，可在导出页查看交付文件`;
        case "auto_export_failed":
          return `[${time}] ⚠️ 自动导出失败: ${e.error || e.message || "未知错误"}`;
        case "done":
          return `[${time}] 🎉 全部完成`;
        default:
          return `[${time}] ${e.type}: ${JSON.stringify(e).slice(0, 200)}`;
      }
    }),
);

// 检查点事件
const checkpointEvent = computed(() => {
  const cp = jobStore.sseEvents
    .filter((e) => e.type === "checkpoint" || e.type === "smart_stop")
    .pop();
  return cp;
});

// 进度百分比
const progressPercentage = computed(() => {
  if (!jobStore.currentJob) return 0;
  const total = jobStore.currentJob.target_chapter_count;
  const doneFromEvents = new Set(
    jobStore.sseEvents
      .filter((event) => event.type === "chapter_completed")
      .map((event) => event.chapter_number),
  ).size;
  const done = Math.max(jobStore.currentJob.completed_chapter_count ?? 0, doneFromEvents);
  const derived = total > 0 ? Math.round((done / total) * 100) : 0;
  return Math.max(jobStore.currentJob.progress_percent ?? 0, derived);
});

const displayedChapterNumber = computed(() => {
  if (jobStore.currentChapterNumber) return jobStore.currentChapterNumber;
  if (jobStore.currentJob?.current_chapter_number) return jobStore.currentJob.current_chapter_number;
  const latestStep = [...jobStore.steps].reverse().find((step) => step.chapter_number);
  return latestStep?.chapter_number || jobStore.currentJob?.completed_chapter_count || 0;
});

async function handlePause() {
  try {
    await jobStore.pauseJob(projectId.value, jobId.value);
    message.info("已暂停");
  } catch (e: any) {
    message.error(e.message);
  }
}

async function handleResume() {
  try {
    await jobStore.resumeJob(projectId.value, jobId.value);
    message.success("已恢复");
    jobStore.startStream(projectId.value, jobId.value);
  } catch (e: any) {
    message.error(e.message);
  }
}

async function handleAbort() {
  try {
    await jobStore.abortJob(projectId.value, jobId.value);
    message.warning("已中止");
    jobStore.stopStream();
  } catch (e: any) {
    message.error(e.message);
  }
}

async function handleCheckpointContinue() {
  try {
    await jobStore.continueCheckpoint(projectId.value, jobId.value);
    message.success("已放行检查点");
    jobStore.startStream(projectId.value, jobId.value);
  } catch (e: any) {
    message.error(e.message);
  }
}

const jobStatus = computed(() => jobStore.currentJob?.status || "unknown");
const isRunning = computed(() => jobStatus.value === "running");
const isPaused = computed(() => jobStatus.value === "paused" || jobStatus.value === "checkpoint");
</script>

<template>
  <div class="progress-page">
    <!-- 检查点通知 -->
    <CheckpointNotification
      v-if="checkpointEvent"
      :event="checkpointEvent"
      @continue="handleCheckpointContinue"
      @abort="handleAbort"
    />

    <!-- 顶部概览 -->
    <NCard style="margin-bottom: 16px">
      <NGrid :cols="4" :x-gap="16">
        <NGridItem>
          <NStatistic
            label="当前章节"
            :value="displayedChapterNumber"
          />
        </NGridItem>
        <NGridItem>
          <NStatistic
            label="总章数"
            :value="jobStore.currentJob?.target_chapter_count || 0"
          />
        </NGridItem>
        <NGridItem>
          <NStatistic label="进度" :value="`${progressPercentage}%`" />
        </NGridItem>
        <NGridItem>
          <NTag
            :type="isRunning ? 'success' : isPaused ? 'warning' : 'default'"
            size="large"
          >
            {{ jobStatus }}
          </NTag>
        </NGridItem>
      </NGrid>
      <NProgress
        type="line"
        :percentage="progressPercentage"
        :show-indicator="false"
        style="margin-top: 16px"
      />
    </NCard>

    <!-- 九步明细 + 标签页 -->
    <NCard>
      <NTabs v-model:value="activeTab" type="line" animated>
        <NTabPane name="steps" tab="九步进度">
          <div class="steps-grid">
            <div
              v-for="(step, idx) in STEP_META"
              :key="step.name"
              class="step-row"
            >
              <span class="step-index">{{ idx + 1 }}</span>
              <span class="step-icon">{{ step.icon }}</span>
              <span class="step-label">{{ step.label }}</span>
              <span class="step-name">{{ step.name }}</span>
              <span
                class="step-dot"
                :class="getStepStatus(step.name)"
              />
            </div>
          </div>
        </NTabPane>

        <NTabPane name="chapters" tab="章节列表">
          <ChapterStream
            :project-id="projectId"
            :chapters="chapterStore.chapters"
            :current-chapter="jobStore.currentChapterNumber"
          />
        </NTabPane>

        <NTabPane name="logs" tab="日志流">
          <div class="log-stream">
            <NEmpty v-if="logLines.length === 0" description="等待日志..." />
            <div v-for="(line, idx) in logLines" :key="idx" class="log-line">
              {{ line }}
            </div>
          </div>
        </NTabPane>
      </NTabs>

      <!-- 控制按钮 -->
      <NSpace justify="end" style="margin-top: 16px">
        <NButton
          v-if="isRunning"
          type="warning"
          @click="handlePause"
        >暂停</NButton>
        <NButton
          v-if="isPaused"
          type="success"
          @click="handleResume"
        >恢复</NButton>
        <NPopconfirm @positive-click="handleAbort">
          <template #trigger>
            <NButton type="error" ghost>中止任务</NButton>
          </template>
          确认中止此生成任务？已生成的章节不会丢失。
        </NPopconfirm>
        <NButton
          v-if="jobStore.currentJob && jobStatus === 'completed'"
          type="primary"
          @click="router.push({ name: 'JobResults', params: { projectId, jobId } })"
        >查看结果</NButton>
      </NSpace>
    </NCard>
  </div>
</template>

<style scoped>
.progress-page { max-width: 900px; }
.steps-grid {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.step-row {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px 12px;
  border-radius: 8px;
  background: rgba(128, 128, 128, 0.04);
  transition: background 0.15s;
}
.step-row:hover {
  background: rgba(128, 128, 128, 0.08);
}
.step-index {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: rgba(128, 128, 128, 0.15);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 600;
  color: #888;
}
.step-icon { font-size: 16px; }
.step-label { font-weight: 500; min-width: 80px; }
.step-name { color: #999; font-size: 12px; font-family: monospace; flex: 1; }
.step-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
}
.step-dot.done { background: #18a058; }
.step-dot.active { background: #2080f0; animation: pulse 1.2s infinite; }
.step-dot.pending { background: #d4d4d4; }
</style>
