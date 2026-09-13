const logoUrl = "/static/infinitydb-logo.svg";
let logoMarkup;

async function getLogoMarkup() {
  if (!logoMarkup) {
    logoMarkup = fetch(logoUrl)
      .then((response) => {
        if (!response.ok) throw new Error(`Could not load the site logo (${response.status}).`);
        return response.text();
      });
  }
  return logoMarkup;
}

/** Replaces decorative logo images with inline SVG so CSS custom properties inherit into it. */
export async function hydrateThemedLogos() {
  const images = [...document.querySelectorAll("img[data-themed-logo]")];
  if (!images.length) return;

  try {
    const markup = await getLogoMarkup();
    const documentFragment = new DOMParser().parseFromString(markup, "image/svg+xml");
    const sourceLogo = documentFragment.documentElement;

    for (const image of images) {
      const logo = sourceLogo.cloneNode(true);
      logo.setAttribute("class", image.className);
      logo.setAttribute("aria-hidden", "true");
      logo.setAttribute("focusable", "false");
      image.replaceWith(logo);
    }
  } catch {
    // Retain the image fallback if the inline themed logo cannot be loaded.
  }
}
