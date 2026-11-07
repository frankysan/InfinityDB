import { getRestrictionsReference } from "./api.js";
import { restrictionsSection } from "./restrictions-reference.js";

const controller = new AbortController();
const content = document.getElementById("restrictions-content");
const status = document.getElementById("restrictions-status");

document.addEventListener(
  "infinity:beforenavigation",
  () => controller.abort(),
  { once: true },
);

function revealRestrictionHash() {
  const hash = window.location.hash;
  if (!hash.startsWith("#restriction")) return;
  let target;
  try {
    target = document.getElementById(decodeURIComponent(hash.slice(1)));
  } catch {
    target = null;
  }
  if (target && content.contains(target)) {
    target.scrollIntoView({ block: "start" });
  }
}

getRestrictionsReference(controller.signal).then((data) => {
  if (controller.signal.aborted) return;
  content.replaceChildren(restrictionsSection(data));
  content.hidden = false;
  status.hidden = true;
  requestAnimationFrame(revealRestrictionHash);
}).catch((error) => {
  if (error.name === "AbortError") return;
  status.textContent = "Restrictions chart unavailable. Other General Rules remain accessible.";
  console.error("Could not load Restrictions reference", error);
});

window.addEventListener("hashchange", revealRestrictionHash, { signal: controller.signal });
