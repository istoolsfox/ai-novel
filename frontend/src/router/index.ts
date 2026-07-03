import { createRouter, createWebHistory, type RouteRecordRaw } from "vue-router";

const routes: RouteRecordRaw[] = [
  {
    path: "/",
    redirect: "/projects",
  },
  {
    path: "/projects",
    name: "ProjectList",
    component: () => import("../views/ProjectList.vue"),
    meta: { title: "项目列表" },
  },
  {
    path: "/projects/:projectId",
    component: () => import("../layouts/MainLayout.vue"),
    children: [
      {
        path: "",
        name: "Dashboard",
        component: () => import("../views/Dashboard.vue"),
        meta: { title: "概览" },
      },
      {
        path: "blueprints",
        name: "Blueprints",
        component: () => import("../components/BlueprintEditor.vue"),
        meta: { title: "卷蓝图" },
      },
      {
        path: "generate",
        name: "Generate",
        component: () => import("../components/JobLauncher.vue"),
        meta: { title: "托管生成" },
      },
      {
        path: "progress/:jobId",
        name: "JobProgress",
        component: () => import("../components/JobProgressPanel.vue"),
        meta: { title: "生成进度" },
      },
      {
        path: "chapters",
        name: "Chapters",
        component: () => import("../components/NovelEditor.vue"),
        meta: { title: "章节编辑" },
      },
      {
        path: "emotion",
        name: "Emotion",
        component: () => import("../components/EmotionWorkbench.vue"),
        meta: { title: "情感工作台" },
      },
      {
        path: "results/:jobId",
        name: "JobResults",
        component: () => import("../components/JobResultOverview.vue"),
        meta: { title: "结果总览" },
      },
      {
        path: "settings",
        name: "Settings",
        component: () => import("../components/SettingsPage.vue"),
        meta: { title: "设置" },
      },
    ],
  },
];

const router = createRouter({
  history: createWebHistory(),
  routes,
});

router.afterEach((to) => {
  const title = (to.meta?.title as string) || "AI 小说工作台";
  document.title = `${title} · AI 小说工作台`;
});

export default router;
