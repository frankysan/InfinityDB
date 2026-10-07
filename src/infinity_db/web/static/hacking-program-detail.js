import { getCatalogItem } from "./api.js";
import { rulesReferenceArticle } from "./rules-reference.js";
import { skillCategoryBadge } from "./skill-categories.js";
import { tableViewport } from "./view-components.js";

const itemId = window.location.pathname.split("/").pop();
const name = document.getElementById("item-name");
const meta = document.getElementById("item-meta");
const content = document.getElementById("item-content");
const status = document.getElementById("item-status");
const pageController = new AbortController();

function text(value) {
  return value === null || value === undefined || value === "" ? "—" : String(value);
}

function categoryBadges(categories) {
  const badges = document.createElement("p");
  badges.className = "detail-badges hacking-program-declaration-categories";
  for (const category of categories || []) {
    badges.append(skillCategoryBadge(category));
  }
  return badges;
}

function programProfileContent(program) {
  const nodes = [];
  const table = document.createElement("table");
  table.className = "data-table--compact data-table--profile";
  table.innerHTML =
    "<caption class=\"sr-only\">Hacking Program profile</caption>"
    + "<thead><tr><th class=\"table-column--descriptor\" scope=\"col\">Targets</th>"
    + "<th class=\"table-column--metric\" scope=\"col\">Attack MOD</th>"
    + "<th class=\"table-column--metric\" scope=\"col\">Opponent MOD</th>"
    + "<th class=\"table-column--metric\" scope=\"col\">PS</th>"
    + "<th class=\"table-column--metric\" scope=\"col\">B</th></tr></thead>";
  const row = document.createElement("tr");
  for (const [label, value, role] of [
    ["Targets", program.targets?.length ? program.targets.join(", ") : null, "descriptor"],
    ["Attack MOD", program.attack_mod, "metric"],
    ["Opponent MOD", program.opponent_mod, "metric"],
    ["PS", program.ps, "metric"],
    ["B", program.burst, "metric"],
  ]) {
    const cell = document.createElement("td");
    cell.className = `table-column--${role}`;
    cell.dataset.label = label;
    cell.textContent = text(value);
    row.append(cell);
  }
  const body = document.createElement("tbody");
  body.append(row);
  table.append(body);
  nodes.push(tableViewport(table, "hacking-program-profile-table"));

  if (program.special) {
    const special = document.createElement("div");
    special.className = "detail-fact-group";
    const title = document.createElement("h4");
    title.className = "detail-fact-heading";
    title.textContent = "Special";
    const valueElement = document.createElement("p");
    valueElement.className = "detail-copy";
    valueElement.textContent = program.special;
    special.append(title, valueElement);
    nodes.push(special);
  }
  return nodes;
}

function baselineDevicesGroup(program) {
  const group = document.createElement("div");
  group.className = "detail-fact-group hacking-program-devices";
  const heading = document.createElement("h4");
  heading.className = "detail-fact-heading";
  heading.textContent = "Baseline Hacking Devices";
  group.append(heading);

  if (!program.devices?.length) {
    const note = document.createElement("p");
    note.className = "detail-copy";
    note.textContent =
      "No baseline Hacking Device includes this Program. It may instead be granted separately, "
      + "including as an Upgrade Program.";
    group.append(note);
    return group;
  }

  const list = document.createElement("ul");
  list.className = "detail-list";
  for (const device of program.devices) {
    const item = document.createElement("li");
    if (device.slug) {
      const link = document.createElement("a");
      link.href = `/equipment/${encodeURIComponent(device.slug)}`;
      link.textContent = device.name;
      item.append(link);
    } else {
      item.textContent = device.name;
    }
    list.append(item);
  }
  group.append(list);
  return group;
}

function fallbackProfileArticle(program, leadingContent, headerContent, beforeRelations) {
  const article = document.createElement("article");
  article.className = "surface surface--subtle detail-section";
  const header = document.createElement("header");
  header.className = "surface-titlebar surface-titlebar--ruled rules-card-titlebar";
  const title = document.createElement("h3");
  title.textContent = program.name;
  header.append(title, ...headerContent);
  article.append(header, ...leadingContent, ...beforeRelations);
  return article;
}

function profileSection(program) {
  const section = document.createElement("section");
  section.className = "detail-group rules-reference hacking-program-profile";
  const heading = document.createElement("h2");
  heading.className = "detail-heading";
  heading.textContent = "Program profile";
  const leadingContent = programProfileContent(program);
  const headerContent = program.declaration_categories?.length
    ? [categoryBadges(program.declaration_categories)]
    : [];
  const beforeRelations = [baselineDevicesGroup(program)];
  const rule = program.rules?.[0];
  const article = rule
    ? rulesReferenceArticle(rule, { leadingContent, headerContent, beforeRelations })
    : fallbackProfileArticle(program, leadingContent, headerContent, beforeRelations);
  section.append(heading, article);
  return section;
}

function render(program) {
  document.title = `${program.name} · InfinityDB`;
  name.firstChild.textContent = program.name;
  meta.textContent = `Army program #${program.position}${program.source_extra_id == null ? "" : ` · Upgrade extra #${program.source_extra_id}`}`;
  content.replaceChildren(profileSection(program));
  content.hidden = false;
  status.hidden = true;
}

document.addEventListener(
  "infinity:beforenavigation",
  () => pageController.abort(),
  { once: true },
);
getCatalogItem("hacking-programs", itemId, pageController.signal)
  .then(render)
  .catch((error) => {
    if (error.name === "AbortError") return;
    name.firstChild.textContent = "Hacking Program unavailable";
    status.textContent = error.message || "Could not load this Hacking Program.";
  });
