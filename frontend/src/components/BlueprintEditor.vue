<script setup lang="ts">
import { ref, computed, onMounted } from "vue";
import { useRoute, useRouter } from "vue-router";
import {
  NCard, NButton, NSpace, NInput, NInputNumber, NSelect, NForm, NFormItem,
  NTag, NEmpty, NModal, NPopconfirm, NCollapse, NCollapseItem,
  NDynamicTags, NDivider, useMessage,
} from "naive-ui";
import { blueprintApi } from "../api";
import type { Blueprint, BlueprintInput } from "../api/types";

const route = useRoute();
const router = useRouter();
const message = useMessage();

const projectId = computed(() => route.params.projectId as string);
const blueprints = ref<Blueprint[]>([]);
const loading = ref(false);
const editingBlueprint = ref<Blueprint | null>(null);
const showModal = ref(false);

const form = ref<BlueprintInput>({
  volume_number: 1,
  volume_title: "",
  volume_arc: "",
  chapter_range: { start: 1, end: 10 },
  emotional_climate: {},
  key_foreshadowings: [],
  character_arcs: [],
  recurring_motifs: [],
  taboo_list: [],
  generation_params: {},
});

onMounted(() => fetchBlueprints());

async function fetchBlueprints() {
  loading.value = true;
  try {
    blueprints.value = await blueprintApi.list(projectId.value);
  } finally {
    loading.value = false;
  }
}

const showAutoGenModal = ref(false);
const autoGenVolume = ref(1);
const autoGenerating = ref(false);

function openCreate() {
  editingBlueprint.value = null;
  form.value = {
    volume_number: blueprints.value.length + 1,
    volume_title: "",
    volume_arc: "",
    chapter_range: { start: 1, end: 10 },
    emotional_climate: {},
    key_foreshadowings: [],
    character_arcs: [],
    recurring_motifs: [],
    taboo_list: [],
    generation_params: {},
  };
  showModal.value = true;
}

function openEdit(bp: Blueprint) {
  editingBlueprint.value = bp;
  form.value = {
    volume_number: bp.volume_number,
    volume_title: bp.volume_title,
    volume_arc: bp.volume_arc,
    chapter_range: bp.chapter_range,
    emotional_climate: bp.emotional_climate,
    key_foreshadowings: bp.key_foreshadowings,
    character_arcs: bp.character_arcs,
    recurring_motifs: bp.recurring_motifs,
    taboo_list: bp.taboo_list,
    generation_params: bp.generation_params,
  };
  showModal.value = true;
}

async function handleSave() {
  if (!form.value.volume_title?.trim()) {
    message.warning("请输入卷标题");
    return;
  }
  try {
    if (editingBlueprint.value) {
      await blueprintApi.update(projectId.value, editingBlueprint.value.id, form.value);
      message.success("蓝图已更新");
    } else {
      await blueprintApi.create(projectId.value, form.value);
      message.success("蓝图已创建");
    }
    showModal.value = false;
    await fetchBlueprints();
  } catch (e: any) {
    message.error(`保存失败: ${e.message}`);
  }
}

async function handleApprove(bp: Blueprint) {
  try {
    await blueprintApi.approve(projectId.value, bp.id);
    message.success("蓝图已批准");
    await fetchBlueprints();
  } catch (e: any) {
    message.error(`批准失败: ${e.message}`);
  }
}

async function handleDelete(bp: Blueprint) {
  try {
    await blueprintApi.delete(projectId.value, bp.id);
    message.success("已删除");
    await fetchBlueprints();
  } catch (e: any) {
    message.error(`删除失败: ${e.message}`);
  }
}

function isBlueprintApproved(bp: Blueprint) {
  return bp.status === "approved" || bp.status === "active";
}

function blueprintStatusLabel(bp: Blueprint) {
  return isBlueprintApproved(bp) ? "已批准" : "待批准";
}

function goToGenerate(bp: Blueprint) {
  router.push({ name: "Generate", params: { projectId: projectId.value }, query: { blueprint_id: bp.id } });
}

async function handleAutoGenerate() {
  autoGenerating.value = true;
  try {
    await blueprintApi.autoGenerate(projectId.value, autoGenVolume.value);
    message.success("AI 蓝图已生成");
    showAutoGenModal.value = false;
    await fetchBlueprints();
  } catch (e: any) {
    message.error(`生成失败: ${e.message}`);
  } finally {
    autoGenerating.value = false;
  }
}
</script>

