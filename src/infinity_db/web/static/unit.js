import { getUnit, getUnitProfileHelp } from "./api.js";
import { maintainedTextFragment } from "./maintained-text.js";
import { readShareState, shareStateHref, writeShareState } from "./share-state.js";
import { staticSymbolPath } from "./unit-symbols.js";
import { formatMovement } from "./unit-presentation.js";
import { distanceUnit, formatSkillDistanceExtra, initializeDistanceUnitToggle, optionalUnitFilters } from "./preferences.js";

const name = document.getElementById("unit-name");
const meta = document.getElementById("unit-meta");
const status = document.getElementById("unit-status");
const content = document.getElementById("unit-content");
const pageController = new AbortController();
const unitIdentifier = /^\/units\/([a-z0-9]+(?:-[a-z0-9]+)*)$/.exec(window.location.pathname)?.[1];
const requestedArmyIdentifier = readShareState("unit").params.get("army_id") || "";
writeShareState("unit", requestedArmyIdentifier ? { army_id: requestedArmyIdentifier } : {}, { replace: true });
let profileHelpEntries = new Map();
let attributeHelpEntries = new Map();

function text(value) { return value == null || value === "" ? "—" : String(value); }

function attributeReferenceLabel(label) {
  const item = attributeHelpEntries.get(label);
  if (!item) return document.createTextNode(label);
  return maintainedTextFragment([{
    type: "reference",
    target: item.id,
    label,
    public_reference: { href: item.href },
    preview_tokens: [{ type: "text", text: item.description }],
  }]);
}

function groupArmiesByFaction(armies) {
  const groups = new Map();
  for (const army of armies) {
    const faction = army.faction;
    const key = faction?.id ?? "other";
    if (!groups.has(key)) groups.set(key, {
      key,
      name: faction?.name || "Other armies",
      order: faction?.id ?? Number.MAX_SAFE_INTEGER,
      armies: [],
    });
    groups.get(key).armies.push(army);
  }
  return [...groups.values()]
    .sort((left, right) => left.order - right.order)
    .map((group) => ({
      ...group,
      armies: group.armies.sort((left, right) => (
        Number(left.id) - Number(right.id)
        || Number((left.availability_flags || []).includes("mercs"))
          - Number((right.availability_flags || []).includes("mercs"))
      )),
    }));
}

function cell(value) {
  const structured = value && typeof value === "object";
  const element = document.createElement(structured && value.header ? "th" : "td");
  const highlighted = structured && "highlight" in value;
  if (structured && value.content) element.append(value.content);
  else element.textContent = text(structured && "value" in value ? value.value : value);
  if (structured && value.header) element.scope = "row";
  if (value && typeof value === "object" && value.className) {
    element.classList.add(...value.className.split(/\s+/));
  }
  if (value && typeof value === "object" && value.colSpan) {
    element.colSpan = value.colSpan;
  }
  if (highlighted && value.highlight) {
    element.className = "stat-different";
    element.title = "Differs from the general profile";
  }
  return element;
}

function attributeStatline(
  stats,
  generalStats = null,
  includeAvailability = false,
  generalDifferenceLabels = null,
) {
  const attributes = document.createElement("div");
  attributes.className = "attribute-statline";
  for (const [label, read] of statColumns) {
    const attribute = document.createElement("div");
    if (label === "MOV") attribute.classList.add("movement-attribute");
    const attributeLabel = document.createElement("span");
    attributeLabel.className = "attribute-label";
    const attributeValue = document.createElement("span");
    attributeValue.className = "attribute-value";
    const value = displayStatlineValue(read(stats));
    attributeLabel.append(attributeReferenceLabel(statLabel(label, stats)));
    attributeValue.textContent = text(value);
    attribute.append(attributeLabel, attributeValue);
    if (generalDifferenceLabels?.has(label)) {
      const indicator = document.createElement("sup");
      indicator.className = "general-stat-difference-indicator";
      indicator.textContent = "*";
      indicator.title = "One or more Army profiles differ from this General profile stat";
      indicator.setAttribute("aria-label", indicator.title);
      attribute.title = indicator.title;
      attribute.append(indicator);
    }
    if (generalStats && differsFromGeneral(stats, generalStats, label)) {
      attribute.classList.add("stat-different");
      attribute.title = "Differs from the general profile";
    }
    attributes.append(attribute);
  }
  if (includeAvailability) {
    attributes.classList.add("attribute-statline-with-availability");
    const attribute = document.createElement("div");
    const attributeLabel = document.createElement("span");
    const attributeValue = document.createElement("span");
    attributeLabel.className = "attribute-label";
    attributeValue.className = "attribute-value";
    attributeLabel.append(attributeReferenceLabel("AVA"));
    attributeValue.textContent = text(displayAvailability(stats.ava));
    attribute.append(attributeLabel, attributeValue);
    attributes.append(attribute);
  }
  return attributes;
}

function table(headers, rows, className = "", captionText = "") {
  const element = document.createElement("table");
  element.className = className;
  if (captionText) {
    const caption = document.createElement("caption");
    caption.className = "sr-only";
    caption.textContent = captionText;
    element.append(caption);
  }
  if (headers.length) {
    const head = document.createElement("thead");
    const headerRow = document.createElement("tr");
    for (const header of headers) {
      const th = document.createElement("th");
      th.scope = "col";
      th.textContent = header;
      headerRow.append(th);
    }
    head.append(headerRow);
    element.append(head);
  }
  const body = document.createElement("tbody");
  for (const row of rows) {
    const tr = document.createElement("tr");
    if (row.className) tr.className = row.className;
    row.forEach((value, index) => {
      const item = cell(value);
      if (headers[index]) item.dataset.label = headers[index];
      tr.append(item);
    });
    body.append(tr);
  }
  element.append(body);
  return element;
}

function heading(label) { const value = document.createElement("h2"); value.textContent = label; return value; }

function subheading(label) { const value = document.createElement("h4"); value.textContent = label; return value; }

function profileHelpTargetId(key) {
  return `profile-help-${key}`;
}

function openProfileHelpTarget(key) {
  const target = document.getElementById(profileHelpTargetId(key));
  const disclosure = target?.closest("details");
  if (disclosure) disclosure.open = true;
}

