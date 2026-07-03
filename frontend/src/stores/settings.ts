import { defineStore } from "pinia";
import { ref, computed } from "vue";

const THEME_KEY = "ai-novel-theme";

export const useSettingsStore = defineStore("settings", () => {
  const themeMode = ref<"light" | "dark" | "system">("system");
  const modelProvider = ref("OpenAI");
  const modelApiKey = ref("");
  const modelBaseUrl = ref("https://api.openai.com/v1");
  const modelName = ref("");

  function init() {
    const saved = localStorage.getItem(THEME_KEY);
    if (saved === "light" || saved === "dark" || saved === "system") {
      themeMode.value = saved;
    }
    // 监听系统主题变化
    window
      .matchMedia("(prefers-color-scheme: dark)")
      .addEventListener("change", () => {
        if (themeMode.value === "system") {
          // 触发响应式更新
          themeMode.value = "system";
        }
      });
  }

  function setTheme(mode: "light" | "dark" | "system") {
    themeMode.value = mode;
    localStorage.setItem(THEME_KEY, mode);
  }

  function cycleTheme() {
    const order: ("light" | "dark" | "system")[] = ["light", "dark", "system"];
    const idx = order.indexOf(themeMode.value);
    setTheme(order[(idx + 1) % order.length]);
  }

  const themeLabel = computed(() => {
    const map = { light: "浅色", dark: "深色", system: "跟随系统" };
    return map[themeMode.value];
  });

  return {
    themeMode,
    modelProvider,
    modelApiKey,
    modelBaseUrl,
    modelName,
    init,
    setTheme,
    cycleTheme,
    themeLabel,
  };
});
