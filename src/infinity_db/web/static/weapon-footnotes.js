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

// Source-scoped mappings, not a general weapon-name heuristic. The N5.3
// chart legend (p. 176) identifies the section, and the reviewed rule text
// identifies the target. Match the exact catalog slug and source mode.
// Additional target evidence: Ammunition pp. 63-67; Mixed Weapons p. 68;
// Perimeter Weapons p. 69; D-Charges p. 70; Drop Bears and Disco Baller p. 71;
// Mine Dispenser p. 72; Pitcher and Sepsitor p. 73; WildParrot p. 74.
const REVIEWED_CHART = {
  "blitzen": { marker: "[**]", page: 178, ruleId: "ammunition:em" },
  "e-m-carbine": { marker: "[**]", page: 176, ruleId: "ammunition:em" },
  "e-m-cc-weapon": { marker: "[**]", page: 177, ruleId: "ammunition:em" },
  "trench-hammer": [
    { marker: "[*]", page: 177, mode: "BS Mode", ruleId: "weapon:mixed-weapons" },
    { marker: "[*]", page: 177, mode: "CC Mode", ruleId: "weapon:mixed-weapons" },
  ],
  "vorpal-cc-weapon": [
    { marker: "[*]", page: 177, mode: "BS Mode", ruleId: "weapon:mixed-weapons" },
    { marker: "[*]", page: 177, mode: "CC Mode", ruleId: "weapon:mixed-weapons" },
  ],
  "smoke-grenades": { marker: "[**]", page: 178, ruleId: "ammunition:smoke" },
  "e-m-grenades": { marker: "[**]", page: 178, ruleId: "ammunition:em" },
  "eclipse-grenades": { marker: "[**]", page: 178, ruleId: "ammunition:eclipse" },
  "smoke-grenade-launcher": { marker: "[**]", page: 179, ruleId: "ammunition:smoke" },
  "e-m-grenade-launcher": { marker: "[**]", page: 179, ruleId: "ammunition:em" },
  "eclipse-grenade-launcher": { marker: "[**]", page: 179, ruleId: "ammunition:eclipse" },
  "chest-mine": [
    { marker: "[*]", page: 181, mode: "CC Mode", ruleId: "weapon:chest-mine" },
    // Both sources contain this marker; its exact target remains unverified.
    { marker: "[*]", page: 181, mode: "BS Mode", ruleId: null },
  ],
  "drop-bears": [
    { marker: "[*]", page: 181, mode: "BS Mode", ruleId: "weapon:drop-bears" },
    { marker: "[*]", page: 181, mode: "Deployable Mode", ruleId: "weapon:drop-bears" },
  ],
  "mine-dispenser": { marker: "[*]", page: 181, ruleId: "weapon:mine-dispenser" },
  "wildparrot": { marker: "[*]", page: 181, ruleId: "weapon:wildparrot" },
  "kobra-pistol": [
    { marker: "[*]", page: 182, mode: "BS Mode", ruleId: "weapon:mixed-weapons" },
    { marker: "[*]", page: 182, mode: "CC Mode", ruleId: "weapon:mixed-weapons" },
  ],
  "crazykoala": { marker: "[*]", page: 186, ruleId: "weapon:crazykoala" },
  "d-charges": [
    { marker: "[*]", page: 186, mode: "Demolition Mode", ruleId: "weapon:d-charges" },
    { marker: "[*]", page: 186, mode: "CC Mode", ruleId: "weapon:d-charges" },
  ],
  "disco-baller": { marker: "[*]", page: 186, ruleId: "weapon:disco-baller" },
  "e-marat": { marker: "[**]", page: 186, ruleId: "ammunition:em" },
  "e-mitter": { marker: "[**]", page: 186, ruleId: "ammunition:em" },
  "madtraps": { marker: "[*]", page: 187, ruleId: "weapon:madtraps" },
  "pitcher": { marker: "[*]", page: 187, ruleId: "weapon:pitcher" },
  "sepsitor": { marker: "[*]", page: 187, ruleId: "weapon:sepsitor" },
  "zapper": { marker: "[**]", page: 188, ruleId: "ammunition:em" },
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

// Equipment chart identities, not Weapons of the same name. The applicable
// definitions are in Skills and Equipment (FastPanda p. 122, GizmoKit p. 123,
// MediKit p. 124; Deactivator is reviewed in weapon-trait-source-review.json).
const REVIEWED_EQUIPMENT_CHART = {
  "deactivator": { marker: "[***]", page: 186, ruleId: "equipment:deactivator" },
  "fastpanda": { marker: "[***]", page: 186, ruleId: "equipment:fastpanda" },
  "gizmokit": { marker: "[***]", page: 187, ruleId: "equipment:gizmokit" },
  "medikit": { marker: "[***]", page: 187, ruleId: "equipment:medikit" },
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
  if (!review?.ruleId) return null;
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
  const candidates = Array.isArray(review) ? review : review ? [review] : [];
  const chart = candidates.find((candidate) => (
    (candidate.mode || "") === (profile.mode || "")
  ));
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
