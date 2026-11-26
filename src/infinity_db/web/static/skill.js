import { formatSkillDistanceExtra } from "./distance.js";
import { optionalUnitFilters } from "./preferences.js";
import { getCatalogItem, getRestrictionsReference, visibleUnitIds } from "./api.js";
import { faqRulingsSection, fetchReviewedFaqRulings } from "./faq-rulings.js";
import { renderUnitRows } from "./unit-list.js";
import { gameplayVariantRules, rulesReferenceSection } from "./rules-reference.js";
import { skillCategoryBadge } from "./skill-categories.js";
import { restrictionsContextSection } from "./restrictions-reference.js";
import { referenceLoadMessage, tableViewport } from "./view-components.js";
import { exactVariantUsageSection, loadExactVariantUsage } from "./variant-usage.js";

const skillId = new URLSearchParams(window.location.search).get("id")
  || window.location.pathname.split("/").pop();
const name = document.getElementById("skill-name");
const meta = document.getElementById("skill-meta");
const status = document.getElementById("skill-status");
const content = document.getElementById("skill-content");
let currentSkill;
let displayedSkill;
let faqItems = [];
let restrictionsData = null;
let exactUsage = null;
const pageController = new AbortController();

function displayWikiUrl(url) {
  try {
    return new URL(url).hostname.toLowerCase() === "infinitythewiki.com"
      ? url.split("?", 1)[0]
      : url;
  } catch {
    return url;
  }
}

function withVisibleUnits(skill, ids) {
  return {
    ...skill, variants: skill.variants.map((variant) => ({
      ...variant, units: variant.units.filter((unit) => ids.has(unit.id)),
    })).filter((variant) => variant.units.length)
  };
}

function formatVariantName(variant, parameterSemantics = null) {
  const extras = variant.extras.map((extra) => {
    if (!extra.is_distance) return extra.name;
    return formatSkillDistanceExtra(extra.name, parameterSemantics);
  });
  return extras.length ? `${variant.skill_name} (${extras.join(", ")})` : variant.skill_name;
}

function sourceVariantLabel(variant) {
  const semantics = variant.source_variant;
  if (!semantics) return null;
  if (semantics.kind === "level") return `Level ${semantics.value}`;
  if (semantics.kind === "named") return semantics.label;
  if (semantics.kind === "attribute-replacement") {
    return `${semantics.attribute} = ${semantics.value}`;
  }
  return null;
}

function referenceCell(value, role) {
  const cell = document.createElement("td");
  cell.className = `table-column--${role}`;
  if (value instanceof Node) cell.append(value);
  else cell.textContent = value === null || value === undefined || value === "" ? "—" : String(value);
  return cell;
}

function chartOutcomeLink(text, reference) {
  if (!reference?.id || !["skills", "weapons", "equipment"].includes(reference.catalog)) {
    return document.createTextNode(text);
  }
  const link = document.createElement("a");
  link.href = `/${reference.catalog}/${encodeURIComponent(reference.id)}`;
  link.textContent = text;
  return link;
}

function randomChartOutcome(row) {
  if (row.outcome_components?.length) {
    const parts = document.createElement("span");
    parts.className = "chart-outcome-components";
    for (const [index, component] of row.outcome_components.entries()) {
      if (index) parts.append(" + ");
      const element = document.createElement("span");
      element.className = "chart-outcome-component";
      element.append(chartOutcomeLink(component.text, component.public_reference));
      parts.append(element);
    }
    return parts;
  }
  if (!row.conditional_outcomes?.length) {
    return chartOutcomeLink(row.result, row.public_reference);
  }
  const branches = document.createElement("span");
  branches.className = "chart-outcome-branches";
  for (const [index, branch] of row.conditional_outcomes.entries()) {
    if (index) branches.append("\n");
    branches.append(
      `${branch.label}: `,
      chartOutcomeLink(branch.result, branch.public_reference),
    );
  }
  return branches;
}

