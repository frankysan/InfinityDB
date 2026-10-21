import { getCatalogItems } from "./api.js";

const list = document.getElementById("deployed-list");
const loading = document.getElementById("deployed-loading");
const error = document.getElementById("deployed-error");
const count = document.getElementById("deployed-count");
const unresolved = document.getElementById("deployed-unresolved");

function sourceHref(catalog, id) {
  if (catalog === "weapon") return `/weapons/${encodeURIComponent(id)}`;
  if (catalog === "equipment") return `/equipment/${encodeURIComponent(id)}`;
  return null;
}

function labelledLink(label, href) {
  const link = document.createElement("a");
  link.href = href;
  link.textContent = label;
  return link;
}

function attributeRow(label, attribute) {
  const item = document.createElement("div");
  item.className = "weapon-data-row";
  const heading = document.createElement("h4");
  heading.className = "weapon-data-heading";
  heading.textContent = label;
  const value = document.createElement("p");
  value.className = "weapon-data-value";
  if (attribute.status === "unreported") {
    value.textContent = "Not reported";
  } else if (attribute.status === "disputed") {
    // The primary display value is preserved from the source; no precedence is inferred.
    value.append(`${attribute.value} (sources disagree: `);
    for (const [index, variant] of attribute.provenance.entries()) {
      if (index) value.append("; ");
      const source = variant.source;
      const reference = source.kind === "army"
        ? "Army" : source.kind === "printed" ? "N5.3 PDF" : "Curated";
      const page = source.page ? ` p. ${source.page}` : "";
      value.append(`${reference}${page}: ${variant.value}`);
    }
    value.append(")");
  } else {
    value.textContent = attribute.value;
  }
  item.append(heading, value);
  return item;
}

function entry(object) {
  const section = document.createElement("article");
  section.className = "detail-group deployed-object-entry";
  section.id = object.id;
  section.tabIndex = -1;

  const title = document.createElement("h3");
  title.className = "detail-section-heading";
  title.append(labelledLink(object.name, `#${object.id}`));
  section.append(title);

  const values = document.createElement("div");
  values.className = "deployed-object-attributes";
  for (const key of ["ARM", "BTS", "STR", "S"]) {
    values.append(attributeRow(key, object.attributes[key]));
  }
  section.append(values);

  const profile = object.sourceProfile;
  if (profile) {
    const source = document.createElement("p");
    source.className = "detail-copy";
    const href = sourceHref(profile.catalog, profile.sourceId);
    source.append("Source profile: ");
    if (href) {
      source.append(labelledLink(
        `${profile.name}${profile.mode ? ` — ${profile.mode}` : ""}`,
        href,
      ));
    } else {
      source.append(profile.name);
    }
    section.append(source);
  } else if (object.originRuleId) {
    const [domain, slug] = object.originRuleId.split(":", 2);
    const source = document.createElement("p");
    source.className = "detail-copy";
    source.append("Reviewed rules: ");
    const href = sourceHref(domain, slug);
    if (href) source.append(labelledLink(object.name, href));
    else source.append(object.originRuleId);
    section.append(source);
  }

  if (object.deliverySources.length) {
    const heading = document.createElement("h4");
    heading.className = "weapon-data-heading";
    heading.textContent = "Reviewed delivery sources";
    section.append(heading);
    const uses = document.createElement("ul");
    for (const delivery of object.deliverySources) {
      const [domain, slug] = delivery.recordId.split(":", 2);
      const li = document.createElement("li");
      const href = sourceHref(domain, slug);
      if (href) li.append(labelledLink(slug.replace(/-/g, " "), href));
      else li.append(delivery.recordId);
      li.append(` — ${delivery.method}`);
      uses.append(li);
    }
    section.append(uses);
  }
  return section;
}

function focusHashTarget() {
  const id = decodeURIComponent(window.location.hash.slice(1));
  if (!id) return;
  const target = document.getElementById(id);
  if (target?.classList.contains("deployed-object-entry")) {
    target.focus({ preventScroll: true });
    target.scrollIntoView({ block: "start" });
  }
}

async function load() {
  try {
    const result = await getCatalogItems("deployed-objects");
    for (const object of result.items) list.append(entry(object));
    count.textContent = `${result.items.length} reviewed`;
    if (result.unresolved_deliveries?.length) {
      unresolved.hidden = false;
      unresolved.textContent = "Some delivery identities remain unresolved (including Mine Dispenser's loadout-specific Mine subtype). These are not assigned to a generic deployed object.";
    }
    loading.hidden = true;
    list.hidden = false;
    focusHashTarget();
  } catch (reason) {
    loading.hidden = true;
    error.hidden = false;
    error.textContent = reason?.message || "The deployed-object reference is unavailable.";
    count.textContent = "Unavailable";
  }
}
window.addEventListener("hashchange", focusHashTarget);
load();
