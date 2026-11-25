"""Проверка выбора образов по локальным ссылкам и манифестам релизов."""

from __future__ import annotations

import subprocess
from pathlib import Path

from tests.cli.conftest import BASH_EXECUTABLE

PLANNER = Path(__file__).resolve().parents[2] / "deploy/updater/chatballs-updater-images.awk"
ROOT = "ghcr.io/dartdavros/chatballs/"
BACKEND = f"{ROOT}backend"


def digest(char: str) -> str:
    return f"sha256:{char * 64}"


def plan(*records: str, previous: str = "1.24.0", current: str = "1.25.0") -> set[str]:
    result = subprocess.run(
        [
            BASH_EXECUTABLE, "-c", 'LC_ALL=C awk "$@"', "awk",
            "-v", f"root={ROOT}", "-v", f"previous={previous}", "-v", f"current={current}",
            "-f", PLANNER.as_posix(),
        ],
        input="\n".join(records) + "\n", text=True, capture_output=True, check=True, timeout=10,
    )
    return set(result.stdout.splitlines())


def test_selects_older_release_tags_and_digests_from_history() -> None:
    old_tagged, old_digest, unknown, future, previous, current = map(digest, "abcdef")
    assert plan(
        f"history {BACKEND}:1.9.0@{old_digest}",
        f"history {BACKEND}:1.26.0@{future}",
        f"keep {BACKEND}:1.24.0@{previous}",
        f"keep {BACKEND}:1.25.0@{current}",
        f"image {BACKEND} 1.9.1 <none> {old_tagged}",
        f"image {BACKEND} <none> {old_digest} {old_digest}",
        f"image {BACKEND} <none> {unknown} {unknown}",
        f"image {BACKEND} <none> {future} {future}",
        f"image {BACKEND} 1.24.0 {previous} {previous}",
        f"image {BACKEND} 1.25.0 {current} {current}",
    ) == {old_tagged, old_digest}


def test_preserves_kept_digests_and_images_with_foreign_or_floating_aliases() -> None:
    shared, foreign, floating, different_repository, previous_container = map(digest, "abcde")
    assert not plan(
        f"history {BACKEND}:1.20.0@{shared}",
        f"keep {BACKEND}:1.24.0@{shared}",
        f"keep {previous_container}",
        f"image {BACKEND} 1.20.0 {shared} {shared}",
        f"image {BACKEND} 1.20.0 <none> {previous_container}",
        f"image {BACKEND} 1.20.0 <none> {foreign}",
        f"image another-team/backend 1.20.0 <none> {foreign}",
        f"image {BACKEND} 1.20.0 <none> {floating}",
        f"image {BACKEND} latest <none> {floating}",
        f"image ghcr.io/dartdavros/chatballs-demo/backend 1.20.0 <none> {different_repository}",
    )


def test_compares_release_versions_and_skips_repeated_updates() -> None:
    prerelease, stable, skipped_version = map(digest, "abc")
    records = (
        f"image {BACKEND} 1.24.0-rc.1 <none> {prerelease}",
        f"image {BACKEND} 1.24.0 <none> {stable}",
        f"image {BACKEND} 1.24.1 <none> {skipped_version}",
    )
    assert plan(*records) == {prerelease, skipped_version}
    assert not plan(*records, previous="1.25.0", current="1.25.0")
