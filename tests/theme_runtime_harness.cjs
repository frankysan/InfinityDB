const fs = require("node:fs");
const vm = require("node:vm");

const startupSource = fs.readFileSync(process.argv[2], "utf8");
let preferencesSource = fs.readFileSync(process.argv[3], "utf8");
const themeOptions = process.argv[4];

function startupScenario({ session = {}, cookie = "", systemDark = false }) {
  let prefersDark = systemDark;
  const dataset = { themeOptions };
  const snapshot = () => {
    const { themeOptions: ignored, ...state } = dataset;
    return state;
  };
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

  const initial = snapshot();
  const switchDark = bootstrap.applySelection("dark");
  const afterDark = snapshot();
  const switchLight = bootstrap.applySelection("light");
  const afterLight = snapshot();
  prefersDark = true;
  const system = bootstrap.applySelection("system");
  const afterSystem = snapshot();

  return {
    options: bootstrap.options.map(({ value }) => value),
    palettes: bootstrap.paletteOptions.map(({ value }) => value),
    switchedPalette: bootstrap.applyPalette("nomads"),
    paletteAfterModeChange: (bootstrap.applySelection("light"), dataset.themePalette),
    invalidPalette: bootstrap.applyPalette("not-a-palette"),
    initial,
    switchDark: { ...switchDark, dataset: afterDark },
    switchLight: { ...switchLight, dataset: afterLight },
    system: { ...system, dataset: afterSystem },
  };
}

function preferenceContext(initialCookies = {}, initialSession = {}) {
  const cookies = new Map(Object.entries(initialCookies));
  const session = new Map(Object.entries(initialSession));
  const document = { documentElement: { dataset: { themeOptions } } };
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
  vm.runInContext(startupSource, context, { filename: "theme-startup.js" });
  vm.runInContext(preferencesSource, context, { filename: "preferences.js" });
  return { context, cookies, session };
}

preferencesSource = preferencesSource
  .replace(
    /import\s+\{[\s\S]*?\}\s+from "\.\/theme\.js";/,
    `const THEME_PREFERENCE_KEY = window.infinityThemeBootstrap.preferenceKey;
const PALETTE_PREFERENCE_KEY = window.infinityThemeBootstrap.paletteKey;
const normalizeThemeSelection = window.infinityThemeBootstrap.normalizeSelection;
const normalizePaletteSelection = window.infinityThemeBootstrap.normalizePalette;`,
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
const selectedPalette = startupScenario({
  session: { "infinity-db-theme-palette": "panoceania" },
  systemDark: true,
});
const rememberedPalette = startupScenario({
  session: { "infinity-db-theme-palette": "panoceania" },
  cookie: "infinity-db-remember-settings=true; infinity-db-theme-palette=nomads",
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

const palette = preferenceContext();
const paletteKey = "infinity-db-theme-palette";
palette.context.savePaletteSelection("panoceania");
const paletteTransient = [palette.context.paletteSelection(), palette.session.get(paletteKey),
  palette.cookies.get(paletteKey) ?? null];
palette.context.rememberCurrentSettings();
palette.context.savePaletteSelection("nomads");
const paletteRemembered = [palette.context.paletteSelection(), palette.session.get(paletteKey),
  palette.cookies.get(paletteKey) ?? null];
palette.context.forgetRememberedSettings();
const paletteForgotten = [palette.context.paletteSelection(), palette.session.get(paletteKey),
  palette.cookies.get(paletteKey) ?? null];

console.log(JSON.stringify({
  options: defaultLight.options,
  palettes: defaultLight.palettes,
  paletteStartup: {
    selected: selectedPalette.initial, remembered: rememberedPalette.initial,
    switched: defaultLight.switchedPalette, afterModeChange: defaultLight.paletteAfterModeChange,
    invalid: defaultLight.invalidPalette,
  },
  palettePersistence: { paletteTransient, paletteRemembered, paletteForgotten },
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
