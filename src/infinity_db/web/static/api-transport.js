/** Same-origin JSON transport. Domain/page modules use api.js instead of calling this directly. */
function cacheBustedUrl(path) {
  if (document.documentElement.dataset.disableCache !== "true") return path;
  const url = new URL(path, window.location.origin);
  url.searchParams.set("cache_bust", String(Date.now()));
  return `${url.pathname}${url.search}`;
}

export async function getJson(path, signal) {
  const response = await fetch(cacheBustedUrl(path), {
    signal,
    cache: "no-store",
    headers: { Accept: "application/json" },
  });
  if (!response.ok) {
    let message = `The database returned an error (${response.status}). Please try again.`;
    try {
      const payload = await response.json();
      message = payload.error || message;
    } catch {
      // Preserve the status-based message when an intermediary returns non-JSON.
    }
    throw new Error(message);
  }
  return response.json();
}
