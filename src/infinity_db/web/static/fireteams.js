import { getFireteamArmies, getFireteamChart } from "./api.js";
import { appendMaintainedText } from "./maintained-text.js";
import { fireteamsIncludeWildcards } from "./preferences.js";
import { readShareState, writeShareState } from "./share-state.js";
import { createPanelSwitcher, tableViewport } from "./view-components.js";

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
  landing: byId("fireteam-landing"),
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
let currentReference = null;
let requestController = null;
const pageController = new AbortController();

const show = createPanelSwitcher({
  container: elements.results,
  loading: elements.loading,
  panels: [
    elements.loading,
    elements.error,
    elements.empty,
    elements.landing,
    elements.content,
  ],
});

function armyValue(army) {
  return army.public_slug || army.slug || String(army.id);
}

function currentArmyValue() {
  return readShareState("fireteams").params.get("army") || "";
}

function writeArmyLocation(value, { replace = false } = {}) {
  writeShareState("fireteams", value ? { army: value } : {}, { replace });
}

function populateArmies(items) {
  armies = items;
  elements.army.replaceChildren(new Option("Select an Army…", ""));
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
  const requested = currentArmyValue();
  if (!requested || !armies.length) {
    elements.army.value = "";
    return "";
  }
  const selected = armies.find((army) => (
    armyValue(army) === requested || String(army.id) === requested
  ));
  if (!selected) {
    elements.army.value = "";
    writeArmyLocation("", { replace: true });
    return "";
  }
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
  article.className = "surface surface--subtle surface--raised fireteam-card";
  const header = document.createElement("header");
  header.className = "surface-titlebar surface-titlebar--ruled fireteam-card-titlebar";
  const title = document.createElement("h3");
  title.textContent = team.name || `Fireteam ${team.id}`;
  const typeBadges = document.createElement("div");
  typeBadges.className = "detail-badges fireteam-card-types";
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

  const table = document.createElement("table");
  table.className = "data-table--reference";
  const caption = document.createElement("caption");
  caption.className = "sr-only";
  caption.textContent = `${team.name || "Fireteam"} members`;
  const head = document.createElement("thead");
  const headRow = document.createElement("tr");
  for (const [heading, developerOnly, columnClass] of [
    ["Member", false, "table-column--primary"],
    ["Requirements", false, "table-column--descriptor fireteam-member-requirements"],
    ["FTO Profiles", true, "table-column--descriptor"],
    ["Notes", true, "table-column--descriptor"],
  ]) {
    const cell = document.createElement("th");
    cell.scope = "col";
    cell.textContent = heading;
    cell.className = columnClass;
    if (developerOnly) cell.classList.add("developer-only");
    headRow.append(cell);
  }
  head.append(headRow);
  const body = document.createElement("tbody");
  const appendMemberRow = (member, { wildcard = false } = {}) => {
    const row = document.createElement("tr");
    const name = document.createElement("th");
    name.scope = "row";
    name.className = "table-column--primary";
    name.append(memberName(member));
    if (wildcard) name.append(badge("Wildcard"));
    const requirements = document.createElement("td");
    requirements.className = "table-column--descriptor fireteam-member-requirements";
    appendMemberDetails(requirements, member);
    const fto = document.createElement("td");
    fto.className = "developer-only table-column--descriptor";
    appendFtoDetails(fto, member);
    const note = document.createElement("td");
    note.className = "developer-only table-column--descriptor";
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
  article.append(tableViewport(table, "fireteam-member-table"));
  return article;
}

function fireteamLimitBadge(limit) {
  const kind = String(limit.limit_kind || "maximum");
  let label;
  if (kind === "unavailable") label = `${limit.type}: unavailable`;
  else if (kind === "unlimited") label = `${limit.type}: unlimited`;
  else label = `${limit.type}: max ${limit.max_count}`;
  const element = badge(label);
  if (kind === "unavailable") element.classList.add("developer-only");
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
  if (!reference?.general?.facts || !reference?.levels?.facts) return false;

  const general = reference.general;
  const levels = reference.levels;
  const generalFacts = general.facts;
  const levelFacts = levels.facts;
  const fragment = document.createDocumentFragment();

  const summary = document.createElement("p");
  summary.className = "detail-copy";
  appendMaintainedText(summary, general.summary_tokens, general.summary);
  fragment.append(summary);

  const typeBadges = document.createElement("div");
  typeBadges.className = "detail-badges fireteam-reference-types";
  for (const type of generalFacts.types || []) {
    typeBadges.append(badge(fireteamTypeLabel(type)));
  }
  fragment.append(typeBadges);

  const rules = document.createElement("ul");
  rules.className = "fireteam-reference-rules";
  for (const [index, rule] of (generalFacts.rules || []).entries()) {
    const item = document.createElement("li");
    appendMaintainedText(item, general.fact_tokens?.rules?.[index], rule);
    rules.append(item);
  }
  fragment.append(rules);

  const levelHeading = document.createElement("h4");
  levelHeading.textContent = levels.name;
  const basis = document.createElement("p");
  basis.className = "detail-copy";
  appendMaintainedText(basis, levels.fact_tokens?.basis, levelFacts.basis);
  const table = document.createElement("table");
  table.className = "data-table--reference";
  const caption = document.createElement("caption");
  caption.className = "sr-only";
  caption.textContent = "Fireteam Level bonuses";
  const head = document.createElement("thead");
  const headRow = document.createElement("tr");
  for (const [heading, columnClass] of [
    ["Level", "table-column--metric"],
    ["Requirement", "table-column--descriptor"],
    ["Bonuses", "table-column--descriptor"],
  ]) {
    const cell = document.createElement("th");
    cell.scope = "col";
    cell.className = columnClass;
    cell.textContent = heading;
    headRow.append(cell);
  }
  head.append(headRow);
  const body = document.createElement("tbody");
  for (const level of levelFacts.levels || []) {
    const row = document.createElement("tr");
    const levelCell = document.createElement("th");
    levelCell.scope = "row";
    levelCell.className = "table-column--metric";
    levelCell.textContent = String(level.level);
    const requirement = document.createElement("td");
    requirement.className = "table-column--descriptor";
    appendMaintainedText(
      requirement,
      levels.fact_tokens?.levels?.[body.children.length]?.requirement,
      level.requirement
    );
    const bonuses = document.createElement("td");
    bonuses.className = "table-column--descriptor";
    for (const [bonusIndex, bonus] of (level.bonuses || []).entries()) {
      if (bonusIndex) bonuses.append("; ");
      appendMaintainedText(
        bonuses,
        levels.fact_tokens?.levels?.[body.children.length]?.bonuses?.[bonusIndex],
        bonus
      );
    }
    row.append(levelCell, requirement, bonuses);
    body.append(row);
  }
  table.append(caption, head, body);
  const cumulative = document.createElement("p");
  cumulative.className = "fireteam-reference-note";
  if (levelFacts.cumulative) cumulative.textContent = "Fireteam Level bonuses are cumulative.";
  fragment.append(
    levelHeading,
    basis,
    tableViewport(table, "fireteam-reference-table"),
    cumulative,
  );

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
      appendMaintainedText(
        meaning,
        general.fact_tokens?.terminology?.[terminologyList.children.length],
        term.meaning
      );
      item.append(title, meaning);
      terminologyList.append(item);
    }
    fragment.append(terminologyHeading, terminologyList);
  }

  appendReferenceSources(fragment, [general, levels]);
  elements.referenceContent.append(fragment);
  return true;
}

