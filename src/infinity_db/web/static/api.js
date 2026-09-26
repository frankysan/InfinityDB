import { cacheBustedUrl } from "./preferences.js";

/** Same-origin catalog API. Page modules do not need to know transport details. */
async function get(path, signal) {
  const response = await fetch(cacheBustedUrl(path), {
    signal,
    cache: "no-store",
    headers: { Accept: "application/json" },
  });
  if (!response.ok) {
    let message = `The database returned an error (${response.status}). Please try again.`;
    try {
      const payload = await response.json();
      message = payload.error || message;
    } catch {
      // Preserve the status-based message when an intermediary returns non-JSON.
    }
    throw new Error(message);
  }
  return response.json();
}

export async function visibleUnitIds(signal) {
  const { optionalUnitFilters } = await import("./preferences.js");
  const filters = new URLSearchParams();
  for (const [name, enabled] of Object.entries(optionalUnitFilters())) {
    if (enabled) filters.set(name, "1");
  }
  const payload = await get(`/api/visible-unit-ids?${filters}`, signal);
  return new Set(payload.ids);
}

export function getArmies(signal) {
  return get("/api/armies", signal);
}

export function getFireteamArmies(signal) {
  return get("/api/fireteams", signal);
}

export function getFireteamChart(armyId, signal) {
  const params = new URLSearchParams({ army_id: armyId });
  return get(`/api/fireteams?${params}`, signal);
}

export function getCatalogItems(catalog, signal) {
  return get(`/api/${encodeURIComponent(catalog)}`, signal);
}

export function getCatalogItem(catalog, itemId, signal) {
  return get(`/api/${encodeURIComponent(catalog)}/${encodeURIComponent(itemId)}`, signal);
}

export function getSkillExtras(signal) {
  return get("/api/skill-extras", signal);
}

export function getVersion(signal) {
  return get("/api/version", signal);
}

export function getUnits({ armyId, declaredFactionId, search, skillId, equipmentId, weaponId, limit, offset, mercs, specops, teamops, reinforcement, descending }, signal) {
  const params = new URLSearchParams({ limit: String(limit), offset: String(offset) });
  if (armyId) params.set("army_id", armyId);
  if (declaredFactionId) params.set("declared_faction_id", declaredFactionId);
  if (search) params.set("search", search);
  if (skillId) params.set("skill_id", skillId);
  if (equipmentId) params.set("equipment_id", equipmentId);
  if (weaponId) params.set("weapon_id", weaponId);
  if (mercs) params.set("mercs", "1");
  if (specops) params.set("specops", "1");
  if (teamops) params.set("teamops", "1");
  if (reinforcement) params.set("reinforcement", "1");
  if (descending) params.set("order", "desc");
  return get(`/api/units?${params}`, signal);
}

export function getUnit(unitIdentifier, signal) {
  return get(`/api/units/${encodeURIComponent(unitIdentifier)}`, signal);
}
