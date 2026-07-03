<script setup lang="ts">
import GenericWorkbench from "../components/GenericWorkbench.vue";

const config = {
  resource: "foreshadowings",
  title: "伏笔管理",
  icon: "✨",
  description: "记录埋线、回收节点与悬念提醒",
  categoryDefault: "open",
  aiWorkflow: "extract_memory",
  aiModes: [{ key: "foreshadowing", label: "AI 提取伏笔" }],
  fields: [
    { key: "setup_chapter", label: "埋设章节", type: "input" as const },
    { key: "payoff_chapter", label: "回收章节", type: "input" as const },
    { key: "status", label: "状态", type: "select" as const, options: ["open", "planted", "paid_off", "abandoned"] },
    { key: "related_characters", label: "相关角色", type: "input" as const },
    { key: "hint", label: "伏笔提示", type: "textarea" as const },
    { key: "payoff_plan", label: "回收计划", type: "textarea" as const },
  ],
};
</script>

<template>
  <GenericWorkbench :config="config" />
</template>
