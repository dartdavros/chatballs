"""Тесты custocrm CLI (этап 1): deploy workflow ordering, validation, lock, doctor, status.

Запускают реальный bash-скрипт против замоканного docker/flock (см. conftest.py).
Покрывают: SPEC-HUB-0019 §11 (lock), §12 (doctor), §17 (deploy workflow),
§29 (observability). Не требуют Docker daemon.
"""

from __future__ import annotations

import hashlib
import subprocess


def _run(env, *args):
    """Вызывает custocrm через bash с окружением из fake_env."""
    return subprocess.run(
        [env.bash, str(env.custocrm), *args],
        env=env.make_env(),
        cwd=str(env.instance),
        capture_output=True,
        text=True,
    )


def _rewrite_checksums(env):
    lines = []
    release_files = (
        path for path in env.release.rglob("*") if path.is_file() and path.name != "checksums.txt"
    )
    for path in sorted(release_files):
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        relative = path.relative_to(env.release).as_posix()
        lines.append(f"{digest}  ./{relative}\n")
    (env.release / "checksums.txt").write_text("".join(lines), encoding="utf-8")


def _log_lines(env):
    if not env.log.exists():
        return []
    return [line for line in env.log.read_text().splitlines() if line.strip()]


def _index_of(log, fragment):
    return next(index for index, line in enumerate(log) if fragment in line)


# ---------------------------------------------------------------------------
# deploy
# ---------------------------------------------------------------------------


def test_deploy_success_orders_canonical_workflow(fake_env):
    fake_env.write_env()
    fake_env.install_docker()
    fake_env.install_flock(held=False)

    r = _run(fake_env, "deploy", "--non-interactive")

    assert r.returncode == 0, r.stderr
    log = _log_lines(fake_env)
    joined = "\n".join(log)

    # Канонический порядок (ADR-HUB-0028 §workflow).
    idx_pull = _index_of(log, " pull")
    idx_infra = _index_of(log, " up -d postgres redis")
    idx_init = _index_of(log, "run --rm init")
    idx_app = _index_of(
        log,
        " up -d backend-app backend-platform backend-admin worker frontend gateway",
    )
    idx_exec = _index_of(log, "exec -T backend-app")

    assert idx_pull < idx_infra < idx_init < idx_app < idx_exec, joined
    assert "seed_hub_initial_data" not in joined  # init не запускает Edevs seed
    # applied_release записан.
    assert (fake_env.instance / "state" / "applied_release").exists()
    assert not (fake_env.instance / "compose.yaml").exists()


def test_deploy_includes_coturn_when_calls_profile_active(fake_env):
    fake_env.write_env(
        COMPOSE_PROFILES="calls",
        CUSTOCRM_WEB_LISTENING_IP="203.0.113.10",
        HUB_CALL_TURN_SECRET="turn-secret",
        HUB_CALL_TURN_REALM="turn.hub.test",
        HUB_TURN_EXTERNAL_IP="203.0.113.11",
        HUB_TURN_LISTENING_IP="203.0.113.11",
    )
    fake_env.install_docker()
    fake_env.install_flock(held=False)

    r = _run(fake_env, "deploy", "--non-interactive")
    assert r.returncode == 0, r.stderr
    joined = "\n".join(_log_lines(fake_env))
    assert (
        "up -d backend-app backend-platform backend-admin worker frontend gateway coturn"
        in joined
    )


def test_deploy_rejects_shared_web_and_turn_ip(fake_env):
    fake_env.write_env(
        COMPOSE_PROFILES="calls",
        CUSTOCRM_WEB_LISTENING_IP="203.0.113.10",
        HUB_CALL_TURN_SECRET="turn-secret",
        HUB_CALL_TURN_REALM="turn.hub.test",
        HUB_TURN_EXTERNAL_IP="203.0.113.10",
        HUB_TURN_LISTENING_IP="203.0.113.10",
    )
    fake_env.install_docker()
    fake_env.install_flock(held=False)

    result = _run(fake_env, "deploy", "--non-interactive")

    assert result.returncode != 0
    assert "different public IP" in result.stderr
    assert " pull" not in "\n".join(_log_lines(fake_env))


