import { distanceUnit } from "./preferences.js";

const DISTANCE_NUMBER_PATTERN = /[+-]?\d+(?:\.\d+)?/g;
export const DISTANCE_CENTIMETERS_PER_INCH = 2.5;

export function formatDistanceExtra(value, { showPositiveSign = true, forcePositiveSign = false } = {}) {
  return String(value).replace(DISTANCE_NUMBER_PATTERN, (number) => {
    const converted = distanceUnit() === "in"
      ? Number(number) / DISTANCE_CENTIMETERS_PER_INCH
      : Number(number);
    const sign = converted >= 0 && (forcePositiveSign || (showPositiveSign && number.startsWith("+")))
      ? "+" : "";
    return `${sign}${converted}${distanceUnit() === "in" ? '"' : " cm"}`;
  });
}

export function formatSkillDistanceExtra(value, parameterSemantics = null) {
  const positiveSign = parameterSemantics?.positive_sign || "preserve";
  return formatDistanceExtra(value, {
    showPositiveSign: positiveSign !== "omit",
    forcePositiveSign: positiveSign === "force",
  });
}
