use std::fs;
use std::io::Write;
use std::path::PathBuf;
use std::process::Command as StdCommand;
use std::process::Stdio;
use std::sync::Arc;
use tauri::Manager;
use tokio::sync::RwLock;

// Backend API base URL — configurable for dev vs production
const API_BASE: &str = "http://45.61.55.200:8080";

// Fallback paths for development — used when the bundled sidecar isn't found
const DEV_PYTHON_EXE: &str = "C:\\Users\\Administrator\\AppData\\Local\\Programs\\Python\\Python311\\python.exe";
const DEV_PYTHON_CWD: &str = "C:\\DEV\\Path of Purpose\\path-of-purpose\\src-python";

/// Resolve the Python executable, working directory, and whether it's the compiled sidecar.
/// Returns (exe_path, cwd, is_sidecar).
/// - is_sidecar=true: Nuitka-compiled pop-engine.exe, args go directly (no `-m pop.main` prefix)
/// - is_sidecar=false: Python interpreter, needs `-m pop.main` prefix
fn resolve_python_paths() -> (String, String, bool) {
    if let Ok(exe_path) = std::env::current_exe() {
        if let Some(exe_dir) = exe_path.parent() {
            // 1. Tauri externalBin sidecar: <exe_dir>/pop-engine.exe (production install)
            let sidecar_exe = exe_dir.join("pop-engine.exe");
            if sidecar_exe.exists() {
                return (
                    sidecar_exe.to_string_lossy().to_string(),
                    exe_dir.to_string_lossy().to_string(),
                    true,
                );
            }

            // 2. Dev mode via `cargo tauri dev`: exe is in src-tauri/target/debug/
            //    src-python is at ../../src-python relative to src-tauri/
            let dev_src = exe_dir.join("..").join("..").join("..").join("src-python");
            if dev_src.exists() {
                return (
                    DEV_PYTHON_EXE.to_string(),
                    dev_src.canonicalize()
                        .map(|p| p.to_string_lossy().to_string())
                        .unwrap_or_else(|_| DEV_PYTHON_CWD.to_string()),
                    false,
                );
            }
        }
    }

    // Final fallback: dev paths
    (DEV_PYTHON_EXE.to_string(), DEV_PYTHON_CWD.to_string(), false)
}

