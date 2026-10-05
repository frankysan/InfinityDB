import { formatDistanceExtra } from "./distance.js";

let tooltipSequence = 0;
let activeReference = null;
let activeTouchReference = null;
let pendingTouchReference = null;

function referenceTooltip(link) {
  return link.closest(".maintained-reference-wrap")
    ?.querySelector(".maintained-reference-tooltip") || null;
}

function popoverSupported(tooltip) {
  return typeof tooltip.showPopover === "function" && typeof tooltip.hidePopover === "function";
}

function showReferenceTooltip(tooltip) {
  if (popoverSupported(tooltip)) {
    if (!tooltip.matches(":popover-open")) tooltip.showPopover();
    return;
  }
  tooltip.dataset.tooltipOpen = "true";
}

function hideReferenceTooltip(tooltip) {
  if (popoverSupported(tooltip)) {
    if (tooltip.matches(":popover-open")) tooltip.hidePopover();
    return;
  }
  tooltip.removeAttribute("data-tooltip-open");
}

function forceCloseReferencePreview(link) {
  const tooltip = referenceTooltip(link);
  if (tooltip) hideReferenceTooltip(tooltip);
  if (activeReference === link) activeReference = null;
}

function referencePreviewShouldStayOpen(link) {
  return activeTouchReference === link
    || document.activeElement === link
    || link.matches(":hover");
}

function closeReferencePreview(link) {
  if (referencePreviewShouldStayOpen(link)) return;
  forceCloseReferencePreview(link);
}

function closeTouchPreview() {
  if (!activeTouchReference) return;
  const link = activeTouchReference;
  activeTouchReference = null;
  if (document.activeElement === link) link.blur();
  forceCloseReferencePreview(link);
}

function positionReferenceTooltip(link) {
  const tooltip = referenceTooltip(link);
  if (!tooltip) {
    if (activeReference === link) activeReference = null;
    return;
  }

  if (activeReference && activeReference !== link) forceCloseReferencePreview(activeReference);
  activeReference = link;
  showReferenceTooltip(tooltip);

  const viewportGutter = 12;
  const tooltipGap = 8;
  tooltip.style.left = "0px";
  tooltip.style.top = "0px";

  const linkRect = link.getBoundingClientRect();
  const tooltipRect = tooltip.getBoundingClientRect();
  const spaceAbove = linkRect.top - viewportGutter;
  const spaceBelow = window.innerHeight - linkRect.bottom - viewportGutter;

  let left = linkRect.left + (linkRect.width - tooltipRect.width) / 2;
  const maxLeft = Math.max(
    viewportGutter,
    window.innerWidth - viewportGutter - tooltipRect.width,
  );
  left = Math.min(Math.max(left, viewportGutter), maxLeft);

  let top = linkRect.top - tooltipRect.height - tooltipGap;
  if (spaceAbove < tooltipRect.height + tooltipGap && spaceBelow > spaceAbove) {
    top = linkRect.bottom + tooltipGap;
  }
  const maxTop = Math.max(
    viewportGutter,
    window.innerHeight - viewportGutter - tooltipRect.height,
  );
  top = Math.min(Math.max(top, viewportGutter), maxTop);

  tooltip.style.left = `${Math.round(left)}px`;
  tooltip.style.top = `${Math.round(top)}px`;
}

function openReferencePreview(link) {
  positionReferenceTooltip(link);
}

function openTouchPreview(link) {
  if (activeTouchReference && activeTouchReference !== link) closeTouchPreview();
  activeTouchReference = link;
  openReferencePreview(link);
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
    if (!referenceTooltip(link)) return;
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
  if (reference?.href) return reference.href;
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
    tooltip.setAttribute("popover", "manual");
    tooltip.append(maintainedTextFragment(token.preview_tokens, "", { interactive: false }));
    link.setAttribute("aria-describedby", tooltip.id);
    wrapper.append(tooltip);
    link.addEventListener("pointerenter", (event) => {
      if (event.pointerType !== "touch") openReferencePreview(link);
    });
    link.addEventListener("pointerleave", (event) => {
      if (event.pointerType !== "touch") closeReferencePreview(link);
    });
    link.addEventListener("focus", () => openReferencePreview(link));
    link.addEventListener("blur", () => closeReferencePreview(link));
    prepareTouchReference(link);
  }
  return wrapper;
}

function reviewNeededNode(token, { interactive = true } = {}) {
  const wrapper = document.createElement("span");
  wrapper.className = "maintained-reference-wrap maintained-review-needed-wrap";

  const marker = document.createElement("span");
  marker.className = "maintained-review-needed";
  if (interactive) marker.tabIndex = 0;

  const text = document.createElement("span");
  text.className = "maintained-review-needed-text";
  text.textContent = token.text || "Review needed";
  marker.append(text);

  const badge = document.createElement("span");
  badge.className = "maintained-review-needed-badge";
  badge.textContent = "review";
  marker.append(badge);
  wrapper.append(marker);
  if (!interactive) return wrapper;

  const tooltip = document.createElement("span");
  tooltipSequence += 1;
  tooltip.id = `maintained-reference-tooltip-${tooltipSequence}`;
  tooltip.className = "maintained-reference-tooltip";
  tooltip.role = "tooltip";
  tooltip.setAttribute("popover", "manual");
  tooltip.textContent = `Manual review needed: ${token.reason || "unspecified"}`;
  marker.setAttribute("aria-describedby", tooltip.id);
  wrapper.append(tooltip);

  marker.addEventListener("pointerenter", (event) => {
    if (event.pointerType !== "touch") openReferencePreview(marker);
  });
  marker.addEventListener("pointerleave", (event) => {
    if (event.pointerType !== "touch") closeReferencePreview(marker);
  });
  marker.addEventListener("focus", () => openReferencePreview(marker));
  marker.addEventListener("blur", () => closeReferencePreview(marker));
  prepareTouchReference(marker);
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
    } else if (token?.type === "review-needed") {
      fragment.append(reviewNeededNode(token, { interactive }));
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

document.addEventListener("infinity:beforenavigation", () => {
  closeTouchPreview();
  if (activeReference) forceCloseReferencePreview(activeReference);
});
window.addEventListener("resize", () => {
  if (activeReference) positionReferenceTooltip(activeReference);
});
window.addEventListener("scroll", () => {
  if (activeReference) positionReferenceTooltip(activeReference);
}, { passive: true });
window.addEventListener("distanceunitchange", refreshDistances);
