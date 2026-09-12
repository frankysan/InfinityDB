import { formatDistanceExtra, initializeDistanceUnitToggle } from "./preferences.js";
import { renderUnitRows } from "./unit-list.js";

const skillId = new URLSearchParams(window.location.search).get("id")
  || window.location.pathname.split("/").pop();
const name = document.getElementById("skill-name");
const meta = document.getElementById("skill-meta");
const status = document.getElementById("skill-status");
const content = document.getElementById("skill-content");
let currentSkill;

function formatVariantName(variant) {
  const extras = variant.extras.map((extra) => {
    if (!extra.is_distance) return extra.name;
    return formatDistanceExtra(extra.name, {
      showPositiveSign: variant.skill_name !== "Super-Jump",
      forcePositiveSign: variant.skill_name === "Forward Deployment",
    });
  });
  return extras.length ? `${variant.skill_name} (${extras.join(", ")})` : variant.skill_name;
}

function variantSection(variant) {
  const section = document.createElement("details");
  section.className = "explorer army-profile";
  const heading = document.createElement("summary");
  heading.className = "army-profile-title";
  const title = document.createElement("h2");
  title.textContent = formatVariantName(variant);
  const count = document.createElement("span");
  count.className = "section-index";
  count.textContent = `${variant.units.length} ${variant.units.length === 1 ? "unit" : "units"}`;
  heading.append(title, count);
  const table = document.createElement("table");
  table.innerHTML = "<caption class=\"sr-only\">Units using this skill variant</caption><thead><tr><th scope=\"col\">Unit</th><th scope=\"col\">Armies</th><th class=\"id-column\" scope=\"col\">ID</th></tr></thead>";
  const body = document.createElement("tbody");
  renderUnitRows(body, variant.units);
  table.append(body);
  const container = document.createElement("div");
  container.className = "table-container";
  container.append(table);
  section.append(heading, container);
  return section;
}

function render(skill) {
  currentSkill = skill;
  document.title = `${skill.name} · InfinityDB`;
  name.firstChild.textContent = skill.name;
  meta.textContent = skill.wiki || `Skill #${skill.id}`;
  const variants = [...skill.variants].sort((left, right) => (
    formatVariantName(left).localeCompare(
      formatVariantName(right), undefined, { sensitivity: "base", numeric: true },
    )
  ));
  const sections = document.createElement("section");
  sections.className = "usage-section-group";
  sections.append(...variants.map(variantSection));
  content.replaceChildren(sections);
  status.hidden = true;
  content.hidden = false;
}

initializeDistanceUnitToggle();
window.addEventListener("distanceunitchange", () => {
  if (currentSkill) render(currentSkill);
});
if (!/^\d+$/.test(skillId || "")) {
  name.firstChild.textContent = "Skill unavailable";
  status.textContent = "The requested skill address is invalid.";
} else {
  fetch(`/api/skills/${encodeURIComponent(skillId)}`).then(async (response) => {
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.error || "Could not load this skill.");
    return payload;
  }).then(render).catch((error) => {
    name.firstChild.textContent = "Skill unavailable";
    status.textContent = error.message || "Could not load this skill.";
  });
}
