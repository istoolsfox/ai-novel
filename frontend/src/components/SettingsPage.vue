<script setup lang="ts">
import { ref, computed, onMounted } from "vue";
import { useRoute } from "vue-router";
import {
  NCard, NForm, NFormItem, NInput, NSpace, NButton, NSelect, NInputNumber,
  NSwitch, NDivider, NAlert, NText, useMessage,
} from "naive-ui";
import { aiApi } from "../api";
import { useSettingsStore } from "../stores/settings";

const route = useRoute();
const message = useMessage();
const settings = useSettingsStore();

const projectId = computed(() => route.params.projectId as string);
const testing = ref(false);
const testResult = ref<string | null>(null);

const providerOptions = [
  { label: "OpenAI", value: "OpenAI" },
  { label: "Anthropic", value: "Anthropic" },
  { label: "DeepSeek", value: "DeepSeek" },
  { label: "通义千问", value: "Qwen" },
  { label: "自定义", value: "custom" },
];

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
      testResult.value = "✅ 连接成功";
      message.success("模型连接正常");
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
        <NButton :loading="testing" @click="handleTest">测试连接</NButton>
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
