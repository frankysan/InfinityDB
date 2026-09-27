import { getCatalogItem } from "./api.js";
import { rulesReferenceArticle } from "./rules-reference.js";
import { skillCategoryBadge } from "./skill-categories.js";

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
  const container = document.createElement("div");
  container.className = "table-container hacking-program-profile-table";
  const table = document.createElement("table");
  table.className = "data-table--compact";
  table.innerHTML = "<thead><tr><th>Attack MOD</th><th>Opponent MOD</th><th>PS</th><th>B</th></tr></thead>";
  const row = document.createElement("tr");
  for (const [label, value] of [["Attack MOD", program.attack_mod], ["Opponent MOD", program.opponent_mod], ["PS", program.ps], ["B", program.burst]]) {
    const cell = document.createElement("td");
    cell.dataset.label = label;
    cell.textContent = text(value);
    row.append(cell);
  }
  const body = document.createElement("tbody");
  body.append(row);
  table.append(body);
  container.append(table);
  nodes.push(container);

  const context = document.createElement("div");
  context.className = "hacking-program-context-row";
  const targets = document.createElement("p");
  targets.className = "hacking-program-targets";
  const targetsLabel = document.createElement("strong");
  targetsLabel.textContent = "Targets";
  targets.append(
    targetsLabel,
    ` ${program.targets?.length ? program.targets.join(", ") : "—"}`,
  );
  context.append(targets, categoryBadges(program.declaration_categories));
  nodes.push(context);

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

function fallbackProfileArticle(program, leadingContent) {
  const article = document.createElement("article");
  article.className = "detail-section";
  const header = document.createElement("header");
  header.className = "rules-card-header";
  const title = document.createElement("h3");
  title.textContent = program.name;
  header.append(title);
  article.append(header, ...leadingContent);
  return article;
}

function profileSection(program) {
  const section = document.createElement("section");
  section.className = "detail-group rules-reference hacking-program-profile";
  const heading = document.createElement("h2");
  heading.className = "detail-section-title";
  heading.textContent = "Program profile";
  const leadingContent = programProfileContent(program);
  const rule = program.rules?.[0];
  const article = rule
    ? rulesReferenceArticle(rule, { leadingContent })
    : fallbackProfileArticle(program, leadingContent);
  section.append(heading, article);
  return section;
}

function devicesSection(program) {
  const section = document.createElement("section");
  section.className = "detail-group";
  const heading = document.createElement("h2");
  heading.className = "detail-section-title";
  heading.textContent = "Baseline Hacking Devices";
  section.append(heading);
  if (!program.devices?.length) {
    const note = document.createElement("p");
    note.className = "detail-copy";
    note.textContent = "No baseline Device association is declared by Army. This Program is available through Upgrade/source-specific associations instead.";
    section.append(note);
    return section;
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
  section.append(list);
  return section;
}

function render(program) {
  document.title = `${program.name} · InfinityDB`;
  name.firstChild.textContent = program.name;
  meta.textContent = `Army program #${program.position}${program.source_extra_id == null ? "" : ` · Upgrade extra #${program.source_extra_id}`}`;
  content.replaceChildren(profileSection(program), devicesSection(program));
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
