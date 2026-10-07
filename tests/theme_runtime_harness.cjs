const fs = require("node:fs");
const vm = require("node:vm");

const startupSource = fs.readFileSync(process.argv[2], "utf8");
let preferencesSource = fs.readFileSync(process.argv[3], "utf8");

function startupScenario({ session = {}, cookie = "", systemDark = false }) {
  let prefersDark = systemDark;
  const dataset = {};
  const storage = new Map(Object.entries(session));
  const context = {
    document: { cookie, documentElement: { dataset } },
    window: {
      sessionStorage: {
        getItem(name) {
          return storage.has(name) ? storage.get(name) : null;
        },
      },
      matchMedia(query) {
        if (query !== "(prefers-color-scheme: dark)") {
          throw new Error(`Unexpected media query: ${query}`);
        }
        return { get matches() { return prefersDark; } };
      },
    },
    encodeURIComponent,
    Object,
    Set,
  };
  vm.createContext(context);
  vm.runInContext(startupSource, context, { filename: "theme-startup.js" });
  const bootstrap = context.window.infinityThemeBootstrap;

  const initial = { ...dataset };
  const switchDark = bootstrap.applySelection("dark");
  const afterDark = { ...dataset };
  const switchLight = bootstrap.applySelection("light");
  const afterLight = { ...dataset };
  prefersDark = true;
  const system = bootstrap.applySelection("system");
  const afterSystem = { ...dataset };

  return {
    options: bootstrap.options.map(({ value }) => value),
    initial,
    switchDark: { ...switchDark, dataset: afterDark },
    switchLight: { ...switchLight, dataset: afterLight },
    system: { ...system, dataset: afterSystem },
  };
}

function preferenceContext(initialCookies = {}, initialSession = {}) {
  const cookies = new Map(Object.entries(initialCookies));
  const session = new Map(Object.entries(initialSession));
  const document = {};
  Object.defineProperty(document, "cookie", {
    get() {
      return [...cookies]
        .map(([name, value]) => `${encodeURIComponent(name)}=${encodeURIComponent(value)}`)
        .join("; ");
    },
    set(raw) {
      const [pair, ...attributes] = raw.split("; ").map((value) => value.trim());
      const separator = pair.indexOf("=");
      const name = decodeURIComponent(pair.slice(0, separator));
      const value = decodeURIComponent(pair.slice(separator + 1));
      if (attributes.some((attribute) => attribute.toLowerCase() === "max-age=0")) {
        cookies.delete(name);
      } else {
        cookies.set(name, value);
      }
    },
  });

  const context = {
    document,
    window: {
      sessionStorage: {
        getItem(name) {
          return session.has(name) ? session.get(name) : null;
        },
        setItem(name, value) {
          session.set(name, String(value));
        },
      },
    },
    Boolean,
    decodeURIComponent,
    encodeURIComponent,
    Map,
    Object,
    Set,
    String,
  };
  vm.createContext(context);
  vm.runInContext(preferencesSource, context, { filename: "preferences.js" });
  return { context, cookies, session };
}

preferencesSource = preferencesSource
  .replace(
    /import\s+\{[\s\S]*?\}\s+from "\.\/theme\.js";/,
    `const THEME_PREFERENCE_KEY = "infinity-db-theme";
function normalizeThemeSelection(value) {
  return new Set(["system", "light", "dark"]).has(value) ? value : "system";
}`,
  )
  .replaceAll("export ", "");

const defaultLight = startupScenario({ systemDark: false });
const defaultDark = startupScenario({ systemDark: true });
const sessionWins = startupScenario({
  session: { "infinity-db-theme": "dark" },
  cookie: "infinity-db-theme=light",
  systemDark: false,
});
const cookieWins = startupScenario({
  session: { "infinity-db-theme": "dark" },
  cookie: "infinity-db-remember-settings=true; infinity-db-theme=light",
  systemDark: true,
});
const invalid = startupScenario({
  session: { "infinity-db-theme": "invalid" },
  systemDark: true,
});

const transient = preferenceContext();
transient.context.saveThemeSelection("dark");
const transientSave = {
  selection: transient.context.themeSelection(),
  session: transient.session.get("infinity-db-theme") ?? null,
  cookie: transient.cookies.get("infinity-db-theme") ?? null,
};
transient.context.rememberCurrentSettings();
transient.context.saveThemeSelection("light");
const rememberedSave = {
  selection: transient.context.themeSelection(),
  session: transient.session.get("infinity-db-theme") ?? null,
  cookie: transient.cookies.get("infinity-db-theme") ?? null,
};
transient.context.forgetRememberedSettings();
const forgotten = {
  selection: transient.context.themeSelection(),
  session: transient.session.get("infinity-db-theme") ?? null,
  cookie: transient.cookies.get("infinity-db-theme") ?? null,
};

const restored = preferenceContext(
  { "infinity-db-remember-settings": "true", "infinity-db-theme": "dark" },
  { "infinity-db-theme": "light" },
);
const restoredState = {
  selection: restored.context.themeSelection(),
  session: restored.session.get("infinity-db-theme") ?? null,
  cookie: restored.cookies.get("infinity-db-theme") ?? null,
};
restored.context.saveThemeSelection("invalid");
const invalidNormalized = {
  selection: restored.context.themeSelection(),
  session: restored.session.get("infinity-db-theme") ?? null,
  cookie: restored.cookies.get("infinity-db-theme") ?? null,
};

console.log(JSON.stringify({
  options: defaultLight.options,
  startup: {
    defaultLight: defaultLight.initial,
    defaultDark: defaultDark.initial,
    sessionWinsWithoutRemember: sessionWins.initial,
    cookieWinsWhenRemembered: cookieWins.initial,
    invalidFallsBackToSystem: invalid.initial,
    switchDark: defaultLight.switchDark.dataset,
    switchLight: defaultLight.switchLight.dataset,
    systemTracksChange: defaultLight.system.dataset,
  },
  persistence: {
    transientSave,
    rememberedSave,
    restored: restoredState,
    invalidNormalized,
    forgotten,
  },
}));
