import { formatDistanceExtra } from "./preferences.js";

let tooltipSequence = 0;
let activeTouchReference = null;
let pendingTouchReference = null;

function closeTouchPreview() {
  if (!activeTouchReference) return;
  const wrapper = activeTouchReference.closest(".maintained-reference-wrap");
  wrapper?.removeAttribute("data-touch-open");
  if (document.activeElement === activeTouchReference) activeTouchReference.blur();
  activeTouchReference = null;
}

function positionReferenceTooltip(link) {
  const wrapper = link.closest(".maintained-reference-wrap");
  const tooltip = wrapper?.querySelector(".maintained-reference-tooltip");
  if (!wrapper || !tooltip) return;

  const viewportGutter = 12;
  wrapper.removeAttribute("data-tooltip-placement");
  tooltip.style.removeProperty("--maintained-tooltip-shift-x");

  const linkRect = link.getBoundingClientRect();
  const tooltipRect = tooltip.getBoundingClientRect();
  const spaceAbove = linkRect.top - viewportGutter;
  const spaceBelow = window.innerHeight - linkRect.bottom - viewportGutter;
  if (spaceAbove < tooltipRect.height + 8 && spaceBelow > spaceAbove) {
    wrapper.dataset.tooltipPlacement = "below";
  }

  const positionedRect = tooltip.getBoundingClientRect();
  let shiftX = 0;
  if (positionedRect.left < viewportGutter) {
    shiftX += viewportGutter - positionedRect.left;
  } else if (positionedRect.right > window.innerWidth - viewportGutter) {
    shiftX -= positionedRect.right - (window.innerWidth - viewportGutter);
  }
  tooltip.style.setProperty("--maintained-tooltip-shift-x", `${Math.round(shiftX)}px`);
}

function openTouchPreview(link) {
  if (activeTouchReference && activeTouchReference !== link) closeTouchPreview();
  positionReferenceTooltip(link);
  activeTouchReference = link;
  link.closest(".maintained-reference-wrap")?.setAttribute("data-touch-open", "true");
}

function prepareTouchReference(link) {
  link.addEventListener("pointerdown", (event) => {
    if (event.pointerType !== "touch") {
      pendingTouchReference = null;
      return;
    }
    pendingTouchReference = {
      link,
      follow: activeTouchReference === link,
    };
  });
  link.addEventListener("pointerup", (event) => {
    if (event.pointerType !== "touch" || pendingTouchReference?.link !== link) return;
    if (!pendingTouchReference.follow) openTouchPreview(link);
  });
  link.addEventListener("pointercancel", () => {
    if (pendingTouchReference?.link === link) pendingTouchReference = null;
  });
  link.addEventListener("click", (event) => {
    if (event.detail === 0) {
      pendingTouchReference = null;
      return;
    }
    if (pendingTouchReference?.link !== link) return;
    const { follow } = pendingTouchReference;
    pendingTouchReference = null;
    const tooltip = link.closest(".maintained-reference-wrap")
      ?.querySelector(".maintained-reference-tooltip");
    if (!tooltip) return;
    if (follow) {
      closeTouchPreview();
      return;
    }
    event.preventDefault();
    openTouchPreview(link);
  });
}

function referenceHref(token) {
  const reference = token.public_reference;
  if (!reference?.catalog || !reference?.id) return null;
  return `/${reference.catalog}/${encodeURIComponent(reference.id)}`;
}

function updateDistanceNode(node) {
  const centimeters = node.dataset.distanceCentimeters;
  if (centimeters == null) return;
  node.textContent = formatDistanceExtra(centimeters, {
    showPositiveSign: false,
    forcePositiveSign: node.dataset.positiveSign === "true",
  });
}

function distanceNode(token) {
  const node = document.createElement("span");
  node.className = "maintained-distance";
  node.dataset.distanceCentimeters = String(token.centimeters);
  node.dataset.positiveSign = String(Boolean(token.positive_sign));
  updateDistanceNode(node);
  return node;
}

function referenceNode(token, { interactive = true } = {}) {
  const href = referenceHref(token);
  if (!interactive || !href || !token.label) {
    return document.createTextNode(token.label || token.target || "");
  }

  const wrapper = document.createElement("span");
  wrapper.className = "maintained-reference-wrap";
  const link = document.createElement("a");
  link.className = "maintained-reference";
  link.href = href;
  link.textContent = token.label;
  wrapper.append(link);

  if (Array.isArray(token.preview_tokens) && token.preview_tokens.length) {
    const tooltip = document.createElement("span");
    tooltipSequence += 1;
    tooltip.id = `maintained-reference-tooltip-${tooltipSequence}`;
    tooltip.className = "maintained-reference-tooltip";
    tooltip.role = "tooltip";
    tooltip.append(maintainedTextFragment(token.preview_tokens, "", { interactive: false }));
    link.setAttribute("aria-describedby", tooltip.id);
    wrapper.append(tooltip);
    link.addEventListener("pointerenter", () => positionReferenceTooltip(link));
    link.addEventListener("focus", () => positionReferenceTooltip(link));
    prepareTouchReference(link);
  }
  return wrapper;
}

export function maintainedTextFragment(tokens, fallback = "", { interactive = true } = {}) {
  const fragment = document.createDocumentFragment();
  if (!Array.isArray(tokens)) {
    fragment.append(document.createTextNode(fallback || ""));
    return fragment;
  }
  for (const token of tokens) {
    if (token?.type === "text") {
      fragment.append(document.createTextNode(token.text || ""));
    } else if (token?.type === "distance" && Number.isFinite(Number(token.centimeters))) {
      fragment.append(distanceNode(token));
    } else if (token?.type === "reference") {
      fragment.append(referenceNode(token, { interactive }));
    }
  }
  return fragment;
}

export function appendMaintainedText(container, tokens, fallback = "") {
  container.append(maintainedTextFragment(tokens, fallback));
  return container;
}

function refreshDistances() {
  for (const node of document.querySelectorAll(".maintained-distance[data-distance-centimeters]")) {
    updateDistanceNode(node);
  }
}

document.addEventListener("click", (event) => {
  if (!activeTouchReference) return;
  const wrapper = activeTouchReference.closest(".maintained-reference-wrap");
  if (wrapper?.contains(event.target)) return;
  closeTouchPreview();
});

document.addEventListener("infinity:beforenavigation", closeTouchPreview);
window.addEventListener("resize", () => {
  if (activeTouchReference) positionReferenceTooltip(activeTouchReference);
});
window.addEventListener("scroll", () => {
  if (activeTouchReference) positionReferenceTooltip(activeTouchReference);
}, { passive: true });
window.addEventListener("distanceunitchange", refreshDistances);
