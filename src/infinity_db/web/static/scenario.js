import { getScenario, getScenarios, getSeasonPolicies } from "./api.js";
import { distanceUnit } from "./preferences.js";
import { appendMaintainedText } from "./maintained-text.js";
import { rulesCitationNode, rulesReferenceArticle } from "./rules-reference.js";
import { faqRulingsSection, fetchReviewedFaqRulings } from "./faq-rulings.js";
import { readShareState, writeShareState } from "./share-state.js";
import { collectionLoadMessage, createPanelSwitcher } from "./view-components.js";

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
const pageController = new AbortController();
const summaryController = new AbortController();
let detailController = null;
let summary = null;
let selectedPlayContext = "";
const slug = decodeURIComponent(window.location.pathname.split("/").filter(Boolean).at(-1) || "");
const initialShare = readShareState("scenario");
const selectedPublication = {
  collection: initialShare.params.get("collection") || "",
  revision: initialShare.params.get("revision") || "",
};
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
    {
      ...(value ? { army_points: String(value) } : {}),
      ...(selectedPublication.collection ? { collection: selectedPublication.collection } : {}),
      ...(selectedPublication.revision ? { revision: selectedPublication.revision } : {}),
    },
    { replace },
  );
}

function updateDocumentIdentity(item) {
  elements.name.replaceChildren(document.createTextNode(item.name), Object.assign(document.createElement("span"), { textContent: "." }));
  elements.description.replaceChildren();
  if (item.publication?.collection_id && item.publication.collection_id !== "n5-core") {
    const edition = document.createElement("strong");
    edition.textContent = `${item.publication.collection_title} · v${item.publication.revision}`;
    elements.description.append(edition, " — ");
  }
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

// Match the shared Infinity rules distance convention, not physical marker mm.
function scenarioDistance(inches) {
  const value = distanceUnit() === "cm" ? Number((inches * 2.5).toFixed(2)) : inches;
  return distanceUnit() === "cm" ? `${value} cm` : `${value}″`;
}

function refreshScenarioDistances() {
  const table = elements.content.querySelector(".scenario-table-size");
  if (table) {
    const width = Number(table.dataset.widthInches);
    const height = Number(table.dataset.heightInches);
    table.textContent = `${scenarioDistance(width)} × ${scenarioDistance(height)}`;
  }
  const image = elements.content.querySelector("img.scenario-map");
  if (!image) return;
  const url = new URL(image.src);
  url.searchParams.set("distance_unit", distanceUnit());
  url.searchParams.set("theme", document.documentElement.dataset.theme === "dark" ? "dark" : "light");
  if (image.src !== url.href) image.src = url.href;
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
  const tableFact = fact("Table", "—");
  const swcFact = fact("SWC", String(gameSize.swc ?? "—"));
  const swcIssue = (item.source_issues || []).find(
    (issue) => issue.status === "needs-verification"
      && issue.gameSizeField === "swc"
      && (issue.armyPoints || []).includes(item.selected_army_points),
  );
  if (swcIssue) {
    swcFact.classList.add("scenario-fact--source-conflict");
    const link = document.createElement("a");
    link.className = "scenario-swc-source-conflict";
    link.href = `#scenario-source-issue-${swcIssue.id}`;
    link.textContent = "Official sources disagree — see source note";
    swcFact.querySelector("dd")?.append(link);
  }
  facts.append(
    fact("Army Points", String(item.selected_army_points)),
    swcFact,
    tableFact,
  );
  if (gameSize.minimumVictoryPoints != null) {
    facts.append(fact("Minimum Victory Points", String(gameSize.minimumVictoryPoints)));
  }
  // Table dimensions are derived from canonical inches, not marker footprint metadata.
  const tableValue = tableFact.querySelector("dd");
  if (tableValue && Number.isFinite(table.width) && Number.isFinite(table.height)) {
    tableValue.className = "scenario-table-size";
    tableValue.dataset.widthInches = String(table.width);
    tableValue.dataset.heightInches = String(table.height);
    tableValue.textContent = `${scenarioDistance(table.width)} × ${scenarioDistance(table.height)}`;
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
  const params = new URLSearchParams({
    army_points: String(item.selected_army_points), distance_unit: distanceUnit(),
    theme: document.documentElement.dataset.theme === "dark" ? "dark" : "light",
  });
  if (selectedPublication.collection) params.set("collection", selectedPublication.collection);
  if (selectedPublication.revision) params.set("revision", selectedPublication.revision);
  image.src = `/api/scenarios/${encodeURIComponent(item.slug)}/map.svg?${params}`;
  figure.append(heading, image);
  if (item.slug === "domination" && item.publication?.collection_id === "n5-core") {
    const note = document.createElement("p");
    note.className = "scenario-map-placement-note";
    note.append("Dashed measurements locate each Console center from the nearest table edges. Shaded Quadrants are scoring areas, not marker footprints.");
    const citation = (item.citations || []).find((entry) => entry.page === 152);
    if (citation) {
      note.append(" · ");
      note.append(rulesCitationNode(citation));
    }
    figure.append(note);
  }
  const markers = item.placement?.marker_dimensions || [];
  if (markers.length) {
    const dimensions = document.createElement("div");
    dimensions.className = "scenario-marker-dimensions";
    const title = document.createElement("h3");
    title.textContent = "Physical marker sizes";
    const list = document.createElement("ul");
    list.className = "detail-list";
    for (const marker of markers) {
      const row = document.createElement("li");
      row.textContent = `${marker.count} × ${marker.name} — ${marker.diameter_mm} mm diameter`;
      list.append(row);
    }
    const note = document.createElement("p");
    note.className = "detail-source";
    note.append("Physical token diameter, not scoring area or map scale · ");
    // One shared source specifies the available Core marker types.
    note.append(rulesCitationNode(markers[0].citation));
    dimensions.append(title, list, note);
    figure.append(dimensions);
  }
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
    const regions = condition.elementIds || [];
    if (regions.length === 1 && regions[0].startsWith("sector-")) {
      node.textContent = "Dominate this Sector";
    } else {
      const label = regions.every((id) => id.startsWith("quadrant-"))
        ? "Quadrants" : "scoring regions";
      node.textContent = condition.comparison === "greater"
        ? `Dominate more ${label} than the opponent`
        : `Dominate the same number of ${label} as the opponent${condition.minimum ? ` (at least ${condition.minimum})` : ""}`;
    }
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

function inlineScenarioRuleArticle(inclusion) {
  const article = document.createElement("article");
  article.className = "surface surface--subtle detail-section scenario-inline-rule";
  const header = document.createElement("header");
  header.className = "surface-titlebar surface-titlebar--ruled rules-card-titlebar";
  const heading = document.createElement("h3");
  appendMaintainedText(heading, inclusion.name_tokens, inclusion.name);
  header.append(heading);
  article.append(header);
  for (const [index, paragraph] of (inclusion.paragraphs || []).entries()) {
    const text = document.createElement("p");
    text.className = "detail-copy";
    appendMaintainedText(text, inclusion.paragraph_tokens?.[index], paragraph);
    article.append(text);
  }
  return article;
}

function rulesSection(item) {
  const cards = [];
  for (const inclusion of item.special_rules || []) {
    if (inclusion.rule) cards.push(rulesReferenceArticle(inclusion.rule, { includeApplicability: false }));
    else cards.push(inlineScenarioRuleArticle(inclusion));
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
    card.id = `scenario-source-issue-${issue.id}`;
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

function seasonPolicySection(item, contexts, controller) {
  if (!contexts?.length || item.publication?.collection_id === "n5-core") return null;
  const wrapper = section("ITS tournament and Extra rules");
  const explanation = document.createElement("p");
  explanation.className = "detail-copy";
  explanation.textContent = "These restrictions are not part of the N5 core rules. "
    + "Select the play context used by your event or optional Extra to view them.";
  const label = document.createElement("label");
  label.className = "detail-copy";
  label.textContent = "Play context ";
  const select = document.createElement("select");
  const defaultOption = document.createElement("option");
  defaultOption.value = "";
  defaultOption.textContent = "No tournament or Extra selected";
  select.append(defaultOption);
  for (const context of contexts) {
    const option = document.createElement("option");
    option.value = context;
    option.textContent = context.replaceAll("-", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
    select.append(option);
  }
  select.value = contexts.includes(selectedPlayContext) ? selectedPlayContext : "";
  label.append(select);
  const results = document.createElement("div");
  results.className = "detail-group";
  let requestNumber = 0;
  async function selectContext() {
    const currentRequest = ++requestNumber;
    const context = select.value;
    selectedPlayContext = context;
    results.replaceChildren();
    if (!context) return;
    const message = document.createElement("p");
    message.className = "detail-source";
    message.textContent = "Loading selected ITS rules…";
    results.append(message);
    try {
      const payload = await getSeasonPolicies(
        item.publication.collection_id, item.publication.revision, context, controller.signal,
      );
      if (controller.signal.aborted || currentRequest !== requestNumber) return;
      results.replaceChildren();
      for (const policy of payload.items || []) {
        const card = document.createElement("article");
        card.className = "surface surface--subtle detail-section";
        const title = document.createElement("h3");
        title.className = "surface-titlebar surface-titlebar--subtle";
        title.textContent = policy.title;
        const effect = document.createElement("p");
        effect.className = "detail-copy";
        effect.textContent = policy.effect.text;
        const target = document.createElement("p");
        target.className = "detail-copy";
        const destination = policy.target.recordId.startsWith("skill:") ? "skills" : "rules";
        const link = document.createElement("a");
        link.href = `/${destination}/${encodeURIComponent(policy.target.recordId.split(":")[1])}`;
        link.textContent = policy.target.name;
        target.append("Applies to: ", link);
        const source = document.createElement("p");
        source.className = "detail-source";
        source.append("Sources: ");
        for (const [index, citation] of (policy.citations || []).entries()) {
          if (index) source.append("; ");
          const label = `${citation.sourceTitle || item.publication.collection_title}`
            + `, p. ${citation.page} (${citation.section})`;
          if (!citation.sourceUrl) {
            source.append(label);
            continue;
          }
          const link = document.createElement("a");
          link.href = citation.sourceUrl;
          link.target = "_blank";
          link.rel = "noopener noreferrer";
          link.textContent = label;
          source.append(link);
        }
        card.append(title, effect, target, source);
        results.append(card);
      }
      if (!(payload.items || []).length) {
        const none = document.createElement("p");
        none.className = "detail-copy";
        none.textContent = "No additional ITS policy is published for this play context.";
        results.append(none);
      }
    } catch (error) {
      if (controller.signal.aborted || currentRequest !== requestNumber) return;
      results.replaceChildren();
      message.textContent = "The selected ITS rules could not be loaded.";
      results.append(message);
      console.error("Could not load ITS play-context rules", error);
    }
  }
  select.addEventListener("change", selectContext, { signal: controller.signal });
  wrapper.append(explanation, label, results);
  if (select.value) selectContext();
  return wrapper;
}

function render(item, faqItems = [], policyContexts = [], controller = null) {
  updateDocumentIdentity(item);
  const placement = document.createElement("div");
  placement.className = "scenario-setup-grid";
  placement.append(setupCard(item), mapCard(item));
  const sections = [
    section("Setup", placement),
    objectivesSection(item),
    rulesSection(item),
    controller ? seasonPolicySection(item, policyContexts, controller) : null,
    faqRulingsSection(faqItems),
    endSection(item),
    issuesSection(item),
    sourcesSection(item),
    provenanceSection(item),
  ].filter(Boolean);
  elements.content.replaceChildren(...sections);
  show(elements.content);
  refreshScenarioDistances();
}

async function loadDetail(points) {
  detailController?.abort();
  const controller = new AbortController();
  detailController = controller;
  elements.status.textContent = `Loading ${points} Army Point setup.`;
  show(elements.status);
  try {
    const [item, faq, policyOptions] = await Promise.all([
      getScenario(slug, points, controller.signal, selectedPublication),
      fetchReviewedFaqRulings(`scenario:${slug}`, {
        scenarioId: `scenario:${slug}`,
        seasonId: selectedPublication.collection === "n5-core" ? "" : selectedPublication.collection,
        seasonRevision: selectedPublication.collection === "n5-core" ? "" : selectedPublication.revision,
        signal: controller.signal,
      }).catch((error) => {
        if (error.name !== "AbortError") console.error("Could not load FAQ clarifications", error);
        return { items: [] };
      }),
      selectedPublication.collection && selectedPublication.collection !== "n5-core"
        ? getSeasonPolicies(
          selectedPublication.collection, selectedPublication.revision, "", controller.signal,
        ).catch((error) => {
          if (error.name !== "AbortError") console.error("Could not list ITS contexts", error);
          return { contexts: [] };
        })
        : Promise.resolve({ contexts: [] }),
    ]);
    if (controller.signal.aborted || pageController.signal.aborted) return;
    render(item, faq.items || [], policyOptions.contexts || [], controller);
  } catch (error) {
    if (controller.signal.aborted || pageController.signal.aborted) return;
    if (error.name === "AbortError") return;
    elements.errorMessage.textContent = error.status === 400
      ? "This scenario setup is unavailable for the selected publication and Army Points value. Check the selection."
      : collectionLoadMessage(error, "scenario");
    console.error("Could not load scenario setup", error);
    show(elements.error);
  }
}

function choose(points) {
  if (!points) {
    detailController?.abort();
    setSelectedArmyPoints(null);
    show(elements.choice);
    return;
  }
  const numeric = Number(points);
  if (!summary.supported_army_points.includes(numeric)) {
    detailController?.abort();
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
    const payload = await getScenarios(summaryController.signal, selectedPublication);
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
    elements.errorMessage.textContent = error.status === 400
      ? "This scenario collection or revision is not supported. Open Scenarios to choose another collection."
      : collectionLoadMessage(error, "scenario");
    console.error("Could not load scenario collection", error);
    show(elements.error);
  }
}

elements.points.addEventListener("change", () => choose(elements.points.value));
window.addEventListener("distanceunitchange", refreshScenarioDistances, {
  signal: pageController.signal,
});
window.addEventListener("themechange", refreshScenarioDistances, {
  signal: pageController.signal,
});
document.addEventListener("infinity:beforenavigation", () => {
  pageController.abort();
  summaryController.abort();
  detailController?.abort();
}, { once: true });
initialize();
