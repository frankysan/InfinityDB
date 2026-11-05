import { shareStateHref } from "./share-state.js";
import { tableViewport } from "./view-components.js";

function signatureLabel(effect = {}) {
  const source = effect.sourceVariant;
  const labels = [];
  if (source?.kind === "level") labels.push(`Level ${source.value}`);
  else if (source?.kind === "named" && source.label) labels.push(source.label);
  else if (source?.kind === "attribute-replacement") {
    labels.push(`${source.attribute} = ${source.value}`);
  }
  if (effect.parameter?.label) labels.push(effect.parameter.label);
  else if (effect.parameter?.raw_value) labels.push(effect.parameter.raw_value);
  else if (effect.rawDistance) labels.push(`Distance ${effect.rawDistance}`);
  if (effect.combinationEffects?.length) labels.push("reviewed combination");
  return labels.join(" · ") || "Reviewed source signature";
}

function occurrenceContexts(rows) {
  const seen = new Set();
  const contexts = [];
  let sharedOptions = 0;
  for (const row of rows) {
    const context = row.context;
    if (row.ownerKind === "unit_option") {
      sharedOptions += 1;
      continue;
    }
    if (!["profile", "option"].includes(row.ownerKind)
        || !Number.isInteger(context?.logicalUnitId)
        || !Number.isInteger(context?.applicationArmyId)) continue;
    const key = JSON.stringify([
      context.applicationArmyId, context.logicalUnitId, row.ownerKind,
      row.groupId, row.parentId, context.payloadSha256,
    ]);
    if (seen.has(key)) continue;
    seen.add(key);
    contexts.push(row);
  }
  return { contexts, sharedOptions };
}

function occurrenceTable(rows, units) {
  const { contexts, sharedOptions } = occurrenceContexts(rows);
  const fragment = document.createDocumentFragment();
  if (contexts.length) {
    const table = document.createElement("table");
    table.className = "data-table--compact data-table--reference data-table--listing";
    table.innerHTML = "<caption class=\"sr-only\">Reviewed source profile and loadout occurrences</caption><thead><tr><th scope=\"col\">Unit</th><th scope=\"col\">Army</th><th scope=\"col\">Source context</th></tr></thead>";
    const body = document.createElement("tbody");
    for (const row of contexts) {
      const context = row.context;
      const unitId = context.logicalUnitId;
      const armyId = context.applicationArmyId;
      const unit = units.get(unitId);
      const matchingArmies = (unit?.armies || []).filter((army) => army.id === armyId);
      const army = matchingArmies[0];
      const anchor = matchingArmies.length === 1 && Number.isInteger(row.groupId)
        ? `#profile-group-${[army.id, ...(army.availability_flags || [])].join("-")}-${row.groupId}`
        : "";
      const link = document.createElement("a");
      link.href = shareStateHref(
        `/units/${encodeURIComponent(unit?.public_slug || unitId)}`,
        "unit", { army_id: String(armyId) },
      ) + anchor;
      link.textContent = unit?.name || `Unit #${unitId}`;
      const unitCell = document.createElement("th");
      unitCell.scope = "row";
      unitCell.append(link);
      const armyCell = document.createElement("td");
      armyCell.textContent = army?.name || `Army #${armyId}`;
      const contextCell = document.createElement("td");
      contextCell.textContent = row.ownerKind === "profile"
        ? `Profile group ${row.groupId} · source profile ${row.parentId}`
        : `Profile group ${row.groupId} · source loadout ${row.parentId}`;
      const tr = document.createElement("tr");
      tr.dataset.ownerKind = row.ownerKind;
      tr.append(unitCell, armyCell, contextCell);
      body.append(tr);
    }
    table.append(body);
    fragment.append(tableViewport(table));
  }
  if (sharedOptions) {
    const note = document.createElement("p");
    note.className = "detail-source";
    note.textContent = `${sharedOptions} shared Unit-option source ${sharedOptions === 1 ? "row has" : "rows have"} unverified Army compatibility and cannot be linked to an Army profile.`;
    fragment.append(note);
  }
  return fragment;
}

/** Only curated rule IDs actually attached to the canonical item are queried. */
export function exactVariantRuleIds(item, prefix) {
  const records = [
    ...(item.rules || []),
    ...(item.variants || []).flatMap((variant) => variant.rules || []),
  ];
  const pattern = prefix === "skill" ? /^skill:[a-z0-9][a-z0-9-]*$/
    : /^equipment:[a-z0-9][a-z0-9-]*$/;
  return [...new Set(records.map((rule) => rule.id).filter(
    (id) => typeof id === "string" && pattern.test(id),
  ))].sort();
}

/** Optional matched-publication view; never infer membership from catalog display names. */
export function exactVariantUsageSection(payload, item) {
  if (payload?.scope !== "exact-reviewed-source-variants" || !Array.isArray(payload.items)
      || !payload.items.length) return null;
  const units = new Map(
    (item.variants || []).flatMap((variant) => variant.units || [])
      .map((unit) => [unit.id, unit]),
  );
  const section = document.createElement("section");
  section.className = "detail-group usage-section-group exact-variant-usage";
  const heading = document.createElement("h2");
  heading.className = "detail-heading";
  heading.textContent = "Exact reviewed source occurrences";
  const description = document.createElement("p");
  description.className = "detail-source";
  description.textContent = "Only complete, source-reviewed variants are included. Counts are independent of optional Unit filters; unreviewed signatures are excluded. Profile/loadout source IDs identify the original Army context.";
  section.append(heading, description);

  for (const group of payload.items) {
    const details = document.createElement("details");
    details.className = "surface surface--clipped content-frame army-profile exact-variant-group";
    const summary = document.createElement("summary");
    summary.className = "surface-titlebar surface-titlebar--subtle army-profile-title";
    const label = document.createElement("strong");
    label.textContent = signatureLabel(group.variant?.effect);
    const count = document.createElement("span");
    count.className = "section-index";
    count.textContent = `${group.uniqueUnits} ${group.uniqueUnits === 1 ? "Unit" : "Units"} · ${group.sourceRelationshipRows} source rows`;
    summary.append(label, count);
    details.append(summary);
    details.addEventListener("toggle", () => {
      if (!details.open || details.dataset.loaded) return;
      details.append(occurrenceTable(group.sourceRows || [], units));
      details.dataset.loaded = "true";
    });
    section.append(details);
  }
  return section;
}
