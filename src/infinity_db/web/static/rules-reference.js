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

const relationLabels = {
  "controller-eligible-for": { outbound: "Can control", inbound: "Can be controlled by" },
  "enters-state": { outbound: "Enters state", inbound: "Entered by" },
  "has-subtype": { outbound: "Includes subtype", inbound: "Subtype of" },
  "ignores-modifiers-from": {
    outbound: "Ignores MODs from",
    inbound: "MODs ignored by",
  },
  "negates-effects-of": { outbound: "Negates", inbound: "Negated by" },
  "reveals-state": { outbound: "Reveals state", inbound: "Revealed by" },
  "reduces-modifiers-from": {
    outbound: "Reduces MODs from",
    inbound: "MODs reduced by",
  },
};

function relationHref(record) {
  const catalogs = { skill: "skills", equipment: "equipment", weapon: "weapons" };
  for (const link of record.army_links || []) {
    const catalog = catalogs[link.entity];
    if (!catalog || typeof link.id !== "string" || /^\d+$/.test(link.id)) continue;
    return `/${catalog}/${encodeURIComponent(link.id)}`;
  }
  if (record.kind === "trait" && typeof record.id === "string") {
    const prefix = "trait:";
    if (record.id.startsWith(prefix) && record.id.length > prefix.length) {
      return `/traits/${encodeURIComponent(record.id.slice(prefix.length))}`;
    }
  }
  return null;
}

function relationNode(relation) {
  const labels = relationLabels[relation.type];
  const label = labels?.[relation.direction];
  const record = relation.record;
  if (!label || !record?.name) return null;

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
  const items = (rule.display_relations || []).map(relationNode).filter(Boolean);
  if (!items.length) return;

  const group = document.createElement("div");
  group.className = "detail-fact-group rules-relations";
  const heading = document.createElement("h4");
  heading.className = "detail-fact-heading";
  heading.textContent = "Related rules";
  const list = document.createElement("ul");
  list.className = "detail-list";
  list.append(...items);
  group.append(heading, list);
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

  const badges = [];
  if (rule.skill_type?.name) badges.push(rule.skill_type.name);
  for (const label of rule.labels || []) badges.push(label.name);
  if (badges.length) {
    const badgeRow = document.createElement("p");
    badgeRow.className = "detail-badges";
    for (const badge of badges) {
      const element = document.createElement("span");
      element.className = "badge";
      element.textContent = badge;
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