function structuredTable(titleText, columns, rows) {
  const section = document.createElement("section");
  section.className = "detail-group";
  const title = document.createElement("h2");
  title.className = "detail-heading";
  title.textContent = titleText;
  const table = document.createElement("table");
  table.className = "data-table--compact data-table--reference";
  const caption = document.createElement("caption");
  caption.className = "sr-only";
  caption.textContent = titleText;
  const head = document.createElement("thead");
  const headRow = document.createElement("tr");
  for (const column of columns) {
    const header = document.createElement("th");
    header.scope = "col";
    header.className = `table-column--${column.role}`;
    header.textContent = column.label;
    headRow.append(header);
  }
  head.append(headRow);
  const body = document.createElement("tbody");
  for (const values of rows) {
    const row = document.createElement("tr");
    row.append(...values.map((value, index) => referenceCell(value, columns[index].role)));
    body.append(row);
  }
  table.append(caption, head, body);
  section.append(title, tableViewport(table));
  return section;
}

function hackingProgramLink(row) {
  const link = document.createElement("a");
  link.href = `/hacking-programs/${encodeURIComponent(row.slug || row.id || row.position)}`;
  link.textContent = row.name;
  return link;
}

function hackingDeviceLinks(devices) {
  if (!devices?.length) return "Granted separately / Upgrade";
  const fragment = document.createDocumentFragment();
  for (const [index, device] of devices.entries()) {
    if (index) fragment.append(", ");
    if (device.slug) {
      const link = document.createElement("a");
      link.href = `/equipment/${encodeURIComponent(device.slug)}`;
      link.textContent = device.name;
      fragment.append(link);
    } else {
      fragment.append(device.name);
    }
  }
  return fragment;
}

function declarationCategoryBadges(categories) {
  if (!categories?.length) return "—";
  const badges = document.createElement("span");
  badges.className = "detail-badges";
  for (const category of categories) {
    badges.append(skillCategoryBadge(category));
  }
  return badges;
}
function structuredReferenceSection(reference) {
  if (!reference?.rows?.length) return null;
  if (reference.kind === "hacking-programs") {
    return structuredTable(
      reference.title,
      [
        { label: "Program", role: "primary" },
        { label: "Attack MOD", role: "metric" },
        { label: "Opponent MOD", role: "metric" },
        { label: "PS", role: "metric" },
        { label: "B", role: "metric" },
        { label: "Target", role: "descriptor" },
        { label: "Type(s)", role: "descriptor" },
        { label: "Device", role: "descriptor" },
        { label: "Special", role: "descriptor" },
      ],
      reference.rows.map((row) => [
        hackingProgramLink(row),
        row.attack_mod,
        row.opponent_mod,
        row.ps,
        row.burst,
        row.targets?.length ? row.targets.join(", ") : "—",
        declarationCategoryBadges(row.declaration_categories),
        hackingDeviceLinks(row.devices),
        row.special,
      ]),
    );
  }
  if (reference.kind === "martial-arts") {
    // Current N5 rows have no PS MOD; retain it if a future Army source fills this field.
    const hasPsMod = reference.rows.some(
      (row) => row.ps_mod !== null && row.ps_mod !== undefined
        && row.ps_mod !== "" && row.ps_mod !== "-",
    );
    return structuredTable(
      reference.title,
      [
        { label: "Level", role: "metric" },
        { label: "Attack MOD", role: "metric" },
        { label: "Opponent MOD", role: "metric" },
        ...(hasPsMod ? [{ label: "PS MOD", role: "metric" }] : []),
        { label: "Burst MOD", role: "metric" },
      ],
      reference.rows.map((row) => [
        row.level, row.attack_mod, row.opponent_mod,
        ...(hasPsMod ? [row.ps_mod] : []), row.burst_mod,
      ]),
    );
  }
  if (reference.kind === "random-chart") {
    return structuredTable(
      reference.title,
      [
        { label: "Roll", role: "metric" },
        { label: "Result", role: "descriptor" },
      ],
      reference.rows.map((row) => [row.roll, randomChartOutcome(row)]),
    );
  }
  return null;
}

