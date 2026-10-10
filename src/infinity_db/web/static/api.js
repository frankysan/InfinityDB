import { getJson } from "./api-transport.js";

/** Same-origin application API. Page modules do not need to know transport details. */
export async function visibleUnitIds(optionalFilters, signal) {
  const filters = new URLSearchParams();
  for (const [name, enabled] of Object.entries(optionalFilters)) {
    if (enabled) filters.set(name, "1");
  }
  const payload = await getJson(`/api/visible-unit-ids?${filters}`, signal);
  return new Set(payload.ids);
}

export function getArmies(signal) {
  return getJson("/api/armies", signal);
}

export function getFireteamArmies(signal) {
  return getJson("/api/fireteams", signal);
}

export function getFireteamChart(armyId, signal) {
  const params = new URLSearchParams({ army_id: armyId });
  return getJson(`/api/fireteams?${params}`, signal);
}

export function getCatalogItems(catalog, signal) {
  return getJson(`/api/${encodeURIComponent(catalog)}`, signal);
}

export function getCatalogItem(catalog, itemId, signal) {
  return getJson(`/api/${encodeURIComponent(catalog)}/${encodeURIComponent(itemId)}`, signal);
}

export function getUnitFilters(signal) {
  return getJson("/api/unit-filters", signal);
}

export function getUnitProfileHelp(signal) {
  return getJson("/api/unit-profile-help", signal);
}

export function getSkillExtras(signal) {
  return getJson("/api/skill-extras", signal);
}

export function getVersion(signal) {
  return getJson("/api/version", signal);
}

export function getSearchResults(query, signal) {
  return getJson(`/api/search?${new URLSearchParams({ q: query })}`, signal);
}

export function getGlossary(signal) {
  return getJson("/api/glossary", signal);
}

export function getScenarios(signal) {
  return getJson("/api/scenarios", signal);
}

export function getScenario(scenarioId, armyPoints, signal) {
  const params = new URLSearchParams({ army_points: String(armyPoints) });
  return getJson(`/api/scenarios/${encodeURIComponent(scenarioId)}?${params}`, signal);
}

export function getUnits({ armyId, declaredFactionId, search, skillId, equipmentId, weaponId, troopType, classification, characteristic, ava, avaMin, avaMax, points, pointsMin, pointsMax, swc, swcMin, swcMax, limit, offset, mercs, specops, teamops, reinforcement, descending, extended }, signal) {
  const params = new URLSearchParams({ limit: String(limit), offset: String(offset) });
  if (armyId) params.set("army_id", armyId);
  if (declaredFactionId) params.set("declared_faction_id", declaredFactionId);
  if (search) params.set("search", search);
  if (skillId) params.set("skill_id", skillId);
  if (equipmentId) params.set("equipment_id", equipmentId);
  if (weaponId) params.set("weapon_id", weaponId);
  if (troopType) params.set("troop_type", troopType);
  if (classification) params.set("classification", classification);
  if (characteristic) params.set("characteristic", characteristic);
  if (ava) params.set("ava", ava);
  if (avaMin) params.set("ava_min", avaMin);
  if (avaMax) params.set("ava_max", avaMax);
  if (points) params.set("points", points);
  if (pointsMin) params.set("points_min", pointsMin);
  if (pointsMax) params.set("points_max", pointsMax);
  if (swc) params.set("swc", swc);
  if (swcMin) params.set("swc_min", swcMin);
  if (swcMax) params.set("swc_max", swcMax);
  if (mercs) params.set("mercs", "1");
  if (specops) params.set("specops", "1");
  if (teamops) params.set("teamops", "1");
  if (reinforcement) params.set("reinforcement", "1");
  if (descending) params.set("order", "desc");
  if (extended) params.set("extended", "1");
  return getJson(`/api/units?${params}`, signal);
}

export function getUnit(
  unitIdentifier,
  { optionalFilters = {}, armyId = "" } = {},
  signal,
) {
  const params = new URLSearchParams();
  for (const key of ["mercs", "specops", "teamops", "reinforcement"]) {
    params.set(key, optionalFilters[key] === false ? "0" : "1");
  }
  if (armyId) params.set("army_id", armyId);
  const query = params.toString();
  return getJson(`/api/units/${encodeURIComponent(unitIdentifier)}${query ? `?${query}` : ""}`, signal);
}
