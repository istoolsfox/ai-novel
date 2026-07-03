import { defineStore } from "pinia";
import { ref, computed } from "vue";
import { jobApi } from "../api";
import type { GenerationJob, StepRecord, SSEEvent } from "../api/types";

export const useJobStore = defineStore("job", () => {
  const jobs = ref<GenerationJob[]>([]);
  const currentJob = ref<GenerationJob | null>(null);
  const steps = ref<StepRecord[]>([]);
  const sseEvents = ref<SSEEvent[]>([]);
  const isStreaming = ref(false);

  // 九步管线步骤名称
  const PIPELINE_STEPS = [
    "brief",
    "seed",
    "draft",
    "dialogue",
    "archaeology",
    "reader_pull",
    "deepen",
    "anti_ai",
    "finalize",
  ] as const;

  // 当前正在执行的步骤索引
  const currentStepIndex = computed(() => {
    const lastActive = sseEvents.value
      .filter((e) => e.type === "step_start" || e.type === "step_done")
      .pop();
    if (!lastActive) return -1;
    if (lastActive.type === "step_done") {
      const stepName = lastActive.step_name as string;
      const idx = PIPELINE_STEPS.indexOf(stepName as any);
      return idx + 1;
    }
    const stepName = lastActive.step_name as string;
    return PIPELINE_STEPS.indexOf(stepName as any);
  });

  // 当前章节号
  const currentChapterNumber = computed(() => {
    const chapterEvent = sseEvents.value
      .filter((e) => e.type === "chapter_start")
      .pop();
    return chapterEvent?.chapter_number ?? 0;
  });

  async function fetchJobs(projectId: string) {
    jobs.value = await jobApi.list(projectId);
  }

  async function fetchJob(projectId: string, jobId: string) {
    currentJob.value = await jobApi.get(projectId, jobId);
  }

  async function fetchSteps(projectId: string, jobId: string) {
    steps.value = await jobApi.listSteps(projectId, jobId);
  }

  async function startJob(
    projectId: string,
    data: Parameters<typeof jobApi.start>[1],
  ) {
    const job = await jobApi.start(projectId, data);
    jobs.value.unshift(job);
    currentJob.value = job;
    return job;
  }

  async function pauseJob(projectId: string, jobId: string) {
    currentJob.value = await jobApi.pause(projectId, jobId);
  }

  async function resumeJob(projectId: string, jobId: string) {
    currentJob.value = await jobApi.resume(projectId, jobId);
  }

  async function abortJob(projectId: string, jobId: string) {
    currentJob.value = await jobApi.abort(projectId, jobId);
  }

  async function continueCheckpoint(projectId: string, jobId: string) {
    currentJob.value = await jobApi.continueCheckpoint(projectId, jobId);
  }

  let closeSSE: (() => void) | null = null;

  function startStream(projectId: string, jobId: string) {
    sseEvents.value = [];
    isStreaming.value = true;
    closeSSE = jobApi.subscribe(
      projectId,
      jobId,
      (event: SSEEvent) => {
        sseEvents.value.push(event);
        if (event.type === "done") {
          isStreaming.value = false;
          closeSSE = null;
        }
      },
      () => {
        isStreaming.value = false;
        closeSSE = null;
      },
    );
  }

  function stopStream() {
    if (closeSSE) {
      closeSSE();
      closeSSE = null;
    }
    isStreaming.value = false;
  }

  function clearEvents() {
    sseEvents.value = [];
  }

  return {
    jobs,
    currentJob,
    steps,
    sseEvents,
    isStreaming,
    PIPELINE_STEPS,
    currentStepIndex,
    currentChapterNumber,
    fetchJobs,
    fetchJob,
    fetchSteps,
    startJob,
    pauseJob,
    resumeJob,
    abortJob,
    continueCheckpoint,
    startStream,
    stopStream,
    clearEvents,
  };
});
