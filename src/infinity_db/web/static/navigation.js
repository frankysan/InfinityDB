/** Shared behavior for menus: expanded sidebar sections and compact top-bar popovers. */
const menus = [...document.querySelectorAll("[data-menu]")];
const compactMenuMedia = window.matchMedia("(max-width: 920px)");

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
