import { appendMaintainedText, maintainedTextFragment } from "./maintained-text.js";
import { skillCategoryBadge } from "./skill-categories.js";
import { tableViewport } from "./view-components.js";

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
  const scenarios = Array.isArray(rule.applicable_scenarios) ? rule.applicable_scenarios : [];
  if (scenarios.length) parts.push(scenarios.map((item) => item.name).join(", "));
  return parts.join(" · ");
}

function relationHref(record) {
  const reference = record.public_reference;
  if (reference?.href) return reference.href;
  if (!reference?.catalog || !reference?.id) return null;
  return `/${reference.catalog}/${encodeURIComponent(reference.id)}`;
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
  const labels = rule.labels || [];
  if (!categories.length && !labels.length) return null;

  const badgeRow = document.createElement("p");
  badgeRow.className = "detail-badges";
  for (const label of labels) {
    if (!label.id) {
      const element = document.createElement("span");
      element.className = "badge";
      element.textContent = label.name;
      badgeRow.append(element);
      continue;
    }

    const previewTokens = Array.isArray(label.description_tokens)
      ? label.description_tokens
      : (label.description ? [{ type: "text", text: label.description }] : []);
    const fragment = maintainedTextFragment([{
      type: "reference",
      target: `label:${label.id}`,
      label: label.name,
      public_reference: { href: `/labels/${encodeURIComponent(label.id)}` },
      preview_tokens: previewTokens,
    }]);
    fragment.querySelector(".maintained-reference")?.classList.add("badge");
    badgeRow.append(fragment);
  }
  for (const category of categories) {
    badgeRow.append(
      skillCategoryBadge(category, category.category_name || category.name)
    );
  }
  return badgeRow;
}

function appendRuleDetails(
  container,
  rule,
  { includeBadges = true, beforeRelations = [] } = {},
) {
  const summary = document.createElement("p");
  summary.className = "detail-copy";
  appendMaintainedText(summary, rule.summary_tokens, rule.summary);
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
    for (const [index, fact] of facts[key].entries()) {
      const item = document.createElement("li");
      appendMaintainedText(item, rule.fact_tokens?.[key]?.[index], fact);
      list.append(item);
    }
    group.append(heading, list);
    container.append(group);
  }

  const specialists = facts.specialists?.anyOfSkills;
  if (Array.isArray(specialists) && specialists.length) {
    const group = document.createElement("div");
    group.className = "detail-fact-group";
    const heading = document.createElement("h4");
    heading.className = "detail-fact-heading";
    heading.textContent = "Qualifying Skills";
    const list = document.createElement("ul");
    list.className = "detail-list";
    for (const [index, identifier] of specialists.entries()) {
      const item = document.createElement("li");
      appendMaintainedText(item, rule.fact_tokens?.specialists?.[index], identifier);
      list.append(item);
    }
    group.append(heading, list);
    container.append(group);
  }

  container.append(...beforeRelations);
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


export function hasGameplayRuleFacts(rule) {
  return [rule, ...(rule?.supplements || [])].some((contribution) => {
    const facts = contribution?.facts || {};
    return ["requirements", "effects", "restrictions"].some(
      (key) => Array.isArray(facts[key]) && facts[key].length,
    );
  });
}

export function gameplayVariantRules(variants) {
  const result = [];
  const seen = new Set();
  for (const variant of variants || []) {
    for (const rule of variant.rules || []) {
      if (!hasGameplayRuleFacts(rule)) continue;
      const key = rule.id || rule;
      if (seen.has(key)) continue;
      seen.add(key);
      result.push(rule);
    }
  }
  return result;
}

export function levelEffectsSection(rules) {
  const rule = (rules || []).find((candidate) => (candidate.facts?.levels || []).some(
    (level) => Array.isArray(level?.effects) && level.effects.length,
  ));
  if (!rule) return null;

  const levels = rule.facts.levels
    .map((level, index) => ({ level, index }))
    .filter(({ level }) => Array.isArray(level?.effects) && level.effects.length);
  const section = document.createElement("section");
  section.className = "detail-group";
  const heading = document.createElement("h2");
  heading.className = "detail-heading";
  heading.textContent = `${rule.name} levels`;

  const table = document.createElement("table");
  table.className = "data-table--compact data-table--reference level-effects-table";
  const caption = document.createElement("caption");
  caption.className = "sr-only";
  caption.textContent = `${rule.name} level effects`;
  const head = document.createElement("thead");
  head.innerHTML = '<tr><th class="table-column--metric" scope="col">Level</th><th class="table-column--descriptor" scope="col">Effects</th></tr>';
  const body = document.createElement("tbody");

  for (const { level, index: levelIndex } of levels) {
    const row = document.createElement("tr");
    const levelCell = document.createElement("th");
    levelCell.scope = "row";
    levelCell.className = "table-column--metric";
    levelCell.textContent = String(level.level);
    const effectsCell = document.createElement("td");
    effectsCell.className = "table-column--descriptor";
    const list = document.createElement("ul");
    list.className = "detail-list level-effects-list";
    const tokenRows = rule.fact_tokens?.levels?.[levelIndex]?.effects || [];
    for (const [effectIndex, effect] of level.effects.entries()) {
      const item = document.createElement("li");
      appendMaintainedText(item, tokenRows[effectIndex], effect);
      list.append(item);
    }
    effectsCell.append(list);
    row.append(levelCell, effectsCell);
    body.append(row);
  }

  table.append(caption, head, body);
  section.append(heading, tableViewport(table));
  return section;
}

export function rulesReferenceArticle(
  rule,
  { leadingContent = [], headerContent = [], beforeRelations = [] } = {},
) {
  const article = document.createElement("article");
  article.className = "surface surface--subtle detail-section";
  const header = document.createElement("header");
  header.className = "surface-titlebar surface-titlebar--ruled rules-card-titlebar";
  const title = document.createElement("h3");
  title.textContent = rule.name;
  header.append(title);
  const badgeRow = ruleBadgeRow(rule);
  if (badgeRow) header.append(badgeRow);
  header.append(...headerContent);
  article.append(header, ...leadingContent);
  appendRuleDetails(article, rule, { includeBadges: false, beforeRelations });

  for (const supplement of rule.supplements || []) {
    const supplemental = document.createElement("div");
    supplemental.className = "rules-supplement";
    const supplementTitle = document.createElement("h4");
    supplementTitle.textContent = "Additional rules";
    supplemental.append(supplementTitle);
    appendRuleDetails(supplemental, supplement);
    article.append(supplemental);
  }
  return article;
}

export function rulesReferenceSection(rules, headingText = "Rules reference") {
  const section = document.createElement("section");
  section.className = "detail-group rules-reference";
  const heading = document.createElement("h2");
  heading.className = "detail-heading";
  heading.textContent = headingText;
  section.append(heading, ...rules.map((rule) => rulesReferenceArticle(rule)));
  return section;
}
