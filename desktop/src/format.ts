// Formato español: 1.234,56 €, 12,3 %, fechas en hora de Madrid con su zona.
// "useGrouping: always" porque en es-ES Intl no agrupa los números de 4 cifras (1234).

const TZ = "Europe/Madrid";
const cache = new Map<string, Intl.NumberFormat>();

function nf(min: number, max = min): Intl.NumberFormat {
  const key = `${min}-${max}`;
  let f = cache.get(key);
  if (!f) {
    f = new Intl.NumberFormat("es-ES", {
      minimumFractionDigits: min,
      maximumFractionDigits: max,
      useGrouping: "always",
    });
    cache.set(key, f);
  }
  return f;
}

export const NA = "n/d";
const MINUS = "−"; // signo menos tipográfico

function signed(text: string, x: number, sign: boolean): string {
  if (x < 0) return MINUS + text.replace("-", "");
  return sign && x > 0 ? "+" + text : text;
}

export function fmtNum(x: number | null | undefined, decimals = 2): string {
  if (x == null || !Number.isFinite(x)) return NA;
  return signed(nf(decimals).format(x), x, false);
}

/** Fracción → porcentaje: 0.123 → "12,3 %". */
export function fmtPct(x: number | null | undefined, decimals = 1, sign = false): string {
  if (x == null || !Number.isFinite(x)) return NA;
  return signed(nf(decimals).format(x * 100), x, sign) + " %";
}

const SYMBOLS: Record<string, string> = { EUR: "€", USD: "$", GBP: "£", GBp: "p", CHF: "CHF" };

export function currencySymbol(currency?: string | null): string {
  if (!currency) return "";
  return SYMBOLS[currency] ?? currency;
}

/** Precio con su moneda: "1.234,56 €", "412,50 $". Precios pequeños con más decimales. */
export function fmtMoney(x: number | null | undefined, currency?: string | null): string {
  if (x == null || !Number.isFinite(x)) return NA;
  const decimals = Math.abs(x) < 1 ? 4 : 2;
  const sym = currencySymbol(currency);
  return signed(nf(decimals).format(x), x, false) + (sym ? " " + sym : "");
}

/** Cantidades grandes: "22.091 M€", "1,2 bill. $" (billón = millón de millones). */
export function fmtBig(x: number | null | undefined, currency?: string | null): string {
  if (x == null || !Number.isFinite(x)) return NA;
  const sym = currencySymbol(currency);
  const abs = Math.abs(x);
  if (abs >= 1e12) return `${nf(1).format(x / 1e12)} bill. ${sym}`.trim();
  if (abs >= 1e6) return `${nf(0).format(x / 1e6)} M${sym}`;
  return `${nf(0).format(x)} ${sym}`.trim();
}

const dtFormat = new Intl.DateTimeFormat("es-ES", {
  timeZone: TZ,
  day: "2-digit",
  month: "2-digit",
  year: "numeric",
  hour: "2-digit",
  minute: "2-digit",
  timeZoneName: "short",
});
const dFormat = new Intl.DateTimeFormat("es-ES", {
  timeZone: TZ,
  day: "2-digit",
  month: "2-digit",
  year: "numeric",
});

/** "14/10/2026 18:17 CEST" (hora de Madrid, con su zona). */
export function fmtDateTime(iso: string | null | undefined): string {
  if (!iso) return NA;
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return NA;
  const parts = dtFormat.formatToParts(d);
  const get = (t: string) => parts.find((p) => p.type === t)?.value ?? "";
  return `${get("day")}/${get("month")}/${get("year")} ${get("hour")}:${get("minute")} ${get("timeZoneName")}`;
}

export function fmtDate(iso: string | null | undefined): string {
  if (!iso) return NA;
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? NA : dFormat.format(d);
}

/** Antigüedad legible: "hace 5 min", "hace 3 h", "hace 2 días". */
export function fmtAge(iso: string | null | undefined, now: Date = new Date()): string {
  if (!iso) return NA;
  const s = (now.getTime() - new Date(iso).getTime()) / 1000;
  if (s < 90) return "hace un momento";
  if (s < 3600) return `hace ${Math.round(s / 60)} min`;
  if (s < 86400 * 2) return `hace ${Math.round(s / 3600)} h`;
  return `hace ${Math.round(s / 86400)} días`;
}
