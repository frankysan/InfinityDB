import { DISTANCE_CENTIMETERS_PER_INCH } from "./preferences.js";

export function formatMovement(move1, move2, unit) {
  const values = [move1, move2];
  if (values.some((value) => value == null || value === "")) return "—";
  if (values.every((value) => Number(value) === -1)) return "-";
  if (values.some((value) => Number(value) < 0)) return "—";
  if (unit === "in") {
    return `${values
      .map((value) => Number(value) / DISTANCE_CENTIMETERS_PER_INCH)
      .join("-")}\"`;
  }
  return `${values.join("-")} cm`;
}
