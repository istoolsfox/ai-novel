<script setup lang="ts">
import { darkTheme, type GlobalTheme } from "naive-ui";
import { computed, onMounted } from "vue";
import { useSettingsStore } from "./stores/settings";
import { initApiBase } from "./api/client";

const settings = useSettingsStore();

const theme = computed<GlobalTheme | null>(() => {
  if (settings.themeMode === "dark") return darkTheme;
  if (settings.themeMode === "system") {
    return window.matchMedia("(prefers-color-scheme: dark)").matches
      ? darkTheme
      : null;
  }
  return null;
});

onMounted(async () => {
  settings.init();
  // Tauri 模式下预缓存 sidecar 端口
  await initApiBase();
});
</script>

<template>
  <n-config-provider :theme="theme">
    <n-message-provider>
      <n-dialog-provider>
        <n-notification-provider>
          <router-view />
        </n-notification-provider>
      </n-dialog-provider>
    </n-message-provider>
  </n-config-provider>
</template>