function variantSection(variant, parameterSemantics) {
  const section = document.createElement("details");
  section.className = "surface surface--clipped content-frame army-profile";
  const heading = document.createElement("summary");
  heading.className = "surface-titlebar surface-titlebar--subtle army-profile-title";
  const title = document.createElement("h2");
  title.textContent = formatVariantName(variant, parameterSemantics);
  const count = document.createElement("span");
  count.className = "section-index";
  const semanticLabel = sourceVariantLabel(variant);
  const unitCount = `${variant.units.length} ${variant.units.length === 1 ? "unit" : "units"}`;
  const summaryParts = [semanticLabel, unitCount].filter(Boolean);
  count.textContent = summaryParts.join(" · ");
  heading.append(title, count);
  section.append(heading);
  section.addEventListener("toggle", () => {
    if (!section.open || section.dataset.loaded) return;
    const table = document.createElement("table");
    table.className = "data-table--compact data-table--listing data-table--unit-list data-table--unit-usage data-table--interactive";
    table.innerHTML = "<caption class=\"sr-only\">Units using this skill variant</caption><thead><tr><th class=\"table-column--primary\" scope=\"col\">Unit</th><th class=\"table-column--descriptor\" scope=\"col\">Armies</th><th class=\"id-column table-column--technical\" scope=\"col\">ID</th></tr></thead>";
    const body = document.createElement("tbody");
    renderUnitRows(body, variant.units);
    table.append(body);
    section.append(tableViewport(table));
    section.dataset.loaded = "true";
  });
  return section;
}

function collectionLabel(collection) {
  if (collection === "n5-core") return "Core N5";
  return collection.startsWith("its-") ? `ITS ${collection.slice(4)}` : collection;
}

function scenarioContextLink(scenario) {
  const link = document.createElement("a");
  const query = new URLSearchParams({ collection: scenario.collection, army_points: "300" });
  if (scenario.revision) query.set("revision", scenario.revision);
  link.href = `/scenarios/${encodeURIComponent(scenario.slug)}?${query}`;
  link.textContent = `${collectionLabel(scenario.collection)} — ${scenario.name}`;
  return link;
}

function applicableContexts(skill) {
  const scenarios = skill.scenarios || [];
  const seasons = skill.seasons || [];
  if (!scenarios.length && !seasons.length) return null;
  const section = document.createElement("section");
  section.className = "detail-group scenario-skill-contexts";
  const heading = document.createElement("h2");
  heading.className = "detail-heading";
  heading.textContent = scenarios.length ? "Applicable scenarios" : "Applicable seasons";
  const list = document.createElement("ul");
  list.className = "detail-list";
  for (const scenario of scenarios) {
    const item = document.createElement("li");
    item.append(scenarioContextLink(scenario));
    list.append(item);
  }
  for (const season of seasons) {
    const item = document.createElement("li");
    item.textContent = `${collectionLabel(season.collection)} — ${season.revision}`;
    list.append(item);
  }
  section.append(heading, list);
  return section;
}

function contextualSkillRules(skill) {
  if (!skill.context_variants?.length) return null;
  const section = document.createElement("section");
  section.className = "detail-group scenario-skill-variants";
  const heading = document.createElement("h2");
  heading.className = "detail-heading";
  heading.textContent = "Season and scenario differences";
  const note = document.createElement("p");
  note.className = "detail-copy";
  note.textContent = "Use the exact rule for your selected season and scenario.";
  section.append(heading, note);
  for (const variant of skill.context_variants) {
    const contexts = [
      ...variant.scenarios.map((scenario) =>
        `${collectionLabel(scenario.collection)} — ${scenario.name}`),
      ...variant.seasons.map((season) =>
        `${collectionLabel(season.collection)} — ${season.revision}`),
    ];
    // A variant groups mechanically identical definitions. Display one
    // card with their combined context and citations, not repeated cards.
    const rules = variant.rules;
    const first = rules[0];
    if (!first) continue;
    const citations = [...new Map(rules.flatMap((rule) => rule.citations || [])
      .map((citation) => [JSON.stringify(citation), citation])).values()];
    const rule = {
      ...first,
      scope: {
        ...first.scope,
        seasons: [...new Set(rules.flatMap((entry) => entry.scope?.seasons || []))],
        scenarios: [...new Set(rules.flatMap((entry) => entry.scope?.scenarios || []))],
      },
      applicable_scenarios: variant.scenarios,
      citations,
    };
    section.append(rulesReferenceSection([rule], contexts.join(" · ")));
  }
  return section;
}

