// Abre un enlace https en el navegador del sistema (en la app) o en otra pestaña (desarrollo).

export async function openExternal(url: string): Promise<void> {
  if (!url.startsWith("https://")) return;
  if ("__TAURI_INTERNALS__" in window) {
    const { open } = await import("@tauri-apps/plugin-shell");
    await open(url);
  } else {
    window.open(url, "_blank", "noopener,noreferrer");
  }
}
