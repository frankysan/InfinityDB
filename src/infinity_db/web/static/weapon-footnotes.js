// Reviewed source notation, not gameplay Traits. Exact current N5.3 chart
// evidence: config/validation/mine-variant-effects.json (seven Mines) and
// config/validation/weapon-trait-wiki-review.json (Sepsitor Plus).
// Both reviews pin PDF SHA-256 53921e91c2d3d62ad5f7125abcd4174b2cf937d45320233eed5b6d301b66af3f.
const CATEGORIES = {
  "[*]": "Weaponry",
  "[**]": "Ammunition",
  "[***]": "Skills and Equipment",
};

const SOURCE_MARKERS = /\[\*{1,3}\]/g;

// This small, independently reviewed chart subset is intentionally not a
// general weapon-name heuristic. Match only the exact single-mode catalog slug.
const REVIEWED_CHART = {
  "ap-mine": { marker: "[*]", page: 181, ruleId: "weapon:mines" },
  "e-m-mine": { marker: "[**]", page: 181, ruleId: "ammunition:em" },
  "monofilament-mine": { marker: "[*]", page: 181, ruleId: "weapon:mines" },
  "para-mine": { marker: "[*]", page: 181, ruleId: "weapon:mines", issue: "SRC-013" },
  "shock-mine": { marker: "[*]", page: 181, ruleId: "weapon:mines" },
  "viral-mine": { marker: "[*]", page: 181, ruleId: "weapon:mines" },
  "cybermine": { marker: "[*]", page: 181, ruleId: "weapon:cybermine" },
  "sepsitor-plus": {
    marker: "[*]", page: 187, ruleId: "weapon:sepsitor-plus", issue: "SRC-014",
  },
};

export function weaponFootnoteMarkers(value) {
  if (typeof value !== "string") return [];
  return value.match(SOURCE_MARKERS) || [];
}

export function isWeaponFootnote(value) {
  return typeof value === "string" && Object.hasOwn(CATEGORIES, value);
}

export function withoutWeaponFootnotes(reference) {
  const label = reference?.label;
  if (typeof label !== "string") return reference;
  const markers = weaponFootnoteMarkers(label);
  if (!markers.length) return reference;
  const text = label.replace(SOURCE_MARKERS, "").replace(/\s+/g, " ").trim();
  if (!text) return null;
  // Retain the original label for Developer Mode; do not infer a curated
  // reference for combined source text that had none.
  return {
    ...reference,
    name: reference.slug ? reference.name : text,
    source_alias: true,
  };
}

function href(reference) {
  if (typeof reference?.href === "string" && reference.href.startsWith("/")) {
    return reference.href;
  }
  if (typeof reference?.catalog === "string" && typeof reference?.id === "string") {
    return `/${reference.catalog}/${encodeURIComponent(reference.id)}`;
  }
  return null;
}

function reviewedTarget(review, profile, weaponRules) {
  if (!review) return null;
  const { ruleId } = review;
  if (ruleId.startsWith("weapon:")) {
    const rules = [...(profile.rules || []), ...weaponRules];
    const record = rules.find((rule) => rule.id === ruleId && rule.kind === "weapon");
    return record ? {
      label: record.name || ruleId,
      href: `#rule-${ruleId.replaceAll(":", "-")}`,
    } : null;
  }
  if (ruleId.startsWith("ammunition:")) {
    const references = [
      ...(profile.ammunition_parts || []).map((part) => ({
        id: part.public_reference?.id, label: part.text,
        public_reference: part.public_reference,
      })),
      ...(profile.rule_references || []).map((ref) => ({
        id: ref.id, label: ref.name, public_reference: ref.public_reference,
      })),
    ];
    const slug = ruleId.slice("ammunition:".length);
    const match = references.find((ref) => (
      (ref.id === slug || ref.id === ruleId)
      && ref.public_reference?.catalog === "ammunition"
    ));
    const targetHref = href(match?.public_reference);
    return targetHref ? { label: match.label || ruleId, href: targetHref } : null;
  }
  return null;
}

export function weaponFootnotesForProfile(profile, weaponRules = [], weaponSlug = null) {
  const chart = profile.mode ? null : REVIEWED_CHART[weaponSlug];
  const chartTarget = reviewedTarget(chart, profile, weaponRules);
  const seen = new Set();
  const army = (profile.traits || [])
    .flatMap(weaponFootnoteMarkers)
    .filter((marker) => {
      if (seen.has(marker)) return false;
      seen.add(marker);
      return true;
    })
    .map((marker) => ({
      marker, category: CATEGORIES[marker], source: "Army",
      target: chart?.marker === marker ? chartTarget : null,
      unresolved: chart?.marker !== marker || chartTarget === null,
      mismatch: Boolean(chart && chart.marker !== marker),
    }));
  if (chart) {
    if (army.length === 1 && seen.has(chart.marker)) {
      army[0].source = `Army and N5.3 chart p. ${chart.page}`;
    } else {
      army.push({
        marker: chart.marker, category: CATEGORIES[chart.marker],
        source: `N5.3 chart p. ${chart.page}`, target: chartTarget,
        unresolved: chartTarget === null,
        mismatch: Boolean(chart.issue && (!seen.has(chart.marker) || seen.size > 1)),
        issue: chart.issue,
      });
    }
  }
  return army;
}
