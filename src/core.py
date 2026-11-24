"""Mecanismos de instalação do Instala Fácil (sem dependência da interface)."""
from __future__ import annotations

import configparser
from dataclasses import dataclass
from enum import Enum
import hashlib
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import tempfile
from typing import Callable

Log = Callable[[str], None]


class InstallError(Exception):
    """Erro de instalação com mensagem adequada para a interface."""


class PackageKind(str, Enum):
    DEB = "deb"
    RPM = "rpm"
    APPIMAGE = "appimage"
    FLATPAK_REF = "flatpakref"
    FLATPAK_BUNDLE = "flatpakbundle"


LABELS = {
    PackageKind.DEB: "Pacote Debian / Ubuntu",
    PackageKind.RPM: "Pacote Fedora / RPM",
    PackageKind.APPIMAGE: "Aplicativo portátil AppImage",
    PackageKind.FLATPAK_REF: "Referência Flatpak",
    PackageKind.FLATPAK_BUNDLE: "Pacote Flatpak",
}


@dataclass(frozen=True)
class InstallPlan:
    path: Path
    kind: PackageKind
    display_name: str
    description: str
    needs_admin: bool


def _read_start(path: Path, size: int) -> bytes:
    with path.open("rb") as file:
        return file.read(size)


def detect_kind(path: Path) -> PackageKind:
    name = path.name.lower()
    if name.endswith(".deb"):
        if _read_start(path, 8) != b"!<arch>\n":
            raise InstallError("Este arquivo não parece ser um pacote .deb válido.")
        return PackageKind.DEB
    if name.endswith(".rpm"):
        if _read_start(path, 4) != b"\xed\xab\xee\xdb":
            raise InstallError("Este arquivo não parece ser um pacote .rpm válido.")
        return PackageKind.RPM
    if name.endswith(".appimage"):
        if _read_start(path, 4) != b"\x7fELF":
            raise InstallError("Este arquivo não parece ser um AppImage executável válido.")
        return PackageKind.APPIMAGE
    if name.endswith(".flatpakref"):
        parser = configparser.ConfigParser(interpolation=None)
        try:
            with path.open("r", encoding="utf-8-sig") as file:
                parser.read_file(file)
            if not parser.has_section("Flatpak Ref") or not parser.has_option("Flatpak Ref", "Name"):
                raise ValueError("Sem metadados Flatpak Ref")
        except (OSError, UnicodeError, configparser.Error, ValueError) as exc:
            raise InstallError("Arquivo .flatpakref inválido ou incompleto.") from exc
        return PackageKind.FLATPAK_REF
    if name.endswith((".flatpak", ".flatpakbundle")):
        return PackageKind.FLATPAK_BUNDLE
    raise InstallError(
        "Formato não suportado. Use .deb, .rpm, .AppImage, .flatpakref ou .flatpak. "
        "Arquivos .zip, .tar.gz, .sh e .exe precisam de outros procedimentos."
    )


def _find_command(*candidates: str) -> str | None:
    for candidate in candidates:
        result = shutil.which(candidate)
        if result:
            return result
    return None


def _rpm_backend() -> str | None:
    return _find_command("dnf5", "dnf", "zypper")


def build_plan(source: str | os.PathLike[str]) -> InstallPlan:
    try:
        path = Path(source).expanduser().resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise InstallError("Não foi possível encontrar o arquivo selecionado.") from exc
    if not path.is_file():
        raise InstallError("Selecione um arquivo, não uma pasta.")
    if path.stat().st_size == 0:
        raise InstallError("O arquivo está vazio.")
    try:
        kind = detect_kind(path)
    except OSError as exc:
        raise InstallError("Não foi possível ler o arquivo.") from exc

    if kind == PackageKind.DEB and not _find_command("apt-get"):
        raise InstallError("Arquivos .deb precisam de uma distribuição baseada em Debian/Ubuntu com APT.")
    if kind == PackageKind.RPM and not _rpm_backend():
        raise InstallError("Arquivos .rpm precisam de uma distribuição com DNF ou Zypper.")
    if kind in (PackageKind.FLATPAK_REF, PackageKind.FLATPAK_BUNDLE) and not _find_command("flatpak"):
        raise InstallError("Flatpak não está instalado. Instale-o primeiro pela loja de aplicativos do seu Linux.")

    name = path.name
    if kind == PackageKind.APPIMAGE:
        name = path.name[:-9]  # .AppImage
    if kind in (PackageKind.DEB, PackageKind.RPM):
        description = "Exige autorização de administrador; instala para todo o sistema."
    elif kind == PackageKind.APPIMAGE:
        description = "Instala na sua conta e cria um atalho no menu de aplicativos."
    else:
        description = "Instala apenas na sua conta de usuário pelo Flatpak."
    return InstallPlan(path, kind, name, description, kind in (PackageKind.DEB, PackageKind.RPM))


