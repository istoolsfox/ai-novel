# Cloudflare 域名部署说明

这个项目是 FastAPI 后端 + Vue 前端 + SQLite / llmwiki 文件记忆，不适合只部署到 Cloudflare Pages 静态站。Cloudflare 更适合在这里承担：

```text
域名解析 / HTTPS / CDN / 访问入口
```

实际运行服务建议继续用 Render Free Web Service 或其他支持 Python Web Service 的平台。这样可以完整测试：

```text
前端页面
/api 后端
Autopilot 托管生成
llmwiki
关系画布
导出功能
```

## 推荐结构

```text
用户访问你的域名
  ↓
Cloudflare DNS / HTTPS
  ↓
Render Free Web Service
  ↓
FastAPI 后端托管 Vue 前端 + API
```

## 一、先部署 Web Service

先用仓库根目录的 `render.yaml` 在 Render 创建免费 Web Service。

当前 `render.yaml` 是免费测试模式：

```text
plan: free
AI_NOVEL_DATA_DIR=/tmp/ai-novel-data
AI_NOVEL_DATABASE_URL=sqlite:////tmp/ai-novel-data/app.db
```

这个模式适合测试功能，但数据不保证长期保存。

部署成功后，会得到一个临时地址，例如：

```text
https://你的服务名.onrender.com
```

先确认这个地址能正常打开网站，并且 `/api/health` 返回正常。

## 二、在 Render 里绑定自定义域名

进入 Render：

```text
Service → Settings → Custom Domains → Add Custom Domain
```

建议先绑定子域名，例如：

```text
novel.example.com
```

Render 会提示需要添加 DNS 记录。通常是 CNAME，目标指向你的 Render 服务地址或 Render 给出的验证地址。

## 三、在 Cloudflare 添加 DNS

进入 Cloudflare：

```text
Websites → 你的域名 → DNS → Records → Add record
```

添加记录：

```text
Type: CNAME
Name: novel
Target: 你的 Render 服务域名或 Render 提示的目标
Proxy status: DNS only（灰云，先不要开橙云）
TTL: Auto
```

第一次验证建议用灰云，等 Render 验证和 HTTPS 证书都成功后，再考虑是否打开 Cloudflare 代理。

## 四、回到 Render 验证域名

回到 Render 的 Custom Domains 页面，点击 Verify。

如果暂时失败，等几分钟再试。DNS 生效有延迟。

验证成功后访问：

```text
https://novel.example.com
```

## 五、Cloudflare SSL 设置

Cloudflare 里建议：

```text
SSL/TLS → Overview → Full
```

不要用 Flexible。Flexible 可能导致 HTTPS 回源问题、重定向循环或接口异常。

## 六、上线测试清单

域名打开后，按这个顺序测试：

```text
1. 打开首页
2. 创建项目
3. 配置模型 API，或先用 stub 跑通
4. 启动 Autopilot
5. 检查角色、关系、大纲、关系画布
6. 生成至少 2 章
7. 检查 llmwiki：chapters/index.md、bridges/index.md、关键记忆.md
8. 检查第二章是否承接第一章衔接包
9. 测试导出 Markdown / TXT / DOCX / PDF / EPUB
```

## 七、为什么不直接用 Cloudflare Pages

Cloudflare Pages 很适合托管 Vue 这种静态前端，但这个项目不是纯前端。它需要 Python FastAPI、SQLite、后台章节生成任务和文件系统记忆。

如果只上 Cloudflare Pages，通常只能打开前端页面，核心功能会缺：

```text
/api 后端不可用
SQLite 不可用
llmwiki 文件记忆不可用
后台生成任务不可用
导出功能不可用
```

所以当前建议是：

```text
Cloudflare 管域名 + Render Free 跑完整网站
```

等后续要长期保存数据，再考虑 Render 持久化磁盘、Postgres、R2 或 D1。