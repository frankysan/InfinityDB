export function createPanelSwitcher({ container, loading, panels }) {
  const managedPanels = [...panels];
  return (panel) => {
    for (const element of managedPanels) element.hidden = element !== panel;
    container.setAttribute("aria-busy", String(panel === loading));
  };
}

export function tableViewport(table, className = "") {
  const container = document.createElement("div");
  container.className = `table-viewport${className ? ` ${className}` : ""}`;
  container.append(table);
  return container;
}
