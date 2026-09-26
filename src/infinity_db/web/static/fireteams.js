import { getFireteamArmies, getFireteamChart } from "./api.js";
import { fireteamsIncludeWildcards } from "./preferences.js";

const number = new Intl.NumberFormat();
const byId = (id) => document.getElementById(id);
const elements = {
  army: byId("fireteam-army"),
  count: byId("fireteam-count"),
  results: byId("fireteam-results"),
  loading: byId("fireteam-loading"),
  error: byId("fireteam-error"),
  errorMessage: byId("fireteam-error-message"),
  empty: byId("fireteam-empty"),
  content: byId("fireteam-content"),
  reference: byId("fireteam-reference"),
  referenceContent: byId("fireteam-reference-content"),
  chartName: byId("fireteam-chart-name"),
  description: byId("fireteam-chart-description"),
  limits: byId("fireteam-chart-limits"),
  source: byId("fireteam-chart-source"),
  sourceDetail: byId("fireteam-chart-source-detail"),
  list: byId("fireteam-list"),
};

let armies = [];
let currentChart = null;
let requestController = null;

function show(panel) {
  for (const element of [elements.loading, elements.error, elements.empty, elements.content]) {
    element.hidden = element !== panel;
  }
  elements.results.setAttribute("aria-busy", String(panel === elements.loading));
}

function armyValue(army) {
  return army.public_slug || army.slug || String(army.id);
}

function currentArmyValue() {
  return new URLSearchParams(window.location.search).get("army") || "";
}

function writeArmyLocation(value, { replace = false } = {}) {
  const url = new URL(window.location.href);
  if (value) url.searchParams.set("army", value);
  else url.searchParams.delete("army");
  const method = replace ? "replaceState" : "pushState";
  history[method](null, "", `${url.pathname}${url.search}`);
}

function populateArmies(items) {
  armies = items;
  elements.army.replaceChildren();
  const shownGroups = new Set();
  for (const army of armies) {
    if (army.role === "non_aligned" && army.group_id && !shownGroups.has(army.group_id)) {
      const label = new Option(army.group_name || `Group ${army.group_id}`, "");
      label.disabled = true;
      elements.army.add(label);
      shownGroups.add(army.group_id);
    }
    const indentLevel = army.role === "reinforcement"
      ? 2
      : Number(army.role === "sectorial" || army.role === "non_aligned");
    const indent = "\u00a0\u00a0\u00a0\u00a0".repeat(indentLevel);
    const count = Number(army.fireteam_count || 0);
    elements.army.add(new Option(
      `${indent}${army.name}${count ? ` (${number.format(count)})` : ""}`,
      armyValue(army),
    ));
  }
  elements.army.disabled = armies.length === 0;
}

function normalizeSelection() {
  if (!armies.length) return "";
  const requested = currentArmyValue();
  const selected = armies.find((army) => (
    armyValue(army) === requested || String(army.id) === requested
  )) || armies[0];
  const value = armyValue(selected);
  elements.army.value = value;
  if (requested !== value) writeArmyLocation(value, { replace: true });
  return value;
}

function badge(text, className = "skill-category-badge skill-category-badge--unclassified") {
  const element = document.createElement("span");
  element.className = className;
  element.textContent = text;
  return element;
}

function memberRequirement(member) {
  const parts = [];
  if (member.required) parts.push("Required choice");
  const min = member.min_count;
  const max = member.max_count;
  if (min != null && max != null && min === max) parts.push(`Exactly ${min}`);
  else {
    if (min != null) parts.push(`Min ${min}`);
    if (max != null) parts.push(`Max ${max}`);
  }
  return parts;
}

function memberName(member) {
  if (!member.unit) return document.createTextNode(member.name || "Unnamed member");
  const link = document.createElement("a");
  link.href = `/units/${member.unit.slug || member.unit.id}`;
  link.textContent = member.name || member.unit.name;
  return link;
}

