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
