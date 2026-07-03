# PDR · AI 小说创作平台桌面化改造

| 项 | 值 |
|---|---|
| 文档版本 | 1.0 |
| 创建日期 | 2026-07-01 |
| 状态 | 待实施 |
| 项目代号 | ai-novel-workbench-desktop |
| 仓库根目录 | `G:\ai小说` |
| 关联文档 | `docs/PDR-AI小说创作平台.md`（功能 PDR） |

---

## 1. 项目概述

### 1.1 改造目标

将现有 Web 应用形态（FastAPI 后端 + Vite React 前端，需手动启动两个进程）重构为**可独立打包部署的桌面软件**，面向个人开发者场景，最终产物为可分发给用户的安装程序，无需用户额外配置开发环境。

### 1.2 核心要求

| 要求 | 描述 |
|------|------|
| 单体应用架构 | 所有依赖内嵌打包，一个安装程序包含全部 |
| 一键安装卸载 | 标准 OS 安装程序（Windows .msi/.exe、macOS .dmg、Linux .deb/.AppImage） |
| 图形化配置管理 | 提供原生 GUI 用于配置模型、路径等，无需改环境变量 |
| 本地嵌入式数据库 | SQLite（已有，不动） |
| 跨平台打包 | Windows / macOS / Linux 三端 |
| 无需开发环境 | 用户不需要装 Python、Node.js、Rust |
| 参考项目形态 | 参考 PlotPilot（Tauri + FastAPI sidecar + Vue）的软件形态 |
| 结合本身优点 | 复用现有 FastAPI + React 成熟代码，不重写 |

### 1.3 改造原则

1. **不重写后端**：FastAPI 后端 1813 行代码几乎不动，用 PyInstaller 打包为 sidecar
2. **不重写前端**：React 前端几乎不动，Vite build 产物由 Tauri webview 加载
3. **新增桌面壳**：Tauri 2.0 负责窗口、系统集成、进程管理、打包分发
4. **最小侵入**：现有 dev 模式（手动启动前后端）保留，桌面化是额外的打包路径

---

## 2. 现状基线

### 2.1 当前形态

```
开发模式（现状）：
  终端1: python -m uvicorn backend.app.main:app --reload --port 8000
  终端2: cd frontend && npm run dev  → http://127.0.0.1:5173
  浏览器访问 5173，Vite 代理 /api 到 8000

用户使用现状：
  必须安装 Python 3.13 + Node.js 22
  必须手动启动两个进程
  必须用浏览器访问
  无法作为独立软件分发
```

### 2.2 现有技术栈

| 层 | 技术 | 版本 | 桌面化处理 |
|----|------|------|-----------|
| 后端 | FastAPI + uvicorn | - | PyInstaller 打包为 sidecar |
| 数据库 | SQLite | 嵌入式 | 不动 |
| 前端 | React + TypeScript + Vite | React 19, Vite 7.1 | Vite build 产物给 Tauri |
| 关系图 | @xyflow/react | 12.9 | 不动 |
| 图标 | lucide-react | 0.468 | 不动 |
| 导出 | python-docx / reportlab / ebooklib | - | 随后端打包 |
| Python | 3.13 | - | PyInstaller 内嵌 |
| Node | 22.22 | - | 仅构建时需要，运行时不需要 |

### 2.3 现有启动依赖

| 环境变量 | 默认值 | 作用 | 桌面化处理 |
|----------|--------|------|-----------|
| AI_NOVEL_DATABASE_URL | sqlite:///backend/app.db | 数据库路径 | 改为用户数据目录 |
| AI_NOVEL_DATA_DIR | data | 数据根目录 | 改为用户数据目录 |
| VITE_API_BASE | （空，同源） | 前端 API 地址 | Tauri 下固定为 http://127.0.0.1:{动态端口} |

### 2.4 前端 API 调用方式

```typescript
// frontend/src/api.ts L176
const API_BASE = import.meta.env.VITE_API_BASE ?? '';
// fetch(`${API_BASE}${path}`)
```

桌面化后需改为动态获取 sidecar 端口（Tauri 启动时分配）。

---

## 3. 技术选型

### 3.1 方案对比