function appendMemberDetails(cell, member) {
  const requirements = memberRequirement(member);
  const labels = member.equivalence_labels || [];
  if (requirements.length) {
    const group = document.createElement("div");
    group.className = "detail-badges";
    for (const requirement of requirements) group.append(badge(requirement));
    cell.append(group);
  }
  if (labels.length) {
    const countsAs = document.createElement("span");
    countsAs.className = "fireteam-member-note";
    countsAs.textContent = `Counts as: ${labels.join(", ")}`;
    cell.append(countsAs);
  }
  if (!requirements.length && !labels.length) cell.textContent = "—";
}

function appendFtoDetails(cell, member) {
  const loadouts = member.loadouts || [];
  if (!member.fto_marker && !loadouts.length) {
    cell.textContent = "—";
    return;
  }
  if (member.fto_marker) {
    const marker = member.fto_marker === "generic" ? "FTO" : `FTO-${member.fto_marker}`;
    cell.append(badge(marker));
  }
  if (loadouts.length) {
    const list = document.createElement("ul");
    list.className = "fireteam-loadout-list";
    for (const loadout of loadouts) {
      const item = document.createElement("li");
      item.textContent = loadout.name;
      list.append(item);
    }
    cell.append(list);
  }
}

function renderTeam(team) {
  const article = document.createElement("article");
  article.className = "fireteam-card";
  const header = document.createElement("header");
  header.className = "fireteam-card-header";
  const title = document.createElement("h3");
  title.textContent = team.name || `Fireteam ${team.id}`;
  const typeBadges = document.createElement("div");
  typeBadges.className = "detail-badges";
  if (team.is_wildcard) typeBadges.append(badge("Wildcard"));
  for (const type of team.types || []) typeBadges.append(badge(type));
  header.append(title, typeBadges);
  article.append(header);

  if (team.observation) {
    const observation = document.createElement("p");
    observation.className = "fireteam-observation";
    observation.textContent = team.observation;
    article.append(observation);
  }

  if (!(team.members || []).length && !(team.wildcard_members || []).length) {
    const empty = document.createElement("p");
    empty.className = "detail-copy";
    empty.textContent = "No member rows are defined for this chart entry.";
    article.append(empty);
    return article;
  }

  const tableContainer = document.createElement("div");
  tableContainer.className = "table-container fireteam-member-table";
  const table = document.createElement("table");
  const caption = document.createElement("caption");
  caption.className = "sr-only";
  caption.textContent = `${team.name || "Fireteam"} members`;
  const head = document.createElement("thead");
  const headRow = document.createElement("tr");
  for (const [heading, developerOnly] of [
    ["Member", false],
    ["Requirements", false],
    ["FTO Profiles", true],
    ["Notes", true],
  ]) {
    const cell = document.createElement("th");
    cell.scope = "col";
    cell.textContent = heading;
    if (developerOnly) cell.classList.add("developer-only");
    headRow.append(cell);
  }
  head.append(headRow);
  const body = document.createElement("tbody");
  const appendMemberRow = (member, { wildcard = false } = {}) => {
    const row = document.createElement("tr");
    const name = document.createElement("th");
    name.scope = "row";
    name.append(memberName(member));
    if (wildcard) name.append(badge("Wildcard"));
    const requirements = document.createElement("td");
    appendMemberDetails(requirements, member);
    const fto = document.createElement("td");
    fto.classList.add("developer-only");
    appendFtoDetails(fto, member);
    const note = document.createElement("td");
    note.classList.add("developer-only");
    note.textContent = member.comment || "—";
    const developer = document.createElement("span");
    developer.className = "developer-only fireteam-member-developer";
    developer.textContent = `Resolution: ${member.resolution}; source member #${member.source_member_id}`;
    note.append(developer);
    row.append(name, requirements, fto, note);
    body.append(row);
  };
  for (const member of team.members || []) appendMemberRow(member);
  for (const member of team.wildcard_members || []) appendMemberRow(member, { wildcard: true });
  table.append(caption, head, body);
  tableContainer.append(table);
  article.append(tableContainer);
  return article;
}

