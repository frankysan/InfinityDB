import { attachReferencePreview } from "./maintained-text.js";

// The supplied SVGs share one source-coordinate scale. Keep every diagram in a comparison
// on this conversion instead of fitting each image independently.
const SVG_UNITS_PER_MM = 4.23336;
const GLOSSARY_PIXELS_PER_MM = 2.7;
const PREVIEW_PIXELS_PER_MM = 2.2;
let tooltipSequence = 0;

const SILHOUETTES = Object.freeze([
  { id: 1, widthMm: 25, heightMm: 25, viewBoxWidth: 149.027, viewBoxHeight: 155.329 },
  { id: 2, widthMm: 25, heightMm: 40, viewBoxWidth: 149.376, viewBoxHeight: 218.829 },
  { id: 3, widthMm: 40, heightMm: 32, viewBoxWidth: 212.875, viewBoxHeight: 184.954 },
  { id: 4, widthMm: 55, heightMm: 32, viewBoxWidth: 276.375, viewBoxHeight: 184.953 },
  { id: 5, widthMm: 40, heightMm: 45, viewBoxWidth: 212.875, viewBoxHeight: 239.987 },
  { id: 6, widthMm: 40, heightMm: 55, viewBoxWidth: 212.875, viewBoxHeight: 282.32 },
  { id: 7, widthMm: 55, heightMm: 67, viewBoxWidth: 276.375, viewBoxHeight: 333.128 },
  { id: 8, widthMm: 70, heightMm: 70, viewBoxWidth: 339.875, viewBoxHeight: 345.826 },
]);
const SILHOUETTE_BY_ID = new Map(SILHOUETTES.map((item) => [item.id, item]));
const moduleVersion = new URL(import.meta.url).searchParams.get("v");

function assetPath(id) {
  const path = `/static/silhouettes/silhouette-${id}.svg`;
  return moduleVersion ? `${path}?v=${encodeURIComponent(moduleVersion)}` : path;
}

function label(item, reference = false) {
  const prefix = reference ? `S${item.id} reference` : `S${item.id}`;
  return `${prefix} · ${item.widthMm} × ${item.heightMm} mm`;
}

function diagramFigure(item, { pixelsPerMm, reference = false, visibleCaption = false }) {
  const figure = document.createElement("figure");
  figure.className = "silhouette-figure";
  if (reference) figure.classList.add("silhouette-figure--reference");

  const caption = document.createElement("figcaption");
  caption.className = visibleCaption ? "silhouette-figure-caption" : "sr-only";
  caption.textContent = label(item, reference);

  const image = document.createElement("img");
  image.className = "silhouette-diagram-image";
  image.src = assetPath(item.id);
  image.alt = "";
  image.loading = "lazy";
  image.decoding = "async";
  image.style.width = `${(item.viewBoxWidth / SVG_UNITS_PER_MM) * pixelsPerMm}px`;
  image.style.height = `${(item.viewBoxHeight / SVG_UNITS_PER_MM) * pixelsPerMm}px`;
  figure.append(caption, image);
  return figure;
}

function diagramRow(items, options, pixelsPerMm) {
  const row = document.createElement("div");
  row.className = "silhouette-diagram-row";
  row.dataset.pixelsPerMm = String(pixelsPerMm);
  for (const item of items) row.append(diagramFigure(item, options(item)));
  return row;
}

export function silhouetteReferenceSet() {
  const section = document.createElement("section");
  section.className = "silhouette-reference-section";
  section.setAttribute("aria-labelledby", "silhouette-reference-heading");

  const heading = document.createElement("h4");
  heading.id = "silhouette-reference-heading";
  heading.className = "silhouette-reference-heading";
  heading.textContent = "Silhouette templates";

  const copy = document.createElement("p");
  copy.className = "silhouette-reference-copy";
  copy.textContent = "S1–S8 are shown at the same scale so their relative sizes can be compared directly.";

  const viewport = document.createElement("div");
  viewport.className = "silhouette-reference-viewport";
  viewport.tabIndex = 0;
  viewport.setAttribute("aria-label", "Silhouette templates S1 through S8");
  viewport.append(diagramRow(
    SILHOUETTES,
    () => ({ pixelsPerMm: GLOSSARY_PIXELS_PER_MM, visibleCaption: false }),
    GLOSSARY_PIXELS_PER_MM,
  ));

  section.append(heading, copy, viewport);
  return section;
}

export function silhouetteValuePreview(value) {
  const id = Number(value);
  const selected = Number.isInteger(id) ? SILHOUETTE_BY_ID.get(id) : null;
  if (!selected) return null;

  const wrapper = document.createElement("span");
  wrapper.className = "maintained-reference-wrap silhouette-preview-wrap";

  const trigger = document.createElement("button");
  trigger.type = "button";
  trigger.className = "silhouette-preview-trigger";
  trigger.textContent = String(id);
  trigger.setAttribute("aria-label", `Show S${id} silhouette reference`);

  const tooltip = document.createElement("span");
  tooltipSequence += 1;
  tooltip.id = `silhouette-preview-tooltip-${tooltipSequence}`;
  tooltip.className = "maintained-reference-tooltip silhouette-preview-tooltip";
  tooltip.role = "tooltip";
  tooltip.setAttribute("popover", "manual");

  const title = document.createElement("strong");
  title.className = "silhouette-preview-title";
  title.textContent = `Silhouette S${id}`;
  tooltip.append(title);

  const comparison = id === 2 ? [selected] : [selected, SILHOUETTE_BY_ID.get(2)];
  tooltip.append(diagramRow(
    comparison,
    (item) => ({
      pixelsPerMm: PREVIEW_PIXELS_PER_MM,
      reference: item.id === 2 && id !== 2,
      visibleCaption: true,
    }),
    PREVIEW_PIXELS_PER_MM,
  ));

  if (id !== 2) {
    const note = document.createElement("span");
    note.className = "silhouette-preview-note";
    note.textContent = "S2 is shown at the same scale for reference.";
    tooltip.append(note);
  }

  wrapper.append(trigger, tooltip);
  attachReferencePreview(trigger, tooltip);
  return wrapper;
}
