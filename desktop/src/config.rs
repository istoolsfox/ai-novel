//! 应用配置读写 + 用户数据目录管理

use serde::{Deserialize, Serialize};
use std::fs;
use std::path::PathBuf;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AppConfig {
    pub data_dir: String,
    pub export_dir: String,
    pub version: String,
    pub first_run: bool,
}

impl Default for AppConfig {
    fn default() -> Self {
        let data_dir = default_data_dir();
        Self {
            export_dir: data_dir.join("exports").to_string_lossy().to_string(),
            data_dir: data_dir.to_string_lossy().to_string(),
            version: env!("CARGO_PKG_VERSION").to_string(),
            first_run: true,
        }
    }
}

/// 返回应用在用户本机的数据目录
pub fn default_data_dir() -> PathBuf {
    let base = dirs::data_dir().unwrap_or_else(|| PathBuf::from("."));
    base.join("ai-novel-workbench")
}

/// 确保数据目录存在，返回其路径
pub fn ensure_data_dir() -> Result<PathBuf, Box<dyn std::error::Error>> {
    let dir = default_data_dir();
    fs::create_dir_all(&dir)?;
    fs::create_dir_all(dir.join("exports"))?;
    fs::create_dir_all(dir.join("projects"))?;
    Ok(dir)
}

/// 配置文件路径
fn config_file_path() -> PathBuf {
    let dir = default_data_dir();
    dir.join("config.json")
}

/// 读取配置；不存在时返回默认值
pub fn load_config() -> Result<AppConfig, Box<dyn std::error::Error>> {
    let path = config_file_path();
    if !path.exists() {
        let cfg = AppConfig::default();
        save_config(&cfg)?;
        return Ok(cfg);
    }
    let content = fs::read_to_string(&path)?;
    let cfg: AppConfig = serde_json::from_str(&content)?;
    Ok(cfg)
}

/// 保存配置
pub fn save_config(cfg: &AppConfig) -> Result<(), Box<dyn std::error::Error>> {
    let path = config_file_path();
    if let Some(parent) = path.parent() {
        fs::create_dir_all(parent)?;
    }
    let content = serde_json::to_string_pretty(cfg)?;
    fs::write(&path, content)?;
    Ok(())
}