function profileHelpAnchor(key, ariaLabel = null) {
  if (!profileHelpEntries.has(key)) return null;
  const link = document.createElement("a");
  link.className = "profile-help-link";
  link.href = `#${profileHelpTargetId(key)}`;
  if (ariaLabel) link.setAttribute("aria-label", ariaLabel);
  link.addEventListener("click", () => openProfileHelpTarget(key));
  return link;
}

function profileHelpLabel(label, key) {
  const link = profileHelpAnchor(key);
  if (!link) return document.createTextNode(label);
  link.textContent = label;
  return link;
}

function renderProfileNotationHelp(items) {
  if (!items.length) return null;
  const disclosure = document.createElement("details");
  disclosure.id = "profile-notation-help";
  disclosure.className = "surface surface--subtle surface--clipped content-frame profile-notation-help";

  const summary = document.createElement("summary");
  const title = document.createElement("span");
  title.className = "profile-help-summary-title";
  title.textContent = "Profile notation";
  const hint = document.createElement("span");
  hint.className = "profile-help-summary-hint";
  hint.textContent = "How to read Unit Profiles";
  summary.append(title, hint);
  disclosure.append(summary);

  const body = document.createElement("div");
  body.className = "profile-help-body";
  const intro = document.createElement("p");
  intro.className = "profile-help-intro";
  intro.textContent = "InfinityDB keeps profile domains separate rather than flattening "
    + "the source notation. These notes explain the fields and symbols used below.";
  body.append(intro);

  const grid = document.createElement("div");
  grid.className = "profile-help-grid";
  for (const item of items) {
    const entry = document.createElement("article");
    entry.id = profileHelpTargetId(item.key);
    entry.className = "profile-help-entry";
    const heading = document.createElement("h3");
    heading.textContent = item.name;
    const copy = document.createElement("p");
    copy.textContent = item.summary;
    entry.append(heading, copy);
    grid.append(entry);
  }
  body.append(grid);
  disclosure.append(body);
  return disclosure;
}

const statColumns = [
  ["MOV", (profile) => formatMovement(profile.move_1, profile.move_2, distanceUnit())],
  ["CC", (profile) => profile.cc], ["BS", (profile) => profile.bs],
  ["PH", (profile) => profile.ph], ["WIP", (profile) => profile.wip],
  ["ARM", (profile) => profile.arm], ["BTS", (profile) => profile.bts],
  ["VITA", (profile) => profile.vitality], ["S", (profile) => profile.silhouette],
];

const statProperties = {
  CC: "cc", BS: "bs", PH: "ph", WIP: "wip", ARM: "arm", BTS: "bts",
  VITA: "vitality", S: "silhouette",
};

function isStructureProfile(profile) {
  return profile.is_structure === true || Number(profile.is_structure) === 1;
}

function statLabel(label, profile) {
  return label === "VITA" && isStructureProfile(profile) ? "STR" : label;
}

function displayStatlineValue(value) {
  return (typeof value === "number" && value < 0)
    || (typeof value === "string" && /^-\d+(?:\.\d+)?$/.test(value.trim()))
    ? "—"
    : value;
}

function displayAvailability(value) {
  return Number(value) >= 100 ? "Total" : displayStatlineValue(value);
}

function differsFromGeneral(profile, general, label) {
  if (label.startsWith("MOV")) {
    return profile.move_1 !== general.move_1 || profile.move_2 !== general.move_2;
  }
  if (label === "VITA" && isStructureProfile(profile) !== isStructureProfile(general)) {
    return true;
  }
  return profile[statProperties[label]] !== general[statProperties[label]];
}

function nameWithOrderSymbols(nameText, descriptors) {
  if (!descriptors.length) return nameText;
  const name = document.createElement("span");
  name.className = "order-symbol-name";
  for (const descriptor of descriptors) {
    const href = descriptor.href || null;
    const helpKey = descriptor.help_key || null;
    const helpLink = !href && helpKey
      ? profileHelpAnchor(helpKey, `${descriptor.label} profile help`)
      : null;
    const symbol = document.createElement("img");
    symbol.className = "order-symbol";
    symbol.src = staticSymbolPath(descriptor.symbol_path);
    symbol.alt = href || helpLink ? "" : descriptor.label;
    symbol.title = descriptor.label;
    if (href) {
      const link = document.createElement("a");
      link.className = "profile-symbol-link";
      link.href = href;
      link.setAttribute("aria-label", `${descriptor.label} equipment`);
      link.append(symbol);
      name.append(link);
    } else if (helpLink) {
      helpLink.classList.add("profile-symbol-help-link");
      helpLink.append(symbol);
      name.append(helpLink);
    } else {
      name.append(symbol);
    }
  }
  name.append(document.createTextNode(nameText));
  return name;
}

function generalProfileName(profile) {
  return nameWithOrderSymbols(profile.display_name, profile.symbol_descriptors || []);
}

function profileTitle(profile, profileSymbols = null) {
  const title = document.createElement("h3");
  title.className = "profile-title";
  const name = document.createElement("span");
  name.className = "profile-title-name";
  name.append(generalProfileName(profile));
  title.append(name);
  if (profileSymbols) title.append(profileSymbols);
  return title;
}

function generalProfileSymbols(profile) {
  if (!profile.symbol_path) return null;

  const symbols = document.createElement("div");
  symbols.className = "general-profile-symbols";
  symbols.setAttribute("aria-hidden", "true");
  const icon = document.createElement("img");
  icon.className = "unit-symbol general-profile-unit-symbol";
  icon.src = staticSymbolPath(profile.symbol_path);
  icon.alt = "";
  icon.width = 56;
  icon.height = 56;
  icon.loading = "lazy";
  icon.decoding = "async";
  icon.addEventListener("error", () => icon.remove(), { once: true });
  symbols.append(icon);
  return symbols;
}

