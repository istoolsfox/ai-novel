<script setup lang="ts">
import { h, computed, ref, watch } from "vue";
import { useRoute, useRouter, RouterView } from "vue-router";
import {
  NLayout, NLayoutSider, NLayoutHeader, NLayoutContent, NMenu,
  NButton, NSpace, NText, type MenuOption,
} from "naive-ui";
import { useProjectStore } from "../stores/project";
import { useSettingsStore } from "../stores/settings";

const route = useRoute();
const router = useRouter();
const projectStore = useProjectStore();
const settings = useSettingsStore();

const collapsed = ref(false);
const projectId = computed(() => route.params.projectId as string);

watch(projectId, (id) => {
  if (id) projectStore.fetchProject(id);
}, { immediate: true });

const menuOptions = computed<MenuOption[]>(() => [
  { label: "概览", key: "Dashboard", icon: () => h("span", { class: "menu-emoji" }, "📊") },
  { label: "卷蓝图", key: "Blueprints", icon: () => h("span", { class: "menu-emoji" }, "🗺️") },
  { label: "托管生成", key: "Generate", icon: () => h("span", { class: "menu-emoji" }, "🚀") },
  { label: "章节编辑器", key: "Chapters", icon: () => h("span", { class: "menu-emoji" }, "✍️") },
  { label: "情感工作台", key: "Emotion", icon: () => h("span", { class: "menu-emoji" }, "🎭") },
  { type: "divider", key: "d1" },
  { label: "大纲", key: "Outline", icon: () => h("span", { class: "menu-emoji" }, "📚") },
  { label: "故事圣经", key: "Characters", icon: () => h("span", { class: "menu-emoji" }, "📖") },
  { label: "角色关系图", key: "Graph", icon: () => h("span", { class: "menu-emoji" }, "🕸️") },
  { label: "时间线", key: "Timeline", icon: () => h("span", { class: "menu-emoji" }, "⏳") },
  { label: "伏笔管理", key: "Foreshadowing", icon: () => h("span", { class: "menu-emoji" }, "✨") },
  { type: "divider", key: "d2" },
  { label: "风格学习", key: "Style", icon: () => h("span", { class: "menu-emoji" }, "⭐") },
  { label: "雷点控制", key: "Taboo", icon: () => h("span", { class: "menu-emoji" }, "⚠️") },
  { label: "知识库", key: "Knowledge", icon: () => h("span", { class: "menu-emoji" }, "📚") },
  { label: "llmwiki 记忆", key: "Wiki", icon: () => h("span", { class: "menu-emoji" }, "🧠") },
  { label: "导出", key: "Export", icon: () => h("span", { class: "menu-emoji" }, "📥") },
  { type: "divider", key: "d3" },
  { label: "设置", key: "Settings", icon: () => h("span", { class: "menu-emoji" }, "⚙️") },
]);

const activeKey = computed(() => route.name as string);

function handleMenuUpdate(key: string) {
  router.push({ name: key, params: { projectId: projectId.value } });
}

function goBack() {
  router.push("/projects");
}

const projectTitle = computed(() => projectStore.currentProject?.title || "加载中...");
</script>

<template>
  <NLayout has-sider style="height: 100vh">
    <NLayoutSider
      bordered
      collapse-mode="width"
      :collapsed-width="64"
      :width="240"
      :collapsed="collapsed"
      show-trigger
      @collapse="collapsed = true"
      @expand="collapsed = false"
    >
      <div class="sidebar-logo" @click="goBack">
        <span v-if="!collapsed" class="logo-text">AI 小说工作台</span>
        <span v-else class="logo-emoji">✒️</span>
      </div>
      <div v-if="!collapsed" class="project-name">
        <NText depth="3" style="font-size: 12px">当前项目</NText>
        <NText strong :title="projectTitle">{{ projectTitle }}</NText>
      </div>
      <NScrollbar style="max-height: calc(100vh - 120px)">
        <NMenu
          :options="menuOptions"
          :value="activeKey"
          :collapsed="collapsed"
          :collapsed-width="64"
          :collapsed-icon-size="22"
          @update:value="handleMenuUpdate"
        />
      </NScrollbar>
    </NLayoutSider>

    <NLayout>
      <NLayoutHeader bordered style="height: 52px; display: flex; align-items: center; justify-content: space-between; padding: 0 20px;">
        <NSpace align="center">
          <NButton text @click="goBack">← 项目列表</NButton>
          <NText depth="3">/</NText>
          <NText>{{ projectTitle }}</NText>
        </NSpace>
        <NButton quaternary size="small" @click="settings.cycleTheme()">
          {{ settings.themeLabel }}
        </NButton>
      </NLayoutHeader>
      <NLayoutContent style="padding: 20px; height: calc(100vh - 52px); overflow-y: auto;">
        <RouterView />
      </NLayoutContent>
    </NLayout>
  </NLayout>
</template>

<script lang="ts">
import { NScrollbar } from "naive-ui";
</script>

<style scoped>
.sidebar-logo {
  height: 52px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  border-bottom: 1px solid rgba(128, 128, 128, 0.1);
}
.logo-text {
  font-size: 15px;
  font-weight: 700;
  white-space: nowrap;
}
.logo-emoji {
  font-size: 24px;
}
.project-name {
  padding: 8px 16px 12px;
  display: flex;
  flex-direction: column;
  gap: 2px;
  overflow: hidden;
}
.project-name :deep(.n-text) {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.menu-emoji {
  font-size: 16px;
}
</style>
