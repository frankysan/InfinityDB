import { getArmies, getCatalogItem } from "./api.js";
import { faqRulingsSection, fetchReviewedFaqRulings } from "./faq-rulings.js";
import { appendMaintainedText } from "./maintained-text.js";
import { rulesCitationList, rulesReferenceSection } from "./rules-reference.js";
import { shareStateHref } from "./share-state.js";
import { referenceLoadMessage } from "./view-components.js";

const { catalog, singular, summaryHeading } = document.body.dataset;
const itemId = window.location.pathname.split("/").pop();
const isReinforcementsReference = catalog === "rules" && itemId === "reinforcements-extra";
const name = document.getElementById("item-name");
const meta = document.getElementById("item-meta");
const status = document.getElementById("item-status");
const content = document.getElementById("item-content");
const pageController = new AbortController();
let displayedItem;
let faqItems = [];
let reinforcementArmies = null;

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
  if (Array.isArray(item.vocabulary_sources)) {
    section.append(rulesCitationList(item.vocabulary_sources, {
      label: "Label vocabulary sources: ", discloseArchive: true,
    }));
    if (item.vocabulary_sources.length) {
      const scope = document.createElement("p");
      scope.className = "detail-source";
      scope.textContent = "These sources describe the Label vocabulary as a whole; "
        + "a source may not cover this specific Label.";
      section.append(scope);
    }
  }
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

function reinforcementSectionsSection(armies) {
  if (!Array.isArray(armies)) return null;
  const eligible = armies.filter((army) => army.playable !== false && !army.legacy);
  const byId = new Map(eligible.map((army) => [army.id, army]));
  const sections = eligible.filter((army) => army.role === "reinforcement")
    .sort((left, right) => left.name.localeCompare(right.name));
  if (!sections.length) return null;

  const section = document.createElement("section");
  section.className = "surface surface--subtle detail-section reference-detail-section";
  section.id = "reinforcement-section-navigation";
  const heading = document.createElement("h2");
  heading.className = "surface-titlebar surface-titlebar--ruled";
  heading.textContent = "Reinforcement Sections";
  const description = document.createElement("p");
  description.className = "detail-copy";
  description.textContent = "Explore the current Army source pools and their parent Armies. "
    + "These links do not validate a combined Army List or establish an N5 rewrite of the annex.";
  const list = document.createElement("ul");
  list.className = "reference-usage-list";

  function overviewLink(army) {
    const link = document.createElement("a");
    link.href = `/armies#army-${encodeURIComponent(
      army.public_slug || army.slug || String(army.id)
    )}`;
    link.textContent = army.name;
    return link;
  }

  for (const reinforcement of sections) {
    const item = document.createElement("li");
    item.append(overviewLink(reinforcement));
    const parents = (reinforcement.parent_armies || [])
      .map((parent) => byId.get(parent.id))
      .filter(Boolean);
    if (parents.length) {
      item.append(" — used by ");
      parents.forEach((parent, index) => {
        if (index) item.append(index === parents.length - 1 ? " and " : ", ");
        item.append(overviewLink(parent));
      });
    }
    const units = document.createElement("a");
    units.href = shareStateHref("/units", "units", {
      army_id: reinforcement.public_slug || reinforcement.slug || String(reinforcement.id),
      reinforcement: "1",
    });
    units.textContent = "Browse section units";
    item.append(" · ", units);
    list.append(item);
  }
  section.append(heading, description, list);
  return section;
}

function render(item) {
  displayedItem = item;
  document.title = `${item.name} · InfinityDB`;
  name.firstChild.textContent = item.name;
  if (meta) meta.textContent = `${singular} · ${item.id}`;
  const sections = item.rules?.length
    ? [rulesReferenceSection(item.rules)]
    : [definitionSection(item)];
  if (isReinforcementsReference) {
    const sectionsNavigation = reinforcementSectionsSection(reinforcementArmies);
    if (sectionsNavigation) sections.push(sectionsNavigation);
  }
  const categoryPeers = categoryPeersSection(item.category_peers);
  if (categoryPeers) sections.push(categoryPeers);
  const relatedCategory = relatedCategorySection(item.related_category_peers);
  if (relatedCategory) sections.push(relatedCategory);
  const usedBy = usedBySection(item.used_by);
  if (usedBy) sections.push(usedBy);
  if (faqItems.length) sections.push(faqRulingsSection(faqItems));
  content.replaceChildren(...sections);
  content.hidden = false;
  status.hidden = true;
}

document.addEventListener(
  "infinity:beforenavigation",
  () => pageController.abort(),
  { once: true },
);
getCatalogItem(catalog, itemId, pageController.signal).then((item) => {
  render(item);
  if (isReinforcementsReference) {
    getArmies(pageController.signal).then((payload) => {
      if (pageController.signal.aborted) return;
      reinforcementArmies = payload.items || [];
      if (displayedItem) render(displayedItem);
    }).catch((error) => {
      if (error.name !== "AbortError") {
        console.error("Could not load Reinforcement Section links", error);
      }
    });
  }
  if (catalog !== "rules" && catalog !== "ammunition") return;
  const prefix = catalog === "rules" ? "rule" : "ammunition";
  const topicId = item.rules?.find((rule) => rule.id?.startsWith(`${prefix}:`))?.id
    || `${prefix}:${itemId}`;
  fetchReviewedFaqRulings(topicId, { signal: pageController.signal })
    .then((payload) => {
      if (pageController.signal.aborted) return;
      faqItems = payload.items || [];
      if (faqItems.length && displayedItem) render(displayedItem);
    })
    .catch((error) => {
      if (error.name !== "AbortError") console.error("Could not load FAQ clarifications", error);
    });
}).catch((error) => {
  if (error.name === "AbortError") return;
  name.firstChild.textContent = `${singular} unavailable`;
  status.textContent = referenceLoadMessage(error, singular.toLowerCase());
  console.error("Could not load reference detail", error);
});
