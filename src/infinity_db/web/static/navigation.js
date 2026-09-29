import { shareStateHref } from "./share-state.js";

/** Shared behavior for menus: expanded sidebar sections and compact top-bar popovers. */
const menus = [...document.querySelectorAll("[data-menu]")];
const compactMenuMedia = window.matchMedia("(max-width: 920px)");
const compactSearchMedia = window.matchMedia("(max-width: 700px)");
const globalSearch = document.querySelector("[data-global-search]");
const globalSearchToggle = globalSearch?.querySelector(".global-search-toggle");
const globalSearchInput = globalSearch?.querySelector("#global-search-query");
const navigationShell = globalSearch?.closest(".sidebar");

function setGlobalSearchOpen(isOpen, { focus = false } = {}) {
  if (!globalSearch || !globalSearchToggle || !globalSearchInput) return;
  const open = Boolean(isOpen && compactSearchMedia.matches);
  globalSearch.dataset.open = String(open);
  if (navigationShell) navigationShell.dataset.searchOpen = String(open);
  globalSearchToggle.setAttribute("aria-expanded", String(open));
  globalSearchToggle.setAttribute("aria-label", open ? "Close search" : "Open search");
  if (open && focus) globalSearchInput.focus();
}

function closeGlobalSearch() {
  setGlobalSearchOpen(false);
}

function syncGlobalSearchLayout() {
  closeGlobalSearch();
}

compactSearchMedia.addEventListener("change", syncGlobalSearchLayout);
setGlobalSearchOpen(false);

if (globalSearch && globalSearchToggle && globalSearchInput) {
  globalSearch.addEventListener("submit", (event) => {
    event.preventDefault();
    const query = globalSearchInput.value.trim().slice(0, 200);
    window.location.href = shareStateHref("/search", "search", query ? { q: query } : {});
  });

  globalSearchToggle.addEventListener("click", () => {
    const isOpen = globalSearch.dataset.open === "true";
    setGlobalSearchOpen(!isOpen, { focus: !isOpen });
  });

  document.addEventListener("pointerdown", (event) => {
    if (compactSearchMedia.matches
      && globalSearch.dataset.open === "true"
      && !globalSearch.contains(event.target)) {
      closeGlobalSearch();
    }
  });

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && globalSearch.dataset.open === "true") {
      closeGlobalSearch();
      globalSearchToggle.focus();
    }
  });

  window.addEventListener("pagehide", closeGlobalSearch);
  window.addEventListener("pageshow", closeGlobalSearch);
}

function setMenuOpen(menu, isOpen) {
  menu.dataset.open = String(isOpen);
  menu.querySelector(".menu-button").setAttribute("aria-expanded", String(isOpen));
}

function closeMenus() {
  menus.forEach((menu) => setMenuOpen(menu, false));
}

function syncMenuLayout() {
  closeMenus();
}

syncMenuLayout();
compactMenuMedia.addEventListener("change", syncMenuLayout);

menus.forEach((menu) => {
  const button = menu.querySelector(".menu-button");
  const closeMenu = () => setMenuOpen(menu, false);

  button.addEventListener("click", () => {
    const isDesktopSettings = menu.classList.contains("settings-menu")
      && !compactMenuMedia.matches;
    if (!compactMenuMedia.matches && !isDesktopSettings) return;
    const isOpen = menu.dataset.open !== "true";
    if (compactMenuMedia.matches) closeMenus();
    setMenuOpen(menu, isOpen);
  });

  const closeOnOutsideInteraction = (event) => {
    if (compactMenuMedia.matches && menu.dataset.open === "true" && !menu.contains(event.target)) closeMenu();
  };

  document.addEventListener("pointerdown", closeOnOutsideInteraction);
  document.addEventListener("touchstart", closeOnOutsideInteraction, { passive: true });

  menu.querySelectorAll("a").forEach((link) => {
    link.addEventListener("click", closeMenu);
  });

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && menu.dataset.open === "true") {
      closeMenu();
      button.focus();
    }
  });

  window.addEventListener("pagehide", closeMenu);
  window.addEventListener("pageshow", closeMenu);
});
