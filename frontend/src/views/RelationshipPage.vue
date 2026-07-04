<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { useRoute } from "vue-router";
import * as echarts from "echarts";
import { NCard, NGrid, NGridItem, NText, NButton, NSpace, NTag } from "naive-ui";
import GenericWorkbench from "../components/GenericWorkbench.vue";
import { resourceApi } from "../api";
import type { GenericRecord } from "../api/types";

const route = useRoute();
const projectId = computed(() => route.params.projectId as string);
const chartEl = ref<HTMLDivElement | null>(null);
const characters = ref<GenericRecord[]>([]);
const relationships = ref<GenericRecord[]>([]);
let chart: echarts.ECharts | null = null;

const config = {
  resource: "character-relationships",
  title: "角色关系图",
  icon: "🕸️",
  description: "查看人物关系、同盟、冲突与变化。上方画布会自动读取角色档案与关系记录。",
  categoryDefault: "关系",
  aiWorkflow: "extract_relationships",
  aiModes: [
    { key: "extract", label: "AI 提取关系" },
    { key: "conflict", label: "分析冲突" },
  ],
  fields: [
    { key: "source_character", label: "角色 A", type: "input" as const },
    { key: "target_character", label: "角色 B", type: "input" as const },
    { key: "relationship_type", label: "关系类型", type: "select" as const, options: ["朋友", "敌人", "恋人", "师徒", "亲属", "同盟", "对手", "主线关联", "隐秘同盟", "信息互补", "追捕 / 对手"] },
    { key: "strength", label: "关系强度", type: "number" as const },
    { key: "conflict", label: "冲突描述", type: "textarea" as const },
    { key: "change_history", label: "变化记录", type: "textarea" as const },
    { key: "related_chapters", label: "相关章节", type: "input" as const },
  ],
};

function payloadOf(record: GenericRecord): Record<string, any> {
  if (!record.payload) return {};
  if (typeof record.payload === "string") {
    try {
      return JSON.parse(record.payload);
    } catch {
      return {};
    }
  }
  return record.payload as Record<string, any>;
}

function recordName(record: GenericRecord): string {
  const payload = payloadOf(record);
  return String(payload.name || record.title || "未命名角色");
}

const graphSummary = computed(() => {
  return {
    characterCount: characters.value.length,
    relationshipCount: relationships.value.length,
  };
});

async function fetchGraphData() {
  const [characterRows, relationshipRows] = await Promise.all([
    resourceApi.list(projectId.value, "character-profiles"),
    resourceApi.list(projectId.value, "character-relationships"),
  ]);
  characters.value = characterRows;
  relationships.value = relationshipRows;
  await nextTick();
  renderChart();
}

function renderChart() {
  if (!chartEl.value) return;
  if (!chart) chart = echarts.init(chartEl.value);
  const nodes = characters.value.map((record) => {
    const payload = payloadOf(record);
    const name = recordName(record);
    return {
      name,
      value: payload.role || record.category || "角色",
      symbolSize: payload.role?.includes("主角") || record.category?.includes("主角") ? 64 : 48,
      label: { show: true },
    };
  });
  const known = new Set(nodes.map((n) => n.name));
  const links = relationships.value
    .map((record) => {
      const payload = payloadOf(record);
      const source = String(payload.from || payload.source_character || "");
      const target = String(payload.to || payload.target_character || "");
      if (source && !known.has(source)) {
        nodes.push({ name: source, value: "关系记录补充", symbolSize: 42, label: { show: true } });
        known.add(source);
      }
      if (target && !known.has(target)) {
        nodes.push({ name: target, value: "关系记录补充", symbolSize: 42, label: { show: true } });
        known.add(target);
      }
      return {
        source,
        target,
        value: payload.relationship_type || payload.type || payload.relation || record.category || "关系",
        lineStyle: { width: Math.max(1, Number(payload.strength || 5) / 2) },
        label: { show: true, formatter: "{c}" },
      };
    })
    .filter((link) => link.source && link.target);

  chart.setOption({
    tooltip: {
      formatter(params: any) {
        if (params.dataType === "edge") return `${params.data.source} → ${params.data.target}<br/>${params.data.value || "关系"}`;
        return `${params.name}<br/>${params.data.value || "角色"}`;
      },
    },
    series: [
      {
        type: "graph",
        layout: "force",
        roam: true,
        draggable: true,
        focusNodeAdjacency: true,
        force: { repulsion: 260, edgeLength: 140 },
        data: nodes,
        links,
        edgeSymbol: ["none", "arrow"],
        edgeSymbolSize: 8,
        label: { show: true, position: "right" },
        edgeLabel: { show: true, formatter: "{c}" },
      },
    ],
  });
}

function resizeChart() {
  chart?.resize();
}

onMounted(async () => {
  await fetchGraphData();
  window.addEventListener("resize", resizeChart);
});
watch(projectId, fetchGraphData);
onBeforeUnmount(() => {
  window.removeEventListener("resize", resizeChart);
  chart?.dispose();
  chart = null;
});
</script>

<template>
  <div class="relationship-page">
    <NCard title="关系画布" size="small" class="canvas-card">
      <template #header-extra>
        <NSpace align="center">
          <NTag size="small">角色 {{ graphSummary.characterCount }}</NTag>
          <NTag size="small">关系 {{ graphSummary.relationshipCount }}</NTag>
          <NButton size="small" @click="fetchGraphData">刷新画布</NButton>
        </NSpace>
      </template>
      <NGrid :cols="5" :x-gap="16" responsive="screen">
        <NGridItem :span="4">
          <div ref="chartEl" class="relationship-canvas" />
        </NGridItem>
        <NGridItem>
          <NText depth="3">
            画布读取“故事圣经”和“角色关系”记录。托管生成会自动补齐角色关系，并同步到 llmwiki 的 relationships/canvas.md。
          </NText>
        </NGridItem>
      </NGrid>
    </NCard>

    <GenericWorkbench :config="config" />
  </div>
</template>

<style scoped>
.relationship-page {
  max-width: 1280px;
}
.canvas-card {
  margin-bottom: 16px;
}
.relationship-canvas {
  height: 420px;
  width: 100%;
  border-radius: 12px;
  border: 1px solid rgba(128, 128, 128, 0.16);
}
</style>
