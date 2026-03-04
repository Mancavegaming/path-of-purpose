use std::io::Write;
use std::process::Command as StdCommand;
use std::process::Stdio;

/// Decode a PoB export code via the Python engine.
///
/// Passes the code via stdin to avoid Windows command-line length limits.
#[tauri::command]
async fn decode_build(code: String) -> Result<serde_json::Value, String> {
    let mut child = StdCommand::new("C:\\Users\\ideal\\AppData\\Local\\Programs\\Python\\Python314\\python.exe")
        .args(["-m", "pop.main", "decode", "--stdin", "-v"])
        .current_dir("D:\\Dev\\Path of Purpose\\src-python")
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .map_err(|e| format!("Failed to run Python engine: {}", e))?;

    // Write the code to stdin
    if let Some(mut stdin) = child.stdin.take() {
        stdin.write_all(code.as_bytes())
            .map_err(|e| format!("Failed to write to stdin: {}", e))?;
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
        let stderr = String::from_utf8_lossy(&output.stderr);
        Err(format!("Decode error: {}", stderr))
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

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_opener::init())
        .plugin(tauri_plugin_shell::init())
        .invoke_handler(tauri::generate_handler![decode_build, analyze_delta])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
