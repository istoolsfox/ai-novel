// ===== API 客户端：fetch 封装 + SSE 支持（Tauri/Web 双模式）=====

/**
 * Tauri 环境检测。
 * Tauri 2.0 注入 `window.__TAURI_INTERNALS__`，旧版注入 `window.__TAURI__`。
 */
function isTauri(): boolean {
  return (
    typeof window !== "undefined" &&
    ("__TAURI_INTERNALS__" in window || "__TAURI__" in window)
  );
}

function configuredApiBase(): string {
  const value = import.meta.env.VITE_API_BASE_URL;
  if (typeof value !== "string" || !value.trim()) return "";
  return value.trim().replace(/\/$/, "");
}

let _apiBaseCache = "";

/**
 * 异步获取 API base URL：
 * - Tauri 模式：通过 invoke('get_sidecar_port') 获取 sidecar 端口
 * - Web 模式：默认同源；如果配置了 VITE_API_BASE_URL，则请求外部后端
 */
export async function getApiBase(): Promise<string> {
  if (_apiBaseCache) return _apiBaseCache;

  if (isTauri()) {
    try {
      const { invoke } = await import("@tauri-apps/api/core");
      const port = await invoke<number>("get_sidecar_port");
      _apiBaseCache = `http://127.0.0.1:${port}`;
    } catch {
      // invoke 失败时回退到默认端口
      _apiBaseCache = "http://127.0.0.1:8000";
    }
  } else {
    _apiBaseCache = configuredApiBase();
  }
  return _apiBaseCache;
}

/**
 * 同步获取 API base URL（仅在使用过 getApiBase() 初始化后可用）。
 * 用于 SSE 等需要同步 URL 的场景。
 */
export function getApiBaseSync(): string {
  return _apiBaseCache || configuredApiBase();
}

/**
 * 初始化 API base（在 App.vue onMounted 中调用）。
 * 确保 Tauri 模式下提前缓存端口。
 */
export async function initApiBase(): Promise<void> {
  await getApiBase();
}

async function request<T>(
  method: string,
  path: string,
  body?: any,
): Promise<T> {
  const base = await getApiBase();
  const url = `${base}${path}`;
  const options: RequestInit = {
    method,
    headers: { "Content-Type": "application/json" },
  };
  if (body !== undefined) {
    options.body = JSON.stringify(body);
  }
  const resp = await fetch(url, options);
  if (!resp.ok) {
    const detail = await resp.text();
    throw new Error(`HTTP ${resp.status}: ${detail}`);
  }
  const contentType = resp.headers.get("content-type") || "";
  if (contentType.includes("application/json")) {
    return resp.json() as Promise<T>;
  }
  return resp.text() as unknown as Promise<T>;
}

export const api = {
  get: <T>(path: string) => request<T>("GET", path),
  post: <T>(path: string, body?: any) => request<T>("POST", path, body),
  patch: <T>(path: string, body?: any) => request<T>("PATCH", path, body),
  delete: <T>(path: string, body?: any) => request<T>("DELETE", path, body),
};

/**
 * SSE 订阅：连接到后端 SSE 端点，通过回调推送事件。
 * 返回一个关闭函数。
 */
export function subscribeSSE(
  path: string,
  onEvent: (data: any) => void,
  onError?: (err: Event) => void,
): () => void {
  const url = `${getApiBaseSync()}${path}`;
  const source = new EventSource(url);

  source.onmessage = (ev: MessageEvent) => {
    try {
      const data = JSON.parse(ev.data);
      onEvent(data);
      if (data.type === "done") {
        source.close();
      }
    } catch (e) {
      onEvent({ type: "error", message: "Failed to parse SSE data" });
    }
  };

  source.onerror = (err: Event) => {
    if (onError) onError(err);
    source.close();
  };

  return () => source.close();
}

/**
 * 文件下载（导出用）。
 */
export async function downloadFile(
  path: string,
  filename: string,
): Promise<void> {
  const base = await getApiBase();
  const url = `${base}${path}`;
  const resp = await fetch(url);
  if (!resp.ok) throw new Error(`Download failed: ${resp.status}`);
  const blob = await resp.blob();
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = filename;
  link.click();
  URL.revokeObjectURL(link.href);
}