| 方案 | 桌面壳 | 后端处理 | 安装包体积 | 内存占用 | 跨平台 | 改造量 | 评估 |
|------|--------|---------|-----------|---------|--------|--------|------|
| **A. Tauri + FastAPI sidecar** | Tauri 2.0 | PyInstaller 打包 | ~60-90MB | 低 | 3端 | 小 | **推荐** |
| B. Electron + FastAPI sidecar | Electron | PyInstaller 打包 | ~150-200MB | 高 | 3端 | 中 | 体积过大 |
| C. PyWebView + FastAPI | PyWebView | 直接运行 | ~50-70MB | 低 | 3端 | 中 | webview 不稳定 |
| D. Tauri + Rust 重写后端 | Tauri 2.0 | Rust 重写 | ~10-15MB | 最低 | 3端 | 极大 | 违背"结合本身优点" |

### 3.2 选型决策：方案 A

**Tauri 2.0 + React（现有）+ FastAPI sidecar（PyInstaller 打包）**

理由：
1. **参考 PlotPilot 已验证**：PlotPilot 正是 Tauri + FastAPI sidecar 模式，技术路径可行
2. **结合本身优点**：FastAPI 后端 1813 行 + React 前端几乎零改动
3. **体积可控**：Tauri 壳 ~5MB + Python sidecar ~50-80MB，总计 ~60-90MB，可接受
4. **跨平台**：Tauri 原生支持 Windows/macOS/Linux 三端打包
5. **现代生态**：Tauri 2.0（2024 稳定版）支持 sidecar、自动更新、系统集成

### 3.3 Tauri 2.0 sidecar 机制

Tauri 2.0 原生支持 external binary（sidecar）：
- 在 `tauri.conf.json` 配置 `externalBin`
- Tauri 启动时自动启动 sidecar 进程
- Tauri 关闭时自动结束 sidecar 进程
- 支持 sidecar 的 stdout/stderr 流读取
- 支持 sidecar 健康检查

这完美匹配 FastAPI sidecar 的需求——Tauri 负责窗口，FastAPI 负责业务，两者通过 localhost HTTP 通信。

---

## 4. 架构设计

### 4.1 桌面应用架构

```
┌──────────────────────────────────────────────────┐
│  Tauri 桌面壳（Rust，~5MB）                       │
│  ┌────────────────────────────────────────────┐  │
│  │  WebView（系统原生 webview）                 │  │
│  │  加载 React build 产物                      │  │
│  │  React 19 + @xyflow + lucide               │  │
│  └──────────────────┬─────────────────────────┘  │
│                     │ fetch http://127.0.0.1:{port}│
│  ┌──────────────────▼─────────────────────────┐  │
│  │  Sidecar 进程管理器                          │  │
│  │  启动/监控/关闭 FastAPI sidecar             │  │
│  └──────────────────┬─────────────────────────┘  │
└─────────────────────┼────────────────────────────┘
                      │ HTTP localhost
┌─────────────────────▼────────────────────────────┐
│  FastAPI Sidecar（PyInstaller 打包，~50-80MB）     │
│  uvicorn + FastAPI + SQLite + python-docx + ...  │
│  监听 127.0.0.1:{动态端口}                        │
└─────────────────────┬────────────────────────────┘
                      │ 文件读写
┌─────────────────────▼────────────────────────────┐
│  用户数据目录                                       │
│  ~/AppData/Local/ai-novel-workbench/ (Win)       │
│  ~/Library/Application Support/ai-novel-workbench/ (macOS) │
│  ~/.local/share/ai-novel-workbench/ (Linux)      │
│  ├─ app.db          (SQLite 数据库)               │
│  └─ projects/       (项目数据)                    │
│     ├─ {project_id}/                              │
│     │   ├─ manuscript/                            │
│     │   ├─ memory/                                │
│     │   └─ exports/                               │
│  └─ config.json     (应用配置)                    │
└──────────────────────────────────────────────────┘
```

### 4.2 进程生命周期

```
用户双击应用图标
    ↓
Tauri 主进程启动
    ↓
分配动态端口（避免冲突）
    ↓
启动 FastAPI sidecar：
  AI_NOVEL_DATABASE_URL=sqlite:///{user_data}/app.db
  AI_NOVEL_DATA_DIR={user_data}
  uvicorn backend.app.main:app --host 127.0.0.1 --port {动态端口}
    ↓
健康检查：轮询 GET /api/health 直到 200
    ↓
WebView 加载 React 前端，注入 API_BASE=http://127.0.0.1:{动态端口}
    ↓
显示主窗口
    ↓
用户使用...
    ↓
用户关闭窗口
    ↓
Tauri 发送 SIGTERM 给 sidecar
    ↓
等待 sidecar 优雅退出（最多 5 秒）
    ↓
Tauri 主进程退出
```

### 4.3 通信架构

