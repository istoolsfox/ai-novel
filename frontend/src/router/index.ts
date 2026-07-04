import { createRouter, createWebHashHistory, type RouteRecordRaw } from "vue-router";

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
        meta: { title: "概览", icon: "📊" },
      },
      {
        path: "blueprints",
        name: "Blueprints",
        component: () => import("../components/BlueprintEditor.vue"),
        meta: { title: "卷蓝图", icon: "🗺️" },
      },
      {
        path: "generate",
        name: "Generate",
        component: () => import("../components/JobLauncher.vue"),
        meta: { title: "托管生成", icon: "🚀" },
      },
      {
        path: "progress/:jobId",
        name: "JobProgress",
        component: () => import("../components/JobProgressPanel.vue"),
        meta: { title: "生成进度", icon: "📈" },
      },
      {
        path: "chapters",
        name: "Chapters",
        component: () => import("../components/NovelEditor.vue"),
        meta: { title: "章节编辑器", icon: "✍️" },
      },
      {
        path: "emotion",
        name: "Emotion",
        component: () => import("../components/EmotionWorkbench.vue"),
        meta: { title: "情感工作台", icon: "🎭" },
      },
      {
        path: "outline",
        name: "Outline",
        component: () => import("../views/OutlinePage.vue"),
        meta: { title: "大纲", icon: "📚" },
      },
      {
        path: "characters",
        name: "Characters",
        component: () => import("../views/CharactersPage.vue"),
        meta: { title: "故事圣经", icon: "📖" },
      },
      {
        path: "graph",
        name: "Graph",
        component: () => import("../views/RelationshipPage.vue"),
        meta: { title: "角色关系图", icon: "🕸️" },
      },
      {
        path: "timeline",
        name: "Timeline",
        component: () => import("../views/TimelinePage.vue"),
        meta: { title: "时间线", icon: "⏳" },
      },
      {
        path: "foreshadowing",
        name: "Foreshadowing",
        component: () => import("../views/ForeshadowingPage.vue"),
        meta: { title: "伏笔管理", icon: "✨" },
      },
      {
        path: "style",
        name: "Style",
        component: () => import("../views/StylePage.vue"),
        meta: { title: "风格学习", icon: "⭐" },
      },
      {
        path: "taboo",
        name: "Taboo",
        component: () => import("../views/TabooPage.vue"),
        meta: { title: "雷点控制", icon: "⚠️" },
      },
      {
        path: "knowledge",
        name: "Knowledge",
        component: () => import("../views/KnowledgePage.vue"),
        meta: { title: "知识库", icon: "📚" },
      },
      {
        path: "wiki",
        name: "Wiki",
        component: () => import("../views/WikiPage.vue"),
        meta: { title: "llmwiki 记忆", icon: "🧠" },
      },
      {
        path: "export",
        name: "Export",
        component: () => import("../views/ExportPage.vue"),
        meta: { title: "导出", icon: "📥" },
      },
      {
        path: "results/:jobId",
        name: "JobResults",
        component: () => import("../components/JobResultOverview.vue"),
        meta: { title: "结果总览", icon: "📋" },
      },
      {
        path: "settings",
        name: "Settings",
        component: () => import("../components/SettingsPage.vue"),
        meta: { title: "设置", icon: "⚙️" },
      },
    ],
  },
];

const router = createRouter({
  // Hash 路由能直接部署到 Cloudflare Pages / Netlify / Vercel 静态站点，刷新子页面不会 404。
  history: createWebHashHistory(),
  routes,
});

router.afterEach((to) => {
  const title = (to.meta?.title as string) || "AI 小说工作台";
  document.title = `${title} · AI 小说工作台`;
});

export default router;
