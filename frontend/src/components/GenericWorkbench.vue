<script setup lang="ts">
import { ref, computed, onMounted, watch } from "vue";
import { useRoute } from "vue-router";
import {
  NCard, NSpace, NButton, NInput, NSelect, NTag, NEmpty, NForm,
  NFormItem, NPopconfirm, NCollapse, NCollapseItem, NGrid, NGridItem,
  NText, NDivider, NScrollbar, useMessage,
} from "naive-ui";
import { resourceApi, aiApi } from "../api";
import type { GenericRecord, GenericInput } from "../api/types";

const route = useRoute();
const message = useMessage();
const projectId = computed(() => route.params.projectId as string);

// 工作台配置
interface FieldConfig {
  key: string;
  label: string;
  type?: "input" | "textarea" | "number" | "select";
  options?: string[];
  placeholder?: string;
}

interface WorkbenchConfig {
  resource: string;
  title: string;
  icon: string;
  description: string;
  fields: FieldConfig[];
  categoryDefault?: string;
  aiWorkflow?: string;
  aiModes?: Array<{ key: string; label: string }>;
}

const props = defineProps<{
  config: WorkbenchConfig;
}>();

const records = ref<GenericRecord[]>([]);
const loading = ref(false);
const editingId = ref("");
const formData = ref<Record<string, any>>({});
const aiResults = ref<Array<{ id: string; title: string; content: string; status: string }>>([]);

async function fetchRecords() {
  loading.value = true;
  try {
    records.value = await resourceApi.list(projectId.value, props.config.resource);
  } finally {
    loading.value = false;
  }
}

onMounted(() => fetchRecords());
watch(projectId, () => fetchRecords());

function resetForm() {
  const init: Record<string, any> = {};
  for (const f of props.config.fields) {
    init[f.key] = f.type === "number" ? 0 : "";
  }
  formData.value = init;
  editingId.value = "";
}

function fieldValueToText(value: unknown): string {
  if (value === null || value === undefined) return "";
  if (typeof value === "string") return value;
  if (typeof value === "number" || typeof value === "boolean") return String(value);
  if (Array.isArray(value)) {
    return value
      .map((item) => {
        if (item === null || item === undefined) return "";
        if (typeof item === "string" || typeof item === "number" || typeof item === "boolean") {
          return String(item);
        }
        return JSON.stringify(item, null, 2);
      })
      .filter(Boolean)
      .join("\n");
  }
  if (typeof value === "object") {
    return JSON.stringify(value, null, 2);
  }
  return String(value);
}

function selectRecord(record: GenericRecord) {
  editingId.value = record.id;
  let payload: Record<string, any> = {};
  try {
    payload = typeof record.payload === "string" ? JSON.parse(record.payload) : record.payload || {};
  } catch {}
  const init: Record<string, any> = {};
  for (const f of props.config.fields) {
    const value = payload[f.key] ?? record[f.key as keyof GenericRecord] ?? "";
    init[f.key] = f.type === "number" ? value : fieldValueToText(value);
  }
  formData.value = init;
}

async function handleSave() {
  const titleField = props.config.fields[0];
  const title = formData.value[titleField.key] || "未命名";
  const contentFields = props.config.fields
    .filter((f) => f.type === "textarea" || f.key === "content")
    .map((f) => fieldValueToText(formData.value[f.key]))
    .filter(Boolean)
    .join("\n");
  const payload: GenericInput = {
    title,
    category: formData.value.category || props.config.categoryDefault || "",
    content: contentFields || formData.value.content || "",
    payload: { ...formData.value },
    status: formData.value.status || "active",
  };
  try {
    if (editingId.value) {
      await resourceApi.update(projectId.value, props.config.resource, editingId.value, payload);
      message.success("已更新");
    } else {
      await resourceApi.create(projectId.value, props.config.resource, payload);
      message.success("已保存");
    }
    resetForm();
    await fetchRecords();
  } catch (e: any) {
    message.error(e.message);
  }
}

async function handleDelete(id: string) {
  try {
    await resourceApi.delete(projectId.value, props.config.resource, id);
    message.success("已删除");
    if (editingId.value === id) resetForm();
    await fetchRecords();
  } catch (e: any) {
    message.error(e.message);
  }
}

async function handleAI(mode?: string) {
  if (!props.config.aiWorkflow) {
    message.info("此工作台暂不支持 AI 功能");
    return;
  }
  try {
    const result = await aiApi.run(projectId.value, props.config.aiWorkflow, {
      payload: { mode: mode || "new", ...formData.value },
    });
    aiResults.value.unshift({
      id: `ai-${Date.now()}`,
      title: mode ? `AI 结果 (${mode})` : "AI 结果",
      content: result.text || JSON.stringify(result, null, 2),
      status: result.status || "ok",
    });
    // 尝试自动填充表单
    if (result.structured) {
      const structured = typeof result.structured === "object" ? result.structured : {};
      for (const f of props.config.fields) {
        if (structured[f.key] !== undefined) {
          formData.value[f.key] = f.type === "number" ? structured[f.key] : fieldValueToText(structured[f.key]);
        }
      }
    }
  } catch (e: any) {
    message.error(e.message);
  }
}