/// Run a Python subcommand, optionally piping stdin_data. Returns (stdout, stderr).
/// Args should include `-m pop.main` prefix — it will be stripped automatically for the compiled sidecar.
fn run_python_command(
    args: &[&str],
    stdin_data: Option<&str>,
) -> Result<String, String> {
    let (python_exe, python_cwd, is_sidecar) = resolve_python_paths();

    // For the compiled sidecar, strip the `-m pop.main` prefix from args
    let effective_args: Vec<&str> = if is_sidecar {
        args.iter()
            .skip_while(|a| *a == &"-m" || *a == &"pop.main")
            .copied()
            .collect()
    } else {
        args.to_vec()
    };

    let mut child = StdCommand::new(&python_exe)
        .args(&effective_args)
        .current_dir(&python_cwd)
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

/// Compare two Build objects (guide vs imported character) via the Delta Engine.
#[tauri::command]
async fn analyze_delta(
    guide_build: serde_json::Value,
    character_build: serde_json::Value,
) -> Result<serde_json::Value, String> {
    let input = serde_json::json!({
        "guide_build": guide_build,
        "character_build": character_build,
    });
    let stdin_data = serde_json::to_string(&input)
        .map_err(|e| format!("Failed to serialize input: {}", e))?;

    let stdout = run_python_command(
        &["-m", "pop.main", "delta_builds", "--stdin"],
        Some(&stdin_data),
    )?;

    serde_json::from_str::<serde_json::Value>(&stdout)
        .map_err(|e| format!("Failed to parse delta report: {}", e))
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

/// Resolve passive tree URLs for a BuildGuide's key_nodes.
#[tauri::command]
async fn resolve_tree_urls(guide: serde_json::Value) -> Result<serde_json::Value, String> {
    let input = serde_json::json!({ "guide": guide, "tree_version": "3.28.0" });
    let stdin_data = serde_json::to_string(&input)
        .map_err(|e| format!("Failed to serialize input: {}", e))?;

    let stdout = run_python_command(
        &["-m", "pop.main", "resolve_tree_urls", "--stdin"],
        Some(&stdin_data),
    )?;

    serde_json::from_str::<serde_json::Value>(&stdout)
        .map_err(|e| format!("Failed to parse resolved guide: {}", e))
}

/// Search PoE trade for items similar to a build item.
#[tauri::command]
async fn trade_search(
    item: serde_json::Value,
    league: String,
    equipped_item: Option<serde_json::Value>,
    enabled_mods: Option<Vec<String>>,
    min_links: Option<i32>,
    min_sockets: Option<i32>,
    socket_colours: Option<serde_json::Value>,
) -> Result<serde_json::Value, String> {
    let mut input = serde_json::json!({ "item": item, "league": league });
    if let Some(eq) = equipped_item {
        input["equipped_item"] = eq;
    }
    if let Some(mods) = enabled_mods {
        input["enabled_mods"] = serde_json::json!(mods);
    }
    if let Some(links) = min_links {
        input["min_links"] = serde_json::json!(links);
    }
    if let Some(sockets) = min_sockets {
        input["min_sockets"] = serde_json::json!(sockets);
    }
    if let Some(colours) = socket_colours {
        input["socket_colours"] = colours;
    }
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

/// Synthesize real Item objects from GuideItem stat priorities.
#[tauri::command]
async fn synthesize_items(
    items: serde_json::Value,
    tier: String,
) -> Result<serde_json::Value, String> {
    let input = serde_json::json!({ "items": items, "tier": tier });
    let stdin_data = serde_json::to_string(&input)
        .map_err(|e| format!("Failed to serialize input: {}", e))?;

    let stdout = run_python_command(
        &["-m", "pop.main", "synthesize_items", "--stdin"],
        Some(&stdin_data),
    )?;

    serde_json::from_str::<serde_json::Value>(&stdout)
        .map_err(|e| format!("Failed to parse synthesized items: {}", e))
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

/// Compare full build DPS with an item swap (current vs trade item).
#[tauri::command]
async fn compare_build_dps(
    build: serde_json::Value,
    trade_listing: serde_json::Value,
    slot: String,
) -> Result<serde_json::Value, String> {
    let input = serde_json::json!({
        "build": build,
        "trade_listing": trade_listing,
        "slot": slot,
    });
    let stdin_data = serde_json::to_string(&input)
        .map_err(|e| format!("Failed to serialize input: {}", e))?;

    let stdout = run_python_command(
        &["-m", "pop.main", "compare_build_dps", "--stdin"],
        Some(&stdin_data),
    )?;

    serde_json::from_str::<serde_json::Value>(&stdout)
        .map_err(|e| format!("Failed to parse build DPS comparison: {}", e))
}

/// Batch compare build DPS for multiple trade listings in one invocation.
#[tauri::command]
async fn batch_compare_build_dps(
    build: serde_json::Value,
    listings: Vec<serde_json::Value>,
    slot: String,
    config: Option<serde_json::Value>,
) -> Result<serde_json::Value, String> {
    let mut input = serde_json::json!({
        "build": build,
        "listings": listings,
        "slot": slot,
    });
    if let Some(cfg) = config {
        input["config"] = cfg;
    }
    let stdin_data = serde_json::to_string(&input)
        .map_err(|e| format!("Failed to serialize input: {}", e))?;

    let stdout = run_python_command(
        &["-m", "pop.main", "batch_compare_build_dps", "--stdin"],
        Some(&stdin_data),
    )?;

    serde_json::from_str::<serde_json::Value>(&stdout)
        .map_err(|e| format!("Failed to parse batch DPS result: {}", e))
}

/// Suggest top passive tree nodes by DPS impact.
#[tauri::command]
async fn suggest_passive_nodes(
    build: serde_json::Value,
    config: Option<serde_json::Value>,
    max_suggestions: Option<u32>,
) -> Result<serde_json::Value, String> {
    let mut input = serde_json::json!({
        "build": build,
    });
    if let Some(cfg) = config {
        input["config"] = cfg;
    }
    if let Some(max) = max_suggestions {
        input["max_suggestions"] = serde_json::json!(max);
    }
    let stdin_data = serde_json::to_string(&input)
        .map_err(|e| format!("Failed to serialize input: {}", e))?;

    let stdout = run_python_command(
        &["-m", "pop.main", "suggest_passive_nodes", "--stdin"],
        Some(&stdin_data),
    )?;

    serde_json::from_str::<serde_json::Value>(&stdout)
        .map_err(|e| format!("Failed to parse suggestion result: {}", e))
}

/// Find best DPS upgrades across all gear slots within a budget.
#[tauri::command]
async fn budget_optimize(
    build: serde_json::Value,
    budget_chaos: u32,
    league: String,
    divine_ratio: Option<f64>,
    slots: Option<Vec<String>>,
    max_listings_per_slot: Option<u32>,
    config: Option<serde_json::Value>,
) -> Result<serde_json::Value, String> {
    let mut input = serde_json::json!({
        "build": build,
        "budget_chaos": budget_chaos,
        "league": league,
    });
    if let Some(ratio) = divine_ratio {
        input["divine_ratio"] = serde_json::json!(ratio);
    }
    if let Some(s) = slots {
        input["slots"] = serde_json::json!(s);
    }
    if let Some(max) = max_listings_per_slot {
        input["max_listings_per_slot"] = serde_json::json!(max);
    }
    if let Some(cfg) = config {
        input["config"] = cfg;
    }
    let stdin_data = serde_json::to_string(&input)
        .map_err(|e| format!("Failed to serialize input: {}", e))?;

    let stdout = run_python_command(
        &["-m", "pop.main", "budget_optimize", "--stdin"],
        Some(&stdin_data),
    )?;

    serde_json::from_str::<serde_json::Value>(&stdout)
        .map_err(|e| format!("Failed to parse budget optimization result: {}", e))
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

/// Resolve passive tree URLs via backend server.
#[tauri::command]
async fn resolve_tree_urls_remote(
    token: String,
    guide: serde_json::Value,
) -> Result<serde_json::Value, String> {
    let client = reqwest::Client::new();
    let resp = client
        .post(format!("{}/api/ai/resolve-tree-urls", API_BASE))
        .header("Authorization", format!("Bearer {}", token))
        .json(&serde_json::json!({
            "guide": guide,
            "tree_version": "3.28.0",
        }))
        .send()
        .await
        .map_err(|e| format!("Failed to contact server: {}", e))?;

    if !resp.status().is_success() {
        let status = resp.status();
        let body = resp.text().await.unwrap_or_default();
        return Err(format!("Tree URL resolution failed ({}): {}", status, body));
    }

    resp.json::<serde_json::Value>()
        .await
        .map_err(|e| format!("Failed to parse response: {}", e))
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

/// Calculate DPS for a build's skill via the Python calc engine.
#[tauri::command]
async fn calculate_dps(
    build: serde_json::Value,
    skill_index: Option<u32>,
    config: Option<serde_json::Value>,
) -> Result<serde_json::Value, String> {
    let mut input = serde_json::json!({ "build": build });
    if let Some(idx) = skill_index {
        input["skill_index"] = serde_json::json!(idx);
    }
    if let Some(cfg) = config {
        input["config"] = cfg;
    }
    let stdin_data = serde_json::to_string(&input)
        .map_err(|e| format!("Failed to serialize input: {}", e))?;

    let stdout = run_python_command(
        &["-m", "pop.main", "calc_dps", "--stdin"],
        Some(&stdin_data),
    )?;

    serde_json::from_str::<serde_json::Value>(&stdout)
        .map_err(|e| format!("Failed to parse calc result: {}", e))
}

/// List all known gem names (active + support) from the gem database.
#[tauri::command]
async fn list_gem_names() -> Result<serde_json::Value, String> {
    let stdout = run_python_command(
        &["-m", "pop.main", "list_gem_names"],
        None,
    )?;

    serde_json::from_str::<serde_json::Value>(&stdout)
        .map_err(|e| format!("Failed to parse gem names: {}", e))
}

/// List characters on a public PoE account.
#[tauri::command]
async fn list_public_characters(account_name: String) -> Result<serde_json::Value, String> {
    let input = serde_json::json!({ "account_name": account_name });
    let stdin_data = serde_json::to_string(&input)
        .map_err(|e| format!("JSON error: {}", e))?;

    let stdout = run_python_command(
        &["-m", "pop.main", "list_public_characters", "--stdin"],
        Some(&stdin_data),
    )?;

    serde_json::from_str::<serde_json::Value>(&stdout)
        .map_err(|e| format!("Failed to parse characters: {}", e))
}

/// Import a character from a public PoE profile.
#[tauri::command]
async fn import_character(account_name: String, character_name: String) -> Result<serde_json::Value, String> {
    let input = serde_json::json!({
        "account_name": account_name,
        "character_name": character_name,
    });
    let stdin_data = serde_json::to_string(&input)
        .map_err(|e| format!("JSON error: {}", e))?;

    let stdout = run_python_command(
        &["-m", "pop.main", "import_character", "--stdin"],
        Some(&stdin_data),
    )?;

    serde_json::from_str::<serde_json::Value>(&stdout)
        .map_err(|e| format!("Failed to parse character: {}", e))
}

/// Calculate DPS for all skill groups in a build.
#[tauri::command]
async fn calculate_all_dps(
    build: serde_json::Value,
    config: Option<serde_json::Value>,
) -> Result<serde_json::Value, String> {
    let mut input = serde_json::json!({ "build": build });
    if let Some(cfg) = config {
        input["config"] = cfg;
    }
    let stdin_data = serde_json::to_string(&input)
        .map_err(|e| format!("Failed to serialize input: {}", e))?;

    let stdout = run_python_command(
        &["-m", "pop.main", "calc_all_dps", "--stdin"],
        Some(&stdin_data),
    )?;

    serde_json::from_str::<serde_json::Value>(&stdout)
        .map_err(|e| format!("Failed to parse calc results: {}", e))
}

/// Fetch the passive tree layout for Canvas rendering.
/// Caches locally after first fetch.
#[tauri::command]
async fn get_tree_layout(app: tauri::AppHandle) -> Result<serde_json::Value, String> {
    // Check local cache first
    let cache_dir = app.path().app_data_dir()
        .map_err(|e| format!("No app data dir: {}", e))?;
    let cache_file = cache_dir.join("tree_layout.json");

    if cache_file.exists() {
        if let Ok(data) = fs::read_to_string(&cache_file) {
            if let Ok(val) = serde_json::from_str::<serde_json::Value>(&data) {
                return Ok(val);
            }
        }
    }

    // Fetch from server
    let client = reqwest::Client::new();
    let resp = client
        .get(format!("{}/api/ai/tree-layout", API_BASE))
        .send()
        .await
        .map_err(|e| format!("Failed to fetch tree layout: {}", e))?;

    if !resp.status().is_success() {
        let status = resp.status();
        let body = resp.text().await.unwrap_or_default();
        return Err(format!("Tree layout fetch failed ({}): {}", status, body));
    }

    let body = resp.text().await
        .map_err(|e| format!("Failed to read response: {}", e))?;

    // Cache locally
    let _ = fs::create_dir_all(&cache_dir);
    let _ = fs::write(&cache_file, &body);

    serde_json::from_str::<serde_json::Value>(&body)
        .map_err(|e| format!("Failed to parse tree layout: {}", e))
}

// ---------------------------------------------------------------------------
// Overlay server state + Twitch token storage
// ---------------------------------------------------------------------------

/// Shared overlay state — updated by frontend, read by overlay HTTP server.
struct OverlayState(Arc<RwLock<serde_json::Value>>);

/// Whether the overlay server is already running.
struct OverlayServerRunning(Arc<RwLock<bool>>);

/// Store Twitch token + username in app data.
#[tauri::command]
async fn store_twitch_token(
    app: tauri::AppHandle,
    token: String,
    username: String,
    channel: String,
) -> Result<(), String> {
    let base = app.path().app_data_dir()
        .map_err(|e| format!("No app data dir: {}", e))?;
    if !base.exists() {
        fs::create_dir_all(&base)
            .map_err(|e| format!("Failed to create dir: {}", e))?;
    }
    let path = base.join("twitch_token.json");
    let data = serde_json::json!({
        "token": token,
        "username": username,
        "channel": channel,
    });
    fs::write(&path, serde_json::to_string_pretty(&data).unwrap())
        .map_err(|e| format!("Failed to write twitch token: {}", e))?;
    Ok(())
}

/// Load stored Twitch token.
#[tauri::command]
async fn load_twitch_token(app: tauri::AppHandle) -> Result<serde_json::Value, String> {
    let base = app.path().app_data_dir()
        .map_err(|e| format!("No app data dir: {}", e))?;
    let path = base.join("twitch_token.json");
    if !path.exists() {
        return Ok(serde_json::json!({ "token": null, "username": null, "channel": null }));
    }
    let raw = fs::read_to_string(&path)
        .map_err(|e| format!("Failed to read twitch token: {}", e))?;
    serde_json::from_str::<serde_json::Value>(&raw)
        .map_err(|e| format!("Failed to parse twitch token: {}", e))
}

/// Listen for Twitch OAuth callback on localhost:8460.
/// Twitch implicit grant sends the token in the URL fragment (#access_token=...).
/// Since servers can't see fragments, we serve a page that reads the fragment
/// via JS and posts it back to us.
#[tauri::command]
async fn listen_for_twitch_callback() -> Result<String, String> {
    use tokio::io::{AsyncReadExt, AsyncWriteExt};
    use tokio::net::TcpListener;

    let listener = TcpListener::bind("127.0.0.1:8460").await
        .map_err(|e| format!("Failed to bind Twitch callback listener: {}", e))?;

    // First connection: browser hits /callback — serve a page that reads the fragment
    let (mut stream, _) = listener.accept().await
        .map_err(|e| format!("Failed to accept connection: {}", e))?;

    let mut buf = vec![0u8; 4096];
    let _ = stream.read(&mut buf).await;

    // Serve a small HTML page that extracts the token from the URL fragment
    // and sends it back to us via a second request
    let html_response = r#"HTTP/1.1 200 OK
Content-Type: text/html

<html><body>
<h2>Logging in to Twitch...</h2>
<script>
  const hash = window.location.hash.substring(1);
  const params = new URLSearchParams(hash);
  const token = params.get('access_token');
  if (token) {
    fetch('/token?access_token=' + token).then(() => {
      document.body.innerHTML = '<h2>Twitch login successful!</h2><p>You can close this tab.</p>';
    });
  } else {
    document.body.innerHTML = '<h2>Login failed</h2><p>No token received. Close this tab and try again.</p>';
  }
</script>
</body></html>"#;
    let _ = stream.write_all(html_response.as_bytes()).await;
    drop(stream);

    // Second connection: the JS sends us the token
    let (mut stream2, _) = listener.accept().await
        .map_err(|e| format!("Failed to accept token callback: {}", e))?;

    let mut buf2 = vec![0u8; 4096];
    let n = stream2.read(&mut buf2).await
        .map_err(|e| format!("Failed to read token: {}", e))?;

    let request = String::from_utf8_lossy(&buf2[..n]).to_string();

    // Extract access_token from GET /token?access_token=XXX
    let token = request
        .lines()
        .next()
        .and_then(|line| {
            let path = line.split_whitespace().nth(1)?;
            let query = path.split('?').nth(1)?;
            query.split('&').find_map(|param| {
                let mut kv = param.splitn(2, '=');
                let key = kv.next()?;
                let val = kv.next()?;
                if key == "access_token" { Some(val.to_string()) } else { None }
            })
        })
        .ok_or_else(|| "No access token in callback".to_string())?;

    // Send success response
    let ok_response = "HTTP/1.1 200 OK\r\nContent-Type: text/plain\r\n\r\nOK";
    let _ = stream2.write_all(ok_response.as_bytes()).await;

    Ok(token)
}

/// Clear Twitch token.
#[tauri::command]
async fn clear_twitch_token(app: tauri::AppHandle) -> Result<(), String> {
    let base = app.path().app_data_dir()
        .map_err(|e| format!("No app data dir: {}", e))?;
    let path = base.join("twitch_token.json");
    if path.exists() {
        fs::remove_file(&path)
            .map_err(|e| format!("Failed to remove twitch token: {}", e))?;
    }
    Ok(())
}

/// Update the overlay state (called by frontend on a timer).
#[tauri::command]
async fn update_overlay_state(
    state: tauri::State<'_, OverlayState>,
    payload: serde_json::Value,
) -> Result<(), String> {
    let mut s = state.0.write().await;
    *s = payload;
    Ok(())
}

/// Start the overlay HTTP server on port 8459.
#[tauri::command]
async fn start_overlay_server(
    overlay_state: tauri::State<'_, OverlayState>,
    running: tauri::State<'_, OverlayServerRunning>,
) -> Result<String, String> {
    let mut is_running = running.0.write().await;
    if *is_running {
        return Ok("Overlay server already running at http://localhost:8459/overlay".to_string());
    }

    let state_ref = overlay_state.0.clone();

    tokio::spawn(async move {
        use axum::{Router, routing::get, extract::State, response::Html};

        let app = Router::new()
            .route("/overlay", get(|| async move {
                Html(OVERLAY_HTML.to_string())
            }))
            .route("/api/state", get(|State(s): State<Arc<RwLock<serde_json::Value>>>| async move {
                let data = s.read().await;
                axum::Json(data.clone())
            }))
            .with_state(state_ref);

        let listener = tokio::net::TcpListener::bind("127.0.0.1:8459")
            .await
            .expect("Failed to bind overlay server on port 8459");
        axum::serve(listener, app).await.ok();
    });

    *is_running = true;
    Ok("Overlay server started at http://localhost:8459/overlay".to_string())
}

/// Stop the overlay server.
#[tauri::command]
async fn stop_overlay_server(
    running: tauri::State<'_, OverlayServerRunning>,
) -> Result<(), String> {
    let mut is_running = running.0.write().await;
    *is_running = false;
    // Note: actual tokio task continues until port is rebound.
    // For a clean stop we'd need a shutdown signal, but for now
    // this just marks it as stopped so the UI reflects correctly.
    Ok(())
}

/// Embedded overlay HTML page — self-contained, no external deps.
const OVERLAY_HTML: &str = r##"<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Path of Purpose — Stream Overlay</title>
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body {
  background: transparent;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", system-ui, sans-serif;
  color: #e6edf3;
  width: 1920px;
  height: 1080px;
  overflow: hidden;
}
.overlay-top {
  position: absolute;
  top: 12px;
  left: 12px;
  right: 12px;
  display: flex;
  justify-content: space-between;
  gap: 12px;
  pointer-events: none;
}
.panel {
  background: rgba(13, 17, 23, 0.85);
  border: 1px solid rgba(48, 54, 61, 0.8);
  border-radius: 8px;
  padding: 10px 16px;
  backdrop-filter: blur(8px);
}
.dps-ticker {
  min-width: 240px;
}
.dps-value {
  font-size: 32px;
  font-weight: 800;
  color: #fbbf24;
  transition: transform 0.2s;
}
.dps-value.pulse { transform: scale(1.08); }
.dps-label {
  font-size: 13px;
  color: #8b949e;
  margin-top: 2px;
}
.boss-bar {
  display: flex;
  gap: 8px;
  align-items: center;
  flex-wrap: wrap;
}
.boss-pip {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
}
.boss-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
}
.boss-dot.pass { background: #4ade80; }
.boss-dot.warn { background: #fbbf24; }
.boss-dot.fail { background: #f87171; }

.overlay-bottom {
  position: absolute;
  bottom: 12px;
  left: 12px;
  right: 12px;
  display: flex;
  justify-content: space-between;
  gap: 12px;
  pointer-events: none;
}
.suggestions {
  display: flex;
  flex-direction: column;
  gap: 6px;
  max-width: 500px;
}
.suggestion-card {
  animation: slideIn 0.3s ease-out;
  font-size: 13px;
}
.suggestion-card .user { color: #58a6ff; font-weight: 600; }
.suggestion-card .text { color: #c9d1d9; }

.session-stats {
  text-align: right;
  font-size: 13px;
  color: #8b949e;
}
.session-stats .stat-value { color: #e6edf3; font-weight: 600; }

.build-info {
  font-size: 12px;
  color: #8b949e;
  margin-top: 4px;
}

@keyframes slideIn {
  from { opacity: 0; transform: translateX(20px); }
  to { opacity: 1; transform: translateX(0); }
}
.hidden { display: none; }
</style>
</head>
<body>
<div class="overlay-top">
  <div class="panel dps-ticker" id="dps-panel">
    <div class="dps-value" id="dps-value">—</div>
    <div class="dps-label" id="dps-label">DPS</div>
    <div class="build-info" id="build-info"></div>
  </div>
  <div class="panel boss-bar" id="boss-bar"></div>
</div>

<div class="overlay-bottom">
  <div class="suggestions" id="suggestions"></div>
  <div class="panel session-stats" id="session-stats">
    <div>Uptime: <span class="stat-value" id="uptime">0:00</span></div>
    <div>Commands: <span class="stat-value" id="cmds">0</span></div>
  </div>
</div>

<script>
let lastDps = 0;

function formatDps(v) {
  if (v >= 1e6) return (v / 1e6).toFixed(1) + 'M';
  if (v >= 1e3) return (v / 1e3).toFixed(0) + 'K';
  return Math.round(v).toString();
}

function formatUptime(startMs) {
  if (!startMs) return '0:00';
  const secs = Math.floor((Date.now() - startMs) / 1000);
  const h = Math.floor(secs / 3600);
  const m = Math.floor((secs % 3600) / 60);
  const s = secs % 60;
  if (h > 0) return h + ':' + String(m).padStart(2, '0') + ':' + String(s).padStart(2, '0');
  return m + ':' + String(s).padStart(2, '0');
}

async function poll() {
  try {
    const resp = await fetch('/api/state');
    const data = await resp.json();

    // DPS ticker
    const dpsEl = document.getElementById('dps-value');
    const newDps = data.combined_dps || 0;
    dpsEl.textContent = formatDps(newDps) + ' DPS';
    if (newDps !== lastDps) {
      dpsEl.classList.add('pulse');
      setTimeout(() => dpsEl.classList.remove('pulse'), 200);
      lastDps = newDps;
    }

    // DPS label
    document.getElementById('dps-label').textContent = data.skill_name || 'DPS';

    // Build info
    const parts = [];
    if (data.level) parts.push('Lv' + data.level);
    if (data.ascendancy) parts.push(data.ascendancy);
    document.getElementById('build-info').textContent = parts.join(' ');

    // Boss readiness
    const bossBar = document.getElementById('boss-bar');
    if (data.boss_readiness && data.boss_readiness.length) {
      bossBar.innerHTML = data.boss_readiness.map(b =>
        '<div class="boss-pip"><span class="boss-dot ' + b.status + '"></span>' + b.name + '</div>'
      ).join('');
      bossBar.classList.remove('hidden');
    } else {
      bossBar.classList.add('hidden');
    }

    // Viewer suggestions (show last 3)
    const sugEl = document.getElementById('suggestions');
    if (data.viewer_suggestions && data.viewer_suggestions.length) {
      sugEl.innerHTML = data.viewer_suggestions.slice(-3).map(s =>
        '<div class="panel suggestion-card"><span class="user">' + s.user + ':</span> <span class="text">' + s.text + '</span></div>'
      ).join('');
    } else {
      sugEl.innerHTML = '';
    }

    // Session stats
    document.getElementById('uptime').textContent = formatUptime(data.session_start);
    document.getElementById('cmds').textContent = String(data.commands_handled || 0);

    // Hide panels if no build
    document.getElementById('dps-panel').classList.toggle('hidden', !data.combined_dps);

  } catch (e) {
    // Server not ready yet, retry
  }
}

setInterval(poll, 2000);
poll();
</script>
</body>
</html>
"##;

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_opener::init())
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_updater::Builder::new().build())
        .plugin(tauri_plugin_process::init())
        .manage(OverlayState(Arc::new(RwLock::new(serde_json::json!({})))))
        .manage(OverlayServerRunning(Arc::new(RwLock::new(false))))
        .invoke_handler(tauri::generate_handler![
            decode_build,
            analyze_delta,
            scrape_build_guide,
            open_passive_tree,
            resolve_tree_urls,
            trade_search,
            synthesize_items,
            compare_items,
            compare_build_dps,
            batch_compare_build_dps,
            suggest_passive_nodes,
            budget_optimize,
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
            calculate_dps,
            calculate_all_dps,
            list_gem_names,
            list_public_characters,
            import_character,
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
            resolve_tree_urls_remote,
            get_tree_layout,
            // Streaming / overlay commands
            store_twitch_token,
            load_twitch_token,
            clear_twitch_token,
            listen_for_twitch_callback,
            update_overlay_state,
            start_overlay_server,
            stop_overlay_server,
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
