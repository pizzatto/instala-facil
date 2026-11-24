#!/usr/bin/env python3
"""Instala Fácil: instalador gráfico de programas Linux, em português."""
from __future__ import annotations

import argparse
from datetime import datetime
import os
from pathlib import Path
import queue
import shutil
import sys
import threading
import traceback

from core import InstallError, InstallPlan, build_plan, installation_groups, install_group

VERSION = "2.1.0"
COLORS = {
    "canvas": "#F1F3F6",
    "white": "#FFFFFF",
    "dark": "#101217",
    "dark2": "#20242D",
    "ink": "#151A23",
    "muted": "#586271",
    "subtle": "#8A929F",
    "line": "#DCE1E8",
    "soft": "#F7F8FA",
    "green": "#137451",
    "red": "#B42336",
}


def error_log_path() -> Path:
    base = Path(os.environ.get("XDG_STATE_HOME", str(Path.home() / ".local/state")))
    return base / "instala-facil" / "erros.log"


def save_startup_error(exc: BaseException) -> Path | None:
    try:
        path = error_log_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(f"\nInstala Fácil v{VERSION} — {datetime.now().isoformat(timespec='seconds')}\n")
            traceback.print_exception(type(exc), exc, exc.__traceback__, file=handle)
        return path
    except OSError:
        return None


def diagnostic() -> None:
    import platform
    print(f"Instala Fácil {VERSION}")
    print(f"Sistema: {platform.platform()}")
    print(f"Python: {sys.version.split()[0]} ({sys.executable})")
    print(f"DISPLAY: {os.getenv('DISPLAY', '(não definido)')}")
    print(f"WAYLAND_DISPLAY: {os.getenv('WAYLAND_DISPLAY', '(não definido)')}")
    try:
        import tkinter
        print(f"Tkinter: disponível (Tk {tkinter.TkVersion})")
    except Exception as exc:
        print(f"Tkinter: indisponível ({exc})")
    for program in ("apt-get", "pkexec", "flatpak", "dnf", "zypper"):
        print(f"{program}: {shutil.which(program) or 'não encontrado'}")
    print(f"Log: {error_log_path()}")


def human_size(size: int) -> str:
    if size < 1024:
        return f"{size} B"
    if size < 1024 * 1024:
        return f"{size / 1024:.1f} KB"
    return f"{size / (1024 * 1024):.1f} MB"


