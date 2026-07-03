<script setup lang="ts">
import GenericWorkbench from "../components/GenericWorkbench.vue";

const config = {
  resource: "style-profiles",
  title: "风格学习",
  icon: "⭐",
  description: "保存样本文风，让 AI 模仿写作语气",
  categoryDefault: "style",
  aiWorkflow: "analyze_style_sample",
  aiModes: [
    { key: "analyze", label: "AI 分析风格" },
    { key: "imitate", label: "AI 模拟写作" },
  ],
  fields: [
    { key: "title", label: "档案名称", type: "input" as const },
    { key: "sample", label: "样本文本", type: "textarea" as const },
    { key: "analysis", label: "风格分析", type: "textarea" as const },
    { key: "imitation", label: "模拟片段", type: "textarea" as const },
    { key: "writing_goal", label: "写作目标", type: "input" as const },
  ],
};
</script>

<template>
  <GenericWorkbench :config="config" />
</template>
