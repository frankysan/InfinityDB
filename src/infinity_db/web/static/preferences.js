const DISTANCE_UNIT_KEY = "infinity-db-distance-unit";
const DISTANCE_NUMBER_PATTERN = /[+-]?\d+(?:\.\d+)?/g;

export function distanceUnit() {
  return document.documentElement.dataset.distanceUnit === "in" ? "in" : "cm";
}

export function formatDistanceExtra(value, { showPositiveSign = true, forcePositiveSign = false } = {}) {
  return String(value).replace(DISTANCE_NUMBER_PATTERN, (number) => {
    const converted = distanceUnit() === "in" ? Number(number) / 2.5 : Number(number);
    const sign = converted >= 0 && (forcePositiveSign || (showPositiveSign && number.startsWith("+")))
      ? "+" : "";
    return `${sign}${converted}${distanceUnit() === "in" ? '"' : " cm"}`;
  });
}

export function initializeDistanceUnitToggle() {
  const toggle = document.getElementById("distance-unit-toggle");
  if (!toggle) return;

  const savedUnit = window.localStorage.getItem(DISTANCE_UNIT_KEY);
  const unit = savedUnit === "in" ? "in" : "cm";
  document.documentElement.dataset.distanceUnit = unit;
  toggle.checked = unit === "in";

  toggle.addEventListener("change", () => {
    const nextUnit = toggle.checked ? "in" : "cm";
    document.documentElement.dataset.distanceUnit = nextUnit;
    window.localStorage.setItem(DISTANCE_UNIT_KEY, nextUnit);
    window.dispatchEvent(new CustomEvent("distanceunitchange", { detail: nextUnit }));
  });
}