function profileItems(items, catalog, fallbackLabel) {
  if (!items.length) return "—";
  const result = document.createDocumentFragment();
  items.forEach((item, index) => {
    const name = item.name || fallbackLabel;
    const hiddenIds = [];
    if (!item.name) hiddenIds.push(`${fallbackLabel} #${text(item.id)}`);
    const extras = (item.extras || []).map((extra) => {
      const extraName = extra.name || "Extra";
      if (!extra.name) hiddenIds.push(`Extra #${text(extra.id)}`);
      if (!extra.is_distance) return extraName;
      return formatSkillDistanceExtra(extraName, item.parameter_semantics);
    });
    const decoratedName = extras.length ? `${name} (${extras.join(", ")})` : name;
    const label = item.quantity != null && Number(item.quantity) !== 1
      ? `${decoratedName} ×${item.quantity}`
      : decoratedName;
    const link = document.createElement("a");
    const routeId = item.slug || item.id;
    link.href = `/${catalog}/${encodeURIComponent(routeId)}`;
    link.textContent = label;
    if (hiddenIds.length) {
      const details = document.createElement("span");
      details.className = "developer-only";
      details.textContent = ` (${hiddenIds.join(", ")})`;
      link.append(details);
    }
    if (index) result.append(", ");
    result.append(link);
  });
  return result;
}

function peripheralTypeLabel(item) {
  return item?.type_label || text(item?.type_id);
}


function unitLink(unit) {
  const link = document.createElement("a");
  const routeId = unit.slug || unit.id;
  link.href = `/units/${encodeURIComponent(routeId)}`;
  link.textContent = unit.name || `Unit #${text(unit.id)}`;
  return link;
}

function loadoutAnchorId(anchorScope, payloadId) {
  return `loadout-${anchorScope}-${payloadId}`;
}

function includeTargetLink(target, anchorScope) {
  const link = document.createElement("a");
  link.href = `#${loadoutAnchorId(anchorScope, target.loadout_payload_id)}`;
  const quantity = target.quantity != null && Number(target.quantity) !== 1
    ? ` ×${target.quantity}`
    : "";
  link.textContent = `${target.name || "Loadout"}${quantity}`;
  link.addEventListener("click", () => {
    const targetElement = document.getElementById(
      loadoutAnchorId(anchorScope, target.loadout_payload_id),
    );
    const details = targetElement?.closest("details");
    if (details) details.open = true;
  });
  return link;
}

function includeItems(items, anchorScope) {
  const result = document.createDocumentFragment();
  items.forEach((item, index) => {
    if (index) result.append(", ");
    result.append(includeTargetLink(item, anchorScope));
  });
  return result;
}

function appendIncludeRows(rows, item, anchorScope, colSpan = null) {
  if (!(item.includes || []).length) return;
  rows.push([
    { value: "Includes", header: true, className: "data-label profile-item-label" },
    {
      content: includeItems(item.includes, anchorScope),
      className: "profile-item-list",
      ...(colSpan ? { colSpan } : {}),
    },
  ]);
}

function peripheralItems(items) {
  const result = document.createDocumentFragment();
  items.forEach((item, index) => {
    const quantity = item.quantity != null && Number(item.quantity) !== 1
      ? ` ×${item.quantity}`
      : "";
    const label = `${item.name || "Peripheral"}${quantity} (${peripheralTypeLabel(item)})`;
    if (index) result.append(", ");
    result.append(document.createTextNode(label));
  });
  return result;
}

function peripheralAccessItems(accessItems) {
  const result = document.createDocumentFragment();
  accessItems.forEach((access, accessIndex) => {
    if (accessIndex) result.append("; ");
    const group = document.createElement("span");
    if (access.relationship === "access-pool") {
      group.title = "Access pool; this does not assign fixed Controller ownership.";
    }
    group.append(`${peripheralTypeLabel(access)}: `);
    (access.targets || []).forEach((target, targetIndex) => {
      if (targetIndex) group.append(", ");
      group.append(unitLink(target));
    });
    result.append(group);
  });
  return result;
}

function appendPeripheralRows(rows, item, colSpan = null) {
  if ((item.peripherals || []).length) {
    rows.push([
      { content: profileHelpLabel("Peripherals", "peripheral"), header: true, className: "data-label profile-item-label" },
      {
        content: peripheralItems(item.peripherals),
        className: "profile-item-list",
        ...(colSpan ? { colSpan } : {}),
      },
    ]);
  }
  if ((item.peripheral_access || []).length) {
    rows.push([
      { content: profileHelpLabel("Controller access", "peripheral"), header: true, className: "data-label profile-item-label" },
      {
        content: peripheralAccessItems(item.peripheral_access),
        className: "profile-item-list",
        ...(colSpan ? { colSpan } : {}),
      },
    ]);
  }
}

function profileGroupAnchorId(anchorScope, groupId) {
  return `profile-group-${anchorScope}-${groupId}`;
}

function profileGroupLabel(army, groupId) {
  const names = [];
  const addName = (value) => {
    if (value && !names.includes(value)) names.push(value);
  };
  for (const profile of army?.profiles || []) {
    if (Number(profile.group_id) === Number(groupId)) {
      addName(profile.display_name || profile.name);
    }
  }
  if (!names.length) {
    for (const loadout of army?.loadouts || []) {
      if (Number(loadout.group_id) === Number(groupId)) addName(loadout.name);
    }
  }
  return names.length ? names.join(" / ") : `Profile group ${groupId}`;
}

function openRelationshipTarget(link, targetId) {
  link.addEventListener("click", () => {
    const target = document.getElementById(targetId);
    const details = target?.closest("details");
    if (details) details.open = true;
  });
}

function profileGroupLink(army, groupId) {
  const label = profileGroupLabel(army, groupId);
  if (!army) return document.createTextNode(label);
  const anchorScope = [army.id, ...(army.availability_flags || [])].join("-");
  const targetId = profileGroupAnchorId(anchorScope, groupId);
  const link = document.createElement("a");
  link.href = `#${targetId}`;
  link.textContent = label;
  openRelationshipTarget(link, targetId);
  return link;
}

function dependencyOptionLinks(army, target) {
  const optionIds = new Set((target.options || []).map(Number));
  if (!army || !optionIds.size) return null;
  const loadouts = (army.loadouts || []).filter((loadout) => (
    Number(loadout.group_id) === Number(target.group_id)
      && optionIds.has(Number(loadout.option_id))
  ));
  if (!loadouts.length) return null;
  const result = document.createDocumentFragment();
  const anchorScope = [army.id, ...(army.availability_flags || [])].join("-");
  loadouts.forEach((loadout, index) => {
    if (index) result.append(", ");
    const payloadId = (loadout.loadout_payload_ids || [])[0];
    if (payloadId == null) {
      result.append(document.createTextNode(loadout.name || `Option ${loadout.option_id}`));
      return;
    }
    result.append(includeTargetLink({
      loadout_payload_id: payloadId,
      name: loadout.name || `Option ${loadout.option_id}`,
    }, anchorScope));
  });
  return result;
}

