//! 应用主库：Tauri 桌面壳逻辑

mod config;
mod sidecar;

use std::sync::Mutex;
use tauri::Manager;

pub struct AppState {
    pub sidecar_port: u16,
    pub sidecar_child: Mutex<Option<std::process::Child>>,
}

/// Tauri 命令：返回 sidecar 端口，供前端 fetch 使用
#[tauri::command]
pub fn get_sidecar_port(state: tauri::State<AppState>) -> u16 {
    state.sidecar_port
}

/// Tauri 命令：获取应用配置
#[tauri::command]
pub fn get_app_config() -> Result<config::AppConfig, String> {
    config::load_config().map_err(|e| e.to_string())
}

/// Tauri 命令：保存应用配置
#[tauri::command]
pub fn save_app_config(config: config::AppConfig) -> Result<(), String> {
    config::save_config(&config).map_err(|e| e.to_string())
}

/// Tauri 命令：打开目录选择对话框
#[tauri::command]
pub fn pick_directory(app: tauri::AppHandle) -> Option<String> {
    use tauri_plugin_dialog::DialogExt;
    app.dialog()
        .file()
        .set_title("选择目录")
        .blocking_pick_folder()
        .map(|p| p.to_string())
}

pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_dialog::init())
        .plugin(tauri_plugin_fs::init())
        .setup(|app| {
            // 1. 读取 / 创建用户数据目录
            let data_dir = config::ensure_data_dir().expect("无法创建数据目录");

            // 2. 写入环境变量（供 sidecar 读取）
            let db_path = data_dir.join("app.db");
            let db_url = format!("sqlite:///{}", db_path.display());
            std::env::set_var("AI_NOVEL_DATABASE_URL", &db_url);
            std::env::set_var("AI_NOVEL_DATA_DIR", &data_dir);

            // 3. 分配动态端口
            let port = portpicker::pick_unused_port().expect("无可用端口");
            log::info!("sidecar port = {port}, data_dir = {}", data_dir.display());

            // 4. 启动 sidecar
            let child = sidecar::start(app.handle(), port, &data_dir)
                .map_err(|e| {
                    log::error!("启动 sidecar 失败: {e}");
                    Box::<dyn std::error::Error>::from(e)
                })?;

            app.manage(AppState {
                sidecar_port: port,
                sidecar_child: Mutex::new(Some(child)),
            });

            Ok(())
        })
        .on_window_event(|window, event| {
            if let tauri::WindowEvent::CloseRequested { .. } = event {
                if let Some(state) = window.app_handle().try_state::<AppState>() {
                    sidecar::shutdown(&state.sidecar_child);
                }
            }
        })
        .invoke_handler(tauri::generate_handler![
            get_sidecar_port,
            get_app_config,
            save_app_config,
            pick_directory,
        ])
        .run(tauri::generate_context!())
        .expect("运行 Tauri 应用时出错");
}
