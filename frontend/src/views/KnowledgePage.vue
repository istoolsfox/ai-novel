<script setup lang="ts">
import GenericWorkbench from "../components/GenericWorkbench.vue";

const config = {
  resource: "knowledge-documents",
  title: "知识库",
  icon: "📚",
  description: "管理素材、资料、参考文档与灵感来源",
  categoryDefault: "reference",
  fields: [
    { key: "wiki_path", label: "Wiki 路径", type: "input" as const },
    { key: "source_type", label: "资料类型", type: "select" as const, options: ["reference", "inspiration", "research", "worldbuilding"] },
    { key: "tags", label: "标签", type: "input" as const },
    { key: "content", label: "内容", type: "textarea" as const },
  ],
};
</script>

<template>
  <GenericWorkbench :config="config" />
</template>
