// Render the existing offline report; never upload, fetch, persist or reinterpret source data.
const PAGE_SIZE = 30;
const MAX_BYTES = 64 * 1024 * 1024;
const object = value => value !== null && typeof value === "object" && !Array.isArray(value);
const digest = value => typeof value === "string" && /^[a-f0-9]{64}$/.test(value);
const string = value => typeof value === "string" && value.length > 0;
const own = (value, key) => Object.hasOwn(value, key);
const requireShape = condition => {
  if (!condition) throw new Error("Invalid or unsupported Army snapshot diff report.");
};
const counts = value => object(value) && Object.values(value).every(
  count => Number.isSafeInteger(count) && count >= 0
);
const recorded = value => object(value) && typeof value.present === "boolean"
  && own(value, "value") === value.present;
const pathLabel = path => path.map(String).join(" / ");
const readable = value => value.replace(/([a-z0-9])([A-Z])/g, "$1 $2").replace(/^./, c => c.toUpperCase());
const classificationLabels = {
  gameplayCandidate: "Gameplay candidate",
  representation: "Representation only",
  review: "Needs review",
  effective: "Effective reference evidence",
};
const kindLabels = {
  added: "Appeared",
  removed: "Disappeared",
  updated: "Updated",
  effective: "Effective references",
  context: "Reference review",
};
function kindFor(category) {
  if (["observedKeyAppearance", "observedMemberAppearance"].includes(category)) return "added";
  if (["observedKeyDisappearance", "observedMemberDisappearance"].includes(category)) return "removed";
  return "updated";
}
function endpointValid(endpoint) {
  return object(endpoint) && digest(endpoint.archiveSha256) && digest(endpoint.manifestSha256)
    && (endpoint.contentSha256 === null || digest(endpoint.contentSha256))
    && string(endpoint.archiveName) && string(endpoint.acquiredAt)
    && object(endpoint.source) && string(endpoint.source.language)
    && object(endpoint.members) && object(endpoint.sourceRevisions)
    && Object.values(endpoint.members).every(member => object(member) && digest(member.sha256));
}
function fieldRow(change, member) {
  requireShape(object(change) && string(change.category)
    && ["gameplayCandidate", "representation", "review"].includes(change.classification)
    && Array.isArray(change.path) && change.path.every(part => string(part) || Number.isSafeInteger(part))
    && recorded(change.before) && recorded(change.after));
  return {
    member, kind: kindFor(change.category), classification: change.classification,
    title: pathLabel(change.path), category: change.category, detail: change, pair: true,
  };
}
export function parseReport(report) {
  requireShape(object(report) && report.format === "InfinityDB Army snapshot diff"
    && report.formatVersion === 1 && report.scope === "explicitEndpoints"
    && endpointValid(report.before) && endpointValid(report.after)
    && report.before.source.language === report.after.source.language
    && Number.isSafeInteger(report.sharedMemberCount) && report.sharedMemberCount >= 0
    && counts(report.changeCounts) && counts(report.effectiveReferenceCounts)
    && Array.isArray(report.limitations) && report.limitations.every(string)
    && Array.isArray(report.metadataChanges) && Array.isArray(report.comparisons));
  const rows = report.metadataChanges.map(change => fieldRow(change, "metadata.json"));
  const members = new Set();
  for (const comparison of report.comparisons) {
    requireShape(object(comparison) && string(comparison.member) && !members.has(comparison.member));
    const member = comparison.member;
    members.add(member);
    const before = own(report.before.members, member);
    const after = own(report.after.members, member);
    if (comparison.category !== "compared") {
      requireShape((comparison.category === "observedMemberAppearance" && !before && after)
        || (comparison.category === "observedMemberDisappearance" && before && !after));
      rows.push({
        member, kind: kindFor(comparison.category), classification: "review",
        title: "Army source member", category: comparison.category, detail: comparison,
      });
      continue;
    }
    requireShape(before && after && Array.isArray(comparison.changes)
      && Array.isArray(comparison.effectiveReferences)
      && Array.isArray(comparison.sharedReferenceMetadataFindings)
      && counts(comparison.beforeReferenceShapeIssues) && counts(comparison.afterReferenceShapeIssues));
    for (const change of comparison.changes) rows.push(fieldRow(change, member));
    for (const effect of comparison.effectiveReferences) {
      requireShape(object(effect) && string(effect.field)
        && Number.isSafeInteger(effect.unitId) && Number.isSafeInteger(effect.groupId)
        && (effect.category === "effectiveReview" && string(effect.reason)
          || ["effectiveOccurrenceChange", "effectiveOccurrenceEquivalent"].includes(effect.category)
            && Array.isArray(effect.lost) && Array.isArray(effect.gained)));
      const title = [
        "Unit " + effect.unitId, "Group " + effect.groupId,
        effect.profileId === undefined ? null : "Profile " + effect.profileId,
        effect.loadoutId === undefined ? null : "Loadout " + effect.loadoutId, effect.field,
      ].filter(Boolean).join(" / ");
      rows.push({
        member, kind: "effective", classification: effect.category === "effectiveReview" ? "review" : "effective",
        title, category: effect.category, detail: effect,
      });
    }
    for (const finding of comparison.sharedReferenceMetadataFindings) {
      requireShape(object(finding));
      rows.push({
        member, kind: "context", classification: "review", title: "Shared reference metadata",
        category: "Shared reference metadata finding", detail: finding,
      });
    }
    if (JSON.stringify(comparison.beforeReferenceShapeIssues) !== JSON.stringify(comparison.afterReferenceShapeIssues)) {
      rows.push({
        member, kind: "context", classification: "review", title: "Reference shape issues",
        category: "Reference shape review", detail: {
          before: comparison.beforeReferenceShapeIssues, after: comparison.afterReferenceShapeIssues,
        },
      });
    }
  }
  return rows;
}
function node(tag, content, className) {
  const element = document.createElement(tag);
  if (className) element.className = className;
  if (content !== undefined) element.textContent = String(content);
  return element;
}
function jsonBlock(value) {
  return node("pre", JSON.stringify(value, null, 2));
}
function recordedBlock(value) {
  return value.present ? jsonBlock(value.value) : node("p", "Not present", "detail-copy");
}
function detailBlock(label, value) {
  const details = node("details");
  details.append(node("summary", label), jsonBlock(value));
  return details;
}
function endpointCard(label, endpoint) {
  const card = node("div");
  card.append(node("h3", label), node("p", endpoint.archiveName),
    node("p", "Acquired: " + endpoint.acquiredAt, "detail-copy"),
    node("p", "Language: " + endpoint.source.language, "detail-copy"),
    node("p", "Revisions: " + Object.entries(endpoint.sourceRevisions)
      .map(([revision, count]) => revision + " (" + count + ")").join(", "), "detail-copy"),
    detailBlock("Recorded provenance", endpoint));
  return card;
}
function rowCard(row) {
  const details = node("details", undefined, "snapshot-change");
  const summary = node("summary");
  summary.append(node("strong", kindLabels[row.kind] + " · " + row.title),
    node("span", row.member + " · " + readable(row.category) + " · " + classificationLabels[row.classification],
      "detail-copy snapshot-change-meta"));
  details.append(summary);
  // Build large before/after payloads only when a row is opened.
  details.addEventListener("toggle", () => {
    if (!details.open || details.children.length > 1) return;
    if (row.pair) {
      const pair = node("div", undefined, "snapshot-pair");
      for (const [label, value] of [["Before", row.detail.before], ["After", row.detail.after]]) {
        const side = node("div");
        side.append(node("h4", label), recordedBlock(value));
        pair.append(side);
      }
      details.append(pair);
      if (row.detail.ancestorOrRecordLabelChanged) {
        details.append(node("p", "Record or ancestor label changed; identity requires review.", "detail-copy"));
      }
    }
    if (row.kind === "effective") {
      if (row.detail.category === "effectiveReview") {
        details.append(node("p", "Review reason: " + readable(row.detail.reason)));
      } else if (row.detail.category === "effectiveOccurrenceEquivalent") {
        details.append(node("p", "Effective occurrences equivalent in this compared context. Catalog definition changes are separate."));
      } else {
        const pair = node("div", undefined, "snapshot-pair");
        for (const [label, values] of [["Lost occurrences", row.detail.lost], ["Gained occurrences", row.detail.gained]]) {
          const side = node("div");
          side.append(node("h4", label + " (" + values.length + ")"));
          const list = node("ul");
          for (const value of values) {
            list.append(node("li", value?.filter?.name ?? JSON.stringify(value)));
          }
          side.append(values.length ? list : node("p", "None", "detail-copy"));
          pair.append(side);
        }
        details.append(pair);
      }
    }
    details.append(detailBlock("Exact report record", row.detail));
  });
  return details;
}
function options(select, values, labels = {}) {
  select.replaceChildren(new Option("All", ""));
  for (const value of values) {
    select.add(new Option(labels[value] || value, value));
  }
}
function start() {
  const input = document.getElementById("snapshot-report");
  const status = document.getElementById("snapshot-status");
  const review = document.getElementById("snapshot-review");
  const member = document.getElementById("snapshot-member");
  const kind = document.getElementById("snapshot-kind");
  const classification = document.getElementById("snapshot-classification");
  const search = document.getElementById("snapshot-search");
  const results = document.getElementById("snapshot-results");
  const count = document.getElementById("snapshot-count");
  const previous = document.getElementById("snapshot-previous");
  const next = document.getElementById("snapshot-next");
  let rows = [], page = 0, request = 0;
  document.addEventListener("infinity:beforenavigation", () => {
    request += 1;
    rows = [];
    input.value = "";
    review.hidden = true;
    results.replaceChildren();
  }, { once: true });
  function render() {
    const query = search.value.trim().toLowerCase();
    const filtered = rows.filter(row => (!member.value || row.member === member.value)
      && (!kind.value || row.kind === kind.value)
      && (!classification.value || row.classification === classification.value)
      && (!query || [row.member, row.title, row.category].join(" ").toLowerCase().includes(query)));
    const startIndex = page * PAGE_SIZE;
    const visible = filtered.slice(startIndex, startIndex + PAGE_SIZE);
    results.replaceChildren(...visible.map(rowCard));
    count.textContent = filtered.length
      ? (startIndex + 1) + "–" + (startIndex + visible.length) + " of " + filtered.length + " review entries"
      : "No matching review entries.";
    previous.disabled = page === 0;
    next.disabled = startIndex + PAGE_SIZE >= filtered.length;
  }
  for (const control of [member, kind, classification, search]) {
    control.addEventListener("input", () => { page = 0; render(); });
  }
  previous.addEventListener("click", () => { page -= 1; render(); });
  next.addEventListener("click", () => { page += 1; render(); });
  input.addEventListener("change", async () => {
    const selected = ++request;
    review.hidden = true;
    rows = [];
    results.replaceChildren();
    const file = input.files[0];
    if (!file) { status.textContent = "No report selected."; return; }
    status.textContent = "Reading local report…";
    try {
      if (file.size > MAX_BYTES) throw new Error("Report exceeds the 64 MiB browser limit.");
      const report = JSON.parse(await file.text());
      if (selected !== request) return;
      rows = parseReport(report);
      document.getElementById("snapshot-endpoints").replaceChildren(
        endpointCard("Before", report.before), endpointCard("After", report.after));
      const changed = Object.values(report.changeCounts).reduce((a, b) => a + b, 0);
      const effective = Object.values(report.effectiveReferenceCounts).reduce((a, b) => a + b, 0);
      document.getElementById("snapshot-summary").textContent =
        report.sharedMemberCount + " shared Army members · " + changed + " source differences · "
        + effective + " effective reference findings";
      document.getElementById("snapshot-limitations").replaceChildren(
        ...report.limitations.map(value => node("li", value)));
      options(member, [...new Set(rows.map(row => row.member))].sort());
      options(kind, Object.keys(kindLabels), kindLabels);
      options(classification, Object.keys(classificationLabels), classificationLabels);
      search.value = "";
      page = 0;
      render();
      review.hidden = false;
      status.textContent = "Local comparison report loaded.";
    } catch (error) {
      if (selected !== request) return;
      rows = [];
      status.textContent = error instanceof SyntaxError ? "Could not parse report JSON." : error.message;
    }
  });
}
if (typeof document !== "undefined") start();
