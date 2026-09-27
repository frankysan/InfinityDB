function staticVersion() {
  return document.documentElement.dataset.staticVersion
    || document.documentElement.dataset.appVersion;
}

export function staticSymbolPath(symbolPath) {
  const version = staticVersion();
  return symbolPath && `/static/${encodeURI(symbolPath)}?v=${encodeURIComponent(version)}`;
}

export function unitSymbol(symbolPath, className = "") {
  const path = staticSymbolPath(symbolPath);
  if (!path) return document.createDocumentFragment();

  const icon = document.createElement("img");
  icon.className = `unit-symbol ${className}`.trim();
  icon.src = path;
  icon.alt = "";
  icon.width = 24;
  icon.height = 24;
  icon.loading = "lazy";
  icon.decoding = "async";
  icon.addEventListener("error", () => icon.remove(), { once: true });
  return icon;
}