<template>
  <div class="blueprint-page">
    <div class="page-header">
      <h2>卷蓝图</h2>
      <NSpace>
        <NButton @click="showAutoGenModal = true; autoGenVolume = blueprints.length + 1">AI 生成蓝图</NButton>
        <NButton type="primary" @click="openCreate">+ 新建蓝图</NButton>
      </NSpace>
    </div>

    <NEmpty v-if="!loading && blueprints.length === 0" description="还没有蓝图，创建第一卷蓝图开始托管生成" />

    <NSpace vertical :size="16">
      <NCard v-for="bp in blueprints" :key="bp.id" hoverable>
        <template #header>
          <NSpace align="center">
            <span>第 {{ bp.volume_number }} 卷 · {{ bp.volume_title }}</span>
            <NTag
              size="small"
              :type="isBlueprintApproved(bp) ? 'success' : 'warning'"
            >
              {{ blueprintStatusLabel(bp) }}
            </NTag>
          </NSpace>
        </template>
        <p v-if="bp.volume_arc" style="color: #666; margin-bottom: 12px">{{ bp.volume_arc }}</p>
        <NSpace size="small" style="margin-bottom: 8px">
          <NTag size="small">第 {{ bp.chapter_range?.start }}-{{ bp.chapter_range?.end }} 章</NTag>
          <NTag v-for="motif in bp.recurring_motifs" :key="motif" size="small" type="info">{{ motif }}</NTag>
        </NSpace>
        <NSpace v-if="bp.taboo_list?.length" size="small">
          <NTag v-for="taboo in bp.taboo_list" :key="taboo" size="small" type="error">{{ taboo }}</NTag>
        </NSpace>
        <template #action>
          <NSpace justify="end">
            <NButton size="small" @click="openEdit(bp)">编辑</NButton>
            <NButton
              v-if="!isBlueprintApproved(bp)"
              size="small"
              type="success"
              @click="handleApprove(bp)"
            >批准</NButton>
            <NButton
              size="small"
              type="primary"
              :disabled="!isBlueprintApproved(bp)"
              @click="goToGenerate(bp)"
            >启动生成</NButton>
            <NPopconfirm @positive-click="handleDelete(bp)">
              <template #trigger>
                <NButton size="small" type="error" ghost>删除</NButton>
              </template>
              确认删除此蓝图？
            </NPopconfirm>
          </NSpace>
        </template>
      </NCard>
    </NSpace>

    <!-- 编辑弹窗 -->
    <NModal v-model:show="showModal" preset="card" :title="editingBlueprint ? '编辑蓝图' : '新建蓝图'" style="width: 700px">
      <NForm label-placement="top">
        <NSpace>
          <NFormItem label="卷号">
            <NInputNumber v-model:value="form.volume_number" :min="1" />
          </NFormItem>
          <NFormItem label="卷标题" style="flex: 1">
            <NInput v-model:value="form.volume_title" placeholder="如：第一卷·初入迷局" />
          </NFormItem>
        </NSpace>
        <NFormItem label="本卷主线">
          <NInput v-model:value="form.volume_arc" type="textarea" :autosize="{ minRows: 2 }" placeholder="本卷核心剧情走向" />
        </NFormItem>
        <NSpace>
          <NFormItem label="起始章">
            <NInputNumber v-model:value="form.chapter_range!.start" :min="1" />
          </NFormItem>
          <NFormItem label="结束章">
            <NInputNumber v-model:value="form.chapter_range!.end" :min="1" />
          </NFormItem>
        </NSpace>
        <NDivider>情感与意象</NDivider>
        <NFormItem label="复现意象">
          <NDynamicTags v-model:value="form.recurring_motifs" />
        </NFormItem>
        <NFormItem label="禁忌列表">
          <NDynamicTags v-model:value="form.taboo_list" type="error" />
        </NFormItem>
      </NForm>
      <template #footer>
        <NSpace justify="end">
          <NButton @click="showModal = false">取消</NButton>
          <NButton type="primary" @click="handleSave">保存</NButton>
        </NSpace>
      </template>
    </NModal>

    <!-- AI 自动生成弹窗 -->
    <NModal v-model:show="showAutoGenModal" preset="card" title="AI 生成蓝图" style="width: 400px">
      <NForm label-placement="top">
        <NFormItem label="卷号">
          <NInputNumber v-model:value="autoGenVolume" :min="1" />
        </NFormItem>
      </NForm>
      <NText depth="3" style="font-size: 13px">
        AI 将根据项目设定自动生成完整的卷蓝图（含情感气候、伏笔规划、角色弧线等）。
      </NText>
      <template #footer>
        <NSpace justify="end">
          <NButton @click="showAutoGenModal = false">取消</NButton>
          <NButton type="primary" :loading="autoGenerating" @click="handleAutoGenerate">
            生成
          </NButton>
        </NSpace>
      </template>
    </NModal>
  </div>
</template>

<style scoped>
.blueprint-page { max-width: 800px; }
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}
.page-header h2 { font-size: 20px; font-weight: 700; }
</style>