function renderOverview() {
  currentChart = null;
  elements.count.textContent = `${number.format(armies.length)} armies`;
  if (!renderReference(currentReference)) return show(elements.empty);
  show(elements.landing);
}

function renderChart(chart) {
  currentChart = chart;
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
  if (!value) return renderOverview();
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
    const payload = await getFireteamArmies(pageController.signal);
    populateArmies(payload.items || []);
    currentReference = payload.reference || null;
    if (!armies.length) {
      elements.count.textContent = "0 armies";
      return show(elements.empty);
    }
    const selection = normalizeSelection();
    if (selection) await loadChart(selection);
    else renderOverview();
  } catch (error) {
    if (error.name === "AbortError") return;
    elements.errorMessage.textContent = error.message || "Could not load Fireteam Armies.";
    show(elements.error);
  }
}

document.addEventListener("infinity:beforenavigation", () => {
  pageController.abort();
  requestController?.abort();
}, { once: true });
elements.army.addEventListener("change", () => {
  const value = elements.army.value;
  writeArmyLocation(value);
  if (value) loadChart(value);
  else renderOverview();
}, { signal: pageController.signal });
window.addEventListener(
  "popstate",
  () => loadChart(normalizeSelection()),
  { signal: pageController.signal },
);
window.addEventListener("fireteamswildcardschange", () => {
  if (currentChart) renderChart(currentChart);
}, { signal: pageController.signal });

initialize();
