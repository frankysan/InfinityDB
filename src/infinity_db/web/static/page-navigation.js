/** Replace page content while keeping the shared navigation and its settings mounted. */
const mainSelector = "main#main";
let navigationNumber = 0;

function isSameOriginPage(link) {
  return link
    && link.origin === window.location.origin
    && link.protocol === window.location.protocol
    && !link.hash
    && !link.hasAttribute("download")
    && link.target !== "_blank";
}

function syncActiveNavigation(pathname) {
  document.querySelectorAll(".navigation-menu a[href]").forEach((link) => {
    link.toggleAttribute("aria-current", new URL(link.href).pathname === pathname);
  });
}

function syncBody(nextBody) {
  document.body.className = nextBody.className;
  for (const name of [...document.body.getAttributeNames()]) {
    if (name.startsWith("data-")) document.body.removeAttribute(name);
  }
  for (const { name, value } of [...nextBody.attributes]) {
    if (name.startsWith("data-")) document.body.setAttribute(name, value);
  }
}

async function runPageModules(nextDocument) {
  const persistentModules = new Set(["/static/navigation.js", "/static/page-navigation.js"]);
  const modules = [...nextDocument.querySelectorAll('script[type="module"][src]')]
    .filter((script) => !persistentModules.has(new URL(script.src).pathname));
  for (const module of modules) {
    await new Promise((resolve, reject) => {
      const script = window.document.createElement("script");
      script.type = "module";
      const source = new URL(module.src);
      source.searchParams.set("_navigation", String(navigationNumber));
      script.src = source;
      script.addEventListener("load", () => { script.remove(); resolve(); }, { once: true });
      script.addEventListener("error", () => { script.remove(); reject(new Error(`Could not load ${module.src}`)); }, { once: true });
      window.document.body.append(script);
    });
  }
}

async function navigate(url, { replace = false, restoreScroll } = {}) {
  navigationNumber += 1;
  document.dispatchEvent(new CustomEvent("infinity:beforenavigation"));
  const response = await fetch(url, { headers: { Accept: "text/html" } });
  if (!response.ok || !response.headers.get("content-type")?.includes("text/html")) {
    window.location.assign(url);
    return;
  }

  const nextDocument = new DOMParser().parseFromString(await response.text(), "text/html");
  const nextMain = nextDocument.querySelector(mainSelector);
  const currentMain = document.querySelector(mainSelector);
  if (!nextMain || !currentMain) {
    window.location.assign(url);
    return;
  }

  if (!replace) history.pushState({ scrollY: 0 }, "", url);
  document.title = nextDocument.title;
  syncBody(nextDocument.body);
  currentMain.replaceWith(nextMain);
  syncActiveNavigation(new URL(url, window.location.href).pathname);
  await runPageModules(nextDocument);
  window.scrollTo(0, restoreScroll ?? 0);
  document.dispatchEvent(new CustomEvent("infinity:navigation"));
}

window.infinityNavigate = (url) => navigate(new URL(url, window.location.href));

document.addEventListener("click", (event) => {
  if (event.defaultPrevented || event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
  const link = event.target.closest("a[href]");
  if (!isSameOriginPage(link)) return;
  event.preventDefault();
  history.replaceState({ ...history.state, scrollY: window.scrollY }, "", window.location.href);
  navigate(link.href).catch(() => window.location.assign(link.href));
});

window.addEventListener("popstate", () => {
  navigate(window.location.href, { replace: true, restoreScroll: history.state?.scrollY }).catch(() => window.location.reload());
});
