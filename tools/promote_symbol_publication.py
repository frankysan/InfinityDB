"""Verify and promote accepted external symbol artwork with persistent rollback.

Stop checkout serving first. This operation replaces graphical publication only;
build the complete Army/Rules/ITS runtime set before resuming serving.
"""

from __future__ import annotations

import argparse
import json
import shutil
import tempfile
from dataclasses import fields
from pathlib import Path

from infinity_db.snapshot_provenance import sha256_file
from tools.asset_validation import validate_asset_set
from tools.prepare_symbol_publication import SymbolPublicationHandoff, prepare_symbol_publication
from tools.reorganize_symbols import GENERATED_CATEGORIES, _portable_member

MANIFEST = "data/manifests/symbol-publication.json"
STATIC = "src/infinity_db/web/static"
POLICY = "config/symbols/publication-compatibility-aliases.json"
TARGETS = [*(f"{STATIC}/{category}" for category in GENERATED_CATEGORIES), MANIFEST]


def _load(path: Path) -> dict:
    value = json.loads(path.read_bytes())
    if not isinstance(value, dict):
        raise ValueError(f"Expected JSON object: {path.name}")
    return value


def _write(path: Path, value: dict) -> None:
    temporary = path.with_suffix(".pending")
    temporary.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n"
    )
    temporary.replace(path)


def _tree(root: Path) -> dict[str, str]:
    inventory = {}
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise ValueError(f"Symlinks are not publication inputs: {path}")
        if path.is_file():
            relative = path.relative_to(root).as_posix()
            portable = _portable_member(relative)
            if portable.parts[0] not in GENERATED_CATEGORIES or portable.suffix != ".svg":
                raise ValueError(f"Unexpected publication file: {relative}")
            inventory[relative] = sha256_file(path)
    return inventory


def _current_tree(static: Path) -> dict[str, str]:
    return {
        f"{category}/{name}": digest
        for category in GENERATED_CATEGORIES
        for name, digest in _category_tree(static / category).items()
    }


def _category_tree(path: Path) -> dict[str, str]:
    if path.is_symlink():
        raise ValueError("Publication category must not be a symlink")
    result = {}
    if path.exists() and not path.is_dir():
        raise ValueError("Publication category must be a directory")
    for file in sorted(path.rglob("*")):
        if file.is_symlink() or (file.is_file() and file.suffix != ".svg"):
            raise ValueError(f"Unexpected file in generated publication category: {file}")
        if file.is_file():
            result[file.relative_to(path).as_posix()] = sha256_file(file)
    return result


def _verify(static: Path, manifest: Path) -> dict:
    if manifest.is_symlink():
        raise ValueError("Publication manifest must not be a symlink")
    report = _load(manifest)
    validation = validate_asset_set(static, publication_manifest=manifest)
    if not validation.complete or _current_tree(static) != report["publishedSha256ByPath"]:
        raise ValueError(f"Publication inventory/hash validation failed: {validation}")
    if report["summary"]["publishedAssetCount"] != len(report["publishedSha256ByPath"]):
        raise ValueError("Publication summary does not match inventory")
    return report


def _aliases(policy: Path, report: dict, static: Path) -> None:
    document = _load(policy)
    if (
        document.get("format") != "InfinityDB symbol publication compatibility aliases"
        or document.get("formatVersion") != 1
        or not isinstance(document.get("aliases"), dict)
    ):
        raise ValueError("Unsupported compatibility alias policy")
    aliases = document["aliases"]
    hashes = report["publishedSha256ByPath"]
    for alias, target in aliases.items():
        for relative in (alias, target):
            member = _portable_member(relative)
            if member.parts[0] not in GENERATED_CATEGORIES or member.suffix != ".svg":
                raise ValueError("Invalid compatibility alias path")
        if alias in hashes or target not in hashes or target in aliases:
            raise ValueError(
                "Alias must be new and point directly to a canonical publication asset"
            )
        destination = static / alias
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(static / target, destination)
        hashes[alias] = hashes[target]
    report["compatibilityAliases"] = dict(sorted(aliases.items()))
    report["publishedSha256ByPath"] = dict(sorted(hashes.items()))
    report["summary"]["publishedAssetCount"] = len(hashes)
    report["summary"]["publishedBytes"] = sum((static / path).stat().st_size for path in hashes)
    report["browserUsageSummary"]["unreferencedPublishedAssetCount"] += len(aliases)


