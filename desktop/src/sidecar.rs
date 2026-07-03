//! FastAPI sidecar 进程管理：启动 / 健康检查 / 关闭

use std::path::Path;
use std::process::{Child, Command};
use std::sync::Mutex;
use std::time::{Duration, Instant};
use tauri::AppHandle;

/// 启动 sidecar 进程并做健康检查
pub fn start(app: &AppHandle, port: u16, data_dir: &Path) -> Result<Child, String> {
    let sidecar_path = resolve_sidecar_path(app)?;

    if !sidecar_path.exists() {
        return Err(format!(
            "sidecar 二进制不存在: {}。请先运行 python scripts/build_sidecar.py",
            sidecar_path.display()
        ));
    }

    let db_path = data_dir.join("app.db");
    let db_url = format!("sqlite:///{}", db_path.display());

    let mut cmd = Command::new(&sidecar_path);
    cmd.env("AI_NOVEL_PORT", port.to_string())
        .env("AI_NOVEL_HOST", "127.0.0.1")
        .env("AI_NOVEL_DATABASE_URL", &db_url)
        .env("AI_NOVEL_DATA_DIR", data_dir)
        .env("AI_NOVEL_LOG_LEVEL", "warning")
        .stdout(std::process::Stdio::null())
        .stderr(std::process::Stdio::null());

    #[cfg(windows)]
    {
        // CREATE_NO_WINDOW 隐藏控制台
        const CREATE_NO_WINDOW: u32 = 0x08000000;
        use std::os::windows::process::CommandExt;
        cmd.creation_flags(CREATE_NO_WINDOW);
    }

    let child = cmd
        .spawn()
        .map_err(|e| format!("启动 sidecar 失败: {e}"))?;

    // 健康检查：轮询 /api/health，最多等 30 秒
    let health_url = format!("http://127.0.0.1:{port}/api/health");
    let start = Instant::now();
    let client = reqwest::blocking::Client::builder()
        .timeout(Duration::from_secs(2))
        .build()
        .map_err(|e| e.to_string())?;

    loop {
        if start.elapsed() > Duration::from_secs(30) {
            return Err("sidecar 启动超时（30s 内未响应 /api/health）".to_string());
        }
        if client.get(&health_url).send().map(|r| r.status().is_success()).unwrap_or(false) {
            break;
        }
        std::thread::sleep(Duration::from_millis(200));
    }

    log::info!("sidecar 已就绪 @ 127.0.0.1:{port}");
    Ok(child)
}

/// 关闭 sidecar
pub fn shutdown(child_lock: &Mutex<Option<Child>>) {
    if let Some(mut child) = child_lock.lock().unwrap().take() {
        let _ = child.kill();
        let _ = child.wait();
        log::info!("sidecar 已关闭");
    }
}

fn resolve_sidecar_path(app: &AppHandle) -> Result<std::path::PathBuf, String> {
    use tauri::Manager;

    // 开发模式：desktop/binaries/ai-novel-backend[.exe]
    let dev_path = std::env::current_exe()
        .map_err(|e| e.to_string())?
        .parent()
        .ok_or("无法获取 exe 目录")?
        .join("binaries")
        .join(sidecar_binary_name());

    if dev_path.exists() {
        return Ok(dev_path);
    }

    // 打包模式：从 Tauri 资源目录解析
    if let Ok(resource_path) = app.path().resolve(
        format!("binaries/{}", sidecar_binary_name()),
        tauri::path::BaseDirectory::Resource,
    ) {
        return Ok(resource_path);
    }

    Ok(dev_path)
}

fn sidecar_binary_name() -> String {
    if cfg!(windows) {
        "ai-novel-backend.exe".to_string()
    } else {
        "ai-novel-backend".to_string()
    }
}
