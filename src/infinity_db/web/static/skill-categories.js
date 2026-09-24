const CATEGORY_TOKENS = new Map([
  ["automatic", "automatic"],
  ["automatic skill", "automatic"],
  ["automatic skills", "automatic"],
  ["deployment", "deployment"],
  ["deployment skill", "deployment"],
  ["deployment skills", "deployment"],
  ["basic short skill", "basic-short"],
  ["basic short skills", "basic-short"],
  ["short skill", "short"],
  ["short skills", "short"],
  ["long skill", "long"],
  ["long skills", "long"],
  ["aro", "aro"],
  ["aro skill", "aro"],
  ["aro skills", "aro"],
  ["unclassified", "unclassified"],
]);

export function skillCategoryToken(category) {
  const id = typeof category === "object" && category ? category.id : null;
  if (typeof id === "string") {
    const byId = {
      automatic: "automatic",
      "deployment-skill": "deployment",
      "basic-short-skill": "basic-short",
      "short-skill": "short",
      "long-skill": "long",
      aro: "aro",
    }[id];
    if (byId) return byId;
  }
  const name = typeof category === "object" && category ? category.name : category;
  return CATEGORY_TOKENS.get(String(name || "").trim().toLocaleLowerCase()) || "unclassified";
}

export function skillCategoryBadge(category, label = null) {
  const badge = document.createElement("span");
  badge.className = `skill-category-badge skill-category-badge--${skillCategoryToken(category)}`;
  const categoryName = typeof category === "object" && category
    ? category.category_name || category.name
    : category;
  badge.textContent = label || categoryName || "";
  return badge;
}
