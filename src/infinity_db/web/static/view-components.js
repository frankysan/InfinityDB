export function createPanelSwitcher({ container, loading, panels }) {
  const managedPanels = [...panels];
  return (panel) => {
    for (const element of managedPanels) element.hidden = element !== panel;
    container.setAttribute("aria-busy", String(panel === loading));
  };
}

/** Player-facing load failures must not expose backend validation or schema details. */
export function referenceLoadMessage(error, subject) {
  if (error?.status === 404) return `This ${subject} was not found. Check the link or search for it.`;
  return `Could not load this ${subject}. Please try again.`;
}

/** Keep unexpected collection/selection errors out of ordinary page copy. */
export function collectionLoadMessage(error, subject) {
  if (error?.status === 404) return `The requested ${subject} could not be found. Check the selection.`;
  return `Could not load ${subject}. Please try again.`;
}

export function tableViewport(table, className = "") {
  const container = document.createElement("div");
  container.className = `table-viewport${className ? ` ${className}` : ""}`;
  container.append(table);
  return container;
}
