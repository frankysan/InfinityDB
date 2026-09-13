import { hydrateThemedLogos } from "./themed-logo.js";

hydrateThemedLogos();

/** Shared behavior for compact menus in the top bar. */
document.querySelectorAll("[data-menu]").forEach((menu) => {
  const button = menu.querySelector(".compact-menu-button");
  const setMenuOpen = (isOpen) => {
    menu.dataset.open = String(isOpen);
    button.setAttribute("aria-expanded", String(isOpen));
  };
  const closeMenu = () => setMenuOpen(false);

  button.addEventListener("click", () => {
    setMenuOpen(menu.dataset.open !== "true");
  });

  document.addEventListener("pointerdown", (event) => {
    if (menu.dataset.open === "true" && !menu.contains(event.target)) {
      closeMenu();
    }
  });

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
