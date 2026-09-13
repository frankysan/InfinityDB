/** Reload through a release-specific URL when a newer server version is available. */
const currentVersion = document.documentElement.dataset.appVersion;

async function refreshForNewVersion() {
  try {
    const response = await fetch("/api/version", { cache: "no-store" });
    if (!response.ok) return;

    const { version } = await response.json();
    if (!version || version === currentVersion) return;

    const freshUrl = new URL(window.location.href);
    freshUrl.searchParams.set("app-version", version);
    window.location.replace(freshUrl);
  } catch {
    // Offline users can continue using the already loaded version.
  }
}

refreshForNewVersion();
