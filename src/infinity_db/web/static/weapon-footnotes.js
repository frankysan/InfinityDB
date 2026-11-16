// Reviewed source notation, not gameplay Traits. Exact N5.3 chart evidence:
// config/validation/mine-variant-effects.json (seven Mines),
// weapon-trait-wiki-review.json (Sepsitor Plus),
// weapon-trait-source-review.json (Chest Mine CC, Deactivator),
// data/curated/weapon-shared-effect-reviews.json (Blitzen, E/M Carbine,
// grenades and grenade launchers), and the cited E/M CC Weapon definition
// in data/curated/rules/n5-core-v5.3.json (p. 177). Source reviews pin
// N5.3 PDF SHA-256 53921e91c2d3d62ad5f7125abcd4174b2cf937d45320233eed5b6d301b66af3f.
const CATEGORIES = {
  "[*]": "Weaponry",
  "[**]": "Ammunition",
  "[***]": "Skills and Equipment",
};

const SOURCE_MARKERS = /\[\*{1,3}\]/g;

// This small, independently reviewed chart subset is intentionally not a
// general weapon-name heuristic. Match the reviewed catalog slug and exact
// mode (a mode-less review applies only to a mode-less source profile).
const REVIEWED_CHART = {
  "blitzen": { marker: "[**]", page: 178, ruleId: "ammunition:em" },
  "e-m-carbine": { marker: "[**]", page: 176, ruleId: "ammunition:em" },
  "e-m-cc-weapon": { marker: "[**]", page: 177, ruleId: "ammunition:em" },
  "smoke-grenades": { marker: "[**]", page: 178, ruleId: "ammunition:smoke" },
  "e-m-grenades": { marker: "[**]", page: 178, ruleId: "ammunition:em" },
  "eclipse-grenades": { marker: "[**]", page: 178, ruleId: "ammunition:eclipse" },
  "smoke-grenade-launcher": { marker: "[**]", page: 179, ruleId: "ammunition:smoke" },
  "e-m-grenade-launcher": { marker: "[**]", page: 179, ruleId: "ammunition:em" },
  "chest-mine": { marker: "[*]", page: 181, mode: "CC Mode", ruleId: "weapon:chest-mine" },
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

// N5.3 p. 186; exact reviewed cell in weapon-trait-source-review.json.
// This is the Equipment catalog identity, not a Weapon of the same name.
const REVIEWED_EQUIPMENT_CHART = {
  "deactivator": { marker: "[***]", page: 186, ruleId: "equipment:deactivator" },
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
  if (ruleId.startsWith("weapon:") || ruleId.startsWith("equipment:")) {
    const rules = [...(profile.rules || []), ...weaponRules];
    const kind = ruleId.split(":", 1)[0];
    const record = rules.find((rule) => rule.id === ruleId && rule.kind === kind);
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

export function weaponFootnotesForProfile(
  profile, weaponRules = [], weaponSlug = null, catalog = "weapons",
) {
  const review = catalog === "weapons" ? REVIEWED_CHART[weaponSlug]
    : catalog === "equipment" ? REVIEWED_EQUIPMENT_CHART[weaponSlug] : null;
  const chart = review && (review.mode
    ? profile.mode === review.mode : !profile.mode) ? review : null;
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
