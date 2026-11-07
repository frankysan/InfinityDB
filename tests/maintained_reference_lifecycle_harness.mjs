// Verify that a stale reference cannot reopen its detached popover after navigation.
import assert from "node:assert/strict";

const windowHandlers = new Map();
globalThis.window = {
  addEventListener(type, callback) { windowHandlers.set(type, callback); },
  infinityThemeBootstrap: {
    preferenceKey: "test",
    normalizeSelection: (value) => value,
    applySelection: (value) => value,
  },
  innerHeight: 900,
  innerWidth: 390,
};
globalThis.document = {
  addEventListener() {},
  activeElement: null,
};

const { attachReferencePreview } = await import(
  "../src/infinity_db/web/static/maintained-text.js"
);
const handlers = new Map();
let opened = 0;
let isOpen = false;

const tooltip = {
  id: "test-tooltip",
  isConnected: true,
  style: {},
  dataset: {},
  matches(selector) {
    assert.equal(selector, ":popover-open");
    return isOpen;
  },
  showPopover() {
    if (!this.isConnected) throw new Error("Detached popover was opened");
    isOpen = true;
    opened += 1;
  },
  hidePopover() { isOpen = false; },
  getBoundingClientRect() {
    if (!this.isConnected) throw new Error("Detached popover was measured");
    return { left: 0, top: 0, right: 170, bottom: 80, width: 170, height: 80 };
  },
};
const wrapper = {
  querySelector(selector) {
    assert.equal(selector, ".maintained-reference-tooltip");
    return tooltip;
  },
};
const link = {
  isConnected: true,
  setAttribute() {},
  closest(selector) {
    assert.equal(selector, ".maintained-reference-wrap");
    return wrapper;
  },
  addEventListener(type, handler) { handlers.set(type, handler); },
  getBoundingClientRect() {
    if (!this.isConnected) throw new Error("Detached link was measured");
    return { left: 10, right: 50, top: 110, bottom: 126, width: 40, height: 16 };
  },
  matches(selector) {
    assert.equal(selector, ":hover");
    return false;
  },
};
attachReferencePreview(link, tooltip);
handlers.get("focus")();
assert.equal(opened, 1);
assert.equal(isOpen, true);

link.isConnected = false;
tooltip.isConnected = false;
windowHandlers.get("scroll")();
handlers.get("focus")();
assert.equal(opened, 1);
link.isConnected = true;
handlers.get("focus")();
assert.equal(opened, 1);
console.log("detached reference prevented popover reopening");