function fireteamLimitBadge(limit) {
  const value = Number(limit.max_count);
  let label;
  if (value === 0) label = `${limit.type}: unavailable`;
  else if (value === 256) label = `${limit.type}: unlimited`;
  else label = `${limit.type}: max ${value}`;
  const element = badge(label);
  if (value === 0) element.classList.add("developer-only");
  return element;
}

function teamsForDisplay(chart) {
  const teams = chart.teams || [];
  if (!fireteamsIncludeWildcards()) return teams;

  const wildcardTeams = teams.filter((team) => team.is_wildcard);
  if (wildcardTeams.length !== 1) return teams;

  const wildcardMembers = wildcardTeams[0].members || [];
  return teams
    .filter((team) => !team.is_wildcard)
    .map((team) => ({ ...team, wildcard_members: wildcardMembers }));
}

function fireteamTypeLabel(type) {
  const minimum = Number(type.min);
  const maximum = Number(type.max);
  return minimum === maximum
    ? `${type.type}: ${minimum}`
    : `${type.type}: ${minimum}–${maximum}`;
}

function provenanceLabel(provenance) {
  if (provenance === "historical-official") return "Historical official term";
  if (provenance === "community-historical") return "Community / historical shorthand";
  return provenance || "Context term";
}

function appendReferenceSources(container, records) {
  const sources = [];
  const seen = new Set();
  for (const record of records) {
    for (const citation of record.citations || []) {
      const sourceKey = citation.source_url || citation.source_id || "";
      const key = `${sourceKey}:${citation.page || ""}:${citation.heading || ""}`;
      if (!sourceKey || seen.has(key)) continue;
      seen.add(key);
      sources.push(citation);
    }
  }
  if (!sources.length) return;
  const heading = document.createElement("h4");
  heading.textContent = "Sources";
  const list = document.createElement("ul");
  list.className = "fireteam-reference-sources";
  for (const source of sources) {
    const item = document.createElement("li");
    const labelParts = [source.source_title || source.source_id || "Source"];
    if (source.page) labelParts.push(`p. ${source.page}`);
    if (source.heading) labelParts.push(source.heading);
    if (source.source_url) {
      const link = document.createElement("a");
      link.href = source.source_url;
      link.textContent = labelParts.join(" · ");
      item.append(link);
    } else {
      item.textContent = labelParts.join(" · ");
    }
    list.append(item);
  }
  container.append(heading, list);
}

function renderReference(reference) {
  elements.referenceContent.replaceChildren();
  if (!reference?.general?.facts || !reference?.levels?.facts) {
    elements.reference.hidden = true;
    return;
  }

  const general = reference.general;
  const levels = reference.levels;
  const generalFacts = general.facts;
  const levelFacts = levels.facts;
  const fragment = document.createDocumentFragment();

  const summary = document.createElement("p");
  summary.className = "detail-copy";
  summary.textContent = general.summary;
  fragment.append(summary);

  const typeBadges = document.createElement("div");
  typeBadges.className = "detail-badges fireteam-reference-types";
  for (const type of generalFacts.types || []) {
    typeBadges.append(badge(fireteamTypeLabel(type)));
  }
  fragment.append(typeBadges);

  const rules = document.createElement("ul");
  rules.className = "fireteam-reference-rules";
  for (const rule of generalFacts.rules || []) {
    const item = document.createElement("li");
    item.textContent = rule;
    rules.append(item);
  }
  fragment.append(rules);

  const levelHeading = document.createElement("h4");
  levelHeading.textContent = levels.name;
  const basis = document.createElement("p");
  basis.className = "detail-copy";
  basis.textContent = levelFacts.basis;
  const tableContainer = document.createElement("div");
  tableContainer.className = "table-container fireteam-reference-table";
  const table = document.createElement("table");
  const caption = document.createElement("caption");
  caption.className = "sr-only";
  caption.textContent = "Fireteam Level bonuses";
  const head = document.createElement("thead");
  const headRow = document.createElement("tr");
  for (const heading of ["Level", "Requirement", "Bonuses"]) {
    const cell = document.createElement("th");
    cell.scope = "col";
    cell.textContent = heading;
    headRow.append(cell);
  }
  head.append(headRow);
  const body = document.createElement("tbody");
  for (const level of levelFacts.levels || []) {
    const row = document.createElement("tr");
    const levelCell = document.createElement("th");
    levelCell.scope = "row";
    levelCell.textContent = String(level.level);
    const requirement = document.createElement("td");
    requirement.textContent = level.requirement;
    const bonuses = document.createElement("td");
    bonuses.textContent = (level.bonuses || []).join("; ");
    row.append(levelCell, requirement, bonuses);
    body.append(row);
  }
  table.append(caption, head, body);
  tableContainer.append(table);
  const cumulative = document.createElement("p");
  cumulative.className = "fireteam-reference-note";
  if (levelFacts.cumulative) cumulative.textContent = "Fireteam Level bonuses are cumulative.";
  fragment.append(levelHeading, basis, tableContainer, cumulative);

  const terminology = generalFacts.terminology || [];
  if (terminology.length) {
    const terminologyHeading = document.createElement("h4");
    terminologyHeading.textContent = "Terminology";
    const terminologyList = document.createElement("div");
    terminologyList.className = "fireteam-terminology";
    for (const term of terminology) {
      const item = document.createElement("div");
      item.className = "fireteam-terminology-item";
      const title = document.createElement("div");
      title.className = "fireteam-terminology-title";
      const name = document.createElement("strong");
      name.textContent = term.term;
      title.append(name, badge(provenanceLabel(term.provenance)));
      const meaning = document.createElement("p");
      meaning.textContent = term.meaning;
      item.append(title, meaning);
      terminologyList.append(item);
    }
    fragment.append(terminologyHeading, terminologyList);
  }

  appendReferenceSources(fragment, [general, levels]);
  elements.referenceContent.append(fragment);
  elements.reference.hidden = false;
}

