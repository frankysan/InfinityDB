const TROOP_TYPE_LABELS = {
  LI: "Light Infantry",
  MI: "Medium Infantry",
  HI: "Heavy Infantry",
  REM: "Remote",
  TAG: "Tactical Armored Gear",
  WB: "Warband",
  SK: "Skirmisher",
  VH: "Vehicle",
};

const CHARACTERISTIC_SYMBOLS = {
  regular: { category: "orders", type: "regular", label: "Regular Order" },
  irregular: { category: "orders", type: "irregular", label: "Irregular Order" },
  impetuous: { category: "orders", type: "impetuous", label: "Impetuous" },
  peripheral: { category: "characteristics", type: "peripheral", label: "Peripheral" },
  hackable: { category: "characteristics", type: "hackable", label: "Hackable" },
  cube: { category: "characteristics", type: "cube", label: "Cube" },
  "cube 2.0": { category: "characteristics", type: "cube-2", label: "Cube 2.0" },
};

export function troopTypeLabel(value) {
  return TROOP_TYPE_LABELS[value] || value;
}

export function characteristicSymbol(value) {
  return CHARACTERISTIC_SYMBOLS[String(value || "").trim().toLowerCase()] || null;
}

export function formatMovement(move1, move2, unit) {
  const values = [move1, move2];
  if (values.some((value) => value == null || value === "")) return "—";
  if (unit === "in") {
    return `${values.map((value) => Number(value) / 2.5).join("-")}\"`;
  }
  return `${values.join("-")} cm`;
}
