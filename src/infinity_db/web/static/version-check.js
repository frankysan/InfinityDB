/** Reload through a release-specific URL when a newer server version is available. */
const currentVersion = document.documentElement.dataset.appVersion;
const currentSnapshotRevision = document.documentElement.dataset.snapshotRevision;

async function refreshForNewVersion() {
  try {
    const response = await fetch("/api/version", { cache: "no-store" });
    if (!response.ok) return;

    const { version, snapshot_revision: snapshotRevision } = await response.json();
    if (
      (!version || version === currentVersion) &&
      (!snapshotRevision || snapshotRevision === currentSnapshotRevision)
    ) return;

    const freshUrl = new URL(window.location.href);
    freshUrl.searchParams.set("app-version", version || currentVersion);
    if (snapshotRevision) freshUrl.searchParams.set("snapshot-revision", snapshotRevision);
    window.location.replace(freshUrl);
  } catch {
    // Offline users can continue using the already loaded version.
  }
}

refreshForNewVersion();