```
React 前端
    │ fetch HTTP
    ▼
FastAPI sidecar（localhost）
    │ 文件 I/O
    ▼
SQLite + 项目文件系统

特殊通信（Tauri 原生能力）：
React ↔ Tauri Rust 层：
  - @tauri-apps/api invoke()  调用 Rust 命令
  - 用于：打开系统文件对话框、打开外部链接、系统通知、配置读写
```

---

## 5. 目录结构设计

### 5.1 改造后的仓库结构

```
G:\ai小说\
├── backend/                    # 后端（几乎不动）
│   ├── app/
│   │   ├── main.py
│   │   ├── database.py
│   │   └── storage.py
│   ├── tests/
│   ├── requirements.txt
│   └── sidecar_entry.py       # 新增：PyInstaller 打包入口
├── frontend/                   # 前端（几乎不动）
│   ├── src/
│   ├── dist/                   # Vite build 产物（Tauri 加载）
│   ├── package.json
│   └── vite.config.ts
├── desktop/                    # 新增：Tauri 桌面壳
│   ├── src/                    # Rust 源码
│   │   ├── main.rs             # Tauri 主入口
│   │   ├── sidecar.rs          # sidecar 进程管理
│   │   └── config.rs           # 配置管理
│   ├── Cargo.toml              # Rust 依赖
│   ├── tauri.conf.json         # Tauri 配置
│   ├── icons/                  # 应用图标
│   └── build.rs
├── scripts/                    # 新增：打包脚本
│   ├── build_sidecar.py        # PyInstaller 打包后端
│   ├── build_frontend.sh       # Vite build 前端
│   └── build_all.{sh,ps1}      # 一键全平台打包
├── data/                       # 数据目录（开发模式用）
├── docs/
└── README.md
```

### 5.2 关键新增文件说明

| 文件 | 作用 |
|------|------|
| `backend/sidecar_entry.py` | PyInstaller 打包入口，启动 uvicorn |
| `desktop/src/main.rs` | Tauri 主进程入口 |
| `desktop/src/sidecar.rs` | FastAPI sidecar 启动/监控/关闭 |
| `desktop/src/config.rs` | 应用配置读写（用户数据目录） |
| `desktop/tauri.conf.json` | Tauri 配置（窗口、sidecar、打包） |
| `scripts/build_sidecar.py` | 调用 PyInstaller 打包后端 |
| `scripts/build_all.ps1` | Windows 一键打包脚本 |

---

## 6. Tauri 壳设计

### 6.1 tauri.conf.json

```json
{
  "$schema": "https://schema.tauri.app/config/2",
  "productName": "AI 小说创作平台",
  "version": "1.0.0",
  "identifier": "com.ai-novel.workbench",
  "build": {
    "beforeDevCommand": "cd ../frontend && npm run dev",
    "beforeBuildCommand": "cd ../frontend && npm run build",
    "devUrl": "http://127.0.0.1:5173",
    "frontendDist": "../frontend/dist"
  },
  "app": {
    "windows": [
      {
        "title": "AI 小说创作平台",
        "width": 1280,
        "height": 800,
        "minWidth": 960,
        "minHeight": 600,
        "resizable": true,
        "fullscreen": false
      }
    ],
    "security": {
      "csp": "default-src 'self'; connect-src 'self' http://127.0.0.1:*; img-src 'self' data:; style-src 'self' 'unsafe-inline'"
    }
  },
  "bundle": {
    "active": true,
    "targets": ["msi", "nsis"],
    "icon": ["icons/icon.ico", "icons/icon.png"],
    "resources": [],
    "externalBin": ["binaries/ai-novel-backend"],
    "copyright": "© 2026",
    "category": "Productivity",
    "shortDescription": "AI 长篇小说创作工作台",
    "longDescription": "本地优先的 AI 长篇小说创作工具"
  }
}
```

**关键配置说明**：
- `externalBin`：指定 sidecar 二进制路径，Tauri 自动管理启动/关闭
- `beforeBuildCommand`：打包前自动构建前端
- `frontendDist`：指向 Vite build 产物
- `csp` 的 `connect-src`：允许连接 localhost 任意端口（sidecar 动态端口）
- `targets`：Windows 用 msi + nsis（安装程序）

### 6.2 Rust 主进程（desktop/src/main.rs）

