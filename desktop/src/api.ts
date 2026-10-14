// Conexión con el motor en Python.
// - Dentro de la app (Tauri): el proceso de Rust arranca el motor y nos da puerto y token.
// - En el navegador (desarrollo con `npm run dev`): motor lanzado a mano en el 8765, token "dev".

import { invoke } from "@tauri-apps/api/core";
import { useCallback, useEffect, useState } from "react";

type EngineInfo = { base: string; token: string };

const inTauri = typeof window !== "undefined" && "__TAURI_INTERNALS__" in window;
let enginePromise: Promise<EngineInfo> | null = null;

const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));

async function waitForEngine(): Promise<EngineInfo> {
  // El motor tarda unos segundos en arrancar la primera vez (descomprime Python).
  for (let i = 0; i < 480; i++) {
    const info = await invoke<{ port: number; token: string } | null>("engine_info");
    if (info) return { base: `http://127.0.0.1:${info.port}`, token: info.token };
    const failed = await invoke<string | null>("engine_error");
    if (failed) throw new ApiError(failed, 0, "engine");
    await sleep(250);
  }
  throw new ApiError("El motor de datos no ha arrancado.", 0, "engine");
}

function engine(): Promise<EngineInfo> {
  if (!enginePromise) {
    enginePromise = inTauri
      ? waitForEngine()
      : Promise.resolve({
          base: import.meta.env.VITE_ENGINE_URL ?? "http://127.0.0.1:8765",
          token: import.meta.env.VITE_ENGINE_TOKEN ?? "dev",
        });
  }
  return enginePromise;
}

export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
    public code?: string,
  ) {
    super(message);
  }
}

export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const { base, token } = await engine();
  let res: Response;
  try {
    res = await fetch(base + path, {
      ...init,
      headers: { "Content-Type": "application/json", "X-Radar-Token": token, ...init?.headers },
    });
  } catch {
    throw new ApiError("No se pudo contactar con el motor de datos.", 0, "network");
  }
  const body = await res.json().catch(() => ({}));
  if (!res.ok) {
    const detail = typeof body.detail === "string" ? body.detail : "Error inesperado.";
    throw new ApiError(detail, res.status, body.code);
  }
  return body as T;
}

// Caché sencilla de GET en memoria: navegar entre pantallas es instantáneo y `reload`
// (o `invalidate`) fuerza a pedir de nuevo.
const cache = new Map<string, unknown>();
const listeners = new Set<() => void>();

export function invalidate(prefix = ""): void {
  for (const k of [...cache.keys()]) if (k.startsWith(prefix)) cache.delete(k);
  listeners.forEach((l) => l());
}

export function useApi<T>(path: string | null) {
  const [data, setData] = useState<T | undefined>(() =>
    path ? (cache.get(path) as T | undefined) : undefined,
  );
  const [error, setError] = useState<ApiError | null>(null);
  const [loading, setLoading] = useState(false);
  const [tick, setTick] = useState(0);

  useEffect(() => {
    const l = () => setTick((t) => t + 1);
    listeners.add(l);
    return () => {
      listeners.delete(l);
    };
  }, []);

  useEffect(() => {
    if (!path) return;
    let alive = true;
    const cached = cache.get(path) as T | undefined;
    setData(cached);
    setError(null);
    if (cached !== undefined) return;
    setLoading(true);
    api<T>(path)
      .then((d) => {
        cache.set(path, d);
        if (alive) setData(d);
      })
      .catch((e: ApiError) => alive && setError(e))
      .finally(() => alive && setLoading(false));
    return () => {
      alive = false;
    };
  }, [path, tick]);

  const reload = useCallback(() => {
    if (path) cache.delete(path);
    setTick((t) => t + 1);
  }, [path]);

  return { data, error, loading, reload };
}
