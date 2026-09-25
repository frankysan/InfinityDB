/** Reload when application, static-content, or database snapshot identity changes. */
import { getVersion } from "./api.js";

const currentVersion = document.documentElement.dataset.appVersion;
const currentStaticRevision = document.documentElement.dataset.staticRevision;
const currentSnapshotRevision = document.documentElement.dataset.snapshotRevision;

async function refreshForNewVersion() {
  try {
    const {
      version,
      static_revision: staticRevision,
      snapshot_revision: snapshotRevision,
    } = await getVersion();
    if (
      (!version || version === currentVersion) &&
      (!staticRevision || staticRevision === currentStaticRevision) &&
      (!snapshotRevision || snapshotRevision === currentSnapshotRevision)
    ) return;

    const freshUrl = new URL(window.location.href);
    freshUrl.searchParams.set("app-version", version || currentVersion);
    if (staticRevision) freshUrl.searchParams.set("static-revision", staticRevision);
    if (snapshotRevision) freshUrl.searchParams.set("snapshot-revision", snapshotRevision);
    window.location.replace(freshUrl);
  } catch {
    // Offline users can continue using the already loaded version.
  }
}

refreshForNewVersion();