function selectionInstruction(minCount, maxCount) {
  const minimum = minCount == null ? null : Number(minCount);
  const maximum = maxCount == null ? null : Number(maxCount);
  if (minimum != null && maximum != null && minimum === maximum) {
    return `Select exactly ${minimum}`;
  }
  if (minimum != null && maximum != null) return `Select ${minimum}–${maximum}`;
  if (maximum != null) return `Select at most ${maximum}`;
  if (minimum != null && minimum > 0) return `Select at least ${minimum}`;
  return "Selection applies";
}

function uniqueConstraintMembers(members) {
  const unique = new Map();
  for (const member of members || []) {
    if (!unique.has(member.logical_unit_id)) unique.set(member.logical_unit_id, member);
  }
  return [...unique.values()];
}

function appendUnitLinks(parent, members) {
  members.forEach((member, index) => {
    if (index) parent.append(index === members.length - 1 ? " and " : ", ");
    parent.append(unitLink({
      id: member.logical_unit_id,
      slug: member.slug,
      name: member.name,
    }));
  });
}

function sourceDependencyParameters(relation, member, target) {
  const values = [];
  if (relation.min_count != null) values.push(`relation min ${relation.min_count}`);
  if (relation.max_count != null) values.push(`relation max ${relation.max_count}`);
  if (member.per_parent != null) values.push(`perParent ${text(member.per_parent)}`);
  if (target.source_group_selector != null) {
    values.push(`group selector ${target.source_group_selector}`);
  }
  if (target.min_count != null) values.push(`dependency min ${target.min_count}`);
  if (target.min_dependant != null) values.push(`minDependant ${target.min_dependant}`);
  return values;
}

function appendRelationProvenance(item, relation) {
  const provenance = document.createElement("span");
  provenance.className = "developer-only";
  provenance.textContent = ` · Army relation #${relation.relation_id}`;
  item.append(provenance);
}

function armyExplorerLink(army) {
  const link = document.createElement("a");
  const identifier = army.public_slug || army.slug || army.id;
  link.href = shareStateHref("/units", "units", { army_id: identifier });
  link.textContent = army.name || `Army ${army.id}`;
  return link;
}

function declaredFactionLink(membership) {
  const link = document.createElement("a");
  link.href = shareStateHref("/units", "units", { declared_faction_id: membership.source_faction_id });
  link.textContent = membership.name || `Faction ${membership.source_faction_id}`;
  return link;
}

function renderSourceNotes(unit, armies) {
  const sourceNotes = unit.source_notes || [];
  if (!sourceNotes.length) return null;
  const shownArmyIds = new Set(armies.map((army) => Number(army.id)));

  const section = document.createElement("section");
  section.className = "detail-group source-notes";
  const title = heading("Source notes");
  title.className = "detail-heading detail-heading--rule";
  section.append(title);

  const surface = document.createElement("div");
  surface.className = "surface surface--clipped content-frame connected-unit-surface source-notes-surface";
  const intro = document.createElement("p");
  intro.className = "army-relationship-intro developer-only";
  intro.textContent = "Each note applies only to its named source variant and Army context; "
    + "it is not a rule for every profile shown for this Unit.";
  surface.append(intro);

  const list = document.createElement("ul");
  list.className = "detail-list connected-unit-list";
  for (const sourceNote of sourceNotes) {
    const item = document.createElement("li");
    const sourceName = document.createElement("strong");
    sourceName.textContent = sourceNote.source_name;
    item.append(sourceName, ": ", sourceNote.note);
    const noteArmyIds = new Set(sourceNote.armies.map((army) => Number(army.id)));
    const appliesToAllShownArmies = shownArmyIds.size > 0
      && [...shownArmyIds].every((armyId) => noteArmyIds.has(armyId));
    if (sourceNote.armies.length && !appliesToAllShownArmies) {
      item.append(" Applies in ");
      sourceNote.armies.forEach((army, index) => {
        if (index) item.append(index === sourceNote.armies.length - 1 ? " and " : ", ");
        item.append(armyExplorerLink(army));
      });
      item.append(".");
    }
    const provenance = document.createElement("span");
    provenance.className = "developer-only";
    provenance.textContent = ` Â· Source Unit #${sourceNote.source_unit_id}`
      + (sourceNote.is_representative ? " (representative)" : "");
    item.append(provenance);
    list.append(item);
  }
  surface.append(list);
  section.append(surface);
  return section;
}

