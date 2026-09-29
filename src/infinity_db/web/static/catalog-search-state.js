/** Shared URL state for client-filtered catalog search. */
const SEARCH_PARAMETER = "q";
const MAX_QUERY_LENGTH = 200;

export function readCatalogSearchQuery() {
  return (new URLSearchParams(window.location.search).get(SEARCH_PARAMETER) || "")
    .trim()
    .slice(0, MAX_QUERY_LENGTH);
}

export function replaceCatalogSearchQuery(value) {
  const query = value.trim().slice(0, MAX_QUERY_LENGTH);
  const url = new URL(window.location.href);
  if (query) url.searchParams.set(SEARCH_PARAMETER, query);
  else url.searchParams.delete(SEARCH_PARAMETER);
  if (url.href !== window.location.href) {
    window.history.replaceState(window.history.state, "", url);
  }
  return query;
}
