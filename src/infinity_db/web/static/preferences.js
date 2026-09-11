const DISTANCE_UNIT_KEY = "infinity-db-distance-unit";

export function distanceUnit() {
  return document.documentElement.dataset.distanceUnit === "in" ? "in" : "cm";
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