function renderArmyRelationships(unit, armies) {
  const uniqueArmies = [...new Map(armies.map((army) => [Number(army.id), army])).values()];
  const reinforcementRelations = uniqueArmies.filter((army) => (
    (army.parent_armies || []).length || (army.reinforcement_sections || []).length
  ));
  const declaredFactions = unit.declared_factions || [];
  if (!reinforcementRelations.length && !declaredFactions.length) return null;

  const section = document.createElement("section");
  section.className = "detail-group army-relationships developer-only";
  const title = heading("Army relationships");
  title.className = "detail-heading detail-heading--rule";
  section.append(title);

  const surface = document.createElement("div");
  surface.className = "surface surface--clipped content-frame connected-unit-surface army-relationship-surface";
  const intro = document.createElement("p");
  intro.className = "army-relationship-intro";
  intro.textContent = "Army availability is shown in the profile sections below. These links show "
    + "Reinforcement parentage and broader source-declared faction membership separately.";
  surface.append(intro);

  if (reinforcementRelations.length) {
    surface.append(subheading("Reinforcement Sections"));
    const list = document.createElement("ul");
    list.className = "detail-list connected-unit-list";
    for (const army of reinforcementRelations) {
      if ((army.parent_armies || []).length) {
        const item = document.createElement("li");
        item.append(armyExplorerLink(army), " is a Reinforcement Section for ");
        army.parent_armies.forEach((parent, index) => {
          if (index) item.append(index === army.parent_armies.length - 1 ? " and " : ", ");
          item.append(armyExplorerLink(parent));
        });
        item.append(".");
        list.append(item);
      }
      if ((army.reinforcement_sections || []).length) {
        const item = document.createElement("li");
        item.append(armyExplorerLink(army), " uses ");
        army.reinforcement_sections.forEach((reinforcement, index) => {
          if (index) {
            item.append(index === army.reinforcement_sections.length - 1 ? " and " : ", ");
          }
          item.append(armyExplorerLink(reinforcement));
        });
        item.append(army.reinforcement_sections.length === 1
          ? " as its Reinforcement Section."
          : " as its Reinforcement Sections.");
        list.append(item);
      }
    }
    surface.append(list);
  }

  if (declaredFactions.length) {
    surface.append(subheading("Declared faction membership"));
    const explanation = document.createElement("p");
    explanation.className = "army-relationship-note";
    explanation.textContent = "This source relationship is broader than current Army-list "
      + "availability. Follow a faction link to find other Units with the same declaration.";
    surface.append(explanation);
    const list = document.createElement("ul");
    list.className = "detail-list connected-unit-list";
    for (const membership of declaredFactions) {
      const item = document.createElement("li");
      item.append(declaredFactionLink(membership));
      if (!membership.has_army_list) {
        item.append(" — declared membership; this faction identity has no current Army list.");
      } else if (!membership.available) {
        item.append(" — declared membership only; no concrete current list occurrence for this Unit.");
      } else {
        item.append(" — also represented by current list availability below.");
      }
      const provenance = document.createElement("span");
      provenance.className = "developer-only";
      provenance.textContent = ` · Source faction #${membership.source_faction_id}`;
      item.append(provenance);
      list.append(item);
    }
    surface.append(list);
  }

  section.append(surface);
  return section;
}

function renderSelectionRelationships(unit, armies) {
  const visibleArmyIds = new Set(armies.map((army) => Number(army.id)));
  const constraints = (unit.selection_constraints || []).filter((relation) => (
    visibleArmyIds.has(Number(relation.army_id))
  ));
  const dependencies = (unit.group_dependencies || []).filter((relation) => (
    visibleArmyIds.has(Number(relation.army_id))
  ));
  if (!constraints.length && !dependencies.length) return null;

  const section = document.createElement("section");
  section.className = "detail-group selection-relationships developer-only";
  const title = heading("Selection relationships");
  title.className = "detail-heading detail-heading--rule";
  section.append(title);

  const surface = document.createElement("div");
  surface.className = "surface surface--clipped content-frame connected-unit-surface selection-relationship-surface";
  const intro = document.createElement("p");
  intro.className = "selection-relationship-intro";
  intro.textContent = "These source-defined relationships explain linked choices only; "
    + "InfinityDB does not validate complete Army Lists.";
  surface.append(intro);

  if (constraints.length) {
    surface.append(subheading("Selection constraints"));
    const list = document.createElement("ul");
    list.className = "detail-list connected-unit-list";
    for (const relation of constraints) {
      const item = document.createElement("li");
      const army = armies.find((candidate) => Number(candidate.id) === Number(relation.army_id));
      const armyName = army?.name || `Army ${relation.army_id}`;
      const context = document.createElement("strong");
      context.textContent = `${armyName}: `;
      item.append(context);
      const members = uniqueConstraintMembers(relation.members);
      if (relation.family === "same-logical-cross-context-exclusive") {
        item.append("Select exactly 1 occurrence of ");
        appendUnitLinks(item, members);
        item.append(" across its linked selection contexts.");
      } else if (relation.family === "cross-logical-shared-cardinality") {
        item.append(`${selectionInstruction(relation.min_count, relation.max_count)} total from `);
        appendUnitLinks(item, members);
        item.append(".");
      } else if (relation.family === "single-logical-cardinality") {
        item.append(`${selectionInstruction(relation.min_count, relation.max_count)} of `);
        appendUnitLinks(item, members);
        item.append(".");
      } else {
        item.append(`${selectionInstruction(relation.min_count, relation.max_count)} across `);
        appendUnitLinks(item, members);
        item.append(".");
      }
      appendRelationProvenance(item, relation);
      list.append(item);
    }
    surface.append(list);
  }

  if (dependencies.length) {
    surface.append(subheading("Profile-group dependencies"));
    const explanation = document.createElement("p");
    explanation.className = "selection-relationship-note";
    explanation.textContent = "Dependency direction is normalized; source selector parameters are shown "
      + "verbatim where InfinityDB does not yet assign broader list-building semantics.";
    surface.append(explanation);
    const list = document.createElement("ul");
    list.className = "detail-list connected-unit-list";
    for (const relation of dependencies) {
      const army = armies.find((candidate) => Number(candidate.id) === Number(relation.army_id));
      const armyName = army?.name || `Army ${relation.army_id}`;
      for (const member of relation.members || []) {
        for (const target of member.dependencies || []) {
          const item = document.createElement("li");
          const context = document.createElement("strong");
          context.textContent = `${armyName}: `;
          item.append(context, profileGroupLink(army, member.group_id), " depends on ",
            profileGroupLink(army, target.group_id));
          const optionLinks = dependencyOptionLinks(army, target);
          if (optionLinks) item.append(" for ", optionLinks);
          item.append(".");
          const parameters = sourceDependencyParameters(relation, member, target);
          if (parameters.length) {
            const sourceParameters = document.createElement("span");
            sourceParameters.className = "selection-source-parameters";
            sourceParameters.textContent = ` Source parameters: ${parameters.join(" · ")}.`;
            item.append(sourceParameters);
          }
          appendRelationProvenance(item, relation);
          list.append(item);
        }
      }
    }
    surface.append(list);
  }

  section.append(surface);
  return section;
}