function renderChart(chart) {
  currentChart = chart;
  renderReference(chart.reference);
  elements.chartName.textContent = chart.army.name;
  elements.description.textContent = chart.description || "";
  elements.description.hidden = !chart.description;
  elements.limits.replaceChildren();
  for (const limit of chart.limits || []) {
    elements.limits.append(fireteamLimitBadge(limit));
  }
  const sourceKind = chart.source.kind
    ? chart.source.kind.replaceAll("_", " ")
    : "Army";
  elements.source.textContent = `Authoritative ${sourceKind} chart from the current Army snapshot.`;
  const sourceDetails = [`Source Army #${chart.source.army_id}`];
  if (chart.source.file) sourceDetails.push(chart.source.file);
  if (chart.source.sha256) sourceDetails.push(chart.source.sha256);
  elements.sourceDetail.textContent = sourceDetails.join(" · ");
  const teams = teamsForDisplay(chart);
  elements.list.replaceChildren(...teams.map(renderTeam));
  elements.count.textContent = `${teams.length} chart entries`;
  show(teams.length || (chart.limits || []).length || chart.description
    ? elements.content
    : elements.empty);
}

async function loadChart(value) {
  if (!value) return show(elements.empty);
  requestController?.abort();
  requestController = new AbortController();
  show(elements.loading);
  try {
    renderChart(await getFireteamChart(value, requestController.signal));
  } catch (error) {
    if (error.name === "AbortError") return;
    elements.errorMessage.textContent = error.message || "Could not load the Fireteam chart.";
    show(elements.error);
  }
}

async function initialize() {
  show(elements.loading);
  try {
    const payload = await getFireteamArmies();
    populateArmies(payload.items || []);
    if (!armies.length) {
      elements.count.textContent = "0 armies";
      return show(elements.empty);
    }
    await loadChart(normalizeSelection());
  } catch (error) {
    elements.errorMessage.textContent = error.message || "Could not load Fireteam Armies.";
    show(elements.error);
  }
}

elements.army.addEventListener("change", () => {
  const value = elements.army.value;
  writeArmyLocation(value);
  loadChart(value);
});
window.addEventListener("popstate", () => loadChart(normalizeSelection()));
window.addEventListener("fireteamswildcardschange", () => {
  if (currentChart) renderChart(currentChart);
});

initialize();
