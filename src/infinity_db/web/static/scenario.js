import { getScenario, getScenarios } from "./api.js";
import { appendMaintainedText } from "./maintained-text.js";
import { rulesCitationNode, rulesReferenceArticle } from "./rules-reference.js";
import { readShareState, writeShareState } from "./share-state.js";
import { createPanelSwitcher } from "./view-components.js";

const byId = (id) => document.getElementById(id);
const elements = {
  name: byId("scenario-name"),
  description: byId("scenario-description"),
  config: byId("scenario-config"),
  points: byId("scenario-army-points"),
  state: byId("scenario-state"),
  status: byId("scenario-status"),
  error: byId("scenario-error"),
  errorMessage: byId("scenario-error-message"),
  choice: byId("scenario-choice"),
  content: byId("scenario-content"),
};
const DEFAULT_ARMY_POINTS = 300;
const summaryController = new AbortController();
let detailController = null;
let summary = null;
const slug = decodeURIComponent(window.location.pathname.split("/").filter(Boolean).at(-1) || "");
const show = createPanelSwitcher({
  container: elements.state,
  loading: elements.status,
  panels: [elements.status, elements.error, elements.choice, elements.content],
});

function selectedArmyPointsFromUrl() {
  const { params, source } = readShareState("scenario");
  const raw = params.get("army_points");
  if (!raw || !/^\d+$/.test(raw)) return { points: null, source };
  return { points: Number(raw), source };
}

function setSelectedArmyPoints(value, { replace = true } = {}) {
  writeShareState(
    "scenario",
    value ? { army_points: String(value) } : {},
    { replace },
  );
}

function updateDocumentIdentity(item) {
  elements.name.replaceChildren(document.createTextNode(item.name), Object.assign(document.createElement("span"), { textContent: "." }));
  elements.description.replaceChildren();
  appendMaintainedText(elements.description, item.description_tokens, item.description);
  document.title = `${item.name} · Scenarios · InfinityDB`;
}

function populatePoints(item) {
  for (const points of item.supported_army_points || []) {
    const option = document.createElement("option");
    option.value = String(points);
    option.textContent = `${points} Army Points`;
    elements.points.append(option);
  }
  elements.config.hidden = false;
}

function section(title, ...children) {
  const wrapper = document.createElement("section");
  wrapper.className = "detail-group scenario-section";
  const heading = document.createElement("h2");
  heading.className = "detail-heading";
  heading.textContent = title;
  wrapper.append(heading, ...children);
  return wrapper;
}

function fact(label, value) {
  const item = document.createElement("div");
  item.className = "scenario-fact";
  const term = document.createElement("dt");
  term.textContent = label;
  const detail = document.createElement("dd");
  detail.textContent = value;
  item.append(term, detail);
  return item;
}

function setupCard(item) {
  const card = document.createElement("section");
  card.className = "surface surface--subtle scenario-setup-card";
  const heading = document.createElement("h3");
  heading.className = "surface-titlebar surface-titlebar--subtle surface-titlebar--ruled";
  heading.textContent = "Forces and table";
  const facts = document.createElement("dl");
  facts.className = "scenario-facts";
  const gameSize = item.setup?.game_size || {};
  const geometry = item.placement?.geometry || {};
  const table = geometry.table || {};
  facts.append(
    fact("Army Points", String(item.selected_army_points)),
    fact("SWC", String(gameSize.swc ?? "—")),
    fact("Table", `${table.width ?? "—"} × ${table.height ?? "—"} in`),
  );
  if (gameSize.minimumVictoryPoints != null) {
    facts.append(fact("Minimum Victory Points", String(gameSize.minimumVictoryPoints)));
  }
  card.append(heading, facts);
  return card;
}

function mapCard(item) {
  const figure = document.createElement("figure");
  figure.className = "surface surface--subtle scenario-map-card";
  const heading = document.createElement("figcaption");
  heading.className = "surface-titlebar surface-titlebar--subtle surface-titlebar--ruled";
  heading.textContent = "Deployment and scenario map";
  const image = document.createElement("img");
  image.className = "scenario-map";
  image.alt = `${item.name} deployment and scenario map for ${item.selected_army_points} Army Points`;
  const params = new URLSearchParams({ army_points: String(item.selected_army_points) });
  image.src = `/api/scenarios/${encodeURIComponent(item.slug)}/map.svg?${params}`;
  figure.append(heading, image);
  // <img> SVGs cannot inherit theme variables. Inline the same-origin generated
  // SVG, as we do for the themed logo, keeping the image as a network fallback.
  fetch(image.src)
    .then((response) => {
      if (!response.ok) throw new Error(`Scenario map request failed (${response.status}).`);
      return response.text();
    })
    .then((markup) => {
      if (!image.isConnected) return;
      const svg = new DOMParser().parseFromString(markup, "image/svg+xml").documentElement;
      if (svg.namespaceURI !== "http://www.w3.org/2000/svg" || svg.localName !== "svg") return;
      // External application CSS owns the inline map; its embedded <style>
      // is for standalone SVG responses and is blocked by our document CSP.
      svg.querySelector("style")?.remove();
      svg.setAttribute("class", "scenario-map");
      svg.setAttribute("aria-label", image.alt);
      image.replaceWith(document.importNode(svg, true));
    })
    .catch(() => { /* Keep the standalone SVG image fallback. */ });
  return figure;
}

