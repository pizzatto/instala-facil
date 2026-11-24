"""Testes locais sem alterar o sistema nem instalar programas reais."""
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from core import InstallError, PackageKind, build_plan, detect_kind, install, _desktop_quote, _safe_stem
from main import human_size


class CoreTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.root = Path(self.folder.name)

    def create(self, name: str, data: bytes) -> Path:
        p = self.root / name
        p.write_bytes(data)
        return p

    def test_detect_deb_valid_header(self):
        self.assertEqual(detect_kind(self.create("editor.deb", b"!<arch>\n" + b"abc")), PackageKind.DEB)

    def test_reject_deb_bad_header(self):
        with self.assertRaises(InstallError):
            detect_kind(self.create("corrompido.deb", b"invalido"))

    def test_detect_rpm_valid_header(self):
        self.assertEqual(detect_kind(self.create("app.rpm", bytes.fromhex("edabeedb") + b"more")), PackageKind.RPM)

    def test_detect_appimage_elf_header(self):
        self.assertEqual(detect_kind(self.create("app.AppImage", b"\x7fELF" + b"mock")), PackageKind.APPIMAGE)

    def test_detect_flatpak_ref(self):
        p = self.create("app.flatpakref", b"[Flatpak Ref]\nName=org.example.App\n")
        self.assertEqual(detect_kind(p), PackageKind.FLATPAK_REF)

    def test_invalid_flatpak_ref(self):
        with self.assertRaises(InstallError):
            detect_kind(self.create("app.flatpakref", b"[Other]\nName=app\n"))

    def test_flatpak_bundle_extension(self):
        self.assertEqual(detect_kind(self.create("app.flatpak", b"bundle")), PackageKind.FLATPAK_BUNDLE)

    def test_unsupported_extension(self):
        with self.assertRaises(InstallError):
            detect_kind(self.create("script.sh", b"#!/bin/sh"))

    def test_missing_file(self):
        with self.assertRaises(InstallError):
            build_plan(self.root / "none.deb")

    def test_empty_file(self):
        with self.assertRaises(InstallError):
            build_plan(self.create("empty.deb", b""))

    def test_appimage_install_in_home_and_shortcut(self):
        source = self.create("Meu Editor.AppImage", b"\x7fELF" + b"safe test payload")
        plan = build_plan(source)
        home = self.root / "home"
        events = []
        install(plan, log=events.append, appimage_home=home)
        copied = list((home / ".local/share/instala-facil/appimages").glob("*.AppImage"))
        shortcuts = list((home / ".local/share/applications").glob("instala-facil-*.desktop"))
        self.assertEqual(len(copied), 1)
        self.assertEqual(copied[0].read_bytes(), source.read_bytes())
        self.assertEqual(len(shortcuts), 1)
        self.assertIn("Exec=", shortcuts[0].read_text())
        self.assertTrue(os.access(copied[0], os.X_OK))
        self.assertTrue(any("Atalho criado" in line for line in events))

    def test_appimage_reinstall_is_idempotent(self):
        source = self.create("hello.AppImage", b"\x7fELF" + b"payload")
        plan = build_plan(source)
        for _ in range(2):
            install(plan, log=lambda _: None, appimage_home=self.root / "home")
        self.assertEqual(len(list((self.root / "home/.local/share/applications").glob("*.desktop"))), 1)

    def test_deb_install_refuses_missing_auth_backend(self):
        source = self.create("app.deb", b"!<arch>\n" + b"other")
        plan = build_plan(source)
        with mock.patch("core._find_command", side_effect=lambda *args: "/usr/bin/apt-get" if args == ("apt-get",) else None):
            with self.assertRaisesRegex(InstallError, "pkexec"):
                install(plan, log=lambda _: None)

    def test_deb_installer_never_invokes_shell(self):
        source = self.create("a;rm -rf ignored.deb", b"!<arch>\n" + b"other")
        plan = build_plan(source)
        with mock.patch("core._find_command", side_effect=lambda *args: f"/usr/bin/{args[0]}"):
            with mock.patch("core._run_process") as runner:
                install(plan, log=lambda _: None)
        argv = runner.call_args.args[0]
        self.assertEqual(argv[0], "/usr/bin/pkexec")
        self.assertIn("install", argv)
        self.assertEqual(argv[-1], str(source.resolve()))
        self.assertNotIn("sh", argv)

    def test_safe_stem(self):
        self.assertEqual(_safe_stem("Meu App!"), "meu-app")

    def test_desktop_exec_escapes_dangerous_chars(self):
        encoded = _desktop_quote('hello"$%\\')
        self.assertIn('\\"', encoded)
        self.assertIn("%%", encoded)
        self.assertIn("\\$", encoded)

    def test_human_readable_sizes(self):
        self.assertEqual(human_size(1024), "1.0 KB")
        self.assertEqual(human_size(1048576), "1.0 MB")


if __name__ == "__main__":
    unittest.main()
