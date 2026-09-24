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

const relationGroupOrder = [
  {
    name: "Creates & enables",
    types: new Set([
      "applies-effects-to",
      "causes-state",
      "controller-eligible-for",
      "enables-use-of",
      "enters-state",
      "has-subtype",
      "uses-effects-of",
    ]),
  },
  {
    name: "Cancels & restricts",
    types: new Set([
      "cancels-state",
      "ignores-modifiers-from",
      "negates-effects-of",
      "overrides-effects-of",
      "reduces-modifiers-from",
      "restricts-use-of",
      "reveals-state",
    ]),
  },
  { name: "Other interactions", types: null },
];

const relationLabels = {
  "applies-effects-to": { outbound: "Effects apply to", inbound: "Affected by" },
  "controller-eligible-for": { outbound: "Can control", inbound: "Can be controlled by" },
  "cancels-state": { outbound: "Cancels state", inbound: "Cancelled by" },
  "causes-state": { outbound: "Causes state", inbound: "Caused by" },
  "enters-state": { outbound: "Enters state", inbound: "Entered by" },
  "enables-use-of": { outbound: "Enables use of", inbound: "Enabled by" },
  "has-subtype": { outbound: "Includes subtype", inbound: "Subtype of" },
  "ignores-modifiers-from": {
    outbound: "Ignores MODs from",
    inbound: "MODs ignored by",
  },
  "imposes-modifiers-on": {
    outbound: "Imposes MODs on",
    inbound: "MODs imposed by",
  },
  "negates-effects-of": { outbound: "Negates", inbound: "Negated by" },
  "overrides-effects-of": { outbound: "Overrides", inbound: "Overridden by" },
  "modifies-rolls-for": {
    outbound: "Modifies rolls for",
    inbound: "Rolls modified by",
  },
  "reveals-state": { outbound: "Reveals state", inbound: "Revealed by" },
  "reduces-modifiers-from": {
    outbound: "Reduces MODs from",
    inbound: "MODs reduced by",
  },
  "restricts-use-of": { outbound: "Restricts use of", inbound: "Use restricted by" },
  "uses-effects-of": { outbound: "Uses effects of", inbound: "Effects used by" },
};

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
  const labels = relationLabels[relation.type];
  const label = labels?.[relation.direction];
  const record = relation.record;
  if (!label || !record?.name) return null;
  return { relation, label, record };
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

function relationGroup(relation) {
  return relationGroupOrder.find((group) => group.types?.has(relation.type))
    || relationGroupOrder.at(-1);
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

  for (const relationGroupDefinition of relationGroupOrder) {
    const grouped = relations
      .filter((presentation) => relationGroup(presentation.relation) === relationGroupDefinition)
      .sort((left, right) => (
        left.record.name.localeCompare(right.record.name, undefined, { numeric: true })
        || left.label.localeCompare(right.label)
      ));
    if (!grouped.length) continue;

    const relationGroupElement = document.createElement("div");
    relationGroupElement.className = "rules-relation-group";
    const groupHeading = document.createElement("h5");
    groupHeading.className = "rules-relation-group-heading";
    groupHeading.textContent = relationGroupDefinition.name;
    const list = document.createElement("ul");
    list.className = "detail-list";
    list.append(...grouped.map(relationNode));
    relationGroupElement.append(groupHeading, list);
    group.append(relationGroupElement);
  }
  container.append(group);
}

function appendRuleDetails(container, rule) {
  const applicability = applicabilityText(rule);
  if (applicability) {
    const context = document.createElement("p");
    context.className = "detail-source";
    context.textContent = applicability;
    container.append(context);
  }

  const summary = document.createElement("p");
  summary.className = "detail-copy";
  summary.textContent = rule.summary;
  container.append(summary);

  const skillTypes = rule.skill_types || (rule.skill_type ? [rule.skill_type] : []);
  const labels = (rule.labels || []).map((label) => label.name);
  if (skillTypes.length || labels.length) {
    const badgeRow = document.createElement("p");
    badgeRow.className = "detail-badges";
    for (const skillType of skillTypes) {
      if (skillType?.category_name || skillType?.name) {
        badgeRow.append(
          skillCategoryBadge(skillType, skillType.category_name || skillType.name)
        );
      }
    }
    for (const label of labels) {
      const element = document.createElement("span");
      element.className = "badge";
      element.textContent = label;
      badgeRow.append(element);
    }
    container.append(badgeRow);
  }

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
    const title = document.createElement("h3");
    title.textContent = rule.name;
    article.append(title);
    appendRuleDetails(article, rule);

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