def _run_process(command: list[str], log: Log) -> None:
    name = Path(command[0]).name
    log(f"Iniciando instalador {name}…")
    recent_output: list[str] = []
    try:
        with subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            encoding="utf-8",
            errors="replace",
            text=True,
            bufsize=1,
            stdin=subprocess.DEVNULL,
        ) as process:
            assert process.stdout is not None
            for line in process.stdout:
                clean = line.rstrip("\r\n")
                recent_output.append(clean)
                if len(recent_output) > 30:
                    recent_output.pop(0)
                log(clean)
            code = process.wait()
    except FileNotFoundError as exc:
        raise InstallError(f"O instalador {name} não foi encontrado.") from exc
    except OSError as exc:
        raise InstallError(f"Não foi possível iniciar o instalador: {exc}") from exc
    if code != 0:
        details = "\n".join(line for line in recent_output[-8:] if line.strip())
        lowered = details.lower()
        if name == "pkexec" and code in (126, 127):
            raise InstallError(
                "A autorização de administrador foi cancelada ou não está disponível. "
                "Verifique se há uma janela de senha aberta no Linux.\n" + details
            )
        if 'authentication agent' in lowered or 'not authorized' in lowered:
            raise InstallError("O Linux não encontrou um agente de autorização para solicitar sua senha.\n" + details)
        if any(t in lowered for t in ("could not get lock", "unable to acquire", "another process", "não foi possível obter trava")):
            raise InstallError("Outro gerenciador de pacotes está em execução. Feche-o e tente novamente. Não apague arquivos de bloqueio.\n" + details)
        if any(t in lowered for t in ("no space left", "not enough free space", "espaço insuficiente")):
            raise InstallError("Espaço em disco insuficiente. Libere espaço e tente novamente.\n" + details)
        if 'unable to locate package' in lowered or 'dependências' in lowered or 'dependencies' in lowered:
            raise InstallError("Falha ao resolver as dependências do aplicativo.\n" + details)
        raise InstallError(f"Instalação não concluída (código {code}).\n" + details)


def _safe_stem(name: str) -> str:
    clean = re.sub(r"[^a-zA-Z0-9._-]+", "-", name).strip("-._").lower()
    return clean[:64] or "aplicativo"


def _desktop_quote(value: str) -> str:
    """Aspas para o campo Exec conforme Desktop Entry Specification."""
    value = value.replace("\\", "\\\\").replace('"', '\\"').replace("`", "\\`").replace("$", "\\$").replace("%", "%%")
    return f'"{value}"'


def _install_appimage(plan: InstallPlan, log: Log, home: Path | None = None) -> None:
    home = home or Path.home()
    target_dir = home / ".local" / "share" / "instala-facil" / "appimages"
    shortcuts = home / ".local" / "share" / "applications"
    target_dir.mkdir(parents=True, exist_ok=True)
    shortcuts.mkdir(parents=True, exist_ok=True)

    # Nome estável por nome de arquivo: reinstalar o mesmo pacote atualiza o destino.
    slug = _safe_stem(plan.display_name)
    key = hashlib.sha256(plan.path.name.encode("utf-8")).hexdigest()[:10]
    ident = f"{slug}-{key}"
    target = target_dir / f"{ident}.AppImage"
    desktop_path = shortcuts / f"instala-facil-{ident}.desktop"
    log("Copiando AppImage para sua pasta de aplicativos…")

    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(prefix=".instala-", suffix=".AppImage", dir=target_dir, delete=False) as outfile:
            temp_path = Path(outfile.name)
            with plan.path.open("rb") as infile:
                shutil.copyfileobj(infile, outfile, length=1024 * 1024)
        temp_path.chmod(stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH)
        os.replace(temp_path, target)
    except (OSError, shutil.Error) as exc:
        raise InstallError(f"Não foi possível copiar o AppImage: {exc}") from exc
    finally:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)

    title = plan.display_name.replace("\n", " ").replace("\r", " ").strip()
    desktop = (
        "[Desktop Entry]\n"
        "Type=Application\n"
        f"Name={title}\n"
        f"Comment=Aplicativo instalado pelo Instala Fácil\n"
        f"Exec={_desktop_quote(str(target))}\n"
        "Icon=application-x-executable\n"
        "Terminal=false\n"
        "Categories=Utility;\n"
        "StartupNotify=true\n"
    )
    try:
        with tempfile.NamedTemporaryFile(prefix=".instala-", suffix=".desktop", dir=shortcuts, mode="w", encoding="utf-8", delete=False) as outfile:
            tmp_desktop = Path(outfile.name)
            outfile.write(desktop)
        os.chmod(tmp_desktop, 0o644)
        os.replace(tmp_desktop, desktop_path)
    except OSError as exc:
        raise InstallError(f"O AppImage foi copiado, mas não foi possível criar o atalho: {exc}") from exc
    finally:
        if "tmp_desktop" in locals():
            tmp_desktop.unlink(missing_ok=True)
    log(f"Atalho criado no menu de aplicativos: {title}")
    log(f"Arquivo instalado em: {target}")


