import { getGlossary } from "./api.js";
import { appendMaintainedText } from "./maintained-text.js";
import { readShareState, shareStateHref, writeShareState } from "./share-state.js";

const byId = (id) => document.getElementById(id);
const elements = {
  search: byId("glossary-search"),
  count: byId("glossary-count"),
  results: byId("glossary-results"),
  loading: byId("glossary-loading"),
  error: byId("glossary-error"),
  errorMessage: byId("glossary-error-message"),
  empty: byId("glossary-empty"),
  list: byId("glossary-list"),
};
const controller = new AbortController();
const query = readShareState("glossary").params.get("q")?.trim().slice(0, 200) || "";

function show(panel) {
  for (const element of [elements.loading, elements.error, elements.empty, elements.list]) {
    element.hidden = element !== panel;
  }
  elements.results.setAttribute("aria-busy", String(panel === elements.loading));
}

function anchorId(item) {
  return item.id.replaceAll(":", "-");
}

function matches(item, needle) {
  if (!needle) return true;
  const values = [item.name, item.domain, item.description, ...(item.aliases || [])];
  return values.some((value) => String(value || "").toLocaleLowerCase().includes(needle));
}

function entryNode(item) {
  const article = document.createElement("article");
  article.className = "glossary-entry";
  article.id = anchorId(item);
  article.tabIndex = -1;
  article.dataset.kind = item.kind;

  const header = document.createElement("header");
  header.className = "glossary-entry-header";
  const title = document.createElement("h3");
  if (item.embedded) {
    title.textContent = item.name;
  } else {
    const link = document.createElement("a");
    link.href = item.href;
    link.textContent = item.name;
    title.append(link);
  }
  const domain = document.createElement("span");
  domain.className = "badge glossary-domain";
  domain.textContent = item.domain;
  header.append(title, domain);

  const description = document.createElement("p");
  description.className = "glossary-description";
  appendMaintainedText(description, item.description_tokens, item.description);
  article.append(header, description);

  if (item.aliases?.length) {
    const aliases = document.createElement("p");
    aliases.className = "glossary-aliases";
    aliases.textContent = `Also: ${item.aliases.join(", ")}`;
    article.append(aliases);
  }

  const identifier = document.createElement("p");
  identifier.className = "detail-source developer-only";
  identifier.textContent = item.id;
  article.append(identifier);
  return article;
}

function revealHashTarget() {
  if (!window.location.hash) return;
  const target = document.getElementById(decodeURIComponent(window.location.hash.slice(1)));
  if (!target || target.hidden) return;
  target.scrollIntoView({ block: "start" });
  target.focus?.({ preventScroll: true });
}

function render(items) {
  const needle = query.toLocaleLowerCase();
  const visible = items.filter((item) => matches(item, needle));
  elements.count.textContent = `${visible.length.toLocaleString()} term${visible.length === 1 ? "" : "s"}`;
  if (!visible.length) return show(elements.empty);
  elements.list.replaceChildren(...visible.map(entryNode));
  show(elements.list);
  requestAnimationFrame(revealHashTarget);
}

async function load() {
  show(elements.loading);
  try {
    const payload = await getGlossary(controller.signal);
    render(payload.items);
  } catch (error) {
    if (error.name === "AbortError") return;
    elements.errorMessage.textContent = error.message || "Please try again.";
    show(elements.error);
  }
}

elements.search.value = query;
writeShareState("glossary", query ? { q: query } : {}, { replace: true });
elements.search.form?.addEventListener("submit", (event) => {
  event.preventDefault();
  const nextQuery = elements.search.value.trim().slice(0, 200);
  window.location.href = shareStateHref("/glossary", "glossary", nextQuery ? { q: nextQuery } : {});
});
document.addEventListener("infinity:beforenavigation", () => controller.abort(), { once: true });
window.addEventListener("hashchange", revealHashTarget);
load();
