import { skillCategoryBadge } from "./skill-categories.js";

function citationLabel(citation) {
  const source = citation.source_title || citation.source_id || "Source";
  const version = citation.source_version && !source.toLowerCase().includes(
    citation.source_version.toLowerCase()
  ) ? ` v${citation.source_version}` : "";
  const location = citation.page
    ? `p. ${citation.page}`
    : citation.heading || citation.member || citation.section || "";
  return `${source}${version}${location ? `, ${location}` : ""}`;
}

function citationNode(citation) {
  const label = citationLabel(citation);
  if (!citation.source_url) return document.createTextNode(label);
  const link = document.createElement("a");
  link.href = citation.source_url;
  link.target = "_blank";
  link.rel = "noopener noreferrer";
  link.textContent = label;
  return link;
}

function applicabilityText(rule) {
  const parts = [];
  if (rule.collection?.title) parts.push(rule.collection.title);
  if (rule.scope?.game) parts.push(rule.scope.game);
  const seasons = Array.isArray(rule.scope?.seasons) ? rule.scope.seasons : [];
  if (seasons.length && !(seasons.length === 1 && seasons[0] === "current")) {
    parts.push(seasons.join(", "));
  }
  return parts.join(" · ");
}

function relationHref(record) {
  const catalogs = { skill: "skills", equipment: "equipment", weapon: "weapons" };
  const armyLinks = record.army_links || [];
  for (const link of armyLinks) {
    const catalog = catalogs[link.entity];
    if (!catalog || typeof link.id !== "string" || /^\d+$/.test(link.id)) continue;
    return `/${catalog}/${encodeURIComponent(link.id)}`;
  }
  if (record.kind === "skill" && armyLinks.length === 0 && typeof record.id === "string") {
    const prefix = "skill:";
    if (record.id.startsWith(prefix) && record.id.length > prefix.length) {
      return `/skills/${encodeURIComponent(record.id.slice(prefix.length))}`;
    }
  }
  if (record.kind === "trait" && typeof record.id === "string") {
    const prefix = "trait:";
    if (record.id.startsWith(prefix) && record.id.length > prefix.length) {
      return `/traits/${encodeURIComponent(record.id.slice(prefix.length))}`;
    }
  }
  if (record.kind === "state" && typeof record.id === "string") {
    const prefix = "state:";
    if (record.id.startsWith(prefix) && record.id.length > prefix.length) {
      return `/states/${encodeURIComponent(record.id.slice(prefix.length))}`;
    }
  }
  return null;
}

function relationPresentation(relation) {
  const presentation = relation.presentation;
  const record = relation.record;
  if (!presentation?.label || !presentation?.group_id || !presentation?.group_label
      || !Number.isFinite(presentation?.group_order)
      || !Number.isFinite(presentation?.relation_order) || !record?.name) return null;
  return { relation, presentation, label: presentation.label, record };
}

function relationNode(presentation) {
  const { label, record } = presentation;
  const item = document.createElement("li");
  const relationLabel = document.createElement("span");
  relationLabel.className = "rules-relation-label";
  relationLabel.textContent = `${label}: `;
  item.append(relationLabel);

  const href = relationHref(record);
  if (href) {
    const link = document.createElement("a");
    link.href = href;
    link.textContent = record.name;
    item.append(link);
  } else {
    item.append(document.createTextNode(record.name));
  }
  return item;
}

function appendRuleRelations(container, rule) {
  const relations = (rule.display_relations || [])
    .map(relationPresentation)
    .filter(Boolean);
  if (!relations.length) return;

  const group = document.createElement("div");
  group.className = "detail-fact-group rules-relations";
  const heading = document.createElement("h4");
  heading.className = "detail-fact-heading";
  heading.textContent = "Related rules";
  group.append(heading);

  const groups = new Map();
  for (const item of relations) {
    const { group_id: id, group_label: label, group_order: order } = item.presentation;
    const relationGroup = groups.get(id) || { id, label, order, relations: [] };
    relationGroup.relations.push(item);
    groups.set(id, relationGroup);
  }

  for (const relationGroup of [...groups.values()].sort((left, right) => (
    left.order - right.order || left.label.localeCompare(right.label)
  ))) {
    relationGroup.relations.sort((left, right) => (
      left.presentation.relation_order - right.presentation.relation_order
      || left.label.localeCompare(right.label)
      || left.record.name.localeCompare(right.record.name, undefined, { numeric: true })
    ));

    const relationGroupElement = document.createElement("div");
    relationGroupElement.className = "rules-relation-group";
    const groupHeading = document.createElement("h5");
    groupHeading.className = "rules-relation-group-heading";
    groupHeading.textContent = relationGroup.label;
    const list = document.createElement("ul");
    list.className = "detail-list";
    list.append(...relationGroup.relations.map(relationNode));
    relationGroupElement.append(groupHeading, list);
    group.append(relationGroupElement);
  }
  container.append(group);
}