const metricLabels = {
  "enemy-army-points-killed": "enemy Army Points killed",
  "surviving-victory-points": "surviving Victory Points",
  "surviving-specialist-troops": "surviving Specialist Troops",
  "enemy-specialist-troops-killed": "enemy Specialist Troops killed",
  "enemy-lieutenants-killed": "enemy Lieutenants killed",
};

function conditionNode(condition) {
  const node = document.createElement("span");
  const kind = condition?.kind;
  if (kind === "reviewed-prose") {
    appendMaintainedText(node, condition.text_tokens, condition.text);
    return node;
  }
  if (kind === "numeric-range") {
    const metric = metricLabels[condition.metric] || condition.metric;
    const range = condition.maximum == null
      ? `${condition.minimum}+`
      : `${condition.minimum}–${condition.maximum}`;
    node.textContent = `${range} ${metric}`;
    return node;
  }
  if (kind === "dominated-region-comparison") {
    node.textContent = condition.comparison === "greater"
      ? "Dominate more Quadrants than the opponent"
      : `Dominate the same number of Quadrants as the opponent${condition.minimum ? ` (at least ${condition.minimum})` : ""}`;
    return node;
  }
  if (kind === "element-status-count") {
    const count = condition.elementIds?.length || 0;
    node.textContent = `For each ${condition.status} scenario element${count ? `, up to ${count}` : ""}`;
    return node;
  }
  if (kind === "element-status-comparison") {
    node.textContent = condition.comparison === "all"
      ? `Control all ${condition.elementIds?.length || ""} scenario elements`.replace("  ", " ")
      : `Control more ${condition.status} scenario elements than the opponent`;
    return node;
  }
  if (kind === "metric-comparison") {
    node.textContent = `Have more ${metricLabels[condition.metric] || condition.metric} than the opponent`;
    return node;
  }
  node.textContent = "Meet the objective condition";
  return node;
}

function objectiveCard(objective) {
  const card = document.createElement("article");
  card.className = "surface surface--subtle scenario-objective";
  const header = document.createElement("header");
  header.className = "surface-titlebar surface-titlebar--subtle surface-titlebar--ruled";
  const title = document.createElement("h3");
  appendMaintainedText(title, objective.name_tokens, objective.name);
  const cap = document.createElement("span");
  cap.className = "detail-badge";
  cap.textContent = `${objective.maximumPoints} OP max`;
  header.append(title, cap);
  const timing = document.createElement("p");
  timing.className = "scenario-objective-timing";
  const timingLabel = objective.timing === "end-of-round" ? "End of each Game Round" : "End of game";
  timing.textContent = objective.maximumPointsPerRound
    ? `${timingLabel} · ${objective.maximumPointsPerRound} OP max per round`
    : timingLabel;
  const list = document.createElement("ul");
  list.className = "scenario-awards detail-list";
  for (const award of objective.awards || []) {
    const row = document.createElement("li");
    const points = document.createElement("strong");
    points.textContent = `${award.objectivePoints} OP`;
    row.append(points, document.createTextNode(" — "), conditionNode(award.condition));
    list.append(row);
  }
  card.append(header, timing, list);
  return card;
}

function objectivesSection(item) {
  const grid = document.createElement("div");
  grid.className = "scenario-objective-grid";
  grid.append(...(item.objectives || []).map(objectiveCard));
  return section("Objectives", grid);
}

function rulesSection(item) {
  const cards = [];
  for (const inclusion of item.special_rules || []) {
    if (inclusion.rule) cards.push(rulesReferenceArticle(inclusion.rule, { includeApplicability: false }));
  }
  for (const skill of item.skills || []) cards.push(rulesReferenceArticle(skill, { includeApplicability: false }));
  if (!cards.length) return null;
  const group = document.createElement("div");
  group.className = "scenario-rules rules-card-stack";
  group.append(...cards);
  return section("Scenario rules and Skills", group);
}

function endConditionText(entry) {
  const condition = entry.condition || {};
  if (condition.kind === "round-limit") return `The scenario ends after Game Round ${condition.rounds}.`;
  if (condition.text) return condition.text;
  return "Scenario end condition.";
}

function endSection(item) {
  const list = document.createElement("ul");
  list.className = "surface surface--subtle scenario-end-list detail-list";
  for (const entry of item.end_conditions || []) {
    const row = document.createElement("li");
    if (entry.condition?.text) appendMaintainedText(row, entry.condition.text_tokens, entry.condition.text);
    else row.textContent = endConditionText(entry);
    list.append(row);
  }
  return section("End of the scenario", list);
}

