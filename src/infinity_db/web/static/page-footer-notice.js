/** Session-scoped disclosure state for the floating accuracy notice.
 * The shared navigation stays mounted while soft navigation replaces <main>.
 * New browsing sessions start expanded; storage is optional.
 */
const stateKey = "infinitydb-accuracy-notice-collapsed";

function initAccuracyNotice() {
  const notice = document.querySelector("main#main .page-footer-notice");
  if (!notice) return;
  try {
    if (window.sessionStorage.getItem(stateKey) === "true") notice.open = false;
  } catch {
    // The HTML defaults to expanded if session storage is unavailable.
  }
  notice.addEventListener("toggle", () => {
    if (!notice.isConnected) return;
    try {
      window.sessionStorage.setItem(stateKey, String(!notice.open));
    } catch {
      // Native disclosure remains usable without saved state.
    }
  });
}

initAccuracyNotice();
document.addEventListener("infinity:navigation", initAccuracyNotice);
