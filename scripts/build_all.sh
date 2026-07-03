#!/usr/bin/env bash
# 一键打包脚本（Linux / macOS）。
#
# 用法：
#     chmod +x scripts/build_all.sh && ./scripts/build_all.sh

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
echo -e "\033[36m[build_all] ROOT = $ROOT\033[0m"

# Step 1: 构建前端
echo -e "\n\033[33m=== Step 1/3: 构建前端 ===\033[0m"
cd "$ROOT/frontend"
[ -d node_modules ] || npm install
export VITE_TAURI=true
npm run build
echo -e "\033[32m前端构建完成\033[0m"

# Step 2: 构建 sidecar
echo -e "\n\033[33m=== Step 2/3: 构建后端 sidecar ===\033[0m"
python "$ROOT/scripts/build_sidecar.py"
echo -e "\033[32mSidecar 构建完成\033[0m"

# Step 3: 构建 Tauri
echo -e "\n\033[33m=== Step 3/3: 构建 Tauri 应用 ===\033[0m"
cd "$ROOT/desktop"
cargo tauri build
echo -e "\033[32mTauri 构建完成\033[0m"

echo -e "\n\033[36m=== 全部构建完成 ===\033[0m"
echo -e "\033[36m安装包位于：$ROOT/desktop/target/release/bundle/\033[0m"
