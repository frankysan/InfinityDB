/** Shared, accessible multi-selection controls for Unit Explorer categorical filters. */
const MAX_SELECTIONS = 16;
const VALID_IDENTIFIER = /^(?:[a-z0-9]+(?:-[a-z0-9]+)*)$/u;

export function parseMultiSelection(value) {
  if (!value) return [];
  const entries = value.split(",");
  if (entries.length > MAX_SELECTIONS || entries.some((entry) => !VALID_IDENTIFIER.test(entry))) return [];
  return [...new Set(entries)].sort();
}

export function normalizeMultiSelection(value, items) {
  const aliases = new Map();
  for (const item of items) {
    const canonical = item.slug || String(item.id);
    aliases.set(String(item.id), canonical);
    for (const sourceId of item.source_ids || []) aliases.set(String(sourceId), canonical);
  }
  return [...new Set(parseMultiSelection(value).map((entry) => aliases.get(entry) || entry))]
    .sort().join(",");
}

export function createUnitMultiSelect(select, label, onChange) {
  const originalLabel = select.parentElement.querySelector(`label[for="${select.id}"]`);
  const modeSwitch = document.createElement("input");
  if (originalLabel) {
    const caption = document.createElement("span");
    caption.className = "unit-multi-label";
    caption.textContent = originalLabel.textContent;
    const header = document.createElement("div");
    header.className = "unit-multi-header";
    const modeLabel = document.createElement("label");
    modeLabel.className = "unit-multi-mode";
    modeSwitch.type = "checkbox";
    modeSwitch.setAttribute("role", "switch");
    modeSwitch.setAttribute("aria-label", `Match all selected ${label}`);
    modeSwitch.disabled = true;
    modeLabel.append(
      document.createTextNode("OR"),
      modeSwitch,
      document.createTextNode("AND"),
    );
    header.append(caption, modeLabel);
    originalLabel.replaceWith(header);
    modeSwitch.addEventListener("change", onChange);
  }
  select.hidden = true;
  select.style.display = "none";
  select.tabIndex = -1;
  select.setAttribute("aria-hidden", "true");

  const details = document.createElement("details");
  details.className = "unit-multi-select";
  const summary = document.createElement("summary");
  const panel = document.createElement("div");
  panel.className = "unit-multi-panel";
  const toolbar = document.createElement("div");
  toolbar.className = "unit-multi-toolbar";
  const search = document.createElement("input");
  search.type = "search";
  search.autocomplete = "off";
  search.placeholder = "Find an option…";
  search.setAttribute("aria-label", `Search ${label}`);
  const clear = document.createElement("button");
  clear.type = "button";
  clear.textContent = "Clear";
  clear.className = "unit-multi-clear";
  toolbar.append(search, clear);
  const choices = document.createElement("div");
  choices.className = "unit-multi-choices";
  choices.setAttribute("role", "group");
  choices.setAttribute("aria-label", `${label} choices`);
  const notice = document.createElement("p");
  notice.className = "unit-multi-notice";
  notice.setAttribute("role", "status");
  notice.setAttribute("aria-live", "polite");
  const chips = document.createElement("div");
  chips.className = "unit-multi-chips";
  chips.setAttribute("aria-label", `Selected ${label}`);
  panel.append(toolbar, choices, notice);
  details.append(summary, panel);
  select.after(details, chips);

  let selected = new Set();
  let items = [];
  const rows = new Map();
  const value = () => [...selected].sort().join(",");
  const displayName = (id) => items.find((item) => item.value === id)?.name || `${id} (unavailable)`;

  function renderSelection() {
    const count = selected.size;
    const short = count === 1 ? displayName([...selected][0]) : `${count} selected`;
    const description = count ? short : `All ${label.toLowerCase()}`;
    summary.textContent = description;
    summary.setAttribute("aria-label", `${label}: ${description}`);
    clear.disabled = count === 0;
    modeSwitch.disabled = count < 2;
    for (const [id, { checkbox }] of rows) {
      checkbox.checked = selected.has(id);
      checkbox.disabled = !checkbox.checked && count >= MAX_SELECTIONS;
    }
    chips.replaceChildren();
    for (const id of [...selected].sort()) {
      const chip = document.createElement("button");
      chip.type = "button";
      chip.className = "unit-multi-chip";
      chip.textContent = `${displayName(id)} ×`;
      chip.setAttribute("aria-label", `Remove ${displayName(id)} from ${label}`);
      chip.addEventListener("click", () => {
        selected.delete(id);
        notice.textContent = "";
        renderSelection();
        onChange();
      });
      chips.append(chip);
    }
  }

  function setItems(newItems, formatName = (item) => item.name) {
    items = newItems.map((item) => ({
      id: String(item.id), value: item.slug || String(item.id), name: String(formatName(item)),
    }));
    rows.clear();
    choices.replaceChildren();
    for (const item of items) {
      const row = document.createElement("label");
      row.className = "unit-multi-option";
      const checkbox = document.createElement("input");
      checkbox.type = "checkbox";
      checkbox.value = item.value;
      const count = document.createElement("span");
      count.className = "unit-multi-count";
      row.append(checkbox, document.createTextNode(item.name), count);
      checkbox.addEventListener("change", () => {
        if (checkbox.checked && selected.size >= MAX_SELECTIONS) {
          checkbox.checked = false;
          notice.textContent = `Select up to ${MAX_SELECTIONS} ${label.toLowerCase()}.`;
          return;
        }
        if (checkbox.checked) selected.add(item.value);
        else selected.delete(item.value);
        notice.textContent = "";
        renderSelection();
        onChange();
      });
      rows.set(item.value, { row, checkbox, count });
      choices.append(row);
    }
    search.disabled = false;
    renderSelection();
    search.dispatchEvent(new Event("input"));
  }

  search.disabled = true;
  search.addEventListener("input", () => {
    const query = search.value.trim().toLocaleLowerCase();
    for (const item of items) {
      rows.get(item.value).row.hidden = !item.name.toLocaleLowerCase().includes(query);
    }
  });
  clear.addEventListener("click", () => {
    if (!selected.size) return;
    selected.clear();
    notice.textContent = "";
    renderSelection();
    onChange();
  });
  details.addEventListener("toggle", () => {
    if (!details.open) return;
    for (const other of document.querySelectorAll(".unit-multi-select")) {
      if (other !== details) other.open = false;
    }
  });
  renderSelection();
  return {
    value,
    mode: () => modeSwitch.checked ? "and" : "or",
    setMode(mode) { modeSwitch.checked = mode === "and"; },
    setCounts(counts) {
      choices.setAttribute("aria-busy", counts === null ? "true" : "false");
      for (const item of items) {
        const { checkbox, count } = rows.get(item.value);
        const value = counts === null ? null
          : counts === undefined ? undefined : Number(counts[item.id] || 0);
        count.textContent = value == null ? (value === null ? "…" : "—") : value.toLocaleString();
        count.setAttribute("aria-hidden", "true");
        checkbox.setAttribute("aria-label", value === null
          ? `${item.name}, count loading`
          : value === undefined ? `${item.name}, count unavailable`
            : `${item.name}, ${value} matching ${value === 1 ? "Unit" : "Units"}`);
      }
    },
    setValue(next) {
      selected = new Set(parseMultiSelection(next));
      notice.textContent = "";
      renderSelection();
    },
    setItems,
  };
}