```rust
// 伪代码示意，实际生成时完善
mod sidecar;
mod config;

use tauri::Manager;

fn main() {
    tauri::Builder::default()
        .setup(|app| {
            // 1. 读取/创建用户数据目录
            let data_dir = config::ensure_data_dir(app)?;

            // 2. 分配动态端口
            let port = portpicker::pick_unused_port()
                .expect("no free port");

            // 3. 启动 FastAPI sidecar
            sidecar::start(app, port, data_dir)?;

            // 4. 注入端口到前端（通过环境变量或 Tauri 命令）
            app.manage(SidecarState { port });

            Ok(())
        })
        .on_window_event(|window, event| {
            // 窗口关闭时优雅结束 sidecar
            if let tauri::WindowEvent::CloseRequested { .. } = event {
                sidecar::shutdown(window.app_handle());
            }
        })
        .invoke_handler(tauri::generate_handler![
            config::get_config,
            config::save_config,
            sidecar::get_sidecar_port,
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
```

### 6.3 Sidecar 管理（desktop/src/sidecar.rs）

```rust
// 伪代码示意
use std::process::{Command, Child};
use std::time::{Duration, Instant};
use tauri::AppHandle;

pub struct SidecarState {
    pub port: u16,
    pub child: Option<Child>,
}

pub fn start(app: &AppHandle, port: u16, data_dir: &Path) -> Result<(), String> {
    let sidecar_path = app.path()
        .resolve("binaries/ai-novel-backend", tauri::path::BaseDirectory::Resource)
        .map_err(|e| e.to_string())?;

    let db_path = data_dir.join("app.db");
    let db_url = format!("sqlite:///{}", db_path.display());

    let child = Command::new(&sidecar_path)
        .env("AI_NOVEL_DATABASE_URL", &db_url)
        .env("AI_NOVEL_DATA_DIR", data_dir)
        .env("AI_NOVEL_PORT", port.to_string())
        .spawn()
        .map_err(|e| format!("启动后端失败: {}", e))?;

    // 健康检查：轮询 /api/health
    let health_url = format!("http://127.0.0.1:{}/api/health", port);
    let start = Instant::now();
    loop {
        if start.elapsed() > Duration::from_secs(30) {
            return Err("后端启动超时".into());
        }
        if reqwest::blocking::get(&health_url).is_ok() {
            break;
        }
        std::thread::sleep(Duration::from_millis(200));
    }

    // 保存 child 到状态
    app.state::<SidecarState>().child = Some(child);
    Ok(())
}

pub fn shutdown(app: &AppHandle) {
    if let Some(mut child) = app.state::<SidecarState>().child.lock().unwrap().take() {
        // 优雅关闭
        let _ = child.kill();
        let _ = child.wait();
    }
}

#[tauri::command]
pub fn get_sidecar_port(state: tauri::State<SidecarState>) -> u16 {
    state.port
}
```

---

## 7. FastAPI Sidecar 打包

### 7.1 sidecar_entry.py（新增打包入口）

```python
# backend/sidecar_entry.py
"""PyInstaller 打包入口。启动 uvicorn 服务。"""
import os
import sys


def main():
    port = int(os.environ.get("AI_NOVEL_PORT", "8000"))
    host = os.environ.get("AI_NOVEL_HOST", "127.0.0.1")

    # 确保 backend.app 在 sys.path 中
    if getattr(sys, "frozen", False):
        # PyInstaller 打包后的路径修正
        base_dir = os.path.dirname(sys.executable)
        sys.path.insert(0, base_dir)

    import uvicorn
    uvicorn.run(
        "backend.app.main:app",
        host=host,
        port=port,
        log_level="warning",  # 桌面模式下减少日志
        access_log=False,
    )


if __name__ == "__main__":
    main()
```

### 7.2 PyInstaller 打包脚本（scripts/build_sidecar.py）

```python
# scripts/build_sidecar.py
"""用 PyInstaller 把 FastAPI 后端打包为单文件可执行程序。"""
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
BACKEND = ROOT / "backend"
DIST = ROOT / "desktop" / "binaries"


def build():
    DIST.mkdir(parents=True, exist_ok=True)

    # PyInstaller 命令
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",                          # 单文件
        "--name", "ai-novel-backend",         # 输出名
        "--distpath", str(DIST),              # 输出目录
        "--workpath", str(ROOT / "build" / "pyi"),
        "--specpath", str(ROOT / "build" / "pyi"),
        # 收集数据文件
        "--collect-data", "ebooklib",
        "--collect-data", "reportlab",
        # 隐式导入
        "--hidden-import", "uvicorn.logging",
        "--hidden-import", "uvicorn.protocols.http.auto",
        "--hidden-import", "uvicorn.protocols.websockets.auto",
        "--hidden-import", "uvicorn.lifespan.on",
        # 入口
        str(BACKEND / "sidecar_entry.py"),
    ]

    print("Building FastAPI sidecar...")
    result = subprocess.run(cmd, cwd=str(ROOT))
    if result.returncode != 0:
        print("FAILED: sidecar build")
        sys.exit(1)
    print(f"OK: sidecar at {DIST / 'ai-novel-backend'}")


if __name__ == "__main__":
    build()
```