def _transaction_root(root: Path, transaction: Path) -> Path:
    transaction = transaction.resolve()
    if not transaction.is_relative_to(root.resolve() / "local"):
        raise ValueError("Transaction must be under the selected project's ignored local/")
    return transaction


def _copy_targets(source: Path, destination: Path) -> None:
    for relative in TARGETS:
        src, dst = source / relative, destination / relative
        dst.parent.mkdir(parents=True, exist_ok=True)
        if src.is_dir():
            shutil.copytree(src, dst)
        else:
            shutil.copyfile(src, dst)


def _move(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    source.replace(destination)


def recover_publication(root: Path, transaction: Path) -> None:
    """Recover an interrupted/failed promotion, refusing unrelated destination drift."""
    root = root.resolve()
    transaction = _transaction_root(root, transaction)
    journal_path = transaction / "transaction.json"
    journal = _load(journal_path)
    if (
        journal.get("format") != "InfinityDB symbol publication transaction"
        or journal.get("formatVersion") != 1
        or journal.get("projectRoot") != str(root)
        or journal.get("status") not in {"applying", "recovery-required"}
    ):
        raise ValueError("Transaction is not an interrupted promotion for this checkout")
    backup = transaction / "backup"
    before = _verify(backup / STATIC, backup / MANIFEST)
    if sha256_file(backup / MANIFEST) != journal["previousManifestSha256"]:
        raise ValueError("Recovery backup does not match the previous publication")
    for relative in TARGETS:
        current = root / relative
        if not current.exists():
            continue
        if relative == MANIFEST:
            allowed = {journal["previousManifestSha256"], journal["promotedManifestSha256"]}
            if sha256_file(current) not in allowed:
                raise ValueError("Manifest drift during recovery; retained all backups")
        else:
            category = current.name
            actual = _category_tree(current)
            old = {
                p.split("/", 1)[1]: h
                for p, h in before["publishedSha256ByPath"].items()
                if p.startswith(category + "/")
            }
            new = {
                p.split("/", 1)[1]: h
                for p, h in journal["incomingHashes"].items()
                if p.startswith(category + "/")
            }
            if actual not in (old, new):
                raise ValueError("Asset drift during recovery; retained all backups")
    restore = Path(tempfile.mkdtemp(prefix="restore-", dir=transaction))
    _copy_targets(backup, restore)
    displaced = Path(tempfile.mkdtemp(prefix="displaced-", dir=transaction))
    try:
        for index, relative in enumerate(TARGETS):
            destination = root / relative
            if destination.exists():
                _move(destination, displaced / str(index))
            _move(restore / relative, destination)
        _verify(root / STATIC, root / MANIFEST)
    except BaseException:
        journal["status"] = "recovery-required"
        _write(journal_path, journal)
        raise
    journal["status"] = "rolled-back"
    _write(journal_path, journal)


def promote_publication(
    candidate: Path,
    inputs: Path,
    transaction: Path,
    *,
    root: Path,
    expected_current_sha256: str,
    expected_candidate_sha256: str,
) -> dict:
    """Reverify/rederive the candidate; install accepted bytes and aliases with rollback."""
    root = root.resolve()
    transaction = _transaction_root(root, transaction)
    if transaction.exists():
        raise FileExistsError(
            "Use a fresh transaction directory; recover interrupted work explicitly"
        )
    if sha256_file(root / MANIFEST) != expected_current_sha256:
        raise ValueError("Current publication differs from the expected base")
    before = _verify(root / STATIC, root / MANIFEST)
    if sha256_file(candidate / "symbol-publication.json") != expected_candidate_sha256:
        raise ValueError("Candidate manifest differs from the approved input")
    approved = _load(candidate / "symbol-publication.json")
    if _tree(candidate / "static") != approved["publishedSha256ByPath"]:
        raise ValueError("Candidate assets differ from the approved manifest")
    selection = _load(inputs)
    if (
        selection.get("format") != "InfinityDB symbol publication promotion inputs"
        or selection.get("formatVersion") != 1
    ):
        raise ValueError("Unsupported promotion input selection")
    handoff = SymbolPublicationHandoff(
        **{field.name: Path(selection[field.name]) for field in fields(SymbolPublicationHandoff)}
    )
    policy_sha = sha256_file(root / POLICY)
    transaction.mkdir(parents=True)
    prepared = transaction / "verified"
    # This reuses the full raw/effective/processed receipt verification and semantic mapper.
    # It copies compressed bytes; there is no acquisition, conversion or compression.
    report = prepare_symbol_publication(
        handoff,
        prepared,
        font_aliases=Path(selection["font_aliases"]),
        static_symbols=root / "config/symbols/static-symbols.json",
        legacy_armies=root / "data/curated/identities/legacy-armies.json",
    )
    for name in ("symbol-publication.json", "candidate-evidence.json"):
        if (prepared / name).read_bytes() != (candidate / name).read_bytes():
            raise ValueError(f"Reverified candidate differs from the accepted {name}")
    stage = transaction / "incoming"
    static = stage / STATIC
    shutil.copytree(prepared / "static", static)
    _aliases(root / POLICY, report, static)
    (stage / MANIFEST).parent.mkdir(parents=True, exist_ok=True)
    _write(stage / MANIFEST, report)
    _verify(static, stage / MANIFEST)
    backup = transaction / "backup"
    _copy_targets(root, backup)
    _verify(backup / STATIC, backup / MANIFEST)
    if (
        sha256_file(root / MANIFEST) != expected_current_sha256
        or _current_tree(root / STATIC) != before["publishedSha256ByPath"]
        or sha256_file(root / POLICY) != policy_sha
    ):
        raise ValueError("Publication or alias policy changed during promotion preparation")
    journal = {
        "format": "InfinityDB symbol publication transaction",
        "formatVersion": 1,
        "projectRoot": str(root),
        "status": "applying",
        "previousManifestSha256": expected_current_sha256,
        "candidateManifestSha256": expected_candidate_sha256,
        "candidateEvidenceSha256": sha256_file(prepared / "candidate-evidence.json"),
        "aliasPolicySha256": policy_sha,
        "promotedManifestSha256": sha256_file(stage / MANIFEST),
        "incomingHashes": report["publishedSha256ByPath"],
    }
    journal_path = transaction / "transaction.json"
    _write(journal_path, journal)
    try:
        for index, relative in enumerate(TARGETS):
            destination = root / relative
            _move(destination, transaction / "previous" / str(index))
            _move(stage / relative, destination)
        _verify(root / STATIC, root / MANIFEST)
        journal["status"] = "promoted"
        _write(journal_path, journal)
    except BaseException:
        recover_publication(root, transaction)
        raise
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--transaction", type=Path, required=True)
    parser.add_argument("--recover", action="store_true")
    parser.add_argument("--candidate", type=Path)
    parser.add_argument("--inputs", type=Path)
    parser.add_argument("--expected-current-sha256")
    parser.add_argument("--expected-candidate-sha256")
    args = parser.parse_args(argv)
    try:
        if args.recover:
            recover_publication(args.root, args.transaction)
            print("Previous symbol publication restored")
            return 0
        if any(
            value is None
            for value in (
                args.candidate,
                args.inputs,
                args.expected_current_sha256,
                args.expected_candidate_sha256,
            )
        ):
            parser.error("Promotion requires candidate, inputs and both expected manifest hashes")
        result = promote_publication(
            args.candidate,
            args.inputs,
            args.transaction,
            root=args.root,
            expected_current_sha256=args.expected_current_sha256,
            expected_candidate_sha256=args.expected_candidate_sha256,
        )
        print(f"Promoted {result['summary']['publishedAssetCount']} published SVGs")
        return 0
    except (OSError, ValueError, KeyError, TypeError) as error:
        parser.exit(1, f"Symbol publication promotion failed: {error}\n")


if __name__ == "__main__":
    raise SystemExit(main())
