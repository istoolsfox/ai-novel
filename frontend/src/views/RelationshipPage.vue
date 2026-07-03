<script setup lang="ts">
import GenericWorkbench from "../components/GenericWorkbench.vue";

const config = {
  resource: "character-relationships",
  title: "角色关系图",
  icon: "🕸️",
  description: "查看人物关系、同盟、冲突与变化",
  categoryDefault: "关系",
  aiWorkflow: "extract_relationships",
  aiModes: [
    { key: "extract", label: "AI 提取关系" },
    { key: "conflict", label: "分析冲突" },
  ],
  fields: [
    { key: "source_character", label: "角色 A", type: "input" as const },
    { key: "target_character", label: "角色 B", type: "input" as const },
    { key: "relationship_type", label: "关系类型", type: "select" as const, options: ["朋友", "敌人", "恋人", "师徒", "亲属", "同盟", "对手", "主线关联"] },
    { key: "strength", label: "关系强度", type: "number" as const },
    { key: "conflict", label: "冲突描述", type: "textarea" as const },
    { key: "change_history", label: "变化记录", type: "textarea" as const },
    { key: "related_chapters", label: "相关章节", type: "input" as const },
  ],
};
</script>

<template>
  <GenericWorkbench :config="config" />
</template>