### 7.3 后端改造点

| 改造点 | 位置 | 内容 |
|--------|------|------|
| 端口从环境变量读取 | sidecar_entry.py | `AI_NOVEL_PORT` 环境变量 |
| 数据目录从环境变量读取 | storage.py L8 | 已支持 `AI_NOVEL_DATA_DIR`，无需改 |
| 数据库路径从环境变量读取 | database.py L20 | 已支持 `AI_NOVEL_DATABASE_URL`，无需改 |
| 日志降级 | sidecar_entry.py | `log_level="warning"` |

**关键：后端业务代码零改动。** 所有路径通过环境变量注入，sidecar_entry.py 只负责启动。

---

## 8. 前端适配

### 8.1 改造点

| 改造点 | 位置 | 内容 |
|--------|------|------|
| API_BASE 动态获取 | api.ts L176 | Tauri 模式下调用 `invoke('get_sidecar_port')` 获取端口 |
| Vite build 配置 | vite.config.ts | 增加 base 路径适配 Tauri |
| 环境变量 | .env | `VITE_TAURI=true` 标识桌面模式 |

### 8.2 api.ts 改造

```typescript
// frontend/src/api.ts 改造

// 检测是否在 Tauri 环境中
const isTauri = typeof window !== 'undefined' && '__TAURI_INTERNALS__' in window;

let apiBaseCache = '';

async function getApiBase(): Promise<string> {
  if (apiBaseCache) return apiBaseCache;

  if (isTauri) {
    // Tauri 模式：从 Rust 层获取 sidecar 端口
    const { invoke } = await import('@tauri-apps/api/core');
    const port = await invoke<number>('get_sidecar_port');
    apiBaseCache = `http://127.0.0.1:${port}`;
  } else {
    // Web 模式：保持原有行为
    apiBaseCache = import.meta.env.VITE_API_BASE ?? '';
  }
  return apiBaseCache;
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const base = await getApiBase();
  const response = await fetch(`${base}${path}`, {
    headers: { 'Content-Type': 'application/json', ...(options?.headers ?? {}) },
    ...options,
  });
  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || response.statusText);
  }
  return response.json() as Promise<T>;
}
```

**改造量**：仅 api.ts 的 `request` 函数 + `API_BASE` 获取逻辑，其余全部不动。

### 8.3 vite.config.ts 改造

```typescript
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  // Tauri 模式下使用相对路径
  base: process.env.VITE_TAURI ? './' : '/',
  test: {
    environment: 'jsdom',
    setupFiles: './src/test/setup.ts',
  },
  server: {
    proxy: {
      '/api': 'http://127.0.0.1:8000',
    },
  },
  // Tauri 构建时禁用 sourcemap 减小体积
  build: {
    sourcemap: false,
  },
});
```

### 8.4 package.json 新增依赖

```json
{
  "dependencies": {
    "@tauri-apps/api": "^2.0.0"
  }
}
```

---

## 9. 配置管理 GUI

### 9.1 配置项

| 配置 | 类型 | 默认值 | 存储 |
|------|------|--------|------|
| 数据目录 | path | 用户数据目录 | config.json |
| 默认模型 | string | "" | config.json / SQLite |
| 模型 API Key | string（加密） | "" | config.json |
| 导出目录 | path | {data}/exports | config.json |
| 自动保存 | bool | true | config.json |

### 9.2 配置存储（config.json）

```json
{
  "data_dir": "C:\\Users\\{user}\\AppData\\Local\\ai-novel-workbench",
  "export_dir": "C:\\Users\\{user}\\AppData\\Local\\ai-novel-workbench\\exports",
  "version": "1.0.0",
  "first_run": false
}
```

位置：
- Windows: `%LOCALAPPDATA%\ai-novel-workbench\config.json`
- macOS: `~/Library/Application Support/ai-novel-workbench/config.json`
- Linux: `~/.config/ai-novel-workbench/config.json`

### 9.3 配置 GUI 实现

**方案：React 配置页面 + Tauri 原生命令**

不单独做原生 GUI 窗口——直接在 React 前端里加一个"设置"页面，通过 Tauri invoke 调用 Rust 层读写 config.json。

**新增 React 组件**：`SettingsPage.tsx`

```typescript
// frontend/src/components/SettingsPage.tsx（新增）
// - 数据目录显示与修改（调用 Tauri open dialog）
// - 导出目录显示与修改
// - 模型配置（复用现有 model-configs，但增加全局默认模型）
// - 关于信息（版本号、数据目录路径）
```

**Tauri 命令**（Rust 侧）：

```rust
#[tauri::command]
fn get_config(state: tauri::State<ConfigState>) -> Config {
    state.config.lock().unwrap().clone()
}

