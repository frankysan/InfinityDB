// N5.3 Weapon Chart legend. Army markers are source notation, not Traits.
// Link only when the published profile already identifies one exact rule owner.
const CATEGORIES = {
  "[*]": "Weaponry",
  "[**]": "Ammunition",
  "[***]": "Skills and Equipment",
};

export function isWeaponFootnote(value) {
  return typeof value === "string" && Object.hasOwn(CATEGORIES, value);
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

function targetForRule(rule) {
  return typeof rule?.id === "string" && rule.kind === "weapon"
    ? { label: rule.name || "Weaponry rule", href: `#rule-${rule.id.replaceAll(":", "-")}` }
    : null;
}

function targetsForMarker(marker, profile, weaponRules) {
  if (marker === "[*]") {
    const specific = (profile.rules || []).map(targetForRule).filter(Boolean);
    return specific.length ? specific : weaponRules.map(targetForRule).filter(Boolean);
  }
  if (marker === "[**]") {
    const parts = (profile.ammunition_parts || [])
      .map((part) => ({ label: part.text, href: href(part.public_reference) }))
      .filter((part) => part.href);
    if (parts.length) return parts;
    return (profile.rule_references || [])
      .filter((reference) => reference.kind === "ammunition")
      .map((reference) => ({ label: reference.name, href: href(reference.public_reference) }))
      .filter((reference) => reference.href);
  }
  if (marker === "[***]") {
    return (profile.rule_references || [])
      .filter((reference) => ["skill", "equipment"].includes(reference.kind))
      .map((reference) => ({ label: reference.name, href: href(reference.public_reference) }))
      .filter((reference) => reference.href);
  }
  return [];
}

export function weaponFootnotesForProfile(profile, weaponRules = []) {
  const seen = new Set();
  return (profile.traits || []).filter(isWeaponFootnote)
    .filter((marker) => {
      if (seen.has(marker)) return false;
      seen.add(marker);
      return true;
    })
    .map((marker) => {
      const distinct = new Map();
      for (const candidate of targetsForMarker(marker, profile, weaponRules)) {
        distinct.set(candidate.href, candidate);
      }
      // Several rules can be relevant, but that does not prove which the
      // original printed marker means for this exact weapon/mode.
      const target = distinct.size === 1 ? [...distinct.values()][0] : null;
      return {
        marker, category: CATEGORIES[marker], target,
        unresolved: target === null,
      };
    });
}
