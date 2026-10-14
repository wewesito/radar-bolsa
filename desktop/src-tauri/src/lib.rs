//! Ventana de escritorio de Radar Bolsa.
//!
//! Al abrir la app se lanza el motor en Python (la API local de `src/radar/api`) con un
//! puerto libre y un token aleatorio. El motor escribe `RADAR_ENGINE_READY port=NNNN` al
//! estar listo; la interfaz pregunta por `engine_info` hasta tenerlo. Al cerrar la app se
//! cierra el motor (y él mismo se cierra si la app desaparece: `--watch-parent`).

use std::sync::Mutex;

use serde::Serialize;
use tauri::{AppHandle, Manager, RunEvent};
use tauri_plugin_shell::process::{CommandChild, CommandEvent};
use tauri_plugin_shell::ShellExt;

const READY_PREFIX: &str = "RADAR_ENGINE_READY port=";

#[derive(Clone, Serialize)]
struct EngineInfo {
    port: u16,
    token: String,
}

#[derive(Default)]
struct EngineState {
    info: Mutex<Option<EngineInfo>>,
    error: Mutex<Option<String>>,
    child: Mutex<Option<CommandChild>>,
}

#[tauri::command]
fn engine_info(state: tauri::State<EngineState>) -> Option<EngineInfo> {
    state.info.lock().unwrap().clone()
}

#[tauri::command]
fn engine_error(state: tauri::State<EngineState>) -> Option<String> {
    state.error.lock().unwrap().clone()
}

fn set_error(app: &AppHandle, msg: String) {
    *app.state::<EngineState>().error.lock().unwrap() = Some(msg);
}

fn spawn_engine(app: AppHandle) {
    let token = uuid::Uuid::new_v4().simple().to_string();
    let args = ["--port", "0", "--token", token.as_str(), "--watch-parent"];

    // Desarrollo: el Python del entorno virtual del proyecto (cambios al instante).
    // App instalada: el motor empaquetado con PyInstaller dentro de Resources/engine.
    let command = if cfg!(debug_assertions) {
        let python = std::env::var("RADAR_PYTHON").unwrap_or_else(|_| {
            format!("{}/../../.venv/bin/python", env!("CARGO_MANIFEST_DIR"))
        });
        app.shell().command(python).args(["-m", "radar.api"]).args(args)
    } else {
        let exe = match app.path().resource_dir() {
            Ok(dir) => dir.join("engine").join("radar-engine"),
            Err(e) => return set_error(&app, format!("No se encontró el motor: {e}")),
        };
        app.shell().command(exe).args(args)
    };

    let (mut rx, child) = match command.spawn() {
        Ok(pair) => pair,
        Err(e) => return set_error(&app, format!("No se pudo arrancar el motor de datos: {e}")),
    };
    *app.state::<EngineState>().child.lock().unwrap() = Some(child);

    tauri::async_runtime::spawn(async move {
        while let Some(event) = rx.recv().await {
            match event {
                CommandEvent::Stdout(line) => {
                    let text = String::from_utf8_lossy(&line);
                    if let Some(port) = text.trim().strip_prefix(READY_PREFIX) {
                        if let Ok(port) = port.parse::<u16>() {
                            let info = EngineInfo { port, token: token.clone() };
                            *app.state::<EngineState>().info.lock().unwrap() = Some(info);
                        }
                    }
                }
                CommandEvent::Stderr(line) => eprintln!("[motor] {}", String::from_utf8_lossy(&line)),
                CommandEvent::Terminated(status) => {
                    let msg = format!(
                        "El motor de datos se ha cerrado (código {:?}). Cierra y vuelve a abrir la app.",
                        status.code
                    );
                    *app.state::<EngineState>().info.lock().unwrap() = None;
                    set_error(&app, msg);
                }
                _ => {}
            }
        }
    });
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .manage(EngineState::default())
        .setup(|app| {
            spawn_engine(app.handle().clone());
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![engine_info, engine_error])
        .build(tauri::generate_context!())
        .expect("no se pudo iniciar Radar Bolsa")
        .run(|app, event| {
            if let RunEvent::Exit = event {
                if let Some(child) = app.state::<EngineState>().child.lock().unwrap().take() {
                    let _ = child.kill();
                }
            }
        });
}
