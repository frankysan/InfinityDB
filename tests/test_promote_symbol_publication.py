"""Accepted external promotion, exact-byte aliases and persistent failure recovery."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from test_prepare_symbol_publication import _inputs, _write

from tools import promote_symbol_publication as promotion
from tools.prepare_symbol_publication import prepare_symbol_publication

OLD_SVG = b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1 1"><path d="M0 0h1"/></svg>'


def snapshot(root):
    return {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob("*") if p.is_file()}


@pytest.fixture
def prepared(tmp_path, monkeypatch):
    handoff, aliases = _inputs(tmp_path, monkeypatch)
    candidate = tmp_path / "candidate"
    report = prepare_symbol_publication(handoff, candidate, font_aliases=aliases)
    root = tmp_path / "project"
    static = root / promotion.STATIC
    shutil.copytree(candidate / "static", static)
    for relative in (
        "config/symbols/static-symbols.json",
        "data/curated/identities/legacy-armies.json",
    ):
        destination = root / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(Path(relative), destination)
    target = next(p for p in report["publishedSha256ByPath"] if p.startswith("units/"))
    alias = "units/test/old-name.svg"
    for relative in [*report["publishedSha256ByPath"], alias]:
        destination = static / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(OLD_SVG)
        report["publishedSha256ByPath"][relative] = promotion.sha256_file(destination)
    report["summary"]["publishedAssetCount"] += 1
    report["summary"]["publishedBytes"] = len(OLD_SVG) * len(report["publishedSha256ByPath"])
    report["browserUsageSummary"]["unreferencedPublishedAssetCount"] += 1
    manifest = root / promotion.MANIFEST
    manifest.parent.mkdir(parents=True, exist_ok=True)
    _write(manifest, report)
    _write(
        root / promotion.POLICY,
        {
            "format": "InfinityDB symbol publication compatibility aliases",
            "formatVersion": 1,
            "aliases": {alias: target},
        },
    )
    # Source ownership and non-generated frontend files are outside this transaction.
    (static / "styles.css").write_text("unrelated stylesheet")
    inputs = tmp_path / "promotion.json"
    _write(
        inputs,
        {
            "format": "InfinityDB symbol publication promotion inputs",
            "formatVersion": 1,
            **{k: str(v) for k, v in vars(handoff).items()},
            "font_aliases": str(aliases),
        },
    )
    return (
        {
            "candidate": candidate,
            "inputs": inputs,
            "root": root,
            "transaction": root / "local/transaction",
            "expected_current_sha256": promotion.sha256_file(manifest),
            "expected_candidate_sha256": promotion.sha256_file(
                candidate / "symbol-publication.json"
            ),
        },
        alias,
        target,
    )


def publication_snapshot(root):
    return {
        **snapshot(root / promotion.STATIC),
        "@manifest": (root / promotion.MANIFEST).read_bytes(),
    }


def test_promotes_reverified_bytes_and_preserves_old_url_as_alias(prepared):
    args, alias, target = prepared
    original = publication_snapshot(args["root"])
    candidate_before = snapshot(args["candidate"])
    report = promotion.promote_publication(**args)
    static = args["root"] / promotion.STATIC
    assert (static / alias).read_bytes() == (static / target).read_bytes()
    assert report["compatibilityAliases"] == {alias: target}
    assert report["summary"]["canonicalAssetCount"] == 2
    assert report["summary"]["publishedAssetCount"] == 3
    assert report["browserUsageSummary"] == {
        "browserReferencedAssetCount": 2,
        "unreferencedPublishedAssetCount": 1,
    }
    assert (static / "styles.css").read_text() == "unrelated stylesheet"
    assert snapshot(args["candidate"]) == candidate_before
    backup = args["transaction"] / "backup"
    assert {k: v for k, v in publication_snapshot(backup).items() if k != "styles.css"} == {
        k: v for k, v in original.items() if k != "styles.css"
    }
    assert promotion._load(args["transaction"] / "transaction.json")["status"] == "promoted"
    with pytest.raises(ValueError, match="not an interrupted"):
        promotion.recover_publication(args["root"], args["transaction"])


@pytest.mark.parametrize("call", [1, 2, 5, 10, 12])
def test_install_failure_rolls_back_every_generated_directory_and_manifest(
    prepared, monkeypatch, call
):
    args, _, _ = prepared
    before = publication_snapshot(args["root"])
    move = promotion._move
    count = 0

    def fail_once(source, destination):
        nonlocal count
        count += 1
        if count == call:
            raise OSError("injected installation failure")
        move(source, destination)

    monkeypatch.setattr(promotion, "_move", fail_once)
    with pytest.raises(OSError, match="injected"):
        promotion.promote_publication(**args)
    assert publication_snapshot(args["root"]) == before
    assert promotion._load(args["transaction"] / "transaction.json")["status"] == "rolled-back"


def test_keyboard_interruption_is_rolled_back(prepared, monkeypatch):
    args, _, _ = prepared
    before = publication_snapshot(args["root"])
    move = promotion._move

    def interrupt_once(source, destination):
        if source == args["transaction"] / "incoming" / promotion.MANIFEST:
            monkeypatch.setattr(promotion, "_move", move)
            raise KeyboardInterrupt()
        move(source, destination)

    monkeypatch.setattr(promotion, "_move", interrupt_once)
    with pytest.raises(KeyboardInterrupt):
        promotion.promote_publication(**args)
    assert publication_snapshot(args["root"]) == before


def test_failed_final_validation_restores_previous_publication(prepared, monkeypatch):
    args, _, _ = prepared
    before = publication_snapshot(args["root"])
    verify = promotion._verify
    triggered = False

    def fail_post_install(static, manifest):
        nonlocal triggered
        if (
            static == args["root"] / promotion.STATIC
            and not triggered
            and promotion.sha256_file(manifest) != args["expected_current_sha256"]
        ):
            triggered = True
            raise ValueError("injected final validation failure")
        return verify(static, manifest)

    monkeypatch.setattr(promotion, "_verify", fail_post_install)
    with pytest.raises(ValueError, match="injected"):
        promotion.promote_publication(**args)
    assert publication_snapshot(args["root"]) == before


def test_failed_final_journal_write_also_restores_publication(prepared, monkeypatch):
    args, _, _ = prepared
    before = publication_snapshot(args["root"])
    write = promotion._write

    def fail_completed_journal(path, value):
        if value.get("status") == "promoted":
            raise OSError("injected journal write failure")
        write(path, value)

    monkeypatch.setattr(promotion, "_write", fail_completed_journal)
    with pytest.raises(OSError, match="injected journal"):
        promotion.promote_publication(**args)
    assert publication_snapshot(args["root"]) == before


def test_persistent_recovery_after_lost_process_and_refusal_of_concurrent_drift(
    prepared, monkeypatch
):
    args, _, target = prepared
    before = publication_snapshot(args["root"])
    move, recover = promotion._move, promotion.recover_publication

    def fail_manifest(source, destination):
        if source == args["transaction"] / "incoming" / promotion.MANIFEST:
            raise OSError("simulated process loss")
        move(source, destination)

    def unavailable(*a):
        raise OSError("process cannot roll back now")

    with monkeypatch.context() as context:
        context.setattr(promotion, "_move", fail_manifest)
        context.setattr(promotion, "recover_publication", unavailable)
        with pytest.raises(OSError, match="cannot roll back"):
            promotion.promote_publication(**args)
    installed = args["root"] / promotion.STATIC / target
    accepted = installed.read_bytes()
    installed.write_bytes(b"concurrent writer")
    with pytest.raises(ValueError, match="Asset drift"):
        recover(args["root"], args["transaction"])
    assert installed.read_bytes() == b"concurrent writer"
    installed.write_bytes(accepted)
    recover(args["root"], args["transaction"])
    assert publication_snapshot(args["root"]) == before


@pytest.mark.parametrize(
    "change", ["base", "manifest", "asset", "evidence", "receipt", "policy", "extra"]
)
def test_input_drift_never_replaces_publication(prepared, change):
    args, alias, target = prepared
    before = publication_snapshot(args["root"])
    if change == "base":
        args["expected_current_sha256"] = "0" * 64
    elif change == "manifest":
        args["expected_candidate_sha256"] = "0" * 64
    elif change == "asset":
        (args["candidate"] / "static" / target).write_bytes(b"changed")
    elif change == "evidence":
        (args["candidate"] / "candidate-evidence.json").write_text("{}")
    elif change == "receipt":
        selection = promotion._load(args["inputs"])
        (Path(selection["processed_root"]) / "compression-state.json").write_text("{}")
    elif change == "policy":
        policy = promotion._load(args["root"] / promotion.POLICY)
        policy["aliases"][alias] = "../escape.svg"
        _write(args["root"] / promotion.POLICY, policy)
    else:
        (args["root"] / promotion.STATIC / "units" / "unrelated.txt").write_text("preserve me")
        before = publication_snapshot(args["root"])
    with pytest.raises((ValueError, KeyError)):
        promotion.promote_publication(**args)
    assert publication_snapshot(args["root"]) == before


def test_fresh_local_transaction_required(prepared):
    args, _, _ = prepared
    args["transaction"] = args["root"] / "unsafe"
    with pytest.raises(ValueError, match="ignored local"):
        promotion.promote_publication(**args)
    args["transaction"] = args["root"] / "local/existing"
    args["transaction"].mkdir(parents=True)
    with pytest.raises(FileExistsError):
        promotion.promote_publication(**args)