function renderPeripheralRelationships(unit) {
  const types = unit.peripheral_types || [];
  const controllers = unit.peripheral_controllers || [];
  if (!types.length && !controllers.length) return null;

  const section = document.createElement("section");
  section.className = "detail-group peripheral-relationships";
  const title = heading("Peripheral relationships");
  title.className = "detail-heading detail-heading--rule";
  section.append(title);

  const surface = document.createElement("div");
  surface.className = "surface surface--clipped content-frame connected-unit-surface";
  if (types.length) {
    const type = document.createElement("p");
    type.className = "connected-unit-type";
    type.textContent = `Peripheral type: ${types.map((item) => item.label).join(", ")}`;
    surface.append(type);
  }
  if (controllers.length) {
    surface.append(subheading("Controllers"));
    const list = document.createElement("ul");
    list.className = "detail-list connected-unit-list";
    for (const access of controllers) {
      const item = document.createElement("li");
      item.append(unitLink(access.controller));
      const context = [
        access.army?.name,
        access.controller_option_name
          ? `${access.controller_kind === "profile" ? "Profile" : "Loadout"}: ${access.controller_option_name}`
          : null,
      ].filter(Boolean);
      if (context.length) {
        const detail = document.createElement("span");
        detail.className = "connected-unit-context";
        detail.textContent = ` — ${context.join(" · ")}`;
        item.append(detail);
      }
      if (access.relationship === "access-pool") {
        item.title = "This Controller can select this Peripheral from its access pool; no fixed ownership is implied.";
      }
      list.append(item);
    }
    surface.append(list);
  }
  section.append(surface);
  return section;
}

function generalProfileTableRows(profiles) {
  const rows = [];
  for (const profile of profiles) {
    rows.push(
      [
        { content: profileHelpLabel("Type", "troop-type"), header: true, className: "data-label general-item-label" },
        { value: profile.type_label || profile.type, className: "general-item-list" },
      ],
      [
        { content: profileHelpLabel("Classification", "classification"), header: true, className: "data-label general-item-label" },
        { value: profile.classification, className: "general-item-list" },
      ],
    );
    rows.push([
      { content: profileHelpLabel("Attributes", "attributes"), header: true, className: "data-label profile-attributes-label" },
      {
        content: attributeStatline(
          profile.stats,
          null,
          false,
          new Set(profile.different_stat_labels || []),
        ),
        className: "profile-attributes",
      },
    ]);
    for (const [label, property, fallbackLabel] of [
      ["Skills", "skills", "Skill"],
      ["Equipment", "equipment", "Equipment"],
      ["Weapons", "weapons", "Weapon"],
    ]) {
      if (!(profile.shared_items?.[property] || []).length) continue;
      rows.push([
        {
          content: profileHelpLabel(
            label,
            ["Equipment", "Weapons"].includes(label) ? "equipment-weapons" : null,
          ),
          className: "data-label general-item-label",
        },
        {
          content: profileItems(profile.shared_items[property], property, fallbackLabel),
          className: "general-item-list",
        },
      ]);
    }
  }
  return rows;
}

function profileTableRows(profiles, generalByIdentity, anchorScope) {
  return profiles.flatMap((profile) => {
    const generalProfile = generalByIdentity.get(profile.profile_identity);
    const generalStatsForProfile = generalProfile?.stats || null;
    const profileRow = [{ content: profileNameWithDivisionBadge(profile), header: true, colSpan: 2 }];
    profileRow.className = "profile-summary";
    const rows = [profileRow, [
      { content: profileHelpLabel("Attributes", "attributes"), header: true, className: "data-label profile-attributes-label" },
      {
        content: attributeStatline(profile, generalStatsForProfile, true),
        className: "profile-attributes",
      },
    ]];
    for (const [label, property, fallbackLabel] of [
      ["Skills", "skills", "Skill"],
      ["Equipment", "equipment", "Equipment"],
      ["Weapons", "weapons", "Weapon"],
    ]) {
      const items = profile.specific_items?.[property] || profile[property] || [];
      if (!items.length) continue;
      rows.push([
        {
          content: profileHelpLabel(
            label,
            ["Equipment", "Weapons"].includes(label) ? "equipment-weapons" : null,
          ),
          header: true,
          className: "data-label profile-item-label",
        },
        {
          content: profileItems(items, property, fallbackLabel),
          className: "profile-item-list",
        },
      ]);
    }
    appendIncludeRows(rows, profile, anchorScope);
    appendPeripheralRows(rows, profile);
    return rows;
  });
}

function profileNameWithDivisionBadge(profile) {
  const title = document.createElement("span");
  title.className = "profile-name-with-division";
  title.append(document.createTextNode(text(profile.name)));
  const divisions = new Set((profile.characteristics || []).map((characteristic) => (
    String(characteristic.name || "").toLowerCase()
  )));
  for (const division of ["surface", "deepspace"]) {
    if (!divisions.has(division)) continue;
    const badge = document.createElement("span");
    badge.className = `badge division-badge division-badge-${division}`;
    badge.textContent = division === "surface" ? "Surface" : "Deepspace";
    title.append(badge);
  }
  return title;
}

function loadoutTable(loadouts, anchorScope, anchoredPayloads) {
  return table(
    ["Name", "Points", "SWC"],
    loadouts.flatMap((loadout, index) => {
      const loadoutName = document.createDocumentFragment();
      for (const payloadId of loadout.loadout_payload_ids || []) {
        if (anchoredPayloads.has(payloadId)) continue;
        anchoredPayloads.add(payloadId);
        const anchor = document.createElement("span");
        anchor.id = loadoutAnchorId(anchorScope, payloadId);
        anchor.className = "loadout-anchor";
        anchor.setAttribute("aria-hidden", "true");
        loadoutName.append(anchor);
      }
      loadoutName.append(nameWithOrderSymbols(
        loadout.name, loadout.symbol_descriptors || [],
      ));
      const loadoutRow = [{ content: loadoutName }, loadout.points, loadout.swc];
      loadoutRow.className = index ? "profile-summary loadout-start" : "profile-summary";
      const rows = [loadoutRow];
      for (const [label, property, fallbackLabel] of [
        ["Skills", "skills", "Skill"],
        ["Equipment", "equipment", "Equipment"],
        ["Weapons", "weapons", "Weapon"],
      ]) {
        const items = loadout.specific_items?.[property] || loadout[property] || [];
        if (!items.length) continue;
        rows.push([
          {
            content: profileHelpLabel(
              label,
              ["Equipment", "Weapons"].includes(label) ? "equipment-weapons" : null,
            ),
            header: true,
            className: "data-label profile-item-label",
          },
          {
            content: profileItems(items, property, fallbackLabel),
            className: "profile-item-list",
            colSpan: 2,
          },
        ]);
      }
      appendIncludeRows(rows, loadout, anchorScope, 2);
      appendPeripheralRows(rows, loadout, 2);
      return rows;
    }),
    "data-table--compact loadout-table",
    "Loadouts",
  );
}

