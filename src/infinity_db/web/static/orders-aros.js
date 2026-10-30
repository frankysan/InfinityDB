import { getOrdersAros } from "./api.js";

const state = document.getElementById("matrix-state");
const target = document.getElementById("matrix-sections");
const count = document.getElementById("matrix-count");
const search = document.getElementById("matrix-search");
const scenarioSelect = document.getElementById("matrix-scenario");
const scenarioPanel = document.getElementById("scenario-matrix");
const scenarioTitle = document.getElementById("scenario-matrix-title");
const scenarioCount = document.getElementById("scenario-matrix-count");
const scenarioState = document.getElementById("scenario-matrix-state");
const scenarioTarget = document.getElementById("scenario-matrix-sections");
let controller = null;
let sections = [];
let scoped = null;
const initialScenario = new URLSearchParams(window.location.search).get("scenario") || "";
if (initialScenario) {
  if (![...scenarioSelect.options].some((option) => option.value === initialScenario)) {
    const invalid = document.createElement("option");
    invalid.value = initialScenario;
    invalid.textContent = `Unsupported scenario: ${initialScenario}`;
    scenarioSelect.append(invalid);
  }
  scenarioSelect.value = initialScenario;
}

function renderSections(rows, destination, prefix, query) {
  let total = 0;
  const fragment = document.createDocumentFragment();
  for (const section of rows) {
    const visible = section.items.filter((item) => (
      !query || [item.name, item.source_type, item.owner].some(
        (value) => value.toLocaleLowerCase().includes(query)
      )
    ));
    total += visible.length;
    if (!visible.length) continue;

    const group = document.createElement("section");
    group.className = "surface surface--clipped content-frame";
    group.setAttribute("aria-labelledby", `${prefix}orders-aros-${section.id}`);
    const heading = document.createElement("div");
    heading.className = "section-heading";
    const title = document.createElement("h2");
    title.id = `${prefix}orders-aros-${section.id}`;
    title.textContent = section.title;
    const number = document.createElement("span");
    number.className = "section-index";
    number.textContent = String(visible.length);
    heading.append(title, number);

    const viewport = document.createElement("div");
    viewport.className = "table-viewport";
    const table = document.createElement("table");
    table.className = "data-table--listing";
    const caption = document.createElement("caption");
    caption.className = "sr-only";
    caption.textContent = `${section.title} — N5.3 ${prefix ? "selected scenario" : "core"} reference`;
    const head = document.createElement("thead");
    const headers = document.createElement("tr");
    for (const title of (prefix ? ["Action", "Source type", "Source"] : ["Action", "Source type"])) {
      const cell = document.createElement("th");
      cell.scope = "col";
      cell.textContent = title;
      headers.append(cell);
    }
    head.append(headers);
    const body = document.createElement("tbody");
    for (const item of visible) {
      const row = document.createElement("tr");
      row.dataset.recordId = item.record_id;
      const name = document.createElement("td");
      name.className = "table-column--primary";
      const link = document.createElement("a");
      link.href = item.href;
      link.textContent = item.name;
      name.append(link);
      const kind = document.createElement("td");
      kind.className = "table-column--descriptor";
      kind.textContent = item.source_type;
      row.append(name, kind);
      if (prefix) {
        const source = document.createElement("td");
        source.className = "table-column--descriptor";
        source.textContent = (item.citations || [])
          .filter((citation) => citation.source_id === "n5-core-v5.3-pdf")
          .map((citation) => `N5.3 p. ${citation.page}`).join(", ") || "—";
        row.append(source);
      }
      body.append(row);
    }
    table.append(caption, head, body);
    viewport.append(table);
    group.append(heading, viewport);
    fragment.append(group);
  }
  destination.replaceChildren(fragment);
  return total;
}

function render() {
  const query = search.value.trim().toLocaleLowerCase();
  const total = renderSections(sections, target, "", query);
  count.textContent = `${total} declaration${total === 1 ? "" : "s"}`;
  state.textContent = !total ? "No matching actions." : "";
  scenarioPanel.hidden = !scoped;
  if (scoped) {
    scenarioTitle.textContent = `${scoped.name} — scenario-only actions`;
    const countScoped = renderSections(scoped.sections, scenarioTarget, "scoped-", query);
    scenarioCount.textContent = `${countScoped} additional declaration${countScoped === 1 ? "" : "s"}`;
    scenarioState.textContent = countScoped ? ""
      : query ? "No matching scenario-only actions."
        : "This scenario adds no separately declared Skills to the core matrix.";
  } else {
    scenarioTarget.replaceChildren();
    scenarioState.textContent = "";
  }
}

async function load() {
  controller?.abort();
  controller = new AbortController();
  const signal = controller.signal;
  const selection = scenarioSelect.value;
  scenarioSelect.disabled = true;
  try {
    const payload = await getOrdersAros(signal, selection);
    if (signal.aborted) return;
    if (payload.scope !== "n5-core-current-unscoped"
        || payload.source?.page !== 191 || payload.legalityEvaluation !== false
        || !Array.isArray(payload.sections) || payload.sections.length !== 4
        || (selection && (
          payload.scenario?.id !== `scenario:${selection}`
          || !Array.isArray(payload.scenario.sections)
          || payload.scenario.sections.length !== 4
        ))) {
      throw new Error("Unexpected declaration reference source.");
    }
    sections = payload.sections;
    scoped = selection ? payload.scenario : null;
    target.setAttribute("aria-busy", "false");
    render();
  } catch (error) {
    if (signal.aborted) return;
    target.setAttribute("aria-busy", "false");
    state.textContent = error.message || "Could not load Orders and AROs.";
    count.textContent = "Unavailable";
  } finally {
    if (!signal.aborted) scenarioSelect.disabled = false;
  }
}

search.addEventListener("input", render);
scenarioSelect.addEventListener("change", () => {
  const url = new URL(window.location.href);
  if (scenarioSelect.value) url.searchParams.set("scenario", scenarioSelect.value);
  else url.searchParams.delete("scenario");
  window.history.replaceState(window.history.state, "", url);
  load();
});
document.addEventListener("infinity:beforenavigation", () => controller?.abort(), { once: true });
load();
