import { getFaqRulings } from "./api.js";
import { rulesCitationNode } from "./rules-reference.js";

// Intentional, reviewed N5.3 / FAQ v0.1 source snapshot. Never use the
// viewer's clock to change historical FAQ applicability silently.
const PILOT_CONTEXT = Object.freeze({
  rules_revision: "5.3",
  as_of: "2026-09-01",
});

export function fetchReviewedFaqRulings(
  topicId, { scenarioId, seasonId, seasonRevision, signal } = {},
) {
  return getFaqRulings(topicId, {
    ...PILOT_CONTEXT,
    ...(scenarioId ? { scenario_id: scenarioId } : {}),
    ...(seasonId ? { season_id: seasonId } : {}),
    ...(seasonRevision ? { season_revision: seasonRevision } : {}),
  }, signal);
}

export function faqRulingsSection(items) {
  if (!items?.length) return null;
  const group = document.createElement("section");
  group.className = "detail-group faq-rulings";
  group.setAttribute("aria-label", "FAQ clarifications");

  const heading = document.createElement("h2");
  heading.className = "detail-heading";
  heading.textContent = "FAQ clarifications";
  const context = document.createElement("p");
  context.className = "detail-source";
  context.textContent = "Dated clarifications · N5.3 · FAQ v0.1 (1 September 2026). Base rules remain separate.";
  group.append(heading, context);

  for (const ruling of items) {
    const card = document.createElement("article");
    card.className = "surface surface--subtle detail-section faq-ruling";

    const question = document.createElement("h3");
    question.className = "surface-titlebar surface-titlebar--subtle";
    question.textContent = ruling.question;
    const answer = document.createElement("p");
    answer.className = "detail-copy";
    answer.textContent = ruling.answer;
    card.append(question, answer);

    const source = document.createElement("p");
    source.className = "detail-source";
    const selected = ruling.selected_source || {};
    const publication = ruling.original_publication || {};
    source.append(
      `FAQ clarification · version ${selected.version || "?"} · published ${selected.published_date || "unknown"} · `,
    );
    const citation = (ruling.citations || []).find((item) =>
      item.source_id === ruling.selected_citation?.sourceId
      && item.page === ruling.selected_citation?.page
    );
    if (citation) source.append(rulesCitationNode(citation));
    else source.append("Source page unavailable");
    if (publication.version !== selected.version) {
      source.append(` · first documented v${publication.version} (date anchor ${publication.publishedDate})`);
    }
    card.append(source);
    group.append(card);
  }
  return group;
}