#[tauri::command]
fn save_config(config: Config, state: tauri::State<ConfigState>) -> Result<(), String> {
    let mut current = state.config.lock().unwrap();
    *current = config.clone();
    config::write_config(&config)
}

#[tauri::command]
fn open_directory_dialog(app: tauri::AppHandle) -> Option<String> {
    // 调用系统文件对话框选择目录
    tauri_plugin_dialog::DialogExt::app(&app)
        .file()
        .set_title("选择目录")
        .blocking_pick_folder()
        .map(|p| p.to_string())
}
```

### 9.4 首次启动引导

首次运行时显示引导页面：
1. 欢迎语
2. 选择数据存储目录（默认用户数据目录，可改）
3. （可选）配置默认 AI 模型
4. 创建数据库
5. 进入主界面

---

## 10. 数据存储本地化

### 10.1 数据目录策略

| 平台 | 默认数据目录 |
|------|-------------|
| Windows | `%LOCALAPPDATA%\ai-novel-workbench\` |
| macOS | `~/Library/Application Support/ai-novel-workbench/` |
| Linux | `~/.local/share/ai-novel-workbench/` |

### 10.2 目录结构

```
{user_data_dir}/
├── config.json          # 应用配置
├── app.db               # SQLite 数据库
└── projects/            # 项目数据（复用现有结构）
    └── {project_id}/
        ├── manuscript/
        ├── memory/
        │   ├── raw_sources/
        │   ├── wiki/
        │   └─ index/
        ├── exports/
        └── backups/
```

### 10.3 后端路径注入

Tauri 启动 sidecar 时通过环境变量注入：

```
AI_NOVEL_DATABASE_URL=sqlite:///{user_data}/app.db
AI_NOVEL_DATA_DIR={user_data}
AI_NOVEL_PORT={动态端口}
```

后端 `storage.py` 和 `database.py` 已支持这两个环境变量，**无需改动**。

---

## 11. 跨平台打包

### 11.1 打包流程

```
一键打包脚本（scripts/build_all.ps1 / build_all.sh）：

Step 1: 构建前端
  cd frontend && npm install && npm run build
  → 产出 frontend/dist/

Step 2: 构建后端 sidecar
  python scripts/build_sidecar.py
  → 产出 desktop/binaries/ai-novel-backend[.exe]

