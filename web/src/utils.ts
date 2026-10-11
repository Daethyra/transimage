export function formatBytes(n: number): string {
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / 1024 / 1024).toFixed(1)} MB`;
}

export function clamp(v: number, min: number, max: number, fallback: number): number {
  if (!Number.isFinite(v)) return fallback;
  return Math.max(min, Math.min(max, Math.round(v)));
}

export function optionalInt(s: string, min: number, max: number): number | undefined {
  if (!s.trim()) return undefined;
  const v = parseInt(s, 10);
  if (!Number.isFinite(v)) return undefined;
  return Math.max(min, Math.min(max, v));
}

export function optionalFloat(s: string, min: number): number | undefined {
  if (!s.trim()) return undefined;
  const v = parseFloat(s);
  if (!Number.isFinite(v)) return undefined;
  return Math.max(min, v);
}

export function escapeHtml(s: string): string {
  return s.replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]!),
  );
}

/** Query the DOM and throw if it isn't there — keeps TS strict-friendly. */
export function $<T extends HTMLElement>(sel: string): T {
  const el = document.querySelector<T>(sel);
  if (!el) throw new Error(`Element not found: ${sel}`);
  return el;
}