def install(plan: InstallPlan, log: Log = print, appimage_home: Path | None = None) -> None:
    """Instala um pacote já validado; nunca executa shell ou comandos de arquivos fornecidos."""
    if not plan.path.is_file():
        raise InstallError("O arquivo não existe mais. Baixe-o novamente.")
    if plan.kind == PackageKind.APPIMAGE:
        _install_appimage(plan, log, home=appimage_home)
        return
    if plan.kind == PackageKind.DEB:
        apt = _find_command("apt-get")
        pkexec = _find_command("pkexec")
        if not apt:
            raise InstallError("O gerenciador APT não está disponível neste Linux.")
        if not pkexec:
            raise InstallError("O componente de autenticação 'pkexec' não foi encontrado. "
                               "No Ubuntu, execute uma única vez: sudo apt install pkexec")
        log("Solicitando sua senha no diálogo do sistema…")
        _run_process([pkexec, apt, "-o", "Dpkg::Use-Pty=0", "install", "-y", "--", str(plan.path)], log)
        return
    if plan.kind == PackageKind.RPM:
        backend = _rpm_backend()
        pkexec = _find_command("pkexec")
        if not backend:
            raise InstallError("DNF/Zypper não está disponível nesta distribuição.")
        if not pkexec:
            raise InstallError("A autorização gráfica 'pkexec' não está instalada nesta distribuição.")
        log("Solicitando sua senha no diálogo do sistema…")
        if Path(backend).name == "zypper":
            command = [pkexec, backend, "--non-interactive", "install", "--", str(plan.path)]
        else:
            command = [pkexec, backend, "install", "-y", "--", str(plan.path)]
        _run_process(command, log)
        return
    if plan.kind in (PackageKind.FLATPAK_REF, PackageKind.FLATPAK_BUNDLE):
        flatpak = _find_command("flatpak")
        if not flatpak:
            raise InstallError("Flatpak não está disponível.")
        mode = "--from" if plan.kind == PackageKind.FLATPAK_REF else "--bundle"
        _run_process([flatpak, "install", "--user", "--assumeyes", "--noninteractive", mode, str(plan.path)], log)
        return
    raise InstallError("Formato de arquivo desconhecido.")


def installation_groups(plans: list[InstallPlan]) -> list[list[InstallPlan]]:
    """Agrupa DEB e RPM por formato; mantém os aplicativos de usuário separados."""
    groups: list[list[InstallPlan]] = []
    system: dict[PackageKind, list[InstallPlan]] = {}
    for plan in plans:
        if plan.kind in (PackageKind.DEB, PackageKind.RPM):
            if plan.kind not in system:
                system[plan.kind] = []
                groups.append(system[plan.kind])
            system[plan.kind].append(plan)
        else:
            groups.append([plan])
    return groups


def install_group(plans: list[InstallPlan], log: Log = print) -> None:
    """Solicita uma autorização por lote, sem manter privilégios permanentes."""
    if not plans:
        raise InstallError("Nenhum arquivo selecionado.")
    kind = plans[0].kind
    for plan in plans:
        if build_plan(plan.path).kind != kind or plan.kind != kind:
            raise InstallError("O arquivo mudou ou não pertence ao tipo do lote.")
    if len(plans) == 1:
        install(plans[0], log)
        return
    if kind not in (PackageKind.DEB, PackageKind.RPM):
        raise InstallError("Somente DEB e RPM podem ser instalados em lote.")
    pkexec = _find_command("pkexec")
    backend = _find_command("apt-get") if kind == PackageKind.DEB else _rpm_backend()
    if not pkexec or not backend:
        raise InstallError("Gerenciador de pacotes ou autorização gráfica indisponível.")
    files = [str(plan.path) for plan in plans]
    if kind == PackageKind.DEB:
        command = [pkexec, backend, "-o", "Dpkg::Use-Pty=0", "install", "-y", "--", *files]
    elif Path(backend).name == "zypper":
        command = [pkexec, backend, "--non-interactive", "install", "--", *files]
    else:
        command = [pkexec, backend, "install", "-y", "--", *files]
    log(f"Solicitando uma autorização para {len(plans)} pacotes {kind.value.upper()}…")
    try:
        _run_process(command, log)
    except InstallError as exc:
        raise InstallError(f"Não foi possível confirmar todo o lote. Alguns pacotes podem ter sido instalados; consulte o relatório antes de tentar novamente.\n{exc}") from exc
