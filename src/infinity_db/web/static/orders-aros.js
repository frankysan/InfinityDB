import { getOrdersAros } from "./api.js";

const state = document.getElementById("matrix-state");
const target = document.getElementById("matrix-sections");
const count = document.getElementById("matrix-count");
const search = document.getElementById("matrix-search");
const controller = new AbortController();
let sections = [];

function render() {
  const query = search.value.trim().toLocaleLowerCase();
  let total = 0;
  const fragment = document.createDocumentFragment();
  for (const section of sections) {
    const visible = section.items.filter((item) => (
      !query || [item.name, item.source_type, item.owner].some(
        (value) => value.toLocaleLowerCase().includes(query)
      )
    ));
    total += visible.length;
    if (!visible.length) continue;

    const group = document.createElement("section");
    group.className = "surface surface--clipped content-frame";
    group.setAttribute("aria-labelledby", `orders-aros-${section.id}`);
    const heading = document.createElement("div");
    heading.className = "section-heading";
    const title = document.createElement("h2");
    title.id = `orders-aros-${section.id}`;
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
    caption.textContent = `${section.title} — N5.3 core reference`;
    const head = document.createElement("thead");
    const headers = document.createElement("tr");
    for (const title of ["Action", "Source type"]) {
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
      body.append(row);
    }
    table.append(caption, head, body);
    viewport.append(table);
    group.append(heading, viewport);
    fragment.append(group);
  }
  target.replaceChildren(fragment);
  count.textContent = `${total} declaration${total === 1 ? "" : "s"}`;
  state.textContent = !total ? "No matching actions." : "";
}

async function load() {
  try {
    const payload = await getOrdersAros(controller.signal);
    if (payload.scope !== "n5-core-current-unscoped"
        || payload.source?.page !== 191 || payload.legalityEvaluation !== false
        || !Array.isArray(payload.sections) || payload.sections.length !== 4) {
      throw new Error("Unexpected declaration reference source.");
    }
    sections = payload.sections;
    target.setAttribute("aria-busy", "false");
    render();
  } catch (error) {
    if (error.name === "AbortError") return;
    target.setAttribute("aria-busy", "false");
    state.textContent = error.message || "Could not load Orders and AROs.";
    count.textContent = "Unavailable";
  }
}

search.addEventListener("input", render);
document.addEventListener("infinity:beforenavigation", () => controller.abort(), { once: true });
load();
