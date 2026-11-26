import { DISTANCE_CENTIMETERS_PER_INCH, formatSkillDistanceExtra } from "./distance.js";

export function formatProfileItem(item, fallbackLabel) {
  const name = item.name || fallbackLabel;
  const hiddenIds = [];
  if (!item.name) hiddenIds.push(`${fallbackLabel} #${item.id ?? "—"}`);
  const extras = (item.extras || []).map((extra) => {
    const extraName = extra.name || "Extra";
    if (!extra.name) hiddenIds.push(`Extra #${extra.id ?? "—"}`);
    return extra.is_distance
      ? formatSkillDistanceExtra(extraName, item.parameter_semantics)
      : extraName;
  });
  const decoratedName = extras.length ? `${name} (${extras.join(", ")})` : name;
  const label = item.quantity != null && Number(item.quantity) !== 1
    ? `${decoratedName} ×${item.quantity}`
    : decoratedName;
  return { label, hiddenIds };
}

export function formatMovement(move1, move2, unit) {
  const values = [move1, move2];
  if (values.some((value) => value == null || value === "")) return "—";
  if (values.every((value) => Number(value) === -1)) return "—";
  if (values.some((value) => Number(value) < 0)) return "—";
  if (unit === "in") {
    return `${values
      .map((value) => Number(value) / DISTANCE_CENTIMETERS_PER_INCH)
      .join("-")}\"`;
  }
  return `${values.join("-")} cm`;
}