function ruleBadgeRow(rule) {
  const skillTypes = rule.skill_types || (rule.skill_type ? [rule.skill_type] : []);
  const declarationCategories = rule.declaration_categories || [];
  const categories = [];
  const seenCategories = new Set();
  for (const category of [...skillTypes, ...declarationCategories]) {
    const key = category?.id || category?.category_name || category?.name;
    if (!key || seenCategories.has(key)) continue;
    seenCategories.add(key);
    categories.push(category);
  }
  const labels = (rule.labels || []).map((label) => label.name);
  if (!categories.length && !labels.length) return null;

  const badgeRow = document.createElement("p");
  badgeRow.className = "detail-badges";
  for (const category of categories) {
    badgeRow.append(
      skillCategoryBadge(category, category.category_name || category.name)
    );
  }
  for (const label of labels) {
    const element = document.createElement("span");
    element.className = "badge";
    element.textContent = label;
    badgeRow.append(element);
  }
  return badgeRow;
}

function appendRuleDetails(container, rule, { includeBadges = true } = {}) {
  const summary = document.createElement("p");
  summary.className = "detail-copy";
  summary.textContent = rule.summary;
  container.append(summary);

  const badgeRow = includeBadges ? ruleBadgeRow(rule) : null;
  if (badgeRow) container.append(badgeRow);

  const facts = rule.facts || {};
  for (const [key, label] of [
    ["requirements", "Requirements"],
    ["effects", "Effects"],
    ["restrictions", "Restrictions"],
  ]) {
    if (!Array.isArray(facts[key]) || !facts[key].length) continue;
    const group = document.createElement("div");
    group.className = "detail-fact-group";
    const heading = document.createElement("h4");
    heading.className = "detail-fact-heading";
    heading.textContent = label;
    const list = document.createElement("ul");
    list.className = "detail-list";
    for (const fact of facts[key]) {
      const item = document.createElement("li");
      item.textContent = fact;
      list.append(item);
    }
    group.append(heading, list);
    container.append(group);
  }

  appendRuleRelations(container, rule);

  const applicability = applicabilityText(rule);
  if (applicability) {
    const context = document.createElement("p");
    context.className = "detail-source";
    context.textContent = applicability;
    container.append(context);
  }

  if (rule.citations?.length) {
    const citations = document.createElement("p");
    citations.className = "detail-source";
    for (const [index, citation] of rule.citations.entries()) {
      if (index) citations.append(" · ");
      citations.append(citationNode(citation));
    }
    container.append(citations);
  }
}

export function rulesReferenceSection(rules, headingText = "Rules reference") {
  const section = document.createElement("section");
  section.className = "detail-group rules-reference";
  const heading = document.createElement("h2");
  heading.className = "detail-section-title";
  heading.textContent = headingText;
  section.append(heading);

  for (const rule of rules) {
    const article = document.createElement("article");
    article.className = "detail-section";
    const header = document.createElement("header");
    header.className = "rules-card-header";
    const title = document.createElement("h3");
    title.textContent = rule.name;
    header.append(title);
    const badgeRow = ruleBadgeRow(rule);
    if (badgeRow) header.append(badgeRow);
    article.append(header);
    appendRuleDetails(article, rule, { includeBadges: false });

    for (const supplement of rule.supplements || []) {
      const supplemental = document.createElement("div");
      supplemental.className = "rules-supplement";
      const supplementTitle = document.createElement("h4");
      supplementTitle.textContent = "Additional rules context";
      supplemental.append(supplementTitle);
      appendRuleDetails(supplemental, supplement);
      article.append(supplemental);
    }
    section.append(article);
  }
  return section;
}
