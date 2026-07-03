<script setup lang="ts">
import { ref, computed, onMounted } from "vue";
import { useRoute } from "vue-router";
import {
  NCard, NForm, NFormItem, NInput, NSpace, NButton, NSelect, NInputNumber,
  NSwitch, NDivider, NAlert, NText, useMessage,
} from "naive-ui";
import { aiApi, resourceApi } from "../api";
import type { GenericRecord } from "../api/types";
import { useSettingsStore } from "../stores/settings";

const route = useRoute();
const message = useMessage();
const settings = useSettingsStore();

const projectId = computed(() => route.params.projectId as string);
const testing = ref(false);
const testResult = ref<string | null>(null);
const savedConfigId = ref<string | null>(null);

const providerOptions = [
  { label: "OpenAI", value: "OpenAI" },
  { label: "Anthropic", value: "Anthropic" },
  { label: "DeepSeek", value: "DeepSeek" },
  { label: "通义千问", value: "Qwen" },
  { label: "自定义", value: "custom" },
];

onMounted(() => loadModelConfig());

function applyModelConfig(record: GenericRecord) {
  const payload = record.payload || {};
  settings.modelProvider = payload.provider || record.category || "OpenAI";
  settings.modelApiKey = payload.api_key || "";
  settings.modelBaseUrl = payload.base_url || "https://api.openai.com/v1";
  settings.modelName = payload.model_name || record.title || "";
  savedConfigId.value = record.id;
}

async function loadModelConfig() {
  try {
    const configs = await resourceApi.list(projectId.value, "model-configs");
    const defaultConfig = configs.find((config) => config.payload?.is_default) || configs[0];
    if (defaultConfig) applyModelConfig(defaultConfig);
  } catch (e: any) {
    message.error(`加载模型配置失败: ${e.message}`);
  }
}

async function saveModelConfig() {
  const payload = {
    provider: settings.modelProvider,
    api_key: settings.modelApiKey,
    base_url: settings.modelBaseUrl,
    model_name: settings.modelName,
    temperature: 0.7,
    max_tokens: 4096,
    is_default: true,
  };
  const data = {
    title: settings.modelName || settings.modelProvider || "默认模型",
    category: settings.modelProvider,
    content: "default",
    payload,
    status: "active",
  };

  const saved = savedConfigId.value
    ? await resourceApi.update(projectId.value, "model-configs", savedConfigId.value, data)
    : await resourceApi.create(projectId.value, "model-configs", data);
  savedConfigId.value = saved.id;
}

async function handleTest() {
  testing.value = true;
  testResult.value = null;
  try {
    const result = await aiApi.testConnection(projectId.value, {
      provider: settings.modelProvider,
      api_key: settings.modelApiKey,
      base_url: settings.modelBaseUrl,
      model_name: settings.modelName,
      temperature: 0.1,
      max_tokens: 16,
    });
    if (result.ok || result.status === "ok") {
      await saveModelConfig();
      testResult.value = "✅ 连接成功，已保存为默认模型";
      message.success("模型连接正常，已保存");
    } else {
      testResult.value = `❌ ${result.error || result.message || "连接失败"}`;
      message.error("连接失败");
    }
  } catch (e: any) {
    testResult.value = `❌ ${e.message}`;
    message.error(e.message);
  } finally {
    testing.value = false;
  }
}
</script>

<template>
  <div class="settings-page">
    <h2 style="margin-bottom: 20px">设置</h2>

    <NCard title="模型配置" style="max-width: 600px; margin-bottom: 16px">
      <NForm label-placement="top">
        <NFormItem label="模型提供商">
          <NSelect
            v-model:value="settings.modelProvider"
            :options="providerOptions"
          />
        </NFormItem>
        <NFormItem label="API Key">
          <NInput
            v-model:value="settings.modelApiKey"
            type="password"
            show-password-on="click"
            placeholder="sk-..."
          />
        </NFormItem>
        <NFormItem label="Base URL">
          <NInput
            v-model:value="settings.modelBaseUrl"
            placeholder="https://api.openai.com/v1"
          />
        </NFormItem>
        <NFormItem label="模型名称">
          <NInput
            v-model:value="settings.modelName"
            placeholder="如 gpt-4o / deepseek-chat / qwen-max"
          />
        </NFormItem>
      </NForm>
      <NSpace justify="end">
        <NButton :loading="testing" @click="handleTest">测试并保存</NButton>
      </NSpace>
      <NAlert
        v-if="testResult"
        :type="testResult.startsWith('✅') ? 'success' : 'error'"
        style="margin-top: 12px"
      >
        {{ testResult }}
      </NAlert>
    </NCard>

    <NCard title="界面设置" style="max-width: 600px; margin-bottom: 16px">
      <NForm label-placement="left" :label-width="100">
        <NFormItem label="主题模式">
          <NSpace>
            <NButton
              size="small"
              :type="settings.themeMode === 'light' ? 'primary' : 'default'"
              @click="settings.setTheme('light')"
            >浅色</NButton>
            <NButton
              size="small"
              :type="settings.themeMode === 'dark' ? 'primary' : 'default'"
              @click="settings.setTheme('dark')"
            >深色</NButton>
            <NButton
              size="small"
              :type="settings.themeMode === 'system' ? 'primary' : 'default'"
              @click="settings.setTheme('system')"
            >跟随系统</NButton>
          </NSpace>
        </NFormItem>
      </NForm>
    </NCard>

    <NCard title="关于" style="max-width: 600px">
      <NSpace vertical>
        <NText>AI 小说工作台 · 全流程托管情感深度版</NText>
        <NText depth="3" style="font-size: 13px">
          基于 FastAPI + Vue 3 + Naive UI · 九步管线 · 情感考古架构
        </NText>
      </NSpace>
    </NCard>
  </div>
</template>

<style scoped>
.settings-page { max-width: 700px; }
</style>
