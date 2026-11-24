"""Testes de lotes sem executar instaladores reais."""
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from core import InstallError, InstallPlan, PackageKind, installation_groups, install_group

class BatchTests(unittest.TestCase):
    def plan(self, name, kind):
        return InstallPlan(Path("/tmp") / name, kind, name, "", kind in (PackageKind.DEB, PackageKind.RPM))

    def test_groups(self):
        a = self.plan("a.deb", PackageKind.DEB)
        b = self.plan("b.deb", PackageKind.DEB)
        r = self.plan("a.rpm", PackageKind.RPM)
        img = self.plan("a.AppImage", PackageKind.APPIMAGE)
        self.assertEqual(installation_groups([a, img, b, r]), [[a, b], [img], [r]])

    def test_one_authorization_for_deb(self):
        plans = [self.plan(n, PackageKind.DEB) for n in ("a.deb", "b.deb")]
        with patch("core.build_plan", side_effect=plans), patch("core._find_command", side_effect=lambda n: "/usr/bin/" + n), patch("core._run_process") as run:
            install_group(plans, lambda _: None)
        run.assert_called_once()
        self.assertEqual(run.call_args.args[0][0], "/usr/bin/pkexec")
        self.assertEqual(run.call_args.args[0][-2:], [str(p.path) for p in plans])

    def test_one_authorization_for_rpm(self):
        plans = [self.plan(n, PackageKind.RPM) for n in ("a.rpm", "b.rpm")]
        with patch("core.build_plan", side_effect=plans), patch("core._find_command", return_value="/usr/bin/pkexec"), patch("core._rpm_backend", return_value="/usr/bin/dnf"), patch("core._run_process") as run:
            install_group(plans, lambda _: None)
        run.assert_called_once()
        self.assertEqual(run.call_args.args[0][:2], ["/usr/bin/pkexec", "/usr/bin/dnf"])

    def test_mixed_batch_rejected(self):
        plans = [self.plan("a.deb", PackageKind.DEB), self.plan("a.rpm", PackageKind.RPM)]
        with patch("core.build_plan", side_effect=plans), patch("core._run_process") as run:
            with self.assertRaises(InstallError):
                install_group(plans)
        run.assert_not_called()

    def test_failure_reports_partial_installation(self):
        plans = [self.plan(n, PackageKind.DEB) for n in ("a.deb", "b.deb")]
        with patch("core.build_plan", side_effect=plans), patch("core._find_command", side_effect=lambda n: "/usr/bin/" + n), patch("core._run_process", side_effect=InstallError("falha")):
            with self.assertRaisesRegex(InstallError, "Alguns pacotes podem ter sido instalados"):
                install_group(plans, lambda _: None)

    def test_single_user_app(self):
        plan = self.plan("a.AppImage", PackageKind.APPIMAGE)
        with patch("core.build_plan", return_value=plan), patch("core.install") as install:
            install_group([plan])
        install.assert_called_once()
