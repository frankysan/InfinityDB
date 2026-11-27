import { getSearchResults } from "./api.js";
import { shareStateHref } from "./share-state.js";

const delay = 180;
const limit = 8;

/** One live suggestion controller for the persistent navigation search. */
export function setupLiveSearch(form, input) {
  const panel = form.querySelector("#global-search-panel");
  const status = form.querySelector("#global-search-status");
  const list = form.querySelector("#global-search-results");
  let timer;
  let controller;
  let generation = 0;
  let active = -1;

  input.setAttribute("role", "combobox");
  input.setAttribute("aria-autocomplete", "list");
  input.setAttribute("aria-controls", list.id);
  input.setAttribute("aria-expanded", "false");

  function select(index) {
    const options = [...list.children];
    active = index;
    options.forEach((option, i) => option.setAttribute("aria-selected", String(i === index)));
    if (index < 0 || !options[index]) {
      input.removeAttribute("aria-activedescendant");
      return;
    }
    input.setAttribute("aria-activedescendant", options[index].id);
    options[index].scrollIntoView({ block: "nearest" });
  }

  function dismiss() {
    generation += 1;
    clearTimeout(timer);
    timer = undefined;
    controller?.abort();
    controller = undefined;
    select(-1);
    panel.hidden = true;
    input.setAttribute("aria-expanded", "false");
    list.replaceChildren();
    status.textContent = "";
  }

  function option(name, domain, href, all = false) {
    const link = document.createElement("a");
    link.className = all ? "global-search-option global-search-option--all" : "global-search-option";
    link.id = `global-search-option-${list.children.length}`;
    link.href = href;
    link.tabIndex = -1;
    link.setAttribute("role", "option");
    link.setAttribute("aria-selected", "false");
    const label = document.createElement("span");
    label.textContent = name;
    link.append(label);
    if (domain) {
      const category = document.createElement("span");
      category.className = "global-search-option-domain";
      category.textContent = domain;
      link.append(category);
    }
    list.append(link);
  }

  function show(query, items, message) {
    select(-1);
    list.replaceChildren();
    for (const item of items) {
      const href = item.share_state
        ? shareStateHref(item.href, item.share_state.schema, item.share_state.values)
        : item.href;
      option(item.name, item.domain, href);
    }
    option("View all results", "", shareStateHref("/search", "search", { q: query }), true);
    panel.hidden = false;
    input.setAttribute("aria-expanded", "true");
    status.textContent = message;
  }

  function schedule() {
    dismiss();
    const query = input.value.trim().slice(0, 200);
    if (query.length < 2) return;
    const requestGeneration = generation;
    timer = setTimeout(async () => {
      timer = undefined;
      const request = new AbortController();
      controller = request;
      try {
        const payload = await getSearchResults(query, request.signal, { limit });
        if (requestGeneration !== generation) return;
        const items = payload.items;
        show(query, items, items.length
          ? `${items.length} suggestion${items.length === 1 ? "" : "s"}`
          : "No matching suggestions");
      } catch (error) {
        if (requestGeneration !== generation || error.name === "AbortError") return;
        show(query, [], "Suggestions unavailable");
      } finally {
        if (controller === request) controller = undefined;
      }
    }, delay);
  }

  input.addEventListener("input", (event) => {
    if (event.isComposing) dismiss();
    else schedule();
  });
  input.addEventListener("compositionend", schedule);
  input.addEventListener("focus", schedule);
  input.addEventListener("keydown", (event) => {
    if (event.isComposing) return;
    if (event.key === "Escape" && (!panel.hidden || timer !== undefined || controller)) {
      event.preventDefault();
      dismiss();
    } else if (!panel.hidden && (event.key === "ArrowDown" || event.key === "ArrowUp")) {
      event.preventDefault();
      const count = list.children.length;
      const next = active < 0
        ? (event.key === "ArrowDown" ? 0 : count - 1)
        : (active + (event.key === "ArrowDown" ? 1 : -1) + count) % count;
      select(next);
    } else if (event.key === "Enter" && !panel.hidden && active >= 0) {
      event.preventDefault();
      list.children[active].click();
    }
  });
  form.addEventListener("focusout", (event) => {
    if (!form.contains(event.relatedTarget)) dismiss();
  });
  document.addEventListener("pointerdown", (event) => {
    if (!form.contains(event.target)) dismiss();
  });
  list.addEventListener("pointerdown", (event) => {
    // Preserve input focus until the native link click is handled.
    if (event.pointerType === "mouse" && event.button === 0) event.preventDefault();
  });
  return { dismiss };
}
