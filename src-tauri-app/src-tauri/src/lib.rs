use std::io::Write;
use std::process::Command as StdCommand;
use std::process::Stdio;
use tauri::Manager;

/// Decode a PoB export code via the Python engine.
///
/// Passes the code via stdin to avoid Windows command-line length limits.
#[tauri::command]
async fn decode_build(code: String) -> Result<serde_json::Value, String> {
    let mut child = StdCommand::new("C:\\Users\\Administrator\\AppData\\Local\\Programs\\Python\\Python311\\python.exe")
        .args(["-m", "pop.main", "decode", "--stdin", "-v"])
        .current_dir("C:\\DEV\\Path of Purpose\\path-of-purpose\\src-python")
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .map_err(|e| format!("Failed to run Python engine: {}", e))?;

    // Write the code to stdin, then drop to close the pipe (signals EOF)
    {
        let mut stdin = child.stdin.take()
            .ok_or("Failed to open stdin pipe")?;
        stdin.write_all(code.as_bytes())
            .map_err(|e| format!("Failed to write to stdin: {}", e))?;
        stdin.flush()
            .map_err(|e| format!("Failed to flush stdin: {}", e))?;
        // stdin drops here, closing the pipe
    }

    let output = child.wait_with_output()
        .map_err(|e| format!("Failed to wait for Python engine: {}", e))?;

    if output.status.success() {
        let stdout = String::from_utf8_lossy(&output.stdout);
        // The decode command outputs a summary line first, then JSON
        if let Some(json_start) = stdout.find('{') {
            serde_json::from_str::<serde_json::Value>(&stdout[json_start..])
                .map_err(|e| format!("Failed to parse build JSON: {}", e))
        } else {
            Ok(serde_json::json!({ "summary": stdout.trim() }))
        }
    } else {
        let stderr = String::from_utf8_lossy(&output.stderr).trim().to_string();
        let msg = if stderr.is_empty() {
            "Python engine exited with an unknown error.".to_string()
        } else {
            stderr
        };
        Err(msg)
    }
}

/// Placeholder for future delta analysis command.
/// Will compare a PoB code against a live character once OAuth is approved.
#[tauri::command]
async fn analyze_delta(
    _pob_code: String,
    character_name: String,
) -> Result<serde_json::Value, String> {
    // For now, return a mock response showing the structure
    Ok(serde_json::json!({
        "status": "oauth_pending",
        "message": format!(
            "Delta analysis for '{}' is ready — waiting for PoE API OAuth approval.",
            character_name
        ),
        "guide_decoded": true
    }))
}

/// Scrape a mobalytics.gg build guide via the Python engine.
///
/// Passes the URL via stdin to avoid command-line escaping issues.
#[tauri::command]
async fn scrape_build_guide(url: String) -> Result<serde_json::Value, String> {
    let mut child = StdCommand::new("C:\\Users\\Administrator\\AppData\\Local\\Programs\\Python\\Python311\\python.exe")
        .args(["-m", "pop.main", "scrape_guide", "--stdin"])
        .current_dir("C:\\DEV\\Path of Purpose\\path-of-purpose\\src-python")
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .map_err(|e| format!("Failed to run Python engine: {}", e))?;

    {
        let mut stdin = child.stdin.take()
            .ok_or("Failed to open stdin pipe")?;
        stdin.write_all(url.as_bytes())
            .map_err(|e| format!("Failed to write to stdin: {}", e))?;
        stdin.flush()
            .map_err(|e| format!("Failed to flush stdin: {}", e))?;
    }

    let output = child.wait_with_output()
        .map_err(|e| format!("Failed to wait for Python engine: {}", e))?;

    if output.status.success() {
        let stdout = String::from_utf8_lossy(&output.stdout);
        serde_json::from_str::<serde_json::Value>(&stdout)
            .map_err(|e| format!("Failed to parse guide JSON: {}", e))
    } else {
        let stderr = String::from_utf8_lossy(&output.stderr).trim().to_string();
        let msg = if stderr.is_empty() {
            "Python engine exited with an unknown error.".to_string()
        } else {
            stderr
        };
        Err(msg)
    }
}

/// Open the passive skill tree in a dedicated app window.
#[tauri::command]
async fn open_passive_tree(app: tauri::AppHandle, url: String) -> Result<(), String> {
    use tauri::WebviewWindowBuilder;

    // If tree window already exists, focus it instead of creating a new one
    if let Some(window) = app.get_webview_window("passive-tree") {
        window.set_focus().map_err(|e| format!("Failed to focus tree window: {}", e))?;
        return Ok(());
    }

    let parsed_url: tauri::Url = url.parse().map_err(|e| format!("Invalid URL: {}", e))?;

    WebviewWindowBuilder::new(&app, "passive-tree", tauri::WebviewUrl::External(parsed_url))
        .title("Passive Skill Tree — Path of Purpose")
        .inner_size(1100.0, 750.0)
        .center()
        .build()
        .map_err(|e| format!("Failed to open tree viewer: {}", e))?;

    Ok(())
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_opener::init())
        .plugin(tauri_plugin_shell::init())
        .invoke_handler(tauri::generate_handler![decode_build, analyze_delta, scrape_build_guide, open_passive_tree])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
