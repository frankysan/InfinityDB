/** Same-origin catalog API. Page modules do not need to know transport details. */
async function get(path, signal) {
  const response = await fetch(path, { signal, headers: { Accept: "application/json" } });
  if (!response.ok) {
    throw new Error(`The database returned an error (${response.status}). Please try again.`);
  }
  return response.json();
}

export function getArmies(signal) {
  return get("/api/armies", signal);
}

export function getUnits({ armyId, search, limit, offset, mercs, specops, teamops }, signal) {
  const params = new URLSearchParams({ limit: String(limit), offset: String(offset) });
  if (armyId) params.set("army_id", armyId);
  if (search) params.set("search", search);
  if (mercs) params.set("mercs", "1");
  if (specops) params.set("specops", "1");
  if (teamops) params.set("teamops", "1");
  return get(`/api/units?${params}`, signal);
}

export function getUnit(unitId, signal) {
  return get(`/api/units/${encodeURIComponent(unitId)}`, signal);
}
