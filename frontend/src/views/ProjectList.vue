<script setup lang="ts">
import { onMounted, ref, computed } from "vue";
import { useRouter } from "vue-router";
import {
  NCard,
  NButton,
  NSpace,
  NInput,
  NModal,
  NForm,
  NFormItem,
  NInputNumber,
  NSwitch,
  NEmpty,
  NTag,
  NText,
  useMessage,
} from "naive-ui";
import { useProjectStore } from "../stores/project";
import type { ProjectInput } from "../api/types";

const router = useRouter();
const projectStore = useProjectStore();
const message = useMessage();

const showModal = ref(false);
const form = ref<ProjectInput>({
  title: "",
  topic: "",
  genre: "",
  audience: "",
  tone: "",
  target_chapter_count: 20,
  target_words_per_chapter: 3000,
  logline: "",
  synopsis: "",
  privacy_mode: true,
});

onMounted(() => {
  projectStore.fetchProjects();
});

async function handleCreate() {
  if (!form.value.title.trim()) {
    message.warning("请输入项目标题");
    return;
  }
  try {
    const project = await projectStore.createProject(form.value);
    message.success("项目创建成功");
    showModal.value = false;
    form.value = {
      title: "",
      topic: "",
      genre: "",
      audience: "",
      tone: "",
      target_chapter_count: 20,
      target_words_per_chapter: 3000,
      logline: "",
      synopsis: "",
      privacy_mode: true,
    };
    router.push(`/projects/${project.id}`);
  } catch (e: any) {
    message.error(`创建失败: ${e.message}`);
  }
}

function openProject(id: string) {
  router.push(`/projects/${id}`);
}

const isEmpty = computed(
  () => !projectStore.loading && projectStore.projects.length === 0,
);
</script>

<template>
  <div class="project-list-page">
    <div class="page-header">
      <h1>我的项目</h1>
      <NButton type="primary" @click="showModal = true">+ 新建项目</NButton>
    </div>

    <div v-if="projectStore.loading" class="loading-state">加载中...</div>

    <NEmpty
      v-else-if="isEmpty"
      description="还没有项目，点击右上角创建第一个吧"
      style="margin-top: 100px"
    />

    <div v-else class="project-grid">
      <NCard
        v-for="project in projectStore.projects"
        :key="project.id"
        class="project-card"
        hoverable
        @click="openProject(project.id)"
      >
        <template #header>
          <NSpace align="center" justify="space-between">
            <span class="project-title">{{ project.title }}</span>
            <NTag size="small" :type="
              project.status === 'completed' ? 'success' :
              project.status === 'generating' ? 'warning' : 'default'
            ">
              {{ project.status }}
            </NTag>
          </NSpace>
        </template>
        <p class="project-synopsis">
          {{ project.synopsis || project.topic || "暂无简介" }}
        </p>
        <template #footer>
          <NSpace size="small">
            <NTag v-if="project.genre" size="small">{{ project.genre }}</NTag>
            <NText depth="3" style="font-size: 12px">
              {{ project.target_chapter_count }} 章 × {{ project.target_words_per_chapter }} 字
            </NText>
          </NSpace>
        </template>
      </NCard>
    </div>

    <!-- 新建项目弹窗 -->
    <NModal
      v-model:show="showModal"
      preset="card"
      title="新建项目"
      style="width: 600px"
      :bordered="false"
    >
      <NForm label-placement="top">
        <NFormItem label="项目标题" required>
          <NInput v-model:value="form.title" placeholder="给你的小说起个名字" />
        </NFormItem>
        <NFormItem label="题材/类型">
          <NInput v-model:value="form.genre" placeholder="如：都市悬疑、奇幻冒险" />
        </NFormItem>
        <NFormItem label="一句话梗概">
          <NInput
            v-model:value="form.logline"
            type="textarea"
            :autosize="{ minRows: 2 }"
            placeholder="用一句话概括核心故事"
          />
        </NFormItem>
        <NFormItem label="故事简介">
          <NInput
            v-model:value="form.synopsis"
            type="textarea"
            :autosize="{ minRows: 3, maxRows: 6 }"
            placeholder="详细描述故事背景和走向"
          />
        </NFormItem>
        <NSpace>
          <NFormItem label="目标章数">
            <NInputNumber v-model:value="form.target_chapter_count" :min="1" :max="200" />
          </NFormItem>
          <NFormItem label="每章字数">
            <NInputNumber
              v-model:value="form.target_words_per_chapter"
              :min="500"
              :max="10000"
              :step="500"
            />
          </NFormItem>
        </NSpace>
        <NFormItem label="私密模式">
          <NSwitch v-model:value="form.privacy_mode" />
        </NFormItem>
      </NForm>
      <template #footer>
        <NSpace justify="end">
          <NButton @click="showModal = false">取消</NButton>
          <NButton type="primary" @click="handleCreate">创建</NButton>
        </NSpace>
      </template>
    </NModal>
  </div>
</template>

<style scoped>
.project-list-page {
  max-width: 1200px;
  margin: 0 auto;
  padding: 24px;
}
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}
.page-header h1 {
  font-size: 24px;
  font-weight: 700;
}
.loading-state {
  text-align: center;
  padding: 60px;
  color: #999;
}
.project-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
  gap: 16px;
}
.project-card {
  cursor: pointer;
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}
.project-card:hover {
  transform: translateY(-2px);
}
.project-title {
  font-weight: 600;
  font-size: 16px;
}
.project-synopsis {
  color: #666;
  font-size: 13px;
  line-height: 1.6;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
</style>
