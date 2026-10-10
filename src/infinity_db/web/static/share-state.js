/** Compact, versioned, self-contained browser share-state URLs. */
const TOKEN_PARAMETER = "s";
const TOKEN_VERSION = "v1";
const MAX_TOKEN_LENGTH = 8192;

const SCHEMAS = Object.freeze({
  units: Object.freeze({
    scope: "u",
    fields: Object.freeze([
      "army_id", "declared_faction_id", "search", "skill_id", "equipment_id", "weapon_id",
      "troop_type", "classification", "characteristic", "ava", "ava_min", "ava_max",
      "points", "points_min", "points_max", "swc", "swc_min", "swc_max", "offset",
      "mercs", "specops", "teamops", "reinforcement", "order", "extended",
    ]),
  }),
  catalog: Object.freeze({ scope: "c", fields: Object.freeze(["q"]) }),
  fireteams: Object.freeze({ scope: "f", fields: Object.freeze(["army"]) }),
  unit: Object.freeze({ scope: "d", fields: Object.freeze(["army_id"]) }),
  search: Object.freeze({ scope: "s", fields: Object.freeze(["q"]) }),
  glossary: Object.freeze({ scope: "g", fields: Object.freeze(["q"]) }),
  scenario: Object.freeze({ scope: "n", fields: Object.freeze(["army_points"]) }),
});

function schema(name) {
  const value = SCHEMAS[name];
  if (!value) throw new Error(`Unknown share-state schema: ${name}`);
  return value;
}

function base64UrlEncode(bytes) {
  let binary = "";
  for (const byte of bytes) binary += String.fromCharCode(byte);
  return btoa(binary).replaceAll("+", "-").replaceAll("/", "_").replace(/=+$/u, "");
}

function base64UrlDecode(value) {
  const base64 = value.replaceAll("-", "+").replaceAll("_", "/");
  const padded = `${base64}${"=".repeat((4 - (base64.length % 4)) % 4)}`;
  const binary = atob(padded);
  return Uint8Array.from(binary, (character) => character.charCodeAt(0));
}

function appendVarUint(target, value) {
  let remaining = value;
  do {
    let byte = remaining & 0x7f;
    remaining = Math.floor(remaining / 128);
    if (remaining) byte |= 0x80;
    target.push(byte);
  } while (remaining);
}

function readVarUint(bytes, start) {
  let value = 0;
  let multiplier = 1;
  let cursor = start;
  for (let count = 0; count < 5 && cursor < bytes.length; count += 1) {
    const byte = bytes[cursor];
    cursor += 1;
    value += (byte & 0x7f) * multiplier;
    if (!(byte & 0x80)) return { value, cursor };
    multiplier *= 128;
  }
  return null;
}

function decodeToken(definition, token) {
  if (!token || token.length > MAX_TOKEN_LENGTH) return null;
  const [version, scope, payload, ...extra] = token.split(".");
  if (version !== TOKEN_VERSION || scope !== definition.scope || !payload || extra.length) return null;
  try {
    const bytes = base64UrlDecode(payload);
    const decoder = new TextDecoder("utf-8", { fatal: true });
    const result = new URLSearchParams();
    const seen = new Set();
    let cursor = 0;
    while (cursor < bytes.length) {
      const fieldIndex = bytes[cursor];
      cursor += 1;
      if (fieldIndex >= definition.fields.length || seen.has(fieldIndex)) return null;
      seen.add(fieldIndex);
      const length = readVarUint(bytes, cursor);
      if (!length) return null;
      cursor = length.cursor;
      const end = cursor + length.value;
      if (end > bytes.length) return null;
      result.set(definition.fields[fieldIndex], decoder.decode(bytes.subarray(cursor, end)));
      cursor = end;
    }
    return result;
  } catch {
    return null;
  }
}

function encodeToken(definition, values) {
  const encoder = new TextEncoder();
  const bytes = [];
  definition.fields.forEach((name, fieldIndex) => {
    const value = values.get(name);
    if (value === null || value === "") return;
    const encoded = encoder.encode(value);
    bytes.push(fieldIndex);
    appendVarUint(bytes, encoded.length);
    for (const byte of encoded) bytes.push(byte);
  });
  if (!bytes.length) return "";
  return `${TOKEN_VERSION}.${definition.scope}.${base64UrlEncode(bytes)}`;
}

function legacyState(definition, source) {
  const result = new URLSearchParams();
  for (const name of definition.fields) {
    if (source.has(name)) result.set(name, source.get(name));
  }
  return result;
}

function stateParams(values) {
  if (values instanceof URLSearchParams) return values;
  const result = new URLSearchParams();
  for (const [name, value] of Object.entries(values || {})) {
    if (value !== null && value !== undefined && value !== "") result.set(name, String(value));
  }
  return result;
}

function applyShareState(url, name, values) {
  const definition = schema(name);
  const params = stateParams(values);
  for (const legacyName of definition.fields) url.searchParams.delete(legacyName);
  url.searchParams.delete(TOKEN_PARAMETER);
  const token = encodeToken(definition, params);
  if (token) url.searchParams.set(TOKEN_PARAMETER, token);
  return url;
}

export function readShareState(name) {
  const definition = schema(name);
  const source = new URLSearchParams(window.location.search);
  const token = source.get(TOKEN_PARAMETER);
  const decoded = decodeToken(definition, token);
  if (decoded) return { params: decoded, source: "token" };
  const legacy = legacyState(definition, source);
  const hasLegacy = definition.fields.some((field) => source.has(field));
  if (hasLegacy) return { params: legacy, source: token ? "invalid-token" : "legacy" };
  return { params: legacy, source: token ? "invalid-token" : "none" };
}

export function shareStateHref(path, name, values) {
  const url = applyShareState(new URL(path, window.location.origin), name, values);
  return `${url.pathname}${url.search}${url.hash}`;
}

export function writeShareState(name, values, { replace = false } = {}) {
  const url = applyShareState(new URL(window.location.href), name, values);
  if (url.href !== window.location.href) {
    window.history[replace ? "replaceState" : "pushState"](window.history.state, "", url);
  }
  return url;
}
