<script setup lang="ts">
import { ref, computed, onMounted } from "vue";
import { useRoute, useRouter } from "vue-router";
import {
  NCard, NButton, NSpace, NSelect, NInputNumber, NSwitch, NRadioGroup,
  NRadio, NFormItem, NForm, NAlert, NText, useMessage,
} from "naive-ui";
import { blueprintApi, jobApi } from "../api";
import type { Blueprint } from "../api/types";
import { useJobStore } from "../stores/job";

const route = useRoute();
const router = useRouter();
const message = useMessage();
const jobStore = useJobStore();

const projectId = computed(() => route.params.projectId as string);
const blueprints = ref<Blueprint[]>([]);
const selectedBlueprintId = ref<string | null>(null);
const startChapter = ref(1);
const chapterCount = ref(10);
const hostingMode = ref<"pure" | "checkpoint">("pure");
const generationMode = ref<"fast" | "standard" | "deep">("standard");
const checkpointInterval = ref(5);
const autoFinalize = ref(true);
const autoExport = ref(false);
const starting = ref(false);
const autopilotStarting = ref(false);

function isBlueprintUsable(bp: Blueprint) {
  return bp.status === "approved" || bp.status === "active";
}

function blueprintStatusLabel(status: string) {
  if (status === "approved" || status === "active") return "已批准";
  return "待批准";
}

onMounted(async () => {
  try {
    blueprints.value = await blueprintApi.list(projectId.value);
    // 从 query 预选蓝图
    const queryBp = route.query.blueprint_id as string;
    if (queryBp) selectedBlueprintId.value = queryBp;
    else if (blueprints.value.length > 0) {
      const approved = blueprints.value.find(isBlueprintUsable);
      selectedBlueprintId.value = (approved || blueprints.value[0]).id;
    }
  } catch (e: any) {
    message.error(`加载蓝图失败: ${e.message}`);
  }
});

const blueprintOptions = computed(() =>
  blueprints.value.map((bp) => ({
    label: `第 ${bp.volume_number} 卷 · ${bp.volume_title} (${blueprintStatusLabel(bp.status)})`,
    value: bp.id,
    disabled: !isBlueprintUsable(bp),
  })),
);

const selectedBlueprint = computed(() =>
  blueprints.value.find((b) => b.id === selectedBlueprintId.value),
);

async function handleStart() {
  if (!selectedBlueprintId.value) {
    message.warning("请先选择蓝图");
    return;
  }
  starting.value = true;
  try {
    const job = await jobStore.startJob(projectId.value, {
      blueprint_id: selectedBlueprintId.value,
      start_chapter: startChapter.value,
      count: chapterCount.value,
      checkpoint_strategy: hostingMode.value === "checkpoint" ? `every_${checkpointInterval.value}` : "none",
      auto_finalize: autoFinalize.value,
      params: {
        hosting_mode: hostingMode.value,
        generation_mode: generationMode.value,
        smart_stop_policy: hostingMode.value === "pure" ? "warn" : "pause",
        auto_export: autoExport.value,
      },
    });
    message.success("托管任务已启动");
    router.push({
      name: "JobProgress",
      params: { projectId: projectId.value, jobId: job.id },
    });
  } catch (e: any) {
    message.error(`启动失败: ${e.message}`);
  } finally {
    starting.value = false;
  }
}

async function handleAutopilotStart() {
  autopilotStarting.value = true;
  try {
    const result = await jobApi.startAutopilot(projectId.value, {
      start_chapter: startChapter.value,
      count: chapterCount.value,
      checkpoint_strategy: hostingMode.value === "checkpoint" ? `every_${checkpointInterval.value}` : "none",
      auto_finalize: autoFinalize.value,
      generation_mode: generationMode.value,
      params: {
        hosting_mode: hostingMode.value,
        generation_mode: generationMode.value,
        smart_stop_policy: hostingMode.value === "pure" ? "warn" : "pause",
        auto_export: autoExport.value,
      },
    });
    message.success("已自动准备素材并启动托管任务");
    router.push({
      name: "JobProgress",
      params: { projectId: projectId.value, jobId: result.job.id },
    });
  } catch (e: any) {
    message.error(`自动启动失败: ${e.message}`);
  } finally {
    autopilotStarting.value = false;
  }
}
</script>

<template>
  <div class="job-launcher-page">
    <h2 style="margin-bottom: 20px">启动托管生成</h2>

    <NAlert v-if="blueprints.length === 0" type="warning" style="margin-bottom: 16px">
      还没有卷蓝图，请先创建蓝图并批准后再启动生成。
    </NAlert>

    <NCard style="max-width: 600px">
      <NForm label-placement="top">
        <NFormItem label="选择蓝图" required>
          <NSelect
            v-model:value="selectedBlueprintId"
            :options="blueprintOptions"
            placeholder="选择已批准的蓝图"
          />
        </NFormItem>

        <NFormItem v-if="selectedBlueprint" label="蓝图信息">
          <NText depth="3" style="font-size: 13px">
            第 {{ selectedBlueprint.chapter_range?.start }}-{{ selectedBlueprint.chapter_range?.end }} 章
            · {{ selectedBlueprint.recurring_motifs?.length || 0 }} 个意象
          </NText>
        </NFormItem>

        <NSpace>
          <NFormItem label="起始章节">
            <NInputNumber v-model:value="startChapter" :min="1" />
          </NFormItem>
          <NFormItem label="生成章数">
            <NInputNumber v-model:value="chapterCount" :min="1" :max="100" />
          </NFormItem>
        </NSpace>

        <NFormItem label="托管模式">
          <NRadioGroup v-model:value="hostingMode">
            <NSpace>
              <NRadio value="pure">纯托管（全自动跑完）</NRadio>
              <NRadio value="checkpoint">检查点暂停（每 N 章）</NRadio>
            </NSpace>
          </NRadioGroup>
        </NFormItem>

        <NFormItem v-if="hostingMode === 'checkpoint'" label="检查点间隔">
          <NInputNumber v-model:value="checkpointInterval" :min="1" :max="20" />
          <NText depth="3" style="margin-left: 12px; font-size: 13px">每 {{ checkpointInterval }} 章暂停一次</NText>
        </NFormItem>

        <NFormItem label="生成深度">
          <NRadioGroup v-model:value="generationMode">
            <NSpace>
              <NRadio value="fast">快速闭环</NRadio>
              <NRadio value="standard">标准托管</NRadio>
              <NRadio value="deep">完整九步</NRadio>
            </NSpace>
          </NRadioGroup>
        </NFormItem>

        <NSpace>
          <NFormItem label="自动定稿">
            <NSwitch v-model:value="autoFinalize" />
          </NFormItem>
          <NFormItem label="自动导出">
            <NSwitch v-model:value="autoExport" />
          </NFormItem>
        </NSpace>
      </NForm>

      <NSpace justify="end" style="margin-top: 16px">
        <NButton
          size="large"
          :loading="autopilotStarting"
          @click="handleAutopilotStart"
        >
          自动准备并启动
        </NButton>
        <NButton
          type="primary"
          size="large"
          :loading="starting"
          :disabled="!selectedBlueprintId"
          @click="handleStart"
        >
          🚀 启动托管任务
        </NButton>
      </NSpace>
    </NCard>
  </div>
</template>

<style scoped>
.job-launcher-page { max-width: 700px; }
</style>
