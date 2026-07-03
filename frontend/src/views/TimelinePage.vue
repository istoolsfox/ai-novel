<script setup lang="ts">
import GenericWorkbench from "../components/GenericWorkbench.vue";

const config = {
  resource: "timeline-events",
  title: "时间线",
  icon: "⏳",
  description: "梳理事件顺序、因果与剧情节奏",
  categoryDefault: "timeline",
  aiWorkflow: "extract_timeline_events",
  aiModes: [{ key: "extract", label: "AI 提取事件" }],
  fields: [
    { key: "event_time", label: "事件时间", type: "input" as const },
    { key: "chapter", label: "所属章节", type: "input" as const },
    { key: "characters", label: "涉及角色", type: "input" as const },
    { key: "cause", label: "起因", type: "textarea" as const },
    { key: "consequence", label: "后果", type: "textarea" as const },
    { key: "status", label: "状态", type: "select" as const, options: ["待确认", "已确认", "已修改"] },
  ],
};
</script>

<template>
  <GenericWorkbench :config="config" />
</template>