function profileLoadoutGroups(army) {
  const groups = new Map();
  for (const profile of army.profiles) {
    if (!groups.has(profile.group_id)) {
      groups.set(profile.group_id, { id: profile.group_id, profiles: [], loadouts: [] });
    }
    groups.get(profile.group_id).profiles.push(profile);
  }
  for (const loadout of army.loadouts) {
    if (!groups.has(loadout.group_id)) {
      groups.set(loadout.group_id, { id: loadout.group_id, profiles: [], loadouts: [] });
    }
    groups.get(loadout.group_id).loadouts.push(loadout);
  }
  return [...groups.values()];
}

function availabilityBadges(items = []) {
  const badges = document.createElement("span");
  badges.className = "availability-badges";
  for (const item of items) {
    const badge = document.createElement("span");
    badge.className = `badge availability-badge availability-badge-${item.flag}`;
    badge.textContent = item.label;
    badges.append(badge);
  }
  return badges;
}

function isStandardArmy(army) {
  const flags = army.availability_flags || [];
  return !flags.includes("mercs") && !flags.includes("reinforcement");
}

function compositeOptionOrderSummary(option) {
  return (option.orders || []).map((order, index) => {
    const count = Number(order.list) || Number(order.total) || 1;
    const singular = option.order_presentations?.[index]?.label || `${text(order.type)} Order`;
    const label = count === 1 ? singular : singular.replace(/Order$/, "Orders");
    return `${count} ${label}`;
  }).join(", ");
}

function compositeOptionTable(options, anchorScope) {
  return table(
    ["Composite option", "PTS", "SWC"],
    options.flatMap((option, index) => {
      const optionName = document.createDocumentFragment();
      const symbolDescriptors = [...new Map((option.order_presentations || [])
        .map((presentation) => presentation?.symbol_descriptor)
        .filter(Boolean)
        .map((descriptor) => [descriptor.type, descriptor])).values()];
      optionName.append(nameWithOrderSymbols(option.name, symbolDescriptors));
      const sourceId = document.createElement("span");
      sourceId.className = "developer-only";
      sourceId.textContent = ` (Unit #${option.source_unit_id}, option #${option.option_id})`;
      optionName.append(sourceId);
      const rows = [[
        { content: optionName },
        option.points,
        option.swc,
      ]];
      rows[0].className = index ? "profile-summary loadout-start" : "profile-summary";
      if (option.minis != null) {
        rows.push([
          { value: "Miniatures", header: true, className: "data-label profile-item-label" },
          { value: option.minis, colSpan: 2 },
        ]);
      }
      if ((option.orders || []).length) {
        rows.push([
          { value: "Orders", header: true, className: "data-label profile-item-label" },
          { value: compositeOptionOrderSummary(option), colSpan: 2 },
        ]);
      }
      appendIncludeRows(rows, option, anchorScope, 2);
      if (option.disabled) {
        rows.push([
          { value: "Availability", header: true, className: "data-label profile-item-label" },
          { value: "Unavailable in this source data", colSpan: 2 },
        ]);
      }
      return rows;
    }),
    "data-table--compact composite-option-table",
    "Composite options",
  );
}

function renderArmyProfile(army, generalByIdentity, expanded) {
  const section = document.createElement("details");
  const anchorScope = [army.id, ...(army.availability_flags || [])].join("-");
  section.className = "surface surface--clipped content-frame army-profile";
  section.open = expanded;
  const armyHeading = document.createElement("summary");
  armyHeading.className = "surface-titlebar surface-titlebar--subtle army-profile-title";
  armyHeading.textContent = army.name;
  const symbol = staticSymbolPath(army.symbol_path);
  if (symbol) {
    const icon = document.createElement("img");
    icon.className = "army-symbol army-profile-symbol";
    icon.src = symbol;
    icon.alt = "";
    icon.width = 34;
    icon.height = 34;
    icon.loading = "lazy";
    icon.decoding = "async";
    icon.title = army.name;
    armyHeading.prepend(icon);
  }
  armyHeading.append(availabilityBadges(army.availability_badges));
  section.append(armyHeading);
  if ((army.composite_options || []).length) {
    section.append(subheading("Composite options"));
    section.append(compositeOptionTable(army.composite_options, anchorScope));
  }
  const anchoredPayloads = new Set();
  for (const group of profileLoadoutGroups(army)) {
    const groupAnchor = profileGroupAnchorId(anchorScope, group.id);
    let groupAnchored = false;
    if (group.profiles.length) {
      const profilesHeading = subheading("Profiles");
      profilesHeading.className = "army-profiles-heading";
      profilesHeading.id = groupAnchor;
      groupAnchored = true;
      section.append(profilesHeading);
      section.append(table(
        [],
        profileTableRows(group.profiles, generalByIdentity, anchorScope),
        "data-table--compact profile-details-table",
        "Profiles",
      ));
    }
    if (group.loadouts.length) {
      const loadoutsHeading = subheading("Loadouts");
      if (!groupAnchored) loadoutsHeading.id = groupAnchor;
      section.append(loadoutsHeading);
      section.append(loadoutTable(
        group.loadouts,
        anchorScope,
        anchoredPayloads,
      ));
    }
  }
  return section;
}

function filteredProfilesNotice() {
  const notice = document.createElement("section");
  notice.className = "surface surface--subtle content-frame unit-filtered-notice";
  notice.setAttribute("role", "status");
  const title = document.createElement("h2");
  title.textContent = "Profiles filtered out";
  const message = document.createElement("p");
  message.textContent = "This Unit has profile details, but all of them are hidden by your current optional-unit settings. Enable the relevant optional-unit category in Settings to show them.";
  notice.append(title, message);
  return notice;
}

