use std::fs;
use std::io::Write;
use std::path::PathBuf;
use std::process::Command as StdCommand;
use std::process::Stdio;
use tauri::Manager;

// Backend API base URL — configurable for dev vs production
const API_BASE: &str = "http://45.61.55.200:8080";

const PYTHON_EXE: &str = "C:\\Users\\ideal\\AppData\\Local\\Programs\\Python\\Python314\\python.exe";
const PYTHON_CWD: &str = "D:\\Dev\\Path of Purpose\\src-python";

/// Run a Python subcommand, optionally piping stdin_data. Returns (stdout, stderr).
fn run_python_command(
    args: &[&str],
    stdin_data: Option<&str>,
) -> Result<String, String> {
    let mut child = StdCommand::new(PYTHON_EXE)
        .args(args)
        .current_dir(PYTHON_CWD)
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .map_err(|e| format!("Failed to run Python engine: {}", e))?;

    if let Some(data) = stdin_data {
        let mut stdin = child.stdin.take()
            .ok_or("Failed to open stdin pipe")?;
        stdin.write_all(data.as_bytes())
            .map_err(|e| format!("Failed to write to stdin: {}", e))?;
        stdin.flush()
            .map_err(|e| format!("Failed to flush stdin: {}", e))?;
        // stdin drops here, closing the pipe
    }

    let output = child.wait_with_output()
        .map_err(|e| format!("Failed to wait for Python engine: {}", e))?;

    if output.status.success() {
        Ok(String::from_utf8_lossy(&output.stdout).to_string())
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

/// Decode a PoB export code via the Python engine.
///
/// Passes the code via stdin to avoid Windows command-line length limits.
#[tauri::command]
async fn decode_build(code: String) -> Result<serde_json::Value, String> {
    let stdout = run_python_command(
        &["-m", "pop.main", "decode", "--stdin", "-v"],
        Some(&code),
    )?;

    // The decode command outputs a summary line first, then JSON
    if let Some(json_start) = stdout.find('{') {
        serde_json::from_str::<serde_json::Value>(&stdout[json_start..])
            .map_err(|e| format!("Failed to parse build JSON: {}", e))
    } else {
        Ok(serde_json::json!({ "summary": stdout.trim() }))
    }
}

/// Placeholder for future delta analysis command.
/// Will compare a PoB code against a live character once OAuth is approved.
#[tauri::command]
async fn analyze_delta(
    _pob_code: String,
    character_name: String,
) -> Result<serde_json::Value, String> {
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
#[tauri::command]
async fn scrape_build_guide(url: String) -> Result<serde_json::Value, String> {
    let stdout = run_python_command(
        &["-m", "pop.main", "scrape_guide", "--stdin"],
        Some(&url),
    )?;

    serde_json::from_str::<serde_json::Value>(&stdout)
        .map_err(|e| format!("Failed to parse guide JSON: {}", e))
}

/// Open the passive skill tree in a dedicated app window.
#[tauri::command]
async fn open_passive_tree(app: tauri::AppHandle, url: String) -> Result<(), String> {
    use tauri::WebviewWindowBuilder;

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

/// Search PoE trade for items similar to a build item.
#[tauri::command]
async fn trade_search(item: serde_json::Value, league: String) -> Result<serde_json::Value, String> {
    let input = serde_json::json!({ "item": item, "league": league });
    let stdin_data = serde_json::to_string(&input)
        .map_err(|e| format!("Failed to serialize input: {}", e))?;

    let stdout = run_python_command(
        &["-m", "pop.main", "trade_search", "--stdin"],
        Some(&stdin_data),
    )?;

    serde_json::from_str::<serde_json::Value>(&stdout)
        .map_err(|e| format!("Failed to parse trade results: {}", e))
}

/// Send a message to the AI advisor (stateless — history provided by frontend).
#[tauri::command]
async fn ai_chat(
    message: String,
    history: serde_json::Value,
    build_context: serde_json::Value,
    api_key: String,
    provider: String,
) -> Result<serde_json::Value, String> {
    let input = serde_json::json!({
        "message": message,
        "history": history,
        "build_context": build_context,
        "api_key": api_key,
        "provider": provider,
    });
    let stdin_data = serde_json::to_string(&input)
        .map_err(|e| format!("Failed to serialize input: {}", e))?;

    let stdout = run_python_command(
        &["-m", "pop.main", "ai_chat", "--stdin"],
        Some(&stdin_data),
    )?;

    serde_json::from_str::<serde_json::Value>(&stdout)
        .map_err(|e| format!("Failed to parse AI response: {}", e))
}

/// Compare an equipped item against a trade listing.
#[tauri::command]
async fn compare_items(
    equipped_item: serde_json::Value,
    trade_listing: serde_json::Value,
    slot: String,
    weapon_aps: f64,
) -> Result<serde_json::Value, String> {
    let input = serde_json::json!({
        "equipped_item": equipped_item,
        "trade_listing": trade_listing,
        "slot": slot,
        "weapon_aps": weapon_aps,
    });
    let stdin_data = serde_json::to_string(&input)
        .map_err(|e| format!("Failed to serialize input: {}", e))?;

    let stdout = run_python_command(
        &["-m", "pop.main", "compare_items", "--stdin"],
        Some(&stdin_data),
    )?;

    serde_json::from_str::<serde_json::Value>(&stdout)
        .map_err(|e| format!("Failed to parse comparison result: {}", e))
}

/// Store an AI provider API key.
#[tauri::command]
async fn ai_set_key(key: String, provider: String) -> Result<serde_json::Value, String> {
    let input = serde_json::json!({ "api_key": key, "provider": provider });
    let stdin_data = serde_json::to_string(&input)
        .map_err(|e| format!("Failed to serialize input: {}", e))?;

    let stdout = run_python_command(
        &["-m", "pop.main", "ai_set_key", "--stdin"],
        Some(&stdin_data),
    )?;

    serde_json::from_str::<serde_json::Value>(&stdout)
        .map_err(|e| format!("Failed to parse response: {}", e))
}

/// Drive the build generator intake conversation.
#[tauri::command]
async fn generator_chat(
    message: String,
    history: serde_json::Value,
    api_key: String,
    provider: String,
) -> Result<serde_json::Value, String> {
    let input = serde_json::json!({
        "message": message,
        "history": history,
        "api_key": api_key,
        "provider": provider,
    });
    let stdin_data = serde_json::to_string(&input)
        .map_err(|e| format!("Failed to serialize input: {}", e))?;

    let stdout = run_python_command(
        &["-m", "pop.main", "generator_chat", "--stdin"],
        Some(&stdin_data),
    )?;

    serde_json::from_str::<serde_json::Value>(&stdout)
        .map_err(|e| format!("Failed to parse generator chat response: {}", e))
}

/// Generate a full build guide from preferences.
#[tauri::command]
async fn generate_build(
    api_key: String,
    preferences: serde_json::Value,
    history: serde_json::Value,
    provider: String,
) -> Result<serde_json::Value, String> {
    let input = serde_json::json!({
        "api_key": api_key,
        "preferences": preferences,
        "history": history,
        "provider": provider,
    });
    let stdin_data = serde_json::to_string(&input)
        .map_err(|e| format!("Failed to serialize input: {}", e))?;

    let stdout = run_python_command(
        &["-m", "pop.main", "generate_build", "--stdin"],
        Some(&stdin_data),
    )?;

    serde_json::from_str::<serde_json::Value>(&stdout)
        .map_err(|e| format!("Failed to parse generated build: {}", e))
}

/// Refine a build guide with trade prices and budget.
#[tauri::command]
async fn refine_build(
    api_key: String,
    guide: serde_json::Value,
    trade_prices: serde_json::Value,
    budget_chaos: u32,
    history: serde_json::Value,
    message: String,
    provider: String,
) -> Result<serde_json::Value, String> {
    let input = serde_json::json!({
        "api_key": api_key,
        "guide": guide,
        "trade_prices": trade_prices,
        "budget_chaos": budget_chaos,
        "history": history,
        "message": message,
        "provider": provider,
    });
    let stdin_data = serde_json::to_string(&input)
        .map_err(|e| format!("Failed to serialize input: {}", e))?;

    let stdout = run_python_command(
        &["-m", "pop.main", "refine_build", "--stdin"],
        Some(&stdin_data),
    )?;

    serde_json::from_str::<serde_json::Value>(&stdout)
        .map_err(|e| format!("Failed to parse refined build: {}", e))
}

/// Refresh the PoE knowledge cache (gems, uniques, patch notes).
#[tauri::command]
async fn refresh_knowledge() -> Result<serde_json::Value, String> {
    let stdout = run_python_command(
        &["-m", "pop.main", "refresh_knowledge"],
        None,
    )?;

    serde_json::from_str::<serde_json::Value>(&stdout)
        .map_err(|e| format!("Failed to parse knowledge refresh result: {}", e))
}

/// Check knowledge cache; auto-refresh if stale (>24h) or missing.
#[tauri::command]
async fn check_knowledge() -> Result<serde_json::Value, String> {
    let stdout = run_python_command(
        &["-m", "pop.main", "check_knowledge"],
        None,
    )?;

    serde_json::from_str::<serde_json::Value>(&stdout)
        .map_err(|e| format!("Failed to parse knowledge check result: {}", e))
}

/// Check if an AI provider API key is stored.
#[tauri::command]
async fn ai_check_key(provider: String) -> Result<serde_json::Value, String> {
    let input = serde_json::json!({ "provider": provider });
    let stdin_data = serde_json::to_string(&input)
        .map_err(|e| format!("Failed to serialize input: {}", e))?;

    let stdout = run_python_command(
        &["-m", "pop.main", "ai_check_key"],
        Some(&stdin_data),
    )?;

    serde_json::from_str::<serde_json::Value>(&stdout)
        .map_err(|e| format!("Failed to parse response: {}", e))
}

/// Get the builds directory inside app data, creating it if needed.
fn builds_dir(app: &tauri::AppHandle) -> Result<PathBuf, String> {
    let base = app.path().app_data_dir()
        .map_err(|e| format!("Failed to get app data dir: {}", e))?;
    let dir = base.join("builds");
    if !dir.exists() {
        fs::create_dir_all(&dir)
            .map_err(|e| format!("Failed to create builds directory: {}", e))?;
    }
    Ok(dir)
}

/// Sanitize a build name into a safe filename.
fn sanitize_name(name: &str) -> String {
    let sanitized: String = name.chars()
        .map(|c| if c.is_alphanumeric() || c == '-' || c == '_' || c == ' ' { c } else { '_' })
        .collect();
    let trimmed = sanitized.trim();
    if trimmed.len() > 100 { trimmed[..100].to_string() } else { trimmed.to_string() }
}

/// Save a build to disk. `kind` is "guide" (BuildGuide) or "build" (Build).
#[tauri::command]
async fn save_build(
    app: tauri::AppHandle,
    name: String,
    data: serde_json::Value,
    kind: String,
) -> Result<(), String> {
    let dir = builds_dir(&app)?;
    let filename = format!("{}.json", sanitize_name(&name));
    let path = dir.join(&filename);

    let now = chrono::Utc::now().to_rfc3339();
    let wrapper = serde_json::json!({
        "name": name,
        "saved_at": now,
        "kind": kind,
        "data": data,
    });

    let data = serde_json::to_string_pretty(&wrapper)
        .map_err(|e| format!("Failed to serialize build: {}", e))?;
    fs::write(&path, data)
        .map_err(|e| format!("Failed to write build file: {}", e))?;

    Ok(())
}

/// List all saved builds (name + saved_at).
#[tauri::command]
async fn list_saved_builds(app: tauri::AppHandle) -> Result<serde_json::Value, String> {
    let dir = builds_dir(&app)?;
    let mut entries: Vec<serde_json::Value> = Vec::new();

    if let Ok(read_dir) = fs::read_dir(&dir) {
        for entry in read_dir.flatten() {
            let path = entry.path();
            if path.extension().and_then(|e| e.to_str()) == Some("json") {
                if let Ok(data) = fs::read_to_string(&path) {
                    if let Ok(parsed) = serde_json::from_str::<serde_json::Value>(&data) {
                        entries.push(serde_json::json!({
                            "name": parsed.get("name").and_then(|v| v.as_str()).unwrap_or(""),
                            "saved_at": parsed.get("saved_at").and_then(|v| v.as_str()).unwrap_or(""),
                            "kind": parsed.get("kind").and_then(|v| v.as_str()).unwrap_or("guide"),
                        }));
                    }
                }
            }
        }
    }

    // Sort by saved_at descending (newest first)
    entries.sort_by(|a, b| {
        let sa = a.get("saved_at").and_then(|v| v.as_str()).unwrap_or("");
        let sb = b.get("saved_at").and_then(|v| v.as_str()).unwrap_or("");
        sb.cmp(sa)
    });

    Ok(serde_json::json!(entries))
}

/// Load a saved build by name. Returns {kind, data}.
#[tauri::command]
async fn load_saved_build(app: tauri::AppHandle, name: String) -> Result<serde_json::Value, String> {
    let dir = builds_dir(&app)?;
    let filename = format!("{}.json", sanitize_name(&name));
    let path = dir.join(&filename);

    let raw = fs::read_to_string(&path)
        .map_err(|e| format!("Build '{}' not found: {}", name, e))?;
    let parsed: serde_json::Value = serde_json::from_str(&raw)
        .map_err(|e| format!("Failed to parse build file: {}", e))?;

    let kind = parsed.get("kind").and_then(|v| v.as_str()).unwrap_or("guide");
    // Support both old format ("guide" field) and new format ("data" field)
    let data = parsed.get("data")
        .or_else(|| parsed.get("guide"))
        .cloned()
        .ok_or_else(|| "Build file is missing 'data' field".to_string())?;

    Ok(serde_json::json!({ "kind": kind, "data": data }))
}

/// Delete a saved build by name.
#[tauri::command]
async fn delete_saved_build(app: tauri::AppHandle, name: String) -> Result<(), String> {
    let dir = builds_dir(&app)?;
    let filename = format!("{}.json", sanitize_name(&name));
    let path = dir.join(&filename);

    fs::remove_file(&path)
        .map_err(|e| format!("Failed to delete build '{}': {}", name, e))?;

    Ok(())
}

// ---------------------------------------------------------------------------
// Remote API commands (server-side AI via Discord auth + Stripe subscription)
// ---------------------------------------------------------------------------

/// Get the JWT token file path inside app data.
fn jwt_path(app: &tauri::AppHandle) -> Result<PathBuf, String> {
    let base = app.path().app_data_dir()
        .map_err(|e| format!("Failed to get app data dir: {}", e))?;
    if !base.exists() {
        fs::create_dir_all(&base)
            .map_err(|e| format!("Failed to create app data dir: {}", e))?;
    }
    Ok(base.join("auth_token.json"))
}

/// Load the stored JWT token (if any).
#[tauri::command]
async fn load_token(app: tauri::AppHandle) -> Result<serde_json::Value, String> {
    let path = jwt_path(&app)?;
    if !path.exists() {
        return Ok(serde_json::json!({ "token": null, "user": null }));
    }
    let raw = fs::read_to_string(&path)
        .map_err(|e| format!("Failed to read token: {}", e))?;
    serde_json::from_str::<serde_json::Value>(&raw)
        .map_err(|e| format!("Failed to parse token: {}", e))
}

/// Store JWT token + user info after Discord login.
#[tauri::command]
async fn store_token(
    app: tauri::AppHandle,
    token: String,
    user: serde_json::Value,
) -> Result<(), String> {
    let path = jwt_path(&app)?;
    let data = serde_json::json!({ "token": token, "user": user });
    let raw = serde_json::to_string_pretty(&data)
        .map_err(|e| format!("Failed to serialize token: {}", e))?;
    fs::write(&path, raw)
        .map_err(|e| format!("Failed to write token: {}", e))?;
    Ok(())
}

/// Clear stored JWT (logout).
#[tauri::command]
async fn logout(app: tauri::AppHandle) -> Result<(), String> {
    let path = jwt_path(&app)?;
    if path.exists() {
        fs::remove_file(&path)
            .map_err(|e| format!("Failed to remove token: {}", e))?;
    }
    Ok(())
}

/// Start Discord OAuth: open the browser to Discord authorize URL.
/// Returns the Discord authorize URL for the frontend to open.
#[tauri::command]
async fn get_discord_auth_url(client_id: String) -> Result<String, String> {
    let redirect_uri = "http://localhost:8458/callback";
    let url = format!(
        "https://discord.com/api/oauth2/authorize?client_id={}&redirect_uri={}&response_type=code&scope=identify%20guilds",
        client_id,
        urlencoding::encode(redirect_uri)
    );
    Ok(url)
}

/// Listen for the OAuth callback on localhost:8458, extract the code.
#[tauri::command]
async fn listen_for_oauth_callback() -> Result<String, String> {
    use tokio::io::{AsyncReadExt, AsyncWriteExt};
    use tokio::net::TcpListener;

    let listener = TcpListener::bind("127.0.0.1:8458").await
        .map_err(|e| format!("Failed to bind callback listener: {}", e))?;

    let (mut stream, _) = listener.accept().await
        .map_err(|e| format!("Failed to accept connection: {}", e))?;

    let mut buf = vec![0u8; 4096];
    let n = stream.read(&mut buf).await
        .map_err(|e| format!("Failed to read request: {}", e))?;

    let request = String::from_utf8_lossy(&buf[..n]).to_string();

    // Extract the code parameter from GET /callback?code=XXX
    let code = request
        .lines()
        .next()
        .and_then(|line| {
            let path = line.split_whitespace().nth(1)?;
            let query = path.split('?').nth(1)?;
            query.split('&').find_map(|param| {
                let mut kv = param.splitn(2, '=');
                let key = kv.next()?;
                let val = kv.next()?;
                if key == "code" { Some(val.to_string()) } else { None }
            })
        })
        .ok_or_else(|| "No authorization code in callback".to_string())?;

    // Send a success response to the browser
    let response = "HTTP/1.1 200 OK\r\nContent-Type: text/html\r\n\r\n\
        <html><body><h2>Login successful!</h2><p>You can close this tab and return to Path of Purpose.</p></body></html>";
    let _ = stream.write_all(response.as_bytes()).await;

    Ok(code)
}

/// Exchange Discord code for JWT via backend server.
#[tauri::command]
async fn exchange_discord_code(code: String) -> Result<serde_json::Value, String> {
    let client = reqwest::Client::new();
    let resp = client
        .post(format!("{}/api/auth/discord/token", API_BASE))
        .json(&serde_json::json!({
            "code": code,
            "redirect_uri": "http://localhost:8458/callback"
        }))
        .send()
        .await
        .map_err(|e| format!("Failed to contact server: {}", e))?;

    if !resp.status().is_success() {
        let status = resp.status();
        let body = resp.text().await.unwrap_or_default();
        return Err(format!("Server error ({}): {}", status, body));
    }

    resp.json::<serde_json::Value>()
        .await
        .map_err(|e| format!("Failed to parse server response: {}", e))
}

/// Get current user status from backend (refreshes subscription info).
#[tauri::command]
async fn get_user_status(token: String) -> Result<serde_json::Value, String> {
    let client = reqwest::Client::new();
    let resp = client
        .get(format!("{}/api/auth/me", API_BASE))
        .header("Authorization", format!("Bearer {}", token))
        .send()
        .await
        .map_err(|e| format!("Failed to contact server: {}", e))?;

    if !resp.status().is_success() {
        let status = resp.status();
        let body = resp.text().await.unwrap_or_default();
        return Err(format!("Server error ({}): {}", status, body));
    }

    resp.json::<serde_json::Value>()
        .await
        .map_err(|e| format!("Failed to parse response: {}", e))
}

/// Create a Stripe checkout session and return the URL.
#[tauri::command]
async fn open_checkout(token: String) -> Result<String, String> {
    let client = reqwest::Client::new();
    let resp = client
        .post(format!("{}/api/billing/checkout", API_BASE))
        .header("Authorization", format!("Bearer {}", token))
        .send()
        .await
        .map_err(|e| format!("Failed to contact server: {}", e))?;

    if !resp.status().is_success() {
        let status = resp.status();
        let body = resp.text().await.unwrap_or_default();
        return Err(format!("Server error ({}): {}", status, body));
    }

    let data: serde_json::Value = resp.json()
        .await
        .map_err(|e| format!("Failed to parse response: {}", e))?;

    data.get("checkout_url")
        .and_then(|v| v.as_str())
        .map(|s| s.to_string())
        .ok_or_else(|| "No checkout URL in response".to_string())
}

/// Remote AI chat (proxied through backend server).
#[tauri::command]
async fn ai_chat_remote(
    token: String,
    message: String,
    history: serde_json::Value,
    build_context: serde_json::Value,
) -> Result<serde_json::Value, String> {
    let client = reqwest::Client::new();
    let resp = client
        .post(format!("{}/api/ai/chat", API_BASE))
        .header("Authorization", format!("Bearer {}", token))
        .json(&serde_json::json!({
            "message": message,
            "history": history,
            "build_context": build_context,
        }))
        .send()
        .await
        .map_err(|e| format!("Failed to contact server: {}", e))?;

    if !resp.status().is_success() {
        let status = resp.status();
        let body = resp.text().await.unwrap_or_default();
        return Err(format!("AI request failed ({}): {}", status, body));
    }

    resp.json::<serde_json::Value>()
        .await
        .map_err(|e| format!("Failed to parse AI response: {}", e))
}

/// Remote generator chat (proxied through backend server).
#[tauri::command]
async fn generator_chat_remote(
    token: String,
    message: String,
    history: serde_json::Value,
) -> Result<serde_json::Value, String> {
    let client = reqwest::Client::new();
    let resp = client
        .post(format!("{}/api/ai/generator-chat", API_BASE))
        .header("Authorization", format!("Bearer {}", token))
        .json(&serde_json::json!({
            "message": message,
            "history": history,
        }))
        .send()
        .await
        .map_err(|e| format!("Failed to contact server: {}", e))?;

    if !resp.status().is_success() {
        let status = resp.status();
        let body = resp.text().await.unwrap_or_default();
        return Err(format!("Generator chat failed ({}): {}", status, body));
    }

    resp.json::<serde_json::Value>()
        .await
        .map_err(|e| format!("Failed to parse response: {}", e))
}

/// Remote build generation (proxied through backend server).
#[tauri::command]
async fn generate_build_remote(
    token: String,
    preferences: serde_json::Value,
    history: serde_json::Value,
) -> Result<serde_json::Value, String> {
    let client = reqwest::Client::new();
    let resp = client
        .post(format!("{}/api/ai/generate-build", API_BASE))
        .header("Authorization", format!("Bearer {}", token))
        .json(&serde_json::json!({
            "preferences": preferences,
            "history": history,
        }))
        .send()
        .await
        .map_err(|e| format!("Failed to contact server: {}", e))?;

    if !resp.status().is_success() {
        let status = resp.status();
        let body = resp.text().await.unwrap_or_default();
        return Err(format!("Build generation failed ({}): {}", status, body));
    }

    resp.json::<serde_json::Value>()
        .await
        .map_err(|e| format!("Failed to parse generated build: {}", e))
}

/// Remote build refinement (proxied through backend server).
#[tauri::command]
async fn refine_build_remote(
    token: String,
    guide: serde_json::Value,
    trade_prices: serde_json::Value,
    budget_chaos: u32,
    history: serde_json::Value,
    message: String,
) -> Result<serde_json::Value, String> {
    let client = reqwest::Client::new();
    let resp = client
        .post(format!("{}/api/ai/refine-build", API_BASE))
        .header("Authorization", format!("Bearer {}", token))
        .json(&serde_json::json!({
            "guide": guide,
            "trade_prices": trade_prices,
            "budget_chaos": budget_chaos,
            "history": history,
            "message": message,
        }))
        .send()
        .await
        .map_err(|e| format!("Failed to contact server: {}", e))?;

    if !resp.status().is_success() {
        let status = resp.status();
        let body = resp.text().await.unwrap_or_default();
        return Err(format!("Build refinement failed ({}): {}", status, body));
    }

    resp.json::<serde_json::Value>()
        .await
        .map_err(|e| format!("Failed to parse refined build: {}", e))
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_opener::init())
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_updater::Builder::new().build())
        .plugin(tauri_plugin_process::init())
        .invoke_handler(tauri::generate_handler![
            decode_build,
            analyze_delta,
            scrape_build_guide,
            open_passive_tree,
            trade_search,
            compare_items,
            ai_chat,
            ai_set_key,
            ai_check_key,
            refresh_knowledge,
            check_knowledge,
            generator_chat,
            generate_build,
            refine_build,
            save_build,
            list_saved_builds,
            load_saved_build,
            delete_saved_build,
            // Remote API commands
            load_token,
            store_token,
            logout,
            get_discord_auth_url,
            listen_for_oauth_callback,
            exchange_discord_code,
            get_user_status,
            open_checkout,
            ai_chat_remote,
            generator_chat_remote,
            generate_build_remote,
            refine_build_remote,
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