def test_deploy_fails_when_release_env_missing(fake_env):
    fake_env.write_env()
    fake_env.install_docker()
    fake_env.install_flock(held=False)
    # Удаляем release.env — релиз не активирован.
    (fake_env.release / "release.env").unlink()

    r = _run(fake_env, "deploy", "--non-interactive")
    assert r.returncode != 0
    joined = "\n".join(_log_lines(fake_env))
    assert " up -d " not in joined  # до запуска контейнеров не дошло


def test_deploy_fails_when_release_checksum_is_invalid(fake_env):
    fake_env.write_env()
    fake_env.install_docker()
    fake_env.install_flock(held=False)
    (fake_env.release / "Caddyfile").write_text("tampered\n", encoding="utf-8")

    r = _run(fake_env, "deploy", "--non-interactive")

    assert r.returncode != 0
    assert "checksum" in r.stderr.lower()
    assert " pull" not in "\n".join(_log_lines(fake_env))


def test_deploy_fails_when_release_image_is_not_digest_pinned(fake_env):
    fake_env.write_env()
    fake_env.install_docker()
    fake_env.install_flock(held=False)
    release_env = fake_env.release / "release.env"
    release_env.write_text(
        release_env.read_text().replace(
            "registry.test/backend:1.0.0@sha256:" + "a" * 64,
            "registry.test/backend:latest",
        )
    )
    _rewrite_checksums(fake_env)

    r = _run(fake_env, "deploy", "--non-interactive")

    assert r.returncode != 0
    assert "immutable" in r.stderr.lower()
    assert " pull" not in "\n".join(_log_lines(fake_env))


def test_deploy_fails_on_lock_held(fake_env):
    fake_env.write_env()
    fake_env.install_docker()
    fake_env.install_flock(held=True)  # блокировка занята

    r = _run(fake_env, "deploy", "--non-interactive")
    assert r.returncode == 3, r.stderr
    assert "lock" in r.stderr.lower() or "lock" in r.stdout.lower()
    joined = "\n".join(_log_lines(fake_env))
    assert " up -d " not in joined  # destructive операция не началась


# ---------------------------------------------------------------------------
# doctor
# ---------------------------------------------------------------------------


def test_doctor_passes_on_valid_env(fake_env):
    fake_env.write_env()
    fake_env.install_docker()
    fake_env.install_flock(held=False)

    r = _run(fake_env, "doctor")
    assert r.returncode == 0, r.stderr


def test_doctor_fails_on_default_secret_and_missing_password(fake_env):
    fake_env.write_env(
        HUB_SECRET_KEY="change-me-long-random-secret",  # default -> должно провалиться
        POSTGRES_PASSWORD="",  # пусто -> должно провалиться
    )
    fake_env.install_docker()
    fake_env.install_flock(held=False)

    r = _run(fake_env, "doctor")
    assert r.returncode == 1
    assert "POSTGRES_PASSWORD" in r.stderr
    assert "HUB_SECRET_KEY" in r.stderr


def test_doctor_fails_when_acme_email_missing(fake_env):
    fake_env.write_env(CUSTOCRM_ACME_EMAIL="")
    fake_env.install_docker()
    fake_env.install_flock(held=False)

    result = _run(fake_env, "doctor")

    assert result.returncode == 1
    assert "CUSTOCRM_ACME_EMAIL" in result.stderr


def test_doctor_fails_when_surface_domains_match(fake_env):
    fake_env.write_env(CUSTOCRM_PLATFORM_DOMAIN="app.test")
    fake_env.install_docker()
    fake_env.install_flock(held=False)

    result = _run(fake_env, "doctor")

    assert result.returncode == 1
    assert "must be distinct" in result.stderr


# ---------------------------------------------------------------------------
# status
# ---------------------------------------------------------------------------


def test_status_json_reports_target_version(fake_env):
    fake_env.write_env()
    fake_env.install_docker()
    fake_env.install_flock(held=False)

    r = _run(fake_env, "status", "--json")
    assert r.returncode == 0, r.stderr
    out = r.stdout.strip()
    assert out.startswith("{") and '"target_version"' in out
    assert "1.0.0-test" in out
