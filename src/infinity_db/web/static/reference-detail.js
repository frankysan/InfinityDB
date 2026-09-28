import { getCatalogItem } from "./api.js";
import { appendMaintainedText } from "./maintained-text.js";
import { initializeDistanceUnitToggle } from "./preferences.js";
import { rulesReferenceSection } from "./rules-reference.js";

const { catalog, singular, summaryHeading } = document.body.dataset;
const itemId = window.location.pathname.split("/").pop();
const name = document.getElementById("item-name");
const meta = document.getElementById("item-meta");
const status = document.getElementById("item-status");
const content = document.getElementById("item-content");
const pageController = new AbortController();

function definitionSection(item) {
  const section = document.createElement("section");
  section.className = "surface surface--subtle detail-section";
  const heading = document.createElement("h2");
  heading.className = "surface-titlebar surface-titlebar--ruled";
  heading.textContent = summaryHeading || "Definition";
  const copy = document.createElement("p");
  copy.className = "detail-copy";
  appendMaintainedText(
    copy,
    item.description_tokens,
    item.description || "No definition is available.",
  );
  section.append(heading, copy);
  return section;
}

function render(item) {
  document.title = `${item.name} · InfinityDB`;
  name.firstChild.textContent = item.name;
  if (meta) meta.textContent = `${singular} · ${item.id}`;
  content.replaceChildren(
    ...(item.rules?.length
      ? [rulesReferenceSection(item.rules)]
      : [definitionSection(item)]),
  );
  content.hidden = false;
  status.hidden = true;
}

document.addEventListener(
  "infinity:beforenavigation",
  () => pageController.abort(),
  { once: true },
);
initializeDistanceUnitToggle();
getCatalogItem(catalog, itemId, pageController.signal).then(render).catch((error) => {
  if (error.name === "AbortError") return;
  name.firstChild.textContent = `${singular} unavailable`;
  status.textContent = error.message || "Could not load this reference item.";
});
