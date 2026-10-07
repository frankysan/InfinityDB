import { getCatalogItem } from "./api.js";
import { appendMaintainedText } from "./maintained-text.js";
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
  section.className = "surface surface--subtle detail-section reference-detail-section";
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

function usedBySection(items) {
  if (!Array.isArray(items) || !items.length) return null;

  const section = document.createElement("section");
  section.className = "surface surface--subtle detail-section reference-detail-section";
  const heading = document.createElement("h2");
  heading.className = "surface-titlebar surface-titlebar--ruled";
  heading.textContent = "Used by";
  section.append(heading);

  const groups = new Map();
  for (const item of items) {
    const key = item.catalog || item.catalog_name;
    const group = groups.get(key) || { name: item.catalog_name, items: [] };
    group.items.push(item);
    groups.set(key, group);
  }

  for (const group of groups.values()) {
    const container = document.createElement("div");
    container.className = "reference-usage-group";
    const groupHeading = document.createElement("h3");
    groupHeading.className = "detail-fact-heading";
    groupHeading.textContent = group.name;
    const list = document.createElement("ul");
    list.className = "reference-usage-list";
    for (const reference of group.items) {
      const item = document.createElement("li");
      const link = document.createElement("a");
      link.href = reference.href;
      link.textContent = reference.name;
      item.append(link);
      list.append(item);
    }
    container.append(groupHeading, list);
    section.append(container);
  }
  return section;
}

function publicReferenceHref(reference, fallbackCatalog = null) {
  if (reference?.href) return reference.href;
  if (reference?.catalog && reference?.id) {
    return `/${reference.catalog}/${encodeURIComponent(reference.id)}`;
  }
  if (fallbackCatalog && reference?.slug) {
    return `/${fallbackCatalog}/${encodeURIComponent(reference.slug)}`;
  }
  return null;
}

function categoryPeersSection(items) {
  if (!Array.isArray(items) || !items.length) return null;

  const section = document.createElement("section");
  section.className = "surface surface--subtle detail-section reference-detail-section";
  const heading = document.createElement("h2");
  heading.className = "surface-titlebar surface-titlebar--ruled";
  heading.textContent = "Same category";
  const list = document.createElement("ul");
  list.className = "reference-usage-list";
  for (const reference of items) {
    const item = document.createElement("li");
    const link = document.createElement("a");
    link.href = publicReferenceHref({ slug: reference.slug || reference.id }, catalog);
    link.textContent = reference.name;
    item.append(link);
    list.append(item);
  }
  section.append(heading, list);
  return section;
}

function relatedCategorySection(items) {
  if (!Array.isArray(items) || !items.length) return null;

  const section = document.createElement("section");
  section.className = "surface surface--subtle detail-section reference-detail-section";
  const heading = document.createElement("h2");
  heading.className = "surface-titlebar surface-titlebar--ruled";
  heading.textContent = "Related";
  const list = document.createElement("ul");
  list.className = "reference-usage-list";
  for (const reference of items) {
    const href = publicReferenceHref(reference.public_reference);
    if (!href) continue;
    const item = document.createElement("li");
    const link = document.createElement("a");
    link.href = href;
    link.textContent = reference.name;
    item.append(link);
    if (reference.domain) item.append(` · ${reference.domain}`);
    list.append(item);
  }
  if (!list.childElementCount) return null;
  section.append(heading, list);
  return section;
}

function render(item) {
  document.title = `${item.name} · InfinityDB`;
  name.firstChild.textContent = item.name;
  if (meta) meta.textContent = `${singular} · ${item.id}`;
  const sections = item.rules?.length
    ? [rulesReferenceSection(item.rules)]
    : [definitionSection(item)];
  const categoryPeers = categoryPeersSection(item.category_peers);
  if (categoryPeers) sections.push(categoryPeers);
  const relatedCategory = relatedCategorySection(item.related_category_peers);
  if (relatedCategory) sections.push(relatedCategory);
  const usedBy = usedBySection(item.used_by);
  if (usedBy) sections.push(usedBy);
  content.replaceChildren(...sections);
  content.hidden = false;
  status.hidden = true;
}

document.addEventListener(
  "infinity:beforenavigation",
  () => pageController.abort(),
  { once: true },
);
getCatalogItem(catalog, itemId, pageController.signal).then(render).catch((error) => {
  if (error.name === "AbortError") return;
  name.firstChild.textContent = `${singular} unavailable`;
  status.textContent = error.message || "Could not load this reference item.";
});
