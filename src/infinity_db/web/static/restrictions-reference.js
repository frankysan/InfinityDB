/** Read-only, source-scoped N5.3 Restrictions chart, not a legality evaluator. */

function linkOrText(value, href) {
  if (!href) return document.createTextNode(value);
  const anchor = document.createElement("a");
  anchor.href = href;
  anchor.textContent = value;
  return anchor;
}

export function restrictionsSection(data) {
  if (data.scope !== "reviewed-negative-conditions-not-action-legality"
      || data.source?.id !== "n5-core-v5.3-pdf" || data.source?.page !== 194
      || data.rows?.length !== 6) {
    throw new Error("Restrictions reference source/version is unavailable.");
  }
  const section = document.createElement("section");
  section.id = "restrictions";
  section.className = "surface surface--clipped content-frame restrictions-reference";
  section.setAttribute("aria-labelledby", "restrictions-heading");

  const heading = document.createElement("div");
  heading.className = "section-heading";
  const h2 = document.createElement("h2");
  h2.id = "restrictions-heading";
  h2.textContent = "Restrictions chart";
  heading.append(h2);
  const intro = document.createElement("p");
  intro.className = "detail-copy";
  intro.textContent =
    "These are source-listed prohibitions, not a complete list of legal actions. "
    + "Each condition applies only in the stated context; other rules may also restrict actions.";
  section.append(heading, intro);

  for (const row of data.rows) {
    const article = document.createElement("article");
    article.className = "detail-section restrictions-subject";
    article.id = `restriction-${row.id}`;
    const h3 = document.createElement("h3");
    h3.className = "detail-fact-heading";
    h3.append(linkOrText(row.name, row.ownerHref));
    const category = document.createElement("p");
    category.className = "detail-source";
    category.textContent = row.category;
    const list = document.createElement("ul");
    list.className = "reference-usage-list";
    for (const condition of row.conditions) {
      const item = document.createElement("li");
      item.dataset.action = condition.action;
      item.dataset.scope = condition.scope;
      item.append(linkOrText(condition.label, condition.href));
      if (condition.note) {
        const qualification = document.createElement("span");
        qualification.className = "detail-copy";
        qualification.append(` — ${condition.note}`);
        item.append(qualification);
      }
      list.append(item);
    }
    article.append(h3, category, list);
    section.append(article);
  }
  const source = document.createElement("p");
  source.className = "detail-source";
  source.append("Official source: ");
  const link = document.createElement("a");
  link.href = data.source.url;
  link.textContent = `N5.3 Core Rules, p. ${data.source.page}`;
  link.rel = "noopener noreferrer";
  link.target = "_blank";
  source.append(link);
  section.append(source);
  return section;
}
