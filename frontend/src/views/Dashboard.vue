<script setup lang="ts">
import { computed, onMounted } from "vue";
import { useRoute } from "vue-router";
import { NCard, NGrid, NGridItem, NStatistic, NSpace, NTag, NEmpty, NButton } from "naive-ui";
import { useProjectStore } from "../stores/project";
import { useChapterStore } from "../stores/chapter";
import { useJobStore } from "../stores/job";

const route = useRoute();
const projectStore = useProjectStore();
const chapterStore = useChapterStore();
const jobStore = useJobStore();

const projectId = computed(() => route.params.projectId as string);

onMounted(async () => {
  await projectStore.fetchProject(projectId.value);
  await chapterStore.fetchChapters(projectId.value);
  await jobStore.fetchJobs(projectId.value);
});

const project = computed(() => projectStore.currentProject);
const totalWords = computed(() =>
  chapterStore.chapters.reduce((sum, c) => sum + (c.word_count || 0), 0),
);
const completedChapters = computed(
  () => chapterStore.chapters.filter((c) => c.status === "finalized").length,
);
const activeJobs = computed(
  () => jobStore.jobs.filter((j) => j.status === "running" || j.status === "paused").length,
);
</script>

<template>
  <div v-if="project" class="dashboard-page">
    <NCard>
      <h2 style="margin-bottom: 8px">{{ project.title }}</h2>
      <p v-if="project.logline" style="color: #888; margin-bottom: 16px">
        {{ project.logline }}
      </p>
      <NSpace>
        <NTag v-if="project.genre" size="small">{{ project.genre }}</NTag>
        <NTag v-if="project.tone" size="small">{{ project.tone }}</NTag>
        <NTag v-if="project.audience" size="small">{{ project.audience }}</NTag>
      </NSpace>
    </NCard>

    <NGrid :cols="4" :x-gap="16" :y-gap="16" style="margin-top: 16px">
      <NGridItem>
        <NCard>
          <NStatistic label="总章节" :value="chapterStore.chapters.length" />
        </NCard>
      </NGridItem>
      <NGridItem>
        <NCard>
          <NStatistic label="已定稿" :value="completedChapters" />
        </NCard>
      </NGridItem>
      <NGridItem>
        <NCard>
          <NStatistic label="总字数" :value="totalWords" />
        </NCard>
      </NGridItem>
      <NGridItem>
        <NCard>
          <NStatistic label="活跃任务" :value="activeJobs" />
        </NCard>
      </NGridItem>
    </NGrid>

    <NCard title="最近章节" style="margin-top: 16px">
      <NEmpty v-if="chapterStore.chapters.length === 0" description="还没有章节" />
      <div v-else class="chapter-list">
        <div
          v-for="ch in chapterStore.chapters.slice(-5).reverse()"
          :key="ch.id"
          class="chapter-item"
        >
          <span class="ch-number">第 {{ ch.chapter_number }} 章</span>
          <span class="ch-title">{{ ch.title || "未命名" }}</span>
          <NTag
            size="tiny"
            :type="ch.status === 'finalized' ? 'success' : 'default'"
          >
            {{ ch.status }}
          </NTag>
          <span class="ch-words">{{ ch.word_count || 0 }} 字</span>
        </div>
      </div>
    </NCard>
  </div>
  <div v-else class="loading-state">加载中...</div>
</template>

<style scoped>
.dashboard-page {
  max-width: 900px;
}
.loading-state {
  text-align: center;
  padding: 60px;
  color: #999;
}
.chapter-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.chapter-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px 12px;
  border-radius: 8px;
  transition: background 0.15s;
}
.chapter-item:hover {
  background: rgba(128, 128, 128, 0.06);
}
.ch-number {
  font-weight: 600;
  min-width: 80px;
}
.ch-title {
  flex: 1;
  color: #555;
}
.ch-words {
  font-size: 12px;
  color: #999;
}
</style>