def start_gui(paths: list[str], *, smoke_test: bool = False, preview: bool = False) -> None:
    import tkinter as tk
    from tkinter import filedialog, messagebox, ttk

    class InstallerApp:
        def __init__(self):
            self.root = tk.Tk()
            self.root.title(f"Instala Fácil  ·  v{VERSION}")
            self.root.geometry("1160x820")
            self.root.minsize(940, 680)
            self.root.report_callback_exception = self.report_gui_error
            self.root.configure(bg=COLORS["canvas"])
            self.root.protocol("WM_DELETE_WINDOW", self.close)
            self.root.bind("<Control-o>", lambda event: self.choose())
            self.root.bind("<Control-Return>", lambda event: self.start_install())
            self.root.bind("<Delete>", lambda event: self.remove_selected())
            self.root.bind("<Control-Shift-C>", lambda event: self.copy_log())
            self.jobs: list[InstallPlan] = []
            self.busy = False
            self.events: queue.Queue[tuple] = queue.Queue()
            self.results: dict[str, str] = {}
            self.completed = 0
            self.failed = 0
            self.failures: list[str] = []
            self.preview = preview
            self._build()
            if preview:
                self._populate_preview()
            elif paths:
                self.add_files(paths, ask_to_install=False)
            self.root.after(80, self.poll_events)
            if smoke_test:
                self.root.after(400, self.root.destroy)

        def report_gui_error(self, exc_type, exc, tb):
            path = save_startup_error(exc)
            messagebox.showerror("Erro inesperado", f"{exc}\n\nRelatório: {path or 'indisponível'}", parent=self.root)

        def label(self, parent, text, *, size=10, weight="normal", fg=None, bg=None, **extra):
            return tk.Label(parent, text=text, font=("DejaVu Sans", size, weight),
                            fg=fg or COLORS["ink"], bg=bg or COLORS["white"], **extra)

        def button(self, parent, text, command, *, dark=False, small=False):
            bg = COLORS["dark"] if dark else COLORS["white"]
            fg = COLORS["white"] if dark else COLORS["ink"]
            return tk.Button(
                parent, text=text, command=command, bg=bg, fg=fg, bd=0,
                activebackground=COLORS["dark2"] if dark else COLORS["canvas"],
                activeforeground=fg, cursor="hand2", relief="flat",
                padx=12 if small else 20, pady=7 if small else 11,
                font=("DejaVu Sans", 9 if small else 10, "bold"),
                disabledforeground=COLORS["subtle"], highlightthickness=0,
            )

        def separator(self, parent, bg=None):
            return tk.Frame(parent, bg=bg or COLORS["line"], height=1)

        def _build(self):
            self.sidebar = tk.Frame(self.root, bg=COLORS["dark"], width=242)
            self.sidebar.pack(side="left", fill="y")
            self.sidebar.pack_propagate(False)
            brand = tk.Frame(self.sidebar, bg=COLORS["dark"], padx=25, pady=28)
            brand.pack(fill="x")
            logo = tk.Frame(brand, bg=COLORS["white"], width=40, height=40)
            logo.pack(side="left")
            logo.pack_propagate(False)
            self.label(logo, "IF", size=14, weight="bold", bg=COLORS["white"],
                       fg=COLORS["dark"]).pack(expand=True)
            names = tk.Frame(brand, bg=COLORS["dark"])
            names.pack(side="left", padx=(11, 0))
            self.label(names, "INSTALA FÁCIL", size=11, weight="bold",
                       bg=COLORS["dark"], fg=COLORS["white"]).pack(anchor="w")
            self.label(names, "PARA LINUX", size=8, bg=COLORS["dark"],
                       fg="#9DA2AA").pack(anchor="w", pady=(3, 0))

            self.label(self.sidebar, "ESPAÇO DE TRABALHO", size=8, weight="bold",
                       bg=COLORS["dark"], fg="#8C9099").pack(anchor="w", padx=26, pady=(24, 10))
            nav = tk.Frame(self.sidebar, bg=COLORS["dark2"], padx=16, pady=12)
            nav.pack(fill="x", padx=13)
            self.label(nav, "◼   Instalador", size=10, weight="bold",
                       bg=COLORS["dark2"], fg=COLORS["white"]).pack(anchor="w")
            docs_button = self.button(self.sidebar, "?   Como funciona", self.show_help, small=True)
            docs_button.configure(bg=COLORS["dark"], fg="#CFD1D5", activebackground=COLORS["dark2"],
                                  activeforeground=COLORS["white"], anchor="w", padx=18)
            docs_button.pack(fill="x", padx=13, pady=(12, 0))

            tips = tk.Frame(self.sidebar, bg=COLORS["dark2"], padx=16, pady=16)
            tips.pack(side="bottom", fill="x", padx=15, pady=(0, 23))
            self.label(tips, "DICA DE SEGURANÇA", weight="bold", size=8,
                       bg=COLORS["dark2"], fg="#DEE0E4").pack(anchor="w")
            self.label(tips, "Baixe aplicativos somente de\nsites oficiais ou fontes\nconfiáveis.",
                       size=9, justify="left", bg=COLORS["dark2"], fg="#B6BAC2").pack(anchor="w", pady=(9, 0))
            self.label(self.sidebar, f"OPEN SOURCE  •  v{VERSION}", size=8,
                       bg=COLORS["dark"], fg="#9DA2AA").pack(side="bottom", anchor="w", padx=27, pady=(0, 14))

            base = tk.Frame(self.root, bg=COLORS["canvas"])
            base.pack(fill="both", expand=True)
            # Keep installation controls visible when window is resized.
            footer = tk.Frame(base, bg=COLORS["white"], padx=28, pady=12)
            footer.pack(side="bottom", fill="x")
            self.separator(base).pack(side="bottom", fill="x")
            self.footer_status = self.label(footer, "Pronto para receber arquivos.", size=9,
                                            bg=COLORS["white"], fg=COLORS["muted"])
            self.footer_status.pack(side="left", fill="x", expand=True)
            self.install_button = self.button(footer, "Revisar e instalar  →", self.start_install, dark=True)
            self.install_button.pack(side="right")

            content = tk.Frame(base, bg=COLORS["canvas"], padx=31, pady=26)
            content.pack(fill="both", expand=True)
            head = tk.Frame(content, bg=COLORS["canvas"])
            head.pack(fill="x")
            self.label(head, "CENTRAL DE INSTALAÇÃO", size=8, weight="bold", bg=COLORS["canvas"],
                       fg=COLORS["muted"]).pack(anchor="w")
            self.label(head, "Seus aplicativos. Sem complicação.", size=24, weight="bold",
                       bg=COLORS["canvas"]).pack(anchor="w", pady=(5, 3))
            self.label(head, "Organize seus instaladores, revise a fila e acompanhe cada instalação.",
                       size=10, bg=COLORS["canvas"], fg=COLORS["muted"]).pack(anchor="w")

            hero = tk.Frame(content, bg=COLORS["white"], padx=22, pady=20,
                            highlightbackground=COLORS["line"], highlightthickness=1)
            hero.pack(fill="x", pady=(22, 14))
            hero_text = tk.Frame(hero, bg=COLORS["white"])
            hero_text.pack(side="left", fill="x", expand=True)
            self.label(hero_text, "Adicionar instaladores", size=14, weight="bold").pack(anchor="w")
            self.label(hero_text, "Selecione arquivos ou abra pelo menu ‘Abrir com’ do Linux.",
                       fg=COLORS["muted"], size=9).pack(anchor="w", pady=(5, 6))
            self.label(hero_text, ".DEB      .RPM      .APPIMAGE      .FLATPAKREF      .FLATPAK",
                       size=8, fg=COLORS["muted"]).pack(anchor="w")
            self.choose_button = self.button(hero, "+   Selecionar arquivos", self.choose, dark=True)
            self.choose_button.pack(side="right", padx=(15, 0))

            stats = tk.Frame(content, bg=COLORS["canvas"])
            stats.pack(fill="x", pady=(0, 14))
            self.stat_labels = {}
            for i, (key, title) in enumerate((("ready", "PRONTOS"), ("done", "CONCLUÍDOS"), ("errors", "FALHAS"))):
                cell = tk.Frame(stats, bg=COLORS["white"], padx=17, pady=11,
                                highlightbackground=COLORS["line"], highlightthickness=1)
                cell.pack(side="left", fill="x", expand=True, padx=(0, 7 if i < 2 else 0))
                self.label(cell, title, size=8, weight="bold", fg=COLORS["muted"]).pack(anchor="w")
                self.stat_labels[key] = self.label(cell, "0", size=19, weight="bold")
                self.stat_labels[key].pack(anchor="w", pady=(4, 0))

            pane = tk.Frame(content, bg=COLORS["white"], padx=17, pady=15,
                            highlightbackground=COLORS["line"], highlightthickness=1)
            pane.pack(fill="both", expand=True, pady=(0, 14))
            pane_head = tk.Frame(pane, bg=COLORS["white"])
            pane_head.pack(fill="x", pady=(0, 10))
            self.label(pane_head, "Fila de instalação", size=12, weight="bold").pack(side="left")
            self.count_label = self.label(pane_head, "Nenhum arquivo adicionado", size=9, fg=COLORS["muted"])
            self.count_label.pack(side="right")

            tree_frame = tk.Frame(pane, bg=COLORS["white"])
            tree_frame.pack(fill="both", expand=True)
            style = ttk.Style(self.root)
            if "clam" in style.theme_names():
                style.theme_use("clam")
            style.configure("IF.Treeview", rowheight=37, background=COLORS["white"],
                            fieldbackground=COLORS["white"], foreground=COLORS["ink"],
                            font=("DejaVu Sans", 9), borderwidth=0)
            style.configure("IF.Treeview.Heading", font=("DejaVu Sans", 9, "bold"),
                            background=COLORS["soft"], foreground=COLORS["muted"],
                            relief="flat", padding=8)
            style.map("IF.Treeview", background=[("selected", "#E9EAED")],
                      foreground=[("selected", COLORS["ink"])])
            self.tree = ttk.Treeview(tree_frame, columns=("file", "format", "size", "status"),
                                     show="headings", selectmode="extended", style="IF.Treeview")
            for key, name, width, stretch in (("file", "Arquivo", 270, True),
                                              ("format", "Tipo", 120, False),
                                              ("size", "Tamanho", 80, False),
                                              ("status", "Situação", 150, False)):
                self.tree.heading(key, text=name)
                self.tree.column(key, width=width, minwidth=80, stretch=stretch, anchor="w")
            self.tree.tag_configure("odd", background=COLORS["soft"])
            self.tree.tag_configure("error", foreground=COLORS["red"])
            self.tree.tag_configure("success", foreground=COLORS["green"])
            scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
            self.tree.configure(yscrollcommand=scrollbar.set)
            scrollbar.pack(side="right", fill="y")
            self.tree.pack(side="left", fill="both", expand=True)
            self.tree.bind("<Double-1>", self.show_selected_path)
            self.tree.bind("<<TreeviewSelect>>", lambda event: self.update_controls())
            self.tree.bind("<Button-3>", self.queue_menu)
            actions = tk.Frame(pane, bg=COLORS["white"])
            actions.pack(fill="x", pady=(12, 0))
            self.remove_button = self.button(actions, "×  Remover da fila", self.remove_selected, small=True)
            self.remove_button.pack(side="left")
            self.remove_button.configure(fg=COLORS["red"], activeforeground=COLORS["red"])
            self.clear_button = self.button(actions, "Limpar lista", self.clear, small=True)
            self.clear_button.pack(side="left", padx=(9, 0))
            self.label(actions, "Delete: remover  •  Ctrl+O: adicionar",
                       size=8, fg=COLORS["muted"]).pack(side="right")
            # Actions must not vanish when the queue is compact on laptops.
            actions.pack_forget()
            actions.pack(fill="x", pady=(0, 9), before=tree_frame)

            activity = tk.Frame(content, bg=COLORS["white"], padx=17, pady=12,
                                highlightbackground=COLORS["line"], highlightthickness=1)
            activity.pack(fill="x")
            activity_head = tk.Frame(activity, bg=COLORS["white"])
            activity_head.pack(fill="x")
            self.label(activity_head, "Atividade e detalhes", size=11, weight="bold").pack(side="left")
            self.copy_button = self.button(activity_head, "Copiar relatório", self.copy_log, small=True)
            self.copy_button.pack(side="right")
            self.details_button = self.button(activity_head, "Ver detalhes  ▾", self.toggle_details, small=True)
            self.details_button.pack(side="right", padx=(0, 7))
            style.configure("IF.Horizontal.TProgressbar", troughcolor=COLORS["line"],
                            background=COLORS["ink"], borderwidth=0, thickness=7)
            self.progress = ttk.Progressbar(activity, mode="determinate", maximum=100,
                                            style="IF.Horizontal.TProgressbar")
            self.progress.pack(fill="x", pady=(11, 5))
            self.status_detail = self.label(activity, "Nenhuma instalação iniciada.",
                                            size=8, fg=COLORS["muted"])
            self.status_detail.pack(anchor="w")
            self.log = tk.Text(activity, height=4, wrap="word", bg=COLORS["soft"],
                               fg="#42464D", font=("DejaVu Sans Mono", 8),
                               padx=11, pady=7, borderwidth=0, state="disabled",
                               highlightthickness=0)
            self.log.pack(fill="x", pady=(9, 0))
            self.log.pack_forget()
            self.details_expanded = False
            # Reserve the activity panel at the bottom before giving the queue
            # all remaining space. Otherwise Tk can hide the activity log.
            pane.pack_forget()
            activity.pack_forget()
            activity.pack(side="bottom", fill="x")
            pane.pack(fill="both", expand=True, pady=(0, 14))
            self.update_controls()

        def _populate_preview(self):
            samples = (("editor-exemplo.deb", "DEB", "78.4 MB", "Pronto para instalar"),
                       ("imagem-exemplo.AppImage", "APPIMAGE", "146.2 MB", "Pronto para instalar"))
            for ix, row in enumerate(samples):
                self.tree.insert("", "end", iid=f"preview-{ix}", values=row,
                                 tags=("odd",) if ix % 2 else ())
            self.count_label.config(text="2 arquivos de exemplo · prévia visual")
            self.footer_status.config(text="Prévia de interface: instalação desativada.")
            self.status_detail.config(text="Modo de prévia: nenhum software será instalado.")
            self.update_controls()
            self.stat_labels["ready"].config(text="2")

        def choose(self):
            if self.busy or self.preview:
                return
            downloads = Path.home() / "Downloads"
            if not downloads.is_dir():
                downloads = Path.home() / "Baixados"
            selected = filedialog.askopenfilenames(
                parent=self.root, title="Selecione arquivos de instalação",
                initialdir=str(downloads if downloads.is_dir() else Path.home()),
                filetypes=[("Instaladores Linux", "*.deb *.rpm *.AppImage *.appimage *.flatpakref *.flatpak *.flatpakbundle"),
                           ("Todos os arquivos", "*")],
            )
            if selected:
                self.add_files(list(selected), ask_to_install=False)

        def add_files(self, paths, *, ask_to_install=True):
            if self.busy or self.preview:
                return
            known = {str(plan.path) for plan in self.jobs}
            errors = []
            added = 0
            for raw_path in paths:
                try:
                    plan = build_plan(raw_path)
                    size = plan.path.stat().st_size
                except (InstallError, OSError) as exc:
                    errors.append(f"{Path(raw_path).name}: {exc}")
                    continue
                key = str(plan.path)
                if key in known:
                    continue
                known.add(key)
                self.jobs.append(plan)
                self.results[key] = "Pronto para instalar"
                self.tree.insert("", "end", iid=key,
                                 values=(plan.path.name, plan.kind.value.upper(),
                                         human_size(size), "Pronto para instalar"),
                                 tags=("odd",) if len(self.jobs) % 2 else ())
                added += 1
            self.update_controls()
            if added:
                self.footer_status.config(text=f"{added} arquivo(s) adicionado(s). Revise a fila antes de instalar.")
                self.status_detail.config(text="Pronto: confirme a instalação para iniciar.")
                self.append_log(f"{added} arquivo(s) adicionado(s) à fila.")
            if errors:
                for error in errors:
                    self.append_log("ERRO: " + error)
                if not self.details_expanded:
                    self.toggle_details()
                messagebox.showwarning("Arquivos não adicionados", "\n\n".join(errors[:5]), parent=self.root)

        def queue_menu(self, event):
            item = self.tree.identify_row(event.y)
            if not item:
                return
            if item not in self.tree.selection():
                self.tree.selection_set(item)
            menu = tk.Menu(self.root, tearoff=False)
            menu.add_command(label="Ver local do arquivo", command=self.show_selected_path)
            menu.add_command(label="Remover da fila", command=self.remove_selected,
                             state="disabled" if self.busy or self.preview else "normal")
            try:
                menu.tk_popup(event.x_root, event.y_root)
            finally:
                menu.grab_release()

        def show_selected_path(self, event=None):
            selected = self.tree.selection()
            if selected:
                if self.preview:
                    messagebox.showinfo("Prévia", "Arquivos de exemplo, sem instalação.", parent=self.root)
                else:
                    messagebox.showinfo("Local do arquivo", selected[0], parent=self.root)

        def remove_selected(self):
            if self.busy or self.preview:
                return
            selected = set(self.tree.selection())
            if not selected:
                return
            self.jobs = [plan for plan in self.jobs if str(plan.path) not in selected]
            for item in selected:
                self.results.pop(item, None)
                self.tree.delete(item)
            self.update_controls()
            self.footer_status.config(text=f"{len(selected)} arquivo(s) removido(s) da fila. Os arquivos originais não foram apagados.")

        def clear(self):
            if self.busy or self.preview:
                return
            self.jobs.clear()
            self.results.clear()
            for item in self.tree.get_children():
                self.tree.delete(item)
            self.completed = 0
            self.failed = 0
            self.failures.clear()
            self.progress["value"] = 0
            self.status_detail.config(text="Nenhuma instalação iniciada.")
            self.footer_status.config(text="Pronto para receber arquivos.")
            self.append_log("", clear=True)
            self.update_controls()

        def update_controls(self):
            enabled = "normal" if not self.busy and not self.preview else "disabled"
            self.choose_button.config(state=enabled)
            self.remove_button.config(state=enabled if self.tree.selection() else "disabled")
            self.clear_button.config(state=enabled if self.jobs else "disabled")
            self.completed = sum(v == "Concluído" for v in self.results.values())
            self.failed = sum(v == "Falhou" for v in self.results.values())
            pending = sum(1 for value in self.results.values() if value in ("Pronto para instalar", "Preparando…", "Instalando…"))
            self.stat_labels["ready"].config(text=str(pending))
            self.stat_labels["done"].config(text=str(self.completed))
            self.stat_labels["errors"].config(text=str(self.failed))
            if not self.preview:
                self.count_label.config(text=f"{len(self.jobs)} arquivo(s) selecionado(s)" if self.jobs else "Nenhum arquivo adicionado")
            # Let the user retry only failed or not-yet-completed jobs.
            has_work = any(value != "Concluído" for value in self.results.values())
            self.install_button.config(state="normal" if has_work and not self.busy and not self.preview else "disabled",
                                       text="Tentar novamente  →" if self.failed and not pending else "Revisar e instalar  →")

        def append_log(self, text, *, clear=False):
            self.log.config(state="normal")
            if clear:
                self.log.delete("1.0", "end")
            if text:
                stamp = datetime.now().strftime("%H:%M:%S")
                self.log.insert("end", f"[{stamp}] {text}\n")
                if not self.preview and text.startswith("ERRO:"):
                    try:
                        path = error_log_path()
                        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
                        with path.open("a", encoding="utf-8") as handle:
                            handle.write(f"[{datetime.now().isoformat(timespec='seconds')}] {text}\n")
                    except OSError:
                        pass
                self.log.see("end")
            self.log.config(state="disabled")

        def toggle_details(self):
            self.details_expanded = not self.details_expanded
            if self.details_expanded:
                self.log.pack(fill="x", pady=(9, 0))
                self.details_button.config(text="Ocultar detalhes  ▴")
            else:
                self.log.pack_forget()
                self.details_button.config(text="Ver detalhes  ▾")

        def copy_log(self):
            content = self.log.get("1.0", "end-1c").strip()
            if not content:
                self.footer_status.config(text="Nenhuma mensagem para copiar.")
                return
            self.root.clipboard_clear()
            self.root.clipboard_append(content)
            self.footer_status.config(text="Relatório copiado. Cole-o para pedir suporte.")

        def start_install(self):
            if self.busy or self.preview:
                return
            targets = [p for p in self.jobs if self.results.get(str(p.path)) != "Concluído"]
            if not targets:
                return
            if not messagebox.askyesno(
                "Revisar instalação",
                f"Instalar {len(targets)} arquivo(s)?\n\n" +
                "\n".join(p.path.name for p in targets[:8]) +
                (f"\n… e outros {len(targets)-8}" if len(targets) > 8 else "") +
                "\n\nUma autorização por lote DEB/RPM. AppImage e Flatpak de usuário não precisam de senha administrativa.\n"
                "Confirme somente arquivos de fontes confiáveis.", parent=self.root,
            ):
                return
            self.busy = True
            self.failures.clear()
            self.progress["value"] = 0
            self.footer_status.config(text="Preparando instalação…")
            self.status_detail.config(text="Instalação iniciada; acompanhe os detalhes abaixo.")
            self.append_log(f"Iniciando {len(targets)} instalação(ões)…")
            for p in targets:
                self._change_file(str(p.path), "Preparando…")
            self.update_controls()
            try:
                threading.Thread(target=self.worker, args=(targets,), daemon=True).start()
            except RuntimeError as exc:
                self.busy = False
                for p in targets:
                    self._change_file(str(p.path), "Falhou")
                self.update_controls()
                self.append_log(f"ERRO: Falha ao iniciar instalação: {exc}")
                messagebox.showerror("Falha ao iniciar", str(exc), parent=self.root)

        def _change_file(self, key, value):
            self.results[key] = value
            if self.tree.exists(key):
                self.tree.set(key, "status", value)
                if value == "Falhou":
                    self.tree.item(key, tags=("error",))
                elif value == "Concluído":
                    self.tree.item(key, tags=("success",))
                else:
                    self.tree.item(key, tags=())

        def worker(self, targets: list[InstallPlan]):
            successful = failed = processed = 0
            total = len(targets)
            for group in installation_groups(targets):
                names = ", ".join(plan.path.name for plan in group)
                for plan in group:
                    self.events.put(("file", str(plan.path), "Instalando…"))
                self.events.put(("status", f"Instalando {processed+1}–{processed+len(group)}/{total}"))
                self.events.put(("log", f"── {names} ──"))
                try:
                    install_group(group, log=lambda line: self.events.put(("log", line)))
                except Exception as exc:
                    failed += len(group)
                    for plan in group:
                        self.events.put(("file", str(plan.path), "Falhou"))
                    self.events.put(("log", f"ERRO: {names}: {exc}"))
                    self.events.put(("failure", f"{names}: {exc}"))
                else:
                    successful += len(group)
                    for plan in group:
                        self.events.put(("file", str(plan.path), "Concluído"))
                    self.events.put(("log", "Instalação concluída."))
                processed += len(group)
                self.events.put(("progress", processed / total * 100, processed, total))
            self.events.put(("complete", successful, failed))

        def poll_events(self):
            while True:
                try:
                    item = self.events.get_nowait()
                except queue.Empty:
                    break
                kind = item[0]
                if kind == "file":
                    self._change_file(item[1], item[2])
                    self.update_controls()
                elif kind == "status":
                    self.footer_status.config(text=item[1])
                    self.status_detail.config(text=item[1])
                elif kind == "log":
                    self.append_log(item[1])
                elif kind == "failure":
                    self.failures.append(item[1])
                elif kind == "progress":
                    self.progress["value"] = item[1]
                    self.status_detail.config(text=f"{item[2]} de {item[3]} aplicativo(s) processado(s)")
                elif kind == "complete":
                    self.busy = False
                    self.completed = sum(v == "Concluído" for v in self.results.values())
                    self.failed = sum(v == "Falhou" for v in self.results.values())
                    self.update_controls()
                    summary = f"{item[1]} instalado(s) • {item[2]} falha(s) nesta execução."
                    self.footer_status.config(text=summary)
                    if self.failures:
                        if not self.details_expanded:
                            self.toggle_details()
                        summary += "\n\nErros:\n" + "\n\n".join(self.failures[:3])
                        summary += "\n\nUse 'Copiar relatório' para enviar os detalhes."
                    (messagebox.showwarning if item[2] else messagebox.showinfo)(
                        "Instalação finalizada", summary, parent=self.root,
                    )
            self.root.after(80, self.poll_events)

        def show_help(self):
            messagebox.showinfo(
                "Como usar o Instala Fácil",
                "1. Baixe o programa no site oficial.\n"
                "2. Clique em 'Selecionar arquivos'.\n"
                "3. Confirme a instalação.\n"
                "4. Autorize com sua senha, quando o Linux solicitar.\n\n"
                "DEB: Ubuntu, Debian e derivados.\n"
                "RPM: Fedora/openSUSE com DNF/Zypper.\n"
                "AppImage: instala apenas para o usuário.\n"
                "Flatpak: requer o Flatpak instalado.\n\n"
                "Para diagnóstico: instala-facil --diagnostico\n"
                "Ajuda e contribuições: github.com/pizzatto/instala-facil (após publicação).",
                parent=self.root,
            )

        def close(self):
            if self.busy:
                messagebox.showinfo("Instalação em andamento", "Aguarde a conclusão antes de fechar para não interromper o gerenciador de pacotes.", parent=self.root)
                return
            self.root.destroy()

        def run(self):
            self.root.mainloop()

    InstallerApp().run()


def main() -> int:
    parser = argparse.ArgumentParser(description="Instala Fácil — instalador gráfico para Linux")
    parser.add_argument("--version", action="version", version=VERSION)
    parser.add_argument("--diagnostico", action="store_true", help="Verifica componentes necessários")
    parser.add_argument("--smoke-test", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--preview", action="store_true", help=argparse.SUPPRESS)
    args, paths = parser.parse_known_args()
    if args.diagnostico:
        diagnostic()
        return 0
    try:
        start_gui(paths, smoke_test=args.smoke_test, preview=args.preview)
    except Exception as exc:
        file = save_startup_error(exc)
        error = f"O Instala Fácil não conseguiu abrir: {exc}"
        if file:
            error += f"\nDetalhes: {file}"
        print(error, file=sys.stderr)
        try:
            from tkinter import Tk, messagebox
            root = Tk()
            root.withdraw()
            messagebox.showerror("Instala Fácil — erro", error, parent=root)
            root.destroy()
        except Exception:
            pass
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
