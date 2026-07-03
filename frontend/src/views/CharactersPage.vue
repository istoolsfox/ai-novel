<script setup lang="ts">
import GenericWorkbench from "../components/GenericWorkbench.vue";

const config = {
  resource: "character-profiles",
  title: "故事圣经",
  icon: "📖",
  description: "沉淀角色、世界观、设定与核心规则",
  categoryDefault: "character",
  aiWorkflow: "generate_characters",
  aiModes: [
    { key: "new", label: "AI 生成新角色" },
    { key: "complete", label: "补全角色" },
    { key: "dialogue", label: "生成对白" },
  ],
  fields: [
    { key: "name", label: "姓名", type: "input" as const },
    { key: "role", label: "身份", type: "input" as const },
    { key: "faction", label: "阵营", type: "input" as const },
    { key: "appearance", label: "年龄 / 外貌", type: "textarea" as const },
    { key: "traits", label: "性格关键词", type: "textarea" as const },
    { key: "desire", label: "欲望目标", type: "textarea" as const },
    { key: "fear", label: "恐惧 / 弱点", type: "textarea" as const },
    { key: "mainline_relation", label: "与主线关系", type: "textarea" as const },
    { key: "arc", label: "人物弧光", type: "textarea" as const },
    { key: "voice", label: "口癖 / 说话方式", type: "textarea" as const },
    { key: "related_chapters", label: "相关章节", type: "input" as const },
    { key: "notes", label: "备注", type: "textarea" as const },
  ],
};
</script>

<template>
  <GenericWorkbench :config="config" />
</template>
