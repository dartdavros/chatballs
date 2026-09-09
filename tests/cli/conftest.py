"""Pytest fixtures для chatballs CLI-харнесса.

Тесты запускают реальный bash-скрипт chatballs против временного layout'а
instance + release, с замоканными `docker` и `flock` на PATH. Реальный Docker
не требуется (ADR-CHATBALLS-0028 §testing — machine-readable, без внешних зависимостей).

На Windows pytest запускает скрипт через Git Bash (не WSL), поэтому бинарник
bash детектится явно. Все генерируемые файлы пишутся с LF, чтобы `\r` не ломал
awk-парсинг env-файлов и shebang-строки.
"""

from __future__ import annotations

import hashlib
import os
import shutil
import stat
from pathlib import Path

import pytest

REPO_RELEASE_ROOT = Path(__file__).resolve().parents[2]  # code/chatballs

# Релиз — это один compose.yaml. Caddyfile, init-скрипты базы и генератор
# секретов лежат внутри образов, поэтому в бандле их нет.
RELEASE_FILES = ["compose.yaml"]
LIB_GLOB_DIR = "deploy/cli/lib"


def _write_lf(path: Path, text: str) -> None:
    path.write_bytes(text.replace("\r\n", "\n").encode("utf-8"))


def _chmod_x(path: Path) -> None:
    path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def _find_bash() -> str:
    if os.name != "nt":
        bash = shutil.which("bash")
        if bash:
            return bash
        raise RuntimeError("bash not found")

    candidates = [
        r"C:\Program Files\Git\bin\bash.exe",
        r"C:\Program Files\Git\usr\bin\bash.exe",
        r"C:\Program Files (x86)\Git\bin\bash.exe",
    ]
    for c in candidates:
        if Path(c).exists():
            return c
    # Через git: git installation -> bash.
    git = shutil.which("git")
    if git:
        g = Path(git).resolve()
        for parent in [g.parent, g.parent.parent]:
            cand = parent / "bin" / "bash.exe"
            if cand.exists():
                return str(cand)
    raise RuntimeError("Git bash not found; install Git for Windows or set GIT_BASH")


BASH_EXECUTABLE = _find_bash()

FAKE_DOCKER = r"""#!/usr/bin/env bash
# Записывает каждую invocation в $FAKE_DOCKER_LOG и отвечает успехом на
# canonical workflow. Эмулирует `compose ps` (healthy) и `config -q`.
set -u
echo "docker $*" >> "$FAKE_DOCKER_LOG"

if [[ "$1" == "info" ]]; then exit 0; fi
if [[ "$1" == "compose" ]]; then
  shift
  cmd=""
  prev=""
  for a in "$@"; do
    case "$a" in
      --project-directory|--env-file|-f) prev="$a"; continue ;;
      *) if [[ -n "$prev" ]]; then prev=""; continue; fi ;;
    esac
    cmd="$cmd $a"
  done
  case "$cmd" in
    *"version"*) exit 0 ;;
    *"config"*) exit 0 ;;
    *"pull"*) exit 0 ;;
    *"up -d"*) exit 0 ;;
    *"run --rm init"*) exit 0 ;;
    *"ps --format json"*)
      svc="${@: -1}"
      echo "{\"Service\":\"$svc\",\"Health\":\"healthy\"}"
      exit 0 ;;
    *"exec -T backend-app"*) exit 0 ;;
    *"logs"*) exit 0 ;;
    *) exit 0 ;;
  esac
fi
exit 0
"""

FAKE_FLOCK_OK = "#!/usr/bin/env bash\nexit 0\n"
FAKE_FLOCK_HELD = '#!/usr/bin/env bash\necho "flock: lock held" >&2\nexit 1\n'


@pytest.fixture
def fake_env(tmp_path: Path):
    release = tmp_path / "release"
    instance = tmp_path / "instance"
    bin_dir = tmp_path / "bin"
    release.mkdir()
    instance.mkdir()
    (instance / "data").mkdir()
    (instance / "state").mkdir()
    bin_dir.mkdir()

    for name in RELEASE_FILES:
        shutil.copy(REPO_RELEASE_ROOT / name, release / name)
    lib_src = REPO_RELEASE_ROOT / LIB_GLOB_DIR
    lib_dst = release / LIB_GLOB_DIR
    lib_dst.mkdir(parents=True)
    for f in lib_src.glob("*.sh"):
        shutil.copy(f, lib_dst / f.name)

    digest = "a" * 64
    _write_lf(
        release / "release.env",
        "CHATBALLS_VERSION=1.0.0-test\n"
        f"CHATBALLS_BACKEND_IMAGE=registry.test/backend:1.0.0@sha256:{digest}\n"
        f"CHATBALLS_FRONTEND_IMAGE=registry.test/frontend:1.0.0@sha256:{digest}\n"
        f"CHATBALLS_POSTGRES_IMAGE=pgvector/pgvector:pg16@sha256:{digest}\n"
        f"CHATBALLS_REDIS_IMAGE=redis:7-alpine@sha256:{digest}\n"
        f"CHATBALLS_GATEWAY_IMAGE=caddy:2.8.4@sha256:{digest}\n"
        f"CHATBALLS_COTURN_IMAGE=coturn/coturn:4.6@sha256:{digest}\n",
    )

    checksum_lines = []
    for file_path in sorted(path for path in release.rglob("*") if path.is_file()):
        relative = file_path.relative_to(release).as_posix()
        checksum = hashlib.sha256(file_path.read_bytes()).hexdigest()
        checksum_lines.append(f"{checksum}  ./{relative}\n")
    _write_lf(release / "checksums.txt", "".join(checksum_lines))

    log_file = tmp_path / "docker.log"

    # Файла с переменными у продукта нет: установка поднимается со значениями
    # по умолчанию. То немногое, что ещё настраивается снаружи (профиль calls
    # и его адреса), приходит переменными окружения — их и подставляем.
    extra_env: dict[str, str] = {}

    def set_env(**overrides) -> None:
        extra_env.update({k: str(v) for k, v in overrides.items()})

    def install_flock(held: bool = False) -> None:
        flock = bin_dir / "flock"
        _write_lf(flock, FAKE_FLOCK_HELD if held else FAKE_FLOCK_OK)
        _chmod_x(flock)

    def install_docker() -> None:
        docker = bin_dir / "docker"
        _write_lf(docker, FAKE_DOCKER)
        _chmod_x(docker)

    chatballs = REPO_RELEASE_ROOT / "chatballs"

    def make_env() -> dict:
        env = os.environ.copy()
        sys_path = os.environ.get("PATH", "")
        env["PATH"] = str(bin_dir) + os.pathsep + sys_path
        env["CHATBALLS_RELEASE_DIR"] = str(release)
        env["CHATBALLS_INSTANCE_DIR"] = str(instance)
        env["FAKE_DOCKER_LOG"] = str(log_file)
        env.update(extra_env)
        # BASH-интерпретатор для скриптов-моков (env bash резолвится из PATH баша).
        return env

    class Env:
        pass

    e = Env()
    e.tmp = tmp_path
    e.release = release
    e.instance = instance
    e.bin = bin_dir
    e.log = log_file
    e.chatballs = chatballs
    e.bash = BASH_EXECUTABLE
    e.set_env = set_env
    e.install_flock = install_flock
    e.install_docker = install_docker
    e.make_env = make_env
    return e