Step 3: 构建 Tauri 应用
  cd desktop && cargo tauri build
  → 产出安装包：
    Windows: desktop/target/release/bundle/{msi,nsis}/*.msi / *.exe
    macOS:   desktop/target/release/bundle/{dmg,app}/*.dmg
    Linux:   desktop/target/release/bundle/{deb,appimage}/*.deb / *.AppImage
```

### 11.2 各平台产物

| 平台 | 产物格式 | 工具链要求（构建机） |
|------|---------|---------------------|
| Windows | .msi + .exe (NSIS) | Rust + Tauri CLI + PyInstaller + Node.js |
| macOS | .dmg | Rust + Tauri CLI + PyInstaller + Node.js（需 macOS 机器） |
| Linux | .deb + .AppImage | Rust + Tauri CLI + PyInstaller + Node.js（需 Linux 机器） |

**注意**：跨平台打包必须在对应平台进行（macOS 包必须在 macOS 上构建）。如需 CI，可用 GitHub Actions 矩阵构建。

### 11.3 GitHub Actions CI（可选，后续）

```yaml
# .github/workflows/build-desktop.yml
strategy:
  matrix:
    os: [windows-latest, macos-latest, ubuntu-latest]
runs-on: ${{ matrix.os }}
steps:
  - uses: actions/checkout@v4
  - uses: actions/setup-node@v4
  - uses: actions/setup-python@v5
  - uses: dtolnay/rust-toolchain@stable
  - run: npm install
  - run: pip install -r backend/requirements.txt pyinstaller
  - run: python scripts/build_sidecar.py
  - run: cargo install tauri-cli
  - run: cargo tauri build
  - uses: actions/upload-artifact@v4
```

---

## 12. 代码改造点清单

### 12.1 新增文件

| 文件 | 作用 |
|------|------|
| `backend/sidecar_entry.py` | PyInstaller 打包入口 |
| `desktop/Cargo.toml` | Rust 依赖声明 |
| `desktop/tauri.conf.json` | Tauri 配置 |
| `desktop/build.rs` | Tauri 构建脚本 |
| `desktop/src/main.rs` | Tauri 主入口 |
| `desktop/src/sidecar.rs` | Sidecar 进程管理 |
| `desktop/src/config.rs` | 配置管理 |
| `desktop/icons/icon.ico` | Windows 图标 |
| `desktop/icons/icon.png` | 通用图标 |
| `scripts/build_sidecar.py` | PyInstaller 打包脚本 |
| `scripts/build_all.ps1` | Windows 一键打包 |
| `scripts/build_all.sh` | Linux/macOS 一键打包 |
| `frontend/src/components/SettingsPage.tsx` | 配置管理页面 |

### 12.2 改动文件

| 文件 | 改动 |
|------|------|
| `frontend/src/api.ts` L176-188 | API_BASE 改为动态获取（Tauri/Web 双模式） |
| `frontend/vite.config.ts` | 增加 base 和 build.sourcemap 配置 |
| `frontend/package.json` | 新增 `@tauri-apps/api` 依赖 |
| `frontend/src/App.tsx` | 新增设置页面入口（可选） |
| `backend/requirements.txt` | 无需改（PyInstaller 收集现有依赖） |

### 12.3 不动的文件

| 文件 | 原因 |
|------|------|
| `backend/app/main.py` | 业务逻辑零改动，端口/路径通过环境变量注入 |
| `backend/app/database.py` | 已支持环境变量 |
| `backend/app/storage.py` | 已支持环境变量 |
| 现有全部 React 组件 | 仅 api.ts 改请求方式 |
| 现有测试 | 不受影响 |

---

## 13. 实施路线图

### Phase 0：环境准备（0.5天）

```
1. 安装 Rust 工具链
2. 安装 Tauri CLI：cargo install tauri-cli
3. 安装 PyInstaller：pip install pyinstaller
4. 前端新增 @tauri-apps/api 依赖
5. 创建 desktop/ 目录结构
```

### Phase 1：Sidecar 打包（1天）

```
1. 编写 backend/sidecar_entry.py
2. 编写 scripts/build_sidecar.py
3. 执行打包，验证 ai-novel-backend 可独立运行
4. 验证：设置环境变量后，sidecar 能正常启动并响应 /api/health
验收：sidecar 二进制可在无 Python 环境的机器上运行
```

### Phase 2：Tauri 壳搭建（1.5天）

```
1. 初始化 Tauri 项目：cargo tauri init
2. 编写 tauri.conf.json
3. 编写 desktop/src/main.rs（窗口创建）
4. 编写 desktop/src/sidecar.rs（进程管理 + 健康检查）
5. 编写 desktop/src/config.rs（配置读写）
6. 验证：cargo tauri dev 能启动窗口 + sidecar + 加载前端
验收：开发模式下桌面窗口可正常使用全部功能
```

### Phase 3：前端适配（0.5天）

```
1. 改造 api.ts：动态 API_BASE
2. 改造 vite.config.ts：base + sourcemap
3. 新增 SettingsPage.tsx
4. App.tsx 接入设置页面
验收：Tauri 模式下 API 调用正常，设置页面可读写配置
```

### Phase 4：打包分发（1天）

```
1. 编写 scripts/build_all.ps1
2. 执行完整打包流程
3. 验证安装包：在干净 Windows 上安装运行
4. 验证卸载：卸载后无残留
验收：.msi 安装包可在无开发环境的 Windows 上安装运行卸载
```

### Phase 5：跨平台（后续）

```
1. macOS 上执行 build_all.sh，产出 .dmg
2. Linux 上执行 build_all.sh，产出 .deb + .AppImage
3. （可选）配置 GitHub Actions CI 矩阵构建
```

---

## 14. 验收标准

### 14.1 Sidecar 验收

| 验收项 | 标准 |
|--------|------|
| 打包成功 | PyInstaller 产出 ai-novel-backend.exe |
| 独立运行 | 在无 Python 的机器上能启动 |
| 环境变量 | 支持 AI_NOVEL_PORT / AI_NOVEL_DATABASE_URL / AI_NOVEL_DATA_DIR |
| 健康检查 | GET /api/health 返回 200 |
| 功能完整 | 全部 30 个 API 端点正常工作 |
| 导出功能 | docx/pdf/epub 导出正常（依赖被打包） |

### 14.2 Tauri 壳验收

| 验收项 | 标准 |
|--------|------|
| 窗口启动 | 双击应用可打开 1280×800 窗口 |
| Sidecar 管理 | 启动时自动拉起 sidecar，关闭时自动结束 |
| 健康检查 | sidecar 就绪后才显示主窗口 |
| 端口动态 | 无端口冲突（动态分配） |
| 前端加载 | React 界面正常显示 |
| API 通信 | 前端 fetch 正常到达 sidecar |

### 14.3 安装包验收

| 验收项 | 标准 |
|--------|------|
| 安装 | .msi 双击安装成功，无需额外依赖 |
| 首次启动 | 显示引导，创建数据目录和数据库 |
| 数据隔离 | 数据存到用户数据目录，不污染安装目录 |
| 卸载 | 控制面板可卸载，安装目录清除 |
| 数据保留 | 卸载后用户数据目录保留（可选清除） |
| 体积 | 安装包 < 100MB |

---

## 15. 风险与对策

| 风险 | 等级 | 对策 |
|------|------|------|
| PyInstaller 遗漏隐式导入 | 中 | 用 `--collect-all` 收集 fastapi/uvicorn；打包后完整测试 |
| ebooklib/reportlab 数据文件未打包 | 中 | `--collect-data` 显式收集 |
| Tauri sidecar 路径在打包后变化 | 中 | 用 `tauri::path::BaseDirectory::Resource` 解析 |
| 动态端口被占用 | 低 | portpicker 选未用端口 + 健康检查重试 |
| macOS 代码签名 | 中 | 后续配置 Apple Developer 证书；首版可 unsigned（用户手动信任） |
| Windows Defender 误报 | 中 | 申请代码签名证书；首版可在 README 说明 |
| SQLite 并发（sidecar 单进程） | 低 | 现有 Write Dispatch 模式无并发写，不受影响 |
| 前端 CSP 阻止 localhost | 中 | tauri.conf.json 的 csp 已配置 connect-src |

---

## 16. 与功能 PDR 的关系

本 PDR（桌面化改造）与 `PDR-AI小说创作平台.md`（功能 PDR）是**正交**关系：

```
功能 PDR：定义"做什么功能"（情感考古、种子、加深等）
桌面化 PDR：定义"怎么打包成分发软件"（Tauri + sidecar）

两者可并行推进：
  - 功能开发在 backend/ + frontend/ 上进行（dev 模式验证）
  - 桌面化在 desktop/ + scripts/ 上进行（打包流程）
  - 功能开发完成后，桌面化打包自动包含新功能
```

**建议实施顺序**：
1. 先做桌面化 Phase 0-2（搭好 Tauri 壳 + sidecar），让现有功能能跑在桌面里
2. 再做功能 PDR 的 P0（情感考古），在桌面环境里验证
3. 最后桌面化 Phase 3-4（前端适配 + 打包分发）

---

## 附录 A：开发环境要求

### 构建机环境

| 工具 | 版本 | 用途 |
|------|------|------|
| Rust | stable (1.75+) | Tauri 壳编译 |
| Tauri CLI | 2.0+ | Tauri 命令行 |
| Python | 3.13 | sidecar 打包 |
| PyInstaller | 6.0+ | Python 打包 |
| Node.js | 22+ | 前端构建 |
| Windows SDK | 10+ | Windows 打包（仅 Windows） |

### 用户机器环境

**无要求。** 安装包自包含全部运行时。

---

## 附录 B：Cargo.toml 依赖

```toml
# desktop/Cargo.toml
[package]
name = "ai-novel-workbench"
version = "1.0.0"
edition = "2021"

[build-dependencies]
tauri-build = { version = "2", features = [] }

[dependencies]
tauri = { version = "2", features = [] }
tauri-plugin-dialog = "2"
serde = { version = "1", features = ["derive"] }
serde_json = "1"
portpicker = "0.1"
reqwest = { version = "0.12", features = ["blocking"] }
dirs = "5"

[features]
custom-protocol = ["tauri/custom-protocol"]
```

---

## 附录 C：不做什么（明确排除）

- ❌ 不重写后端为 Rust（结合本身优点，保留 FastAPI）
- ❌ 不用 Electron（体积过大，不符合参考 PlotPilot 的要求）
- ❌ 不改后端业务代码（通过环境变量注入路径/端口）
- ❌ 不改现有数据模型（SQLite + 文件系统不动）
- ❌ 不做云同步（本地优先原则不变）
- ❌ 不做自动更新（首版手动分发，后续可加 Tauri updater）
- ❌ 不做代码签名（首版 unsigned，后续配置证书）
- ❌ 不破坏现有 dev 模式（Web 开发模式保留）