function issuesSection(item) {
  if (!(item.source_issues || []).length) return null;
  const cards = item.source_issues.map((issue) => {
    const card = document.createElement("article");
    card.className = "surface surface--highlighted scenario-source-issue";
    const heading = document.createElement("div");
    heading.className = "scenario-source-issue-heading";
    const title = document.createElement("h3");
    const reviewed = issue.status === "reviewed-resolution";
    title.textContent = reviewed ? "Reviewed interpretation" : "Needs verification";
    const badge = document.createElement("span");
    badge.className = "detail-badge";
    badge.textContent = reviewed ? "reviewed" : "uncertain";
    heading.append(title, badge);
    const copy = document.createElement("p");
    copy.className = "detail-copy";
    appendMaintainedText(copy, issue.description_tokens, issue.description);
    card.append(heading, copy);
    return card;
  });
  return section("Source notes", ...cards);
}

function sourcesSection(item) {
  if (!(item.citations || []).length) return null;
  const citations = document.createElement("p");
  citations.className = "surface surface--subtle scenario-citations detail-source";
  for (const [index, citation] of item.citations.entries()) {
    if (index) citations.append(" · ");
    citations.append(rulesCitationNode(citation));
  }
  return section("Sources", citations);
}

function provenanceSection(item) {
  const publication = item.publication || {};
  const card = document.createElement("section");
  card.className = "surface surface--subtle scenario-provenance developer-only";
  const heading = document.createElement("h3");
  heading.className = "surface-titlebar surface-titlebar--subtle surface-titlebar--ruled";
  heading.textContent = "Publication";
  const facts = document.createElement("dl");
  facts.className = "scenario-facts";
  facts.append(
    fact("Collection", publication.collection_title || publication.collection_id || "—"),
    fact("Revision", publication.revision || "—"),
    fact("Source", publication.source_title || publication.source_collection_id || "—"),
    fact("Content SHA-256", publication.content_sha256 || "—"),
  );
  card.append(heading, facts);
  const wrapper = section("Developer details", card);
  wrapper.classList.add("developer-only");
  return wrapper;
}

function render(item) {
  updateDocumentIdentity(item);
  const placement = document.createElement("div");
  placement.className = "scenario-setup-grid";
  placement.append(setupCard(item), mapCard(item));
  const sections = [
    section("Setup", placement),
    objectivesSection(item),
    rulesSection(item),
    endSection(item),
    issuesSection(item),
    sourcesSection(item),
    provenanceSection(item),
  ].filter(Boolean);
  elements.content.replaceChildren(...sections);
  show(elements.content);
}

async function loadDetail(points) {
  detailController?.abort();
  detailController = new AbortController();
  elements.status.textContent = `Loading ${points} Army Point setup.`;
  show(elements.status);
  try {
    const item = await getScenario(slug, points, detailController.signal);
    render(item);
  } catch (error) {
    if (error.name === "AbortError") return;
    elements.errorMessage.textContent = error.message || "Could not load this scenario.";
    show(elements.error);
  }
}

function choose(points) {
  if (!points) {
    setSelectedArmyPoints(null);
    show(elements.choice);
    return;
  }
  const numeric = Number(points);
  if (!summary.supported_army_points.includes(numeric)) {
    elements.errorMessage.textContent = `${numeric} Army Points is not supported by this scenario.`;
    show(elements.error);
    return;
  }
  setSelectedArmyPoints(numeric);
  loadDetail(numeric);
}

async function initialize() {
  show(elements.status);
  try {
    const payload = await getScenarios(summaryController.signal);
    summary = (payload.items || []).find((item) => item.slug === slug);
    if (!summary) {
      elements.errorMessage.textContent = "Scenario not found.";
      show(elements.error);
      return;
    }
    updateDocumentIdentity(summary);
    populatePoints(summary);
    const { points: requested, source } = selectedArmyPointsFromUrl();
    if (requested != null && summary.supported_army_points.includes(requested)) {
      elements.points.value = String(requested);
      if (source !== "token") setSelectedArmyPoints(requested);
      await loadDetail(requested);
      return;
    }
    if (requested != null) {
      elements.errorMessage.textContent = `${requested} Army Points is not supported by this scenario.`;
      show(elements.error);
      return;
    }
    if (summary.supported_army_points.includes(DEFAULT_ARMY_POINTS)) {
      elements.points.value = String(DEFAULT_ARMY_POINTS);
      setSelectedArmyPoints(DEFAULT_ARMY_POINTS);
      await loadDetail(DEFAULT_ARMY_POINTS);
      return;
    }
    show(elements.choice);
  } catch (error) {
    if (error.name === "AbortError") return;
    elements.errorMessage.textContent = error.message || "Could not load this scenario.";
    show(elements.error);
  }
}

elements.points.addEventListener("change", () => choose(elements.points.value));
document.addEventListener("infinity:beforenavigation", () => {
  summaryController.abort();
  detailController?.abort();
}, { once: true });
initialize();
