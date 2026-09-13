/** Controls the compact navigation without relying on native disclosures. */
const menu = document.querySelector(".navigation-menu");

if (menu) {
  const button = menu.querySelector(".navigation-menu-button");
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
}