function render(unit, helpItems = [], attributeItems = []) {
  content.replaceChildren();
  profileHelpEntries = new Map(helpItems.map((item) => [item.key, item]));
  attributeHelpEntries = new Map(attributeItems.map((item) => [
    item.id.split(":").at(-1).toUpperCase(),
    item,
  ]));
  document.title = `${unit.name} · InfinityDB`;
  name.textContent = unit.name;
  const displayArmySymbol = staticSymbolPath(unit.display_army_symbol_path);
  if (displayArmySymbol) {
    const displayIcon = document.createElement("img");
    displayIcon.className = "army-symbol display-army-symbol display-army-symbol-detail";
    displayIcon.src = displayArmySymbol;
    displayIcon.alt = "";
    displayIcon.width = 48;
    displayIcon.height = 48;
    displayIcon.decoding = "async";
    displayIcon.title = unit.display_army_name
      || unit.armies.find((army) => army.id === unit.display_army_id)?.name
      || "Army symbol";
    name.prepend(displayIcon);
  }
  const unitMetadata = [
    unit.isc,
    unit.isc_abbr && `(${unit.isc_abbr})`,
  ].filter(Boolean);
  meta.replaceChildren(document.createTextNode(unitMetadata.join(" · ")));
  const unitIds = document.createElement("span");
  unitIds.className = "developer-only";
  unitIds.textContent = `${unitMetadata.length ? " · " : ""}Unit ${unit.source_ids.map((sourceId) => `#${sourceId}`).join(" / ")}`;
  meta.append(unitIds);
  status.hidden = true;
  const requestedArmy = unit.armies.find((army) => army.presentation_requested);
  const armies = unit.armies.filter((army) => army.presentation_visible);
  const generalProfiles = unit.general_profiles || [];
  const displayedGeneralProfiles = generalProfiles.filter(
    (profile) => profile.presentation_visible !== false,
  );
  const generalByIdentity = new Map(generalProfiles.map((profile) => [
    profile.profile_identity, profile,
  ]));
  const generalProfilesSection = document.createElement("section");
  generalProfilesSection.className = "detail-group general-profile-group";
  const displayFaction = unit.display_faction?.slug;
  if (displayFaction) {
    generalProfilesSection.classList.add(`general-profile-group--faction-${displayFaction}`);
  }
  const generalHeading = heading(
    displayedGeneralProfiles.length === 1 ? "General profile" : "General profiles",
  );
  generalHeading.className = "detail-heading detail-heading--rule";
  generalProfilesSection.append(generalHeading);
  for (const profile of displayedGeneralProfiles) {
    const generalProfile = document.createElement("section");
    generalProfile.className = "surface content-frame general-profile";
    const profileSymbols = generalProfileSymbols(profile);
    generalProfile.append(profileTitle(profile, profileSymbols), table(
      [],
      generalProfileTableRows([profile]),
      "statline",
      `${profile.display_name || "Unit"} general profile`,
    ));
    generalProfilesSection.append(generalProfile);
  }
  const profileHelp = renderProfileNotationHelp(helpItems);
  if (profileHelp) content.append(profileHelp);
  const profilesFilteredOut = armies.length === 0
    && unit.armies.some((army) => army.presentation_visible === false);
  content.append(profilesFilteredOut ? filteredProfilesNotice() : generalProfilesSection);
  const sourceNotes = renderSourceNotes(unit, armies);
  if (sourceNotes) content.append(sourceNotes);
  const armyRelationships = renderArmyRelationships(unit, unit.armies);
  if (armyRelationships) content.append(armyRelationships);
  const peripheralRelationships = renderPeripheralRelationships(unit);
  if (peripheralRelationships) content.append(peripheralRelationships);
  const selectionRelationships = renderSelectionRelationships(unit, armies);
  if (selectionRelationships) content.append(selectionRelationships);
  let standardArmyExpanded = false;
  const hasRequestedArmy = Boolean(requestedArmy);
  for (const group of groupArmiesByFaction(armies)) {
    const section = document.createElement("section");
    section.className = "detail-group faction-profile-group";
    const groupHeading = heading(group.name);
    groupHeading.className = "detail-heading detail-heading--rule";
    section.append(groupHeading);
    const profiles = document.createElement("div");
    profiles.className = "detail-group faction-profile-grid";
    for (const army of group.armies) {
      const expanded = hasRequestedArmy
        ? army === requestedArmy
        : !standardArmyExpanded && isStandardArmy(army);
      if (!hasRequestedArmy && expanded) standardArmyExpanded = true;
      profiles.append(renderArmyProfile(army, generalByIdentity, expanded));
    }
    section.append(profiles);
    content.append(section);
  }
  content.hidden = false;
}

document.addEventListener(
  "infinity:beforenavigation",
  () => pageController.abort(),
  { once: true },
);
initializeDistanceUnitToggle();

if (!unitIdentifier) {
  status.textContent = "The requested unit address is invalid.";
} else {
  const unitRequestOptions = () => ({
    optionalFilters: optionalUnitFilters(),
    armyId: requestedArmyIdentifier,
  });
  let currentUnit = null;
  let unitRequestNumber = 0;
  const fetchUnit = () => {
    const requestNumber = ++unitRequestNumber;
    return getUnit(unitIdentifier, unitRequestOptions(), pageController.signal)
      .then((unit) => ({ unit, requestNumber }));
  };
  Promise.all([
    fetchUnit(),
    getUnitProfileHelp(pageController.signal).catch((error) => {
      if (error.name === "AbortError") throw error;
      return { items: [] };
    }),
  ]).then(([initialUnit, help]) => {
    const helpItems = help.items || [];
    const attributeItems = help.attributes || [];
    currentUnit = initialUnit.unit;
    render(currentUnit, helpItems, attributeItems);
    window.addEventListener("distanceunitchange", () => {
      if (currentUnit) render(currentUnit, helpItems, attributeItems);
    }, { signal: pageController.signal });
    window.addEventListener("optionalunitschange", () => {
      fetchUnit().then(({ unit: updatedUnit, requestNumber }) => {
        if (requestNumber !== unitRequestNumber) return;
        currentUnit = updatedUnit;
        render(currentUnit, helpItems, attributeItems);
      }).catch((error) => {
        if (error.name !== "AbortError") console.error(error);
      });
    }, { signal: pageController.signal });
  }).catch((error) => {
    if (error.name === "AbortError") return;
    name.textContent = "Unit unavailable";
    status.textContent = error.message || "Could not load this unit.";
  });
}
