import assert from "node:assert/strict";

globalThis.document = { documentElement: { dataset: { disableCache: "false" } } };

const { getJson } = await import("../src/infinity_db/web/static/api-transport.js");
const { referenceLoadMessage } = await import("../src/infinity_db/web/static/view-components.js");

for (const status of [404, 503]) {
  globalThis.fetch = async () => ({
    ok: false,
    status,
    json: async () => ({ error: "Internal SQLite schema validation failed" }),
  });
  let caught;
  try {
    await getJson("/api/rules/example");
  } catch (error) {
    caught = error;
  }
  assert.equal(caught?.status, status);
  assert.equal(caught.message, "Internal SQLite schema validation failed");
  const message = referenceLoadMessage(caught, "Rule");
  assert.equal(message, status === 404
    ? "This Rule was not found. Check the link or search for it."
    : "Could not load this Rule. Please try again.");
  assert.ok(!message.includes("SQLite"));
}

globalThis.fetch = async () => ({
  ok: false,
  status: 500,
  json: async () => { throw new Error("Not JSON"); },
});
try {
  await getJson("/api/skills/example");
  assert.fail("Expected an API error");
} catch (error) {
  assert.equal(error.status, 500);
  assert.equal(referenceLoadMessage(error, "Skill"), "Could not load this Skill. Please try again.");
}
assert.equal(
  referenceLoadMessage(new Error("Network request failed"), "glossary"),
  "Could not load this glossary. Please try again.",
);
console.log("Reference errors: missing, unavailable and non-JSON responses use player copy");
