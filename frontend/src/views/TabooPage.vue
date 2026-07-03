<script setup lang="ts">
import GenericWorkbench from "../components/GenericWorkbench.vue";

const config = {
  resource: "taboo-rules",
  title: "雷点控制",
  icon: "⚠️",
  description: "列出禁写内容、读者雷点与避坑规则",
  categoryDefault: "medium",
  aiWorkflow: "check_taboo_rules",
  aiModes: [{ key: "check", label: "AI 检查雷点" }],
  fields: [
    { key: "rule", label: "规则内容", type: "textarea" as const },
    { key: "severity", label: "严重程度", type: "select" as const, options: ["low", "medium", "high"] },
    { key: "scope", label: "适用范围", type: "input" as const },
    { key: "response", label: "处理方式", type: "textarea" as const },
  ],
};
</script>

<template>
  <GenericWorkbench :config="config" />
</template>