function render(skill) {
  displayedSkill = skill;
  document.title = `${skill.name} · InfinityDB`;
  name.firstChild.textContent = skill.name;
  const categories = (skill.categories || []).map((category) => category.name).join(", ");
  if (skill.wiki) {
    const link = document.createElement("a");
    link.href = skill.wiki;
    link.target = "_blank";
    link.rel = "noopener noreferrer";
    link.textContent = displayWikiUrl(skill.wiki);
    meta.replaceChildren(link);
    if (categories) meta.append(` · ${categories}`);
  } else {
    meta.textContent = `Skill #${skill.id}${categories ? ` · ${categories}` : ""}`;
  }
  const variants = [...skill.variants].sort((left, right) => (
    formatVariantName(left, skill.parameter_semantics).localeCompare(
      formatVariantName(right, skill.parameter_semantics),
      undefined,
      { sensitivity: "base", numeric: true },
    )
  ));
  const sections = document.createElement("section");
  sections.className = "detail-group usage-section-group";
  const children = [];
  if (skill.scenario) {
    const context = document.createElement("p");
    context.className = "detail-copy";
    context.append("Scenario-specific Skill for ");
    context.append(scenarioContextLink(skill.scenario));
    children.push(context);
  }
  if (skill.canonical_slug) {
    const context = document.createElement("p");
    context.className = "detail-copy";
    const link = document.createElement("a");
    link.href = `/skills/${encodeURIComponent(skill.canonical_slug)}`;
    link.textContent = "View all applicable contexts";
    context.append(link);
    children.push(context);
  }
  if (skill.rules?.length) {
    children.push(rulesReferenceSection(
      skill.rules, skill.context_variants?.length ? "Common mechanics" : "Rules reference",
    ));
  }
  const applicable = applicableContexts(skill);
  if (applicable) children.push(applicable);
  const contextualRules = contextualSkillRules(skill);
  if (contextualRules) children.push(contextualRules);
  const variantRules = gameplayVariantRules(variants);
  if (variantRules.length) children.push(rulesReferenceSection(variantRules, "Variant rules"));
  const context = restrictionsData && restrictionsContextSection(
    restrictionsData, (skill.rules || []).map((rule) => rule.id),
  );
  if (context) children.push(context);
  const structuredReference = structuredReferenceSection(skill.structured_reference);
  if (structuredReference) children.push(structuredReference);
  if (faqItems.length) children.push(faqRulingsSection(faqItems));
  const exactSection = exactVariantUsageSection(exactUsage, currentSkill || skill);
  if (exactSection) children.push(exactSection);
  children.push(sections);
  sections.append(...variants.map((variant) => variantSection(variant, skill.parameter_semantics)));
  content.replaceChildren(...children);
  status.hidden = true;
  content.hidden = false;
}

getRestrictionsReference(pageController.signal).then((data) => {
  if (pageController.signal.aborted) return;
  restrictionsData = data;
  if (displayedSkill) render(displayedSkill);
}).catch((error) => {
  if (error.name !== "AbortError") console.error("Restrictions chart unavailable", error);
});

document.addEventListener(
  "infinity:beforenavigation",
  () => pageController.abort(),
  { once: true },
);
window.addEventListener("distanceunitchange", () => {
  if (currentSkill) render(currentSkill);
}, { signal: pageController.signal });
if (!skillId) {
  name.firstChild.textContent = "Skill unavailable";
  status.textContent = "This Skill link is invalid.";
} else {
  getCatalogItem("skills", skillId, pageController.signal).then((skill) => {
    currentSkill = skill;
    render(skill);
    const topicId = skill.rules?.find((rule) => rule.id?.startsWith("skill:"))?.id
      || `skill:${skillId}`;
    loadExactVariantUsage(skill, "skill", pageController.signal, (payload) => {
      exactUsage = payload;
      if (displayedSkill) render(displayedSkill);
    });
    fetchReviewedFaqRulings(topicId, { signal: pageController.signal })
      .then((payload) => {
        if (pageController.signal.aborted) return;
        faqItems = payload.items || [];
        if (faqItems.length && displayedSkill) render(displayedSkill);
      })
      .catch((error) => {
        if (error.name !== "AbortError") console.error("Could not load FAQ clarifications", error);
      });
    return visibleUnitIds(optionalUnitFilters(), pageController.signal)
      .then((ids) => render(withVisibleUnits(skill, ids)));
  }).catch((error) => {
    if (error.name === "AbortError") return;
    name.firstChild.textContent = "Skill unavailable";
    status.textContent = referenceLoadMessage(error, "Skill");
    console.error("Could not load Skill detail", error);
  });
}
window.addEventListener("optionalunitschange", () => {
  if (!currentSkill) return;
  visibleUnitIds(optionalUnitFilters(), pageController.signal)
    .then((ids) => render(withVisibleUnits(currentSkill, ids)))
    .catch((error) => {
      if (error.name !== "AbortError") throw error;
    });
}, { signal: pageController.signal });
