# Cloudflare Pages 前端部署说明

这个文件用于把项目做成类似 `*.netlify.app` 那种“打开就能访问”的前端站点。

注意：Cloudflare Pages 只托管前端静态页面。完整功能仍然需要一个后端 API，例如 Render Free Web Service。

## 当前已经完成的适配

前端现在支持外部后端地址：

```text
VITE_API_BASE_URL=https://你的后端地址
```

同时路由已经改成 Hash 模式，所以 Cloudflare Pages 上刷新子页面不会 404。

## 推荐架构

```text
Cloudflare Pages
  托管 Vue 前端页面
  访问地址例如：https://ai-novel.pages.dev

Render Free Web Service
  托管 FastAPI 后端
  访问地址例如：https://ai-novel.onrender.com

前端通过 VITE_API_BASE_URL 调用后端 /api
```

## 一、先部署后端

先用仓库根目录的 `render.yaml` 在 Render Free 创建 Web Service。

后端部署成功后，记录地址，例如：

```text
https://ai-novel.onrender.com
```

确认：

```text
https://ai-novel.onrender.com/api/health
```

能正常返回。

## 二、Cloudflare Pages 新建项目

进入 Cloudflare：

```text
Workers & Pages → Create application → Pages → Connect to Git
```

选择仓库：

```text
wlxb625/ai-novel
```

分支：

```text
codex/ai-novel-workbench-updates
```

构建配置：

```text
Framework preset: Vite
Root directory: frontend
Build command: npm install && npm run build
Build output directory: dist
```

## 三、配置环境变量

在 Cloudflare Pages 的环境变量里添加：

```text
VITE_API_BASE_URL=https://你的后端地址
```

例如：

```text
VITE_API_BASE_URL=https://ai-novel.onrender.com
```

注意不要在末尾加 `/`。

## 四、部署并访问

部署成功后，Cloudflare 会给一个地址，例如：

```text
https://ai-novel.pages.dev
```

打开后测试：

```text
1. 首页能打开
2. 项目列表能加载
3. 能创建项目
4. 能进入设置页
5. 能启动 Autopilot
6. 能查看 llmwiki
7. 能导出文件
```

## 五、绑定自定义域名

如果你有自己的域名，在 Cloudflare Pages 项目里：

```text
Custom domains → Set up a custom domain
```

例如绑定：

```text
novel.example.com
```

因为域名本来就在 Cloudflare，通常会自动帮你添加 DNS 记录。

## 六、限制说明

这种方案的优点是：

```text
前端免费、访问快、像 Netlify 一样容易打开
```

限制是：

```text
后端仍然依赖 Render Free
Render Free 休眠后第一次访问会慢
免费模式数据不保证长期保存
```

如果以后要长期保存项目，建议把后端数据库和文件记忆迁移到持久化存储。