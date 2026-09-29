/** Shared URL state for client-filtered catalog search. */
import { readShareState, writeShareState } from "./share-state.js";

const MAX_QUERY_LENGTH = 200;

export function readCatalogSearchQuery() {
  return (readShareState("catalog").params.get("q") || "").trim().slice(0, MAX_QUERY_LENGTH);
}

export function replaceCatalogSearchQuery(value) {
  const query = value.trim().slice(0, MAX_QUERY_LENGTH);
  writeShareState("catalog", query ? { q: query } : {}, { replace: true });
  return query;
}
