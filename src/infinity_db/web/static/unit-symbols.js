function slugify(name) {
  return String(name)
    .normalize("NFKD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .replace(/&/g, " and ")
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
}

export function unitSymbolPath(unitName) {
  const slug = slugify(unitName);
  const symbol = unitSymbolSlug(slug) || slug;
  const version = document.documentElement.dataset.appVersion;
  return symbol && `/static/units/${encodeURI(symbol)}.svg?v=${encodeURIComponent(version)}`;
}

export function unitSymbol(unitName, className = "") {
  const icon = document.createElement("img");
  icon.className = `unit-symbol ${className}`.trim();
  icon.src = unitSymbolPath(unitName);
  icon.alt = "";
  icon.width = 24;
  icon.height = 24;
  icon.loading = "lazy";
  icon.decoding = "async";
  icon.addEventListener("error", () => icon.remove(), { once: true });
  return icon;
}
import { unitSymbolSlug } from "./unit-symbol-map.js";
