<script setup lang="ts">
import GenericWorkbench from "../components/GenericWorkbench.vue";

const config = {
  resource: "outlines",
  title: "大纲",
  icon: "📚",
  description: "分卷章节树、剧情板与 AI 多章大纲",
  categoryDefault: "chapter_outline",
  aiWorkflow: "generate_outline",
  aiModes: [
    { key: "five", label: "AI 生成5章大纲" },
    { key: "ten", label: "AI 生成10章大纲" },
    { key: "expand", label: "扩展章节大纲" },
  ],
  fields: [
    { key: "chapter_number", label: "章节序号", type: "input" as const },
    { key: "volume", label: "卷名", type: "input" as const },
    { key: "chapter_title", label: "章节标题", type: "input" as const },
    { key: "chapter_goal", label: "本章目标", type: "textarea" as const },
    { key: "main_conflict", label: "主要冲突", type: "textarea" as const },
    { key: "key_events", label: "关键事件", type: "textarea" as const },
    { key: "emotional_rhythm", label: "情绪节奏", type: "textarea" as const },
    { key: "foreshadowing", label: "伏笔", type: "textarea" as const },
    { key: "hook", label: "结尾钩子", type: "textarea" as const },
    { key: "related_characters", label: "关联角色", type: "input" as const },
    { key: "completion_status", label: "状态", type: "select" as const, options: ["draft", "active", "completed"] },
  ],
};
</script>

<template>
  <GenericWorkbench :config="config" />
</template>
