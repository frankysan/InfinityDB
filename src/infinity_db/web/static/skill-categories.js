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
  return "unclassified";
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
