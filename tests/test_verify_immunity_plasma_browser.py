"""Real Chromium acceptance for N5.3 Immunity/Plasma Example 3."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

from infinity_db.web import create_app
from tools.browser_wsgi_transport import route_browser_page

ROOT = Path(__file__).resolve().parents[1]
ORIGIN = "http://infinitydb-immunity-plasma.test"


@pytest.fixture(scope="module")
def app() -> Any:
    return create_app(
        ROOT / "data/generated/infinity.db",
        rules_database_path=ROOT / "data/generated/rules.db",
    )


@pytest.fixture(scope="module")
def browser() -> Iterator[Any]:
    api = pytest.importorskip("playwright.sync_api")
    with api.sync_playwright() as driver:
        try:
            chrome = driver.chromium.launch(channel="chrome")
        except Exception as exc:
            if "Executable doesn't exist" in str(exc) or "not found" in str(exc):
                pytest.skip(f"Chrome unavailable: {exc}")
            raise
        try:
            yield chrome
        finally:
            chrome.close()


@pytest.mark.parametrize("width,height", [
    (1440, 900), (390, 844), (320, 640),
])
def test_printed_plasma_case_has_separate_normal_reference_without_overflow(
    app: Any, browser: Any, width: int, height: int,
) -> None:
    page = browser.new_page(viewport={"width": width, "height": height})
    route_browser_page(page, app, ORIGIN)
    errors: list[str] = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    try:
        page.goto(f"{ORIGIN}/skills/immunity", wait_until="domcontentloaded")
        rows = page.locator(".immunity-reviewed-cases li")
        page.wait_for_function(
            "() => document.querySelectorAll('.immunity-reviewed-cases li').length === 17",
            timeout=20000,
        )
        plasma = rows.filter(has_text="Immunity (Enhanced) vs Plasma Rifle")
        assert plasma.count() == 1
        assert "1 ARM Saving Roll and 1 BTS Saving Roll" in plasma.inner_text()
        assert "not a general immunity calculation" in plasma.inner_text()
        assert "Explicit N5.3 p. 96, Example 3" in plasma.inner_text()
        assert plasma.locator('a[href="/weapons/plasma-rifle"]').count() == 1
        assert plasma.locator('a[href="/ammunition/normal"]').count() == 1
        assert not plasma.locator("text=Critical").count()
        assert page.evaluate(
            "() => document.documentElement.scrollWidth <= window.innerWidth + 1"
        )
        assert not errors, errors
    finally:
        page.close()


@pytest.mark.parametrize("width,height", [
    (1440, 900), (390, 844), (320, 640),
])
def test_n53_bts_immunity_em_cc_weapon_is_exact_and_source_scoped(
    app: Any, browser: Any, width: int, height: int,
) -> None:
    page = browser.new_page(viewport={"width": width, "height": height})
    route_browser_page(page, app, ORIGIN)
    errors: list[str] = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    try:
        page.goto(f"{ORIGIN}/skills/immunity", wait_until="domcontentloaded")
        page.wait_for_function(
            "() => document.querySelectorAll('.immunity-reviewed-cases li').length === 17",
            timeout=20000,
        )
        cases = page.locator(".immunity-reviewed-cases li")
        reviewed = cases.filter(has_text="Immunity (BTS) vs N + E/M")
        assert reviewed.count() == 1
        assert "E/M CC Weapon" in reviewed.inner_text()
        assert "1 Saving Roll on a hit (2 on a Critical) using BTS" in reviewed.inner_text()
        assert "2 Saving Rolls on a hit (3 on a Critical)" in reviewed.inner_text()
        assert "Derived from reviewed general rules" in reviewed.inner_text()
        assert "Applies to the reviewed non-Comms attack only." in reviewed.inner_text()
        assert reviewed.locator('a[href="/weapons/e-m-cc-weapon"]').count() == 1
        assert reviewed.locator('a[href="/ammunition/normal"]').count() >= 1
        assert reviewed.locator('a[href="/ammunition/em"]').count() == 1
        assert page.evaluate(
            "() => document.documentElement.scrollWidth <= window.innerWidth + 1"
        )
        assert not errors, errors
    finally:
        page.close()


@pytest.mark.parametrize("width,height", [
    (1440, 900), (390, 844), (320, 640),
])
def test_standalone_emitter_immunity_keeps_nonlethal_and_turret_warning(
    app: Any, browser: Any, width: int, height: int,
) -> None:
    page = browser.new_page(viewport={"width": width, "height": height})
    route_browser_page(page, app, ORIGIN)
    errors: list[str] = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    try:
        page.goto(f"{ORIGIN}/skills/immunity", wait_until="domcontentloaded")
        page.wait_for_function(
            "() => document.querySelectorAll('.immunity-reviewed-cases li').length === 17",
            timeout=20000,
        )
        rows = page.locator(".immunity-reviewed-cases li")
        emitter = rows.filter(has_text="Immunity (BTS) vs standalone E/Mitter")
        assert emitter.count() == 1
        rendered = emitter.inner_text()
        assert "2 Saving Rolls on a hit (3 on a Critical) at BTS/2" in rendered
        assert "1 Saving Roll on a hit (2 on a Critical) at BTS" in rendered
        assert "Non-Lethal" in rendered and "inflicts no Wounds" in rendered
        assert "Armed Turret E/Mitter discrepancy is not adjudicated" in rendered
        assert "Derived from reviewed general rules" in rendered
        assert emitter.locator('a[href="/weapons/e-mitter"]').count() == 1
        assert emitter.locator('a[href="/ammunition/em"]').count() == 1
        assert emitter.locator('a[href="/ammunition/normal"]').count() == 1
        assert emitter.locator('a[href="/traits/non-lethal"]').count() == 1
        assert page.evaluate(
            "() => document.documentElement.scrollWidth <= window.innerWidth + 1"
        )
        assert not errors, errors
    finally:
        page.close()


@pytest.mark.parametrize("width,height", [
    (1440, 900), (390, 844), (320, 640),
])
def test_silenced_pistol_ap_immunity_preserves_shock_bts_and_silent(
    app: Any, browser: Any, width: int, height: int,
) -> None:
    page = browser.new_page(viewport={"width": width, "height": height})
    route_browser_page(page, app, ORIGIN)
    errors: list[str] = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    try:
        page.goto(f"{ORIGIN}/skills/immunity", wait_until="domcontentloaded")
        page.wait_for_function(
            "() => document.querySelectorAll('.immunity-reviewed-cases li').length === 17",
            timeout=20000,
        )
        cases = page.locator(".immunity-reviewed-cases li")
        silenced = cases.filter(has_text="Immunity (AP) vs AP + SHOCK")
        assert silenced.count() == 1
        actual = silenced.inner_text()
        assert "Silenced Pistol" in actual
        assert "1 Saving Roll on a hit (2 on a Critical) using BTS" in actual
        assert "rather than 1 Saving Roll on a hit (2 on a Critical) using BTS/2" in actual
        assert "Shock" in actual and "VITA 1 target directly to Dead" in actual
        assert "Silent (-6)" in actual and "separately conditional Trait" in actual
        assert "reviewed non-Comms attack only" in actual
        assert "Derived from reviewed general rules" in actual
        assert silenced.locator('a[href="/weapons/silenced-pistol"]').count() == 1
        assert silenced.locator('a[href="/ammunition/ap"]').count() >= 1
        assert silenced.locator('a[href="/ammunition/shock"]').count() >= 1
        assert silenced.locator('a[href="/states/dead"]').count() == 1
        assert silenced.locator('a[href="/traits/silent-x"]').count() == 1
        assert page.evaluate(
            "() => document.documentElement.scrollWidth <= window.innerWidth + 1"
        )
        assert not errors, errors
    finally:
        page.close()


@pytest.mark.parametrize("width,height", [
    (1440, 900), (390, 844), (320, 640),
])
def test_ap_t2_cc_immunity_keeps_two_wound_hit_and_one_wound_critical(
    app: Any, browser: Any, width: int, height: int,
) -> None:
    page = browser.new_page(viewport={"width": width, "height": height})
    route_browser_page(page, app, ORIGIN)
    errors: list[str] = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    try:
        page.goto(f"{ORIGIN}/skills/immunity", wait_until="domcontentloaded")
        page.wait_for_function(
            "() => document.querySelectorAll('.immunity-reviewed-cases li').length === 17",
            timeout=20000,
        )
        cases = page.locator(".immunity-reviewed-cases li")
        reviewed = cases.filter(has_text="Immunity (AP) vs AP + T2")
        assert reviewed.count() == 1
        actual = reviewed.inner_text()
        assert "AP+T2 CC Weapon" in actual
        assert "1 Saving Roll on a hit (2 on a Critical) using ARM" in actual
        assert "rather than 1 Saving Roll on a hit (2 on a Critical) using ARM/2" in actual
        assert "A failed hit Saving Roll still inflicts 2 Wounds" in actual
        assert "a failed additional Critical Saving Roll inflicts only 1 Wound" in actual
        assert "Identify which die is the hit roll" in actual
        assert "Anti-materiel" in actual and "separate Weapon property" in actual
        assert "reviewed non-Comms attack only" in actual
        assert "Derived from reviewed general rules" in actual
        assert reviewed.locator('a[href="/weapons/ap-t2-cc-weapon"]').count() == 1
        assert reviewed.locator('a[href="/ammunition/ap"]').count() >= 1
        assert reviewed.locator('a[href="/ammunition/t2"]').count() >= 1
        assert reviewed.locator('a[href="/traits/anti-materiel"]').count() == 1
        assert page.evaluate(
            "() => document.documentElement.scrollWidth <= window.innerWidth + 1"
        )
        assert not errors, errors
    finally:
        page.close()


@pytest.mark.parametrize("width,height", [
    (1440, 900), (390, 844), (320, 640),
])
def test_printed_monofilament_immunity_ignores_dead_trait_not_normal_wounds(
    app: Any, browser: Any, width: int, height: int,
) -> None:
    page = browser.new_page(viewport={"width": width, "height": height})
    route_browser_page(page, app, ORIGIN)
    errors: list[str] = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    try:
        page.goto(f"{ORIGIN}/skills/immunity", wait_until="domcontentloaded")
        page.wait_for_function(
            "() => document.querySelectorAll('.immunity-reviewed-cases li').length === 17",
            timeout=20000,
        )
        cases = page.locator(".immunity-reviewed-cases li")
        mono = cases.filter(has_text="Immunity (ARM) vs Monofilament CC Weapon")
        assert mono.count() == 1
        actual = mono.inner_text()
        assert "Explicit N5.3 p. 96, Example 2" in actual
        assert "ARM = 0 is ignored" in actual
        assert "full ARM for 1 Saving Roll on a hit" in actual
        assert "2 Saving Rolls on a Critical" in actual
        assert "State: Dead is also ignored" in actual
        assert "Ordinary failed Normal Ammunition Saving Rolls are not cancelled" in actual
        assert "exact printed non-Comms example" in actual
        assert mono.locator('a[href="/weapons/monofilament-cc-weapon"]').count() == 1
        assert mono.locator('a[href="/traits/arm-0"]').count() == 1
        assert mono.locator('a[href="/traits/state"]').count() == 1
        assert mono.locator('a[href="/ammunition/normal"]').count() == 1
        assert mono.locator('a[href="/states/dead"]').count() == 1
        assert page.evaluate(
            "() => document.documentElement.scrollWidth <= window.innerWidth + 1"
        )
        assert not errors, errors
    finally:
        page.close()


@pytest.mark.parametrize("width,height", [
    (1440, 900), (390, 844), (320, 640),
])
def test_printed_missile_blast_immunity_does_not_merge_hit_mode(
    app: Any, browser: Any, width: int, height: int,
) -> None:
    page = browser.new_page(viewport={"width": width, "height": height})
    route_browser_page(page, app, ORIGIN)
    errors: list[str] = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    try:
        page.goto(f"{ORIGIN}/skills/immunity", wait_until="domcontentloaded")
        page.wait_for_function(
            "() => document.querySelectorAll('.immunity-reviewed-cases li').length === 17",
            timeout=20000,
        )
        cases = page.locator(".immunity-reviewed-cases li")
        blast = cases.filter(has_text="Immunity (ARM) vs Missile Launcher (Blast Mode)")
        assert blast.count() == 1
        rendered = blast.inner_text()
        assert "Explicit N5.3 p. 96, Example 1" in rendered
        assert "3 Saving Rolls using ARM on a hit" in rendered
        assert "1 Saving Roll using full ARM on a hit" in rendered
        assert "2 Saving Rolls on a Critical" in rendered
        assert "Circular Impact Template" in rendered
        assert "Anti-materiel" in rendered
        assert "does not determine their separate applicability" in rendered
        assert "Hit Mode uses AP+EXP with ARM/2 instead" in rendered
        assert blast.locator('a[href="/weapons/missile-launcher"]').count() == 1
        assert blast.locator('a[href="/ammunition/exp"]').count() == 1
        assert blast.locator('a[href="/ammunition/normal"]').count() == 1
        assert blast.locator('a[href="/traits/impact-template"]').count() == 1
        assert blast.locator('a[href="/traits/anti-materiel"]').count() == 1
        assert page.evaluate(
            "() => document.documentElement.scrollWidth <= window.innerWidth + 1"
        )
        assert not errors, errors
    finally:
        page.close()


@pytest.mark.parametrize("width,height", [
    (1440, 900), (390, 844), (320, 640),
])
def test_printed_flash_pulse_example_4_has_pdf_provenance_and_stun_exception(
    app: Any, browser: Any, width: int, height: int,
) -> None:
    page = browser.new_page(viewport={"width": width, "height": height})
    route_browser_page(page, app, ORIGIN)
    errors: list[str] = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    try:
        page.goto(f"{ORIGIN}/skills/immunity", wait_until="domcontentloaded")
        page.wait_for_function(
            "() => document.querySelectorAll('.immunity-reviewed-cases li').length === 17",
            timeout=20000,
        )
        cases = page.locator(".immunity-reviewed-cases li")
        flash = cases.filter(has_text="Immunity (BTS) vs Flash Pulse")
        assert flash.count() == 1
        rendered = flash.inner_text()
        assert "Explicit N5.3 p. 96, Example 4" in rendered
        assert "failed BTS Saving Roll still causes Stunned without Wounds" in rendered
        assert "Saving Roll remains BTS" in rendered
        assert "Non-Lethal" in rendered
        assert "State: Stunned" in rendered
        assert flash.locator('a[href="/weapons/flash-pulse"]').count() == 1
        assert flash.locator('a[href="/ammunition/stun"]').count() == 1
        assert flash.locator('a[href="/ammunition/normal"]').count() == 1
        assert flash.locator('a[href="/states/stunned"]').count() == 1
        assert page.evaluate(
            "() => document.documentElement.scrollWidth <= window.innerWidth + 1"
        )
        assert not errors, errors
    finally:
        page.close()


@pytest.mark.parametrize("width,height", [
    (1440, 900), (390, 844), (320, 640),
])
def test_plasma_critical_immunity_removes_only_extra_arm_roll(
    app: Any, browser: Any, width: int, height: int,
) -> None:
    page = browser.new_page(viewport={"width": width, "height": height})
    route_browser_page(page, app, ORIGIN)
    errors: list[str] = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    try:
        page.goto(f"{ORIGIN}/skills/immunity", wait_until="domcontentloaded")
        page.wait_for_function(
            "() => document.querySelectorAll('.immunity-reviewed-cases li').length === 17",
            timeout=20000,
        )
        cases = page.locator(".immunity-reviewed-cases li")
        critical = cases.filter(has_text="Immunity (Critical) vs Plasma Rifle")
        assert critical.count() == 1
        detail = critical.inner_text()
        assert "2 ARM Saving Rolls and 1 BTS Saving Roll" in detail
        assert "removes only the additional ARM Saving Roll" in detail
        assert "leaving 1 ARM Saving Roll and 1 BTS Saving Roll" in detail
        assert "not Combined Ammunition" in detail
        assert "not a printed Immunity example" in detail
        assert "Derived from reviewed general rules" in detail
        assert critical.locator('a[href="/weapons/plasma-rifle"]').count() == 1
        assert critical.locator('a[href="/ammunition/normal"]').count() == 1
        assert page.evaluate(
            "() => document.documentElement.scrollWidth <= window.innerWidth + 1"
        )
        assert not errors, errors
    finally:
        page.close()


@pytest.mark.parametrize("width,height", [
    (1440, 900), (390, 844), (320, 640),
])
def test_t2_critical_immunity_preserves_hit_and_suppresses_only_extra_roll(
    app: Any, browser: Any, width: int, height: int,
) -> None:
    page = browser.new_page(viewport={"width": width, "height": height})
    route_browser_page(page, app, ORIGIN)
    errors: list[str] = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    try:
        page.goto(f"{ORIGIN}/skills/immunity", wait_until="domcontentloaded")
        page.wait_for_function(
            "() => document.querySelectorAll('.immunity-reviewed-cases li').length === 17",
            timeout=20000,
        )
        cases = page.locator(".immunity-reviewed-cases li")
        t2 = cases.filter(has_text="Immunity (Critical) vs AP+T2 CC Weapon")
        assert t2.count() == 1
        rendered = t2.inner_text()
        assert "2 Saving Rolls using ARM/2" in rendered
        assert "1 Saving Roll using ARM/2 remains" in rendered
        assert "2 Wounds from T2" in rendered
        assert "1 Wound on failure" in rendered
        assert "AP still halves ARM" in rendered
        assert "Anti-materiel" in rendered
        assert "exact non-Comms AP+T2 CC Weapon only" in rendered
        assert "Derived from reviewed general rules" in rendered
        assert t2.locator('a[href="/weapons/ap-t2-cc-weapon"]').count() == 1
        assert t2.locator('a[href="/ammunition/t2"]').count() == 1
        assert t2.locator('a[href="/ammunition/ap"]').count() == 1
        assert t2.locator('a[href="/traits/anti-materiel"]').count() == 1
        assert page.evaluate(
            "() => document.documentElement.scrollWidth <= window.innerWidth + 1"
        )
        assert not errors, errors
    finally:
        page.close()


@pytest.mark.parametrize("width,height", [
    (1440, 900), (390, 844), (320, 640),
])
def test_ap_da_cc_critical_immunity_retains_both_da_rolls_and_arm_halving(
    app: Any, browser: Any, width: int, height: int,
) -> None:
    page = browser.new_page(viewport={"width": width, "height": height})
    route_browser_page(page, app, ORIGIN)
    errors: list[str] = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    try:
        page.goto(f"{ORIGIN}/skills/immunity", wait_until="domcontentloaded")
        page.wait_for_function(
            "() => document.querySelectorAll('.immunity-reviewed-cases li').length === 17",
            timeout=20000,
        )
        reviewed = page.locator(".immunity-reviewed-cases li").filter(
            has_text="Immunity (Critical) vs AP+DA CC Weapon"
        )
        assert reviewed.count() == 1
        content = reviewed.inner_text()
        assert "A hit requires 2 Saving Rolls using ARM/2" in content
        assert "a Critical normally requires 3 Saving Rolls" in content
        assert "Immunity (Critical) cancels only the extra Critical Saving Roll" in content
        assert "2 Saving Rolls using ARM/2 remain because DA" in content
        assert "AP still halves ARM" in content
        assert "Anti-materiel remains a separate Weapon Trait" in content
        assert "exact non-Comms AP+DA CC Weapon profile" in content
        assert "Derived from reviewed general rules" in content
        assert reviewed.locator('a[href="/weapons/ap-da-cc-weapon"]').count() == 1
        assert reviewed.locator('a[href="/ammunition/ap"]').count() == 1
        assert reviewed.locator('a[href="/ammunition/da"]').count() == 1
        assert reviewed.locator('a[href="/traits/anti-materiel"]').count() == 1
        assert page.evaluate(
            "() => document.documentElement.scrollWidth <= window.innerWidth + 1"
        )
        assert not errors, errors
    finally:
        page.close()


@pytest.mark.parametrize("width,height", [
    (1440, 900), (390, 844), (320, 640),
])
def test_em_grenade_bts_immunity_preserves_nonlethal_without_comms_leak(
    app: Any, browser: Any, width: int, height: int,
) -> None:
    page = browser.new_page(viewport={"width": width, "height": height})
    route_browser_page(page, app, ORIGIN)
    errors: list[str] = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    try:
        page.goto(f"{ORIGIN}/skills/immunity", wait_until="domcontentloaded")
        page.wait_for_function(
            "() => document.querySelectorAll('.immunity-reviewed-cases li').length === 17",
            timeout=20000,
        )
        reviewed = page.locator(".immunity-reviewed-cases li").filter(
            has_text="Immunity (BTS) vs E/M Grenade Launcher"
        )
        assert reviewed.count() == 1
        detail = reviewed.inner_text()
        assert "2 Saving Rolls on a hit (3 on a Critical) using BTS/2" in detail
        assert "1 Saving Roll on a hit (2 on a Critical) using full BTS" in detail
        assert "Isolated and conditional Immobilized-B State effects are ignored" in detail
        assert "Non-Lethal still applies, preventing Wounds" in detail
        assert "Circular Impact Template" in detail
        assert "Speculative Attack" in detail
        assert "not Comms Attacks or arbitrary E/M weapons" in detail
        assert "Derived from reviewed general rules" in detail
        for href in (
            "/weapons/e-m-grenade-launcher", "/ammunition/em",
            "/ammunition/normal", "/traits/non-lethal",
            "/traits/impact-template", "/traits/speculative-attack",
        ):
            assert reviewed.locator(f'a[href="{href}"]').count() == 1
        assert page.evaluate(
            "() => document.documentElement.scrollWidth <= window.innerWidth + 1"
        )
        assert not errors, errors
    finally:
        page.close()


@pytest.mark.parametrize("width,height", [
    (1440, 900), (390, 844), (320, 640),
])
def test_oblivion_comms_bts_exclusion_and_isolated_state_exception(
    app: Any, browser: Any, width: int, height: int,
) -> None:
    page = browser.new_page(viewport={"width": width, "height": height})
    route_browser_page(page, app, ORIGIN)
    errors: list[str] = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    try:
        page.goto(f"{ORIGIN}/skills/immunity", wait_until="domcontentloaded")
        page.wait_for_function(
            "() => document.querySelectorAll('.immunity-reviewed-cases li').length === 17",
            timeout=20000,
        )
        reviewed = page.locator(".immunity-reviewed-cases li").filter(
            has_text="Comms exception: Oblivion"
        )
        assert reviewed.count() == 1
        detail = reviewed.inner_text()
        assert "Immunity (BTS) does not apply to Comms Attacks" in detail
        assert "neither removes the AP BTS reduction nor prevents Isolated" in detail
        assert "Immunity (State: Isolated) does apply" in detail
        assert "without cancelling the underlying Saving Roll" in detail
        assert "Burst 2 counts attack dice, not Saving Rolls" in detail
        assert "Non-Lethal" in detail
        assert "not all hacking or Comms effects" in detail
        assert "Derived from reviewed general rules" in detail
        assert reviewed.locator('a[href="/hacking-programs/oblivion"]').count() >= 1
        for href in (
            "/ammunition/ap", "/states/isolated", "/traits/non-lethal",
        ):
            assert reviewed.locator(f'a[href="{href}"]').count() >= 1
        assert page.evaluate(
            "() => document.documentElement.scrollWidth <= window.innerWidth + 1"
        )
        assert not errors, errors
    finally:
        page.close()