function applyResult(content: string) {
  // 尝试解析 JSON 并填充
  try {
    const parsed = JSON.parse(content);
    for (const f of props.config.fields) {
      if (parsed[f.key] !== undefined) {
        formData.value[f.key] = f.type === "number" ? parsed[f.key] : fieldValueToText(parsed[f.key]);
      }
    }
    message.success("AI 结果已填入表单");
  } catch {
    // 填入第一个 textarea
    const textareaField = props.config.fields.find((f) => f.type === "textarea");
    if (textareaField) {
      formData.value[textareaField.key] = content;
      message.success("AI 结果已填入");
    }
  }
}
</script>

<template>
  <div class="generic-workbench">
    <div class="page-header">
      <h2>{{ config.icon }} {{ config.title }}</h2>
      <NText depth="3">{{ config.description }}</NText>
    </div>

    <NGrid :cols="2" :x-gap="16" :y-gap="16" responsive="screen">
      <!-- 左侧：列表 -->
      <NGridItem>
        <NCard title="记录列表" size="small">
          <template #header-extra>
            <NButton size="small" type="primary" @click="resetForm">+ 新建</NButton>
          </template>
          <NScrollbar style="max-height: 500px">
            <NEmpty v-if="records.length === 0" description="暂无记录" />
            <div v-else class="record-list">
              <div
                v-for="r in records"
                :key="r.id"
                class="record-item"
                :class="{ active: r.id === editingId }"
                @click="selectRecord(r)"
              >
                <div class="record-header">
                  <NText strong>{{ r.title || "未命名" }}</NText>
                  <NTag v-if="r.category" size="tiny">{{ r.category }}</NTag>
                </div>
                <NText depth="3" class="record-preview">
                  {{ (r.content || "").slice(0, 100) }}
                </NText>
                <div class="record-actions">
                  <NButton size="tiny" @click.stop="selectRecord(r)">编辑</NButton>
                  <NPopconfirm @positive-click="handleDelete(r.id)">
                    <template #trigger>
                      <NButton size="tiny" type="error" ghost @click.stop>删除</NButton>
                    </template>
                    确认删除？
                  </NPopconfirm>
                </div>
              </div>
            </div>
          </NScrollbar>
        </NCard>
      </NGridItem>

      <!-- 右侧：表单 + AI -->
      <NGridItem>
        <NCard :title="editingId ? '编辑记录' : '新建记录'" size="small">
          <NForm label-placement="top" size="small">
            <NGrid :cols="2" :x-gap="12">
              <NGridItem v-for="field in config.fields" :key="field.key" :span="field.type === 'textarea' ? 2 : 1">
                <NFormItem :label="field.label">
                  <NInput
                    v-if="field.type === 'textarea' || !field.type"
                    v-model:value="formData[field.key]"
                    type="textarea"
                    :autosize="{ minRows: 2, maxRows: 6 }"
                    :placeholder="field.placeholder || `输入${field.label}`"
                  />
                  <NInputNumber
                    v-else-if="field.type === 'number'"
                    v-model:value="formData[field.key]"
                    :placeholder="field.placeholder"
                  />
                  <NSelect
                    v-else-if="field.type === 'select'"
                    v-model:value="formData[field.key]"
                    :options="(field.options || []).map(o => ({ label: o, value: o }))"
                  />
                  <NInput
                    v-else
                    v-model:value="formData[field.key]"
                    :placeholder="field.placeholder || `输入${field.label}`"
                  />
                </NFormItem>
              </NGridItem>
            </NGrid>
          </NForm>
          <NSpace justify="end" style="margin-top: 12px">
            <NButton v-if="editingId" @click="resetForm">取消编辑</NButton>
            <NButton
              v-if="config.aiWorkflow"
              @click="handleAI(config.aiModes?.[0]?.key)"
            >
              {{ config.aiModes?.[0]?.label || "AI 辅助" }}
            </NButton>
            <NButton type="primary" @click="handleSave">
              {{ editingId ? "更新" : "保存" }}
            </NButton>
          </NSpace>

          <!-- AI 结果区 -->
          <NDivider v-if="aiResults.length > 0">AI 结果</NDivider>
          <NCollapse v-if="aiResults.length > 0" accordion>
            <NCollapseItem
              v-for="r in aiResults"
              :key="r.id"
              :title="r.title"
              :name="r.id"
            >
              <div class="ai-result-content">{{ r.content }}</div>
              <NButton size="small" @click="applyResult(r.content)">填入表单</NButton>
            </NCollapseItem>
          </NCollapse>
        </NCard>
      </NGridItem>
    </NGrid>
  </div>
</template>

<style scoped>
.generic-workbench { max-width: 1200px; }
.page-header {
  margin-bottom: 16px;
}
.page-header h2 {
  font-size: 20px;
  font-weight: 700;
  margin-bottom: 4px;
}
.record-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.record-item {
  padding: 10px 12px;
  border-radius: 8px;
  border: 1px solid rgba(128, 128, 128, 0.1);
  cursor: pointer;
  transition: all 0.15s;
}
.record-item:hover {
  background: rgba(128, 128, 128, 0.05);
}
.record-item.active {
  border-color: #2080f0;
  background: rgba(32, 128, 240, 0.05);
}
.record-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 4px;
}
.record-preview {
  font-size: 12px;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.record-actions {
  margin-top: 6px;
  display: flex;
  gap: 6px;
}
.ai-result-content {
  white-space: pre-wrap;
  font-size: 13px;
  line-height: 1.6;
  max-height: 200px;
  overflow-y: auto;
  margin-bottom: 8px;
  padding: 8px;
  border-radius: 6px;
  background: rgba(128, 128, 128, 0.05);
}
</style>
