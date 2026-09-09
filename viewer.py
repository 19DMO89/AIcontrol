"""
AI-Monitor Viewer - password-protected dashboard
Run with:  python viewer.py
"""

import os
import sys
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime
from pathlib import Path

import config
import database as db
import i18n
from i18n import t

# ── Theme ─────────────────────────────────────────────────────────────────────

BG0      = "#0d1117"
BG1      = "#161b22"
BG2      = "#21262d"
BG3      = "#30363d"
ACC      = "#e94560"
ACC2     = "#1f6feb"
TEXT     = "#e6edf3"
TEXT2    = "#8b949e"
CRIT     = "#f85149"
WARN     = "#d29922"
INFO_C   = "#58a6ff"
OK       = "#3fb950"
FONT     = ("Segoe UI", 10)
FONT_B   = ("Segoe UI", 10, "bold")
FONT_H   = ("Segoe UI", 14, "bold")
MONO     = ("Consolas", 9)

SEV_COLORS = {
    "critical": CRIT,
    "warning":  WARN,
    "info":     INFO_C,
}
TYPE_ICONS = {
    "network":   "🌐",
    "browser":   "🔎",
    "process":   "⚙",
    "clipboard": "📋",
}


def center_window(win, w, h):
    win.update_idletasks()
    sw = win.winfo_screenwidth()
    sh = win.winfo_screenheight()
    x  = (sw - w) // 2
    y  = (sh - h) // 2
    win.geometry(f"{w}x{h}+{x}+{y}")


def make_lang_switch(parent, lang, on_set_lang, bg):
    """A small [EN|DE] toggle. Active language highlighted."""
    frame = tk.Frame(parent, bg=bg)
    for code in i18n.LANGUAGES:
        active = (code == lang)
        tk.Button(
            frame, text=code.upper(), font=("Segoe UI", 8, "bold"),
            bg=ACC if active else BG2, fg="white" if active else TEXT2,
            relief="flat", bd=0, padx=8, pady=2, cursor="hand2",
            activebackground=ACC if active else BG3,
            command=(lambda c=code: on_set_lang(c)) if not active else (lambda: None),
        ).pack(side="left", padx=1)
    return frame


# ── Login Window ──────────────────────────────────────────────────────────────

class LoginWindow:
    def __init__(self, root: tk.Tk, lang: str, on_set_lang, on_success):
        self.root = root
        self.lang = lang
        self.on_set_lang = on_set_lang
        self.on_success = on_success
        self.root.title(t("login.window_title", lang))
        self.root.configure(bg=BG0)
        self.root.resizable(False, False)
        # First-run setup adds a "confirm password" field, which needs extra
        # height. The status line below the button also needs room, or error
        # messages land off-screen on this fixed-size, non-resizable window
        # and look like no feedback at all.
        height = 530 if not db.has_credentials() else 410
        center_window(self.root, 440, height)
        self._build()

    def _build(self):
        lang = self.lang

        # Language switch, top-right
        sw = make_lang_switch(self.root, lang, self.on_set_lang, BG0)
        sw.pack(anchor="e", padx=12, pady=(8, 0))

        # Header
        hdr = tk.Frame(self.root, bg=BG0)
        hdr.pack(fill="x", pady=(10, 0))
        tk.Label(hdr, text="AI-Monitor", font=("Segoe UI", 22, "bold"),
                 bg=BG0, fg=ACC).pack()
        tk.Label(hdr, text=t("login.subtitle", lang),
                 font=("Segoe UI", 9), bg=BG0, fg=TEXT2).pack(pady=(2, 0))
        tk.Label(hdr, text=t("login.version", lang, version=config.VERSION),
                 font=("Segoe UI", 8), bg=BG0, fg=TEXT2).pack(pady=(1, 0))

        # Card
        card = tk.Frame(self.root, bg=BG1, bd=0, relief="flat")
        card.pack(padx=40, pady=20, fill="x")

        first_run = not db.has_credentials()
        if first_run:
            tk.Label(card, text=t("login.first_run", lang),
                     font=FONT, bg=BG1, fg=WARN).grid(
                         row=0, column=0, columnspan=2, pady=(12, 4), padx=20)

        tk.Label(card, text=t("login.username", lang), font=FONT, bg=BG1, fg=TEXT2).grid(
            row=1, column=0, sticky="w", padx=20, pady=(12, 2))
        self.user_var = tk.StringVar(value="admin")
        user_e = tk.Entry(card, textvariable=self.user_var, font=FONT,
                          bg=BG2, fg=TEXT, insertbackground=TEXT,
                          relief="flat", bd=6, width=26)
        user_e.grid(row=2, column=0, padx=20, sticky="ew")

        tk.Label(card, text=t("login.password", lang), font=FONT, bg=BG1, fg=TEXT2).grid(
            row=3, column=0, sticky="w", padx=20, pady=(10, 2))
        self.pw_var = tk.StringVar()
        pw_e = tk.Entry(card, textvariable=self.pw_var, show="•", font=FONT,
                        bg=BG2, fg=TEXT, insertbackground=TEXT,
                        relief="flat", bd=6, width=26)
        pw_e.grid(row=4, column=0, padx=20, sticky="ew")
        pw_e.bind("<Return>", lambda _: self._login())

        if first_run:
            tk.Label(card, text=t("login.confirm", lang), font=FONT, bg=BG1, fg=TEXT2).grid(
                row=5, column=0, sticky="w", padx=20, pady=(10, 2))
            self.pw2_var = tk.StringVar()
            pw2_e = tk.Entry(card, textvariable=self.pw2_var, show="•", font=FONT,
                             bg=BG2, fg=TEXT, insertbackground=TEXT,
                             relief="flat", bd=6, width=26)
            pw2_e.grid(row=6, column=0, padx=20, sticky="ew")
            pw2_e.bind("<Return>", lambda _: self._login())
        else:
            self.pw2_var = None

        btn = tk.Button(card, text=t("login.sign_in", lang), command=self._login,
                        bg=ACC, fg="white", font=FONT_B, relief="flat",
                        bd=0, padx=10, pady=8, cursor="hand2",
                        activebackground="#c73652", activeforeground="white")
        btn.grid(row=7, column=0, padx=20, pady=(16, 4), sticky="ew")

        # Status line lives inside the card (fixed row) so error messages are
        # always visible and the layout doesn't jump when one appears.
        self.status_var = tk.StringVar()
        tk.Label(card, textvariable=self.status_var, font=FONT,
                 bg=BG1, fg=CRIT, wraplength=340, justify="center").grid(
                     row=8, column=0, padx=20, pady=(0, 12), sticky="ew")

        card.columnconfigure(0, weight=1)

        pw_e.focus_set()
        self.first_run = first_run

    def _login(self):
        lang = self.lang
        username = self.user_var.get().strip()
        password = self.pw_var.get()

        if self.first_run:
            pw2 = self.pw2_var.get()
            if len(username) < 2:
                self.status_var.set(t("login.err_user_short", lang))
                return
            if len(password) < 6:
                self.status_var.set(t("login.err_pw_short", lang))
                return
            if password != pw2:
                self.status_var.set(t("login.err_pw_match", lang))
                return
            db.set_credentials(username, password)
            self.on_success(username)
        else:
            if db.verify_credentials(username, password):
                self.on_success(username)
            else:
                self.status_var.set(t("login.err_wrong", lang))
                self.pw_var.set("")


# ── Main Viewer Window ────────────────────────────────────────────────────────

class ViewerWindow:
    def __init__(self, root: tk.Tk, lang: str, on_set_lang, admin_name: str):
        self.root = root
        self.lang = lang
        self.on_set_lang = on_set_lang
        self.admin = admin_name
        self._event_map: dict[str, dict] = {}
        self._filter = "all"
        self._auto_refresh = True
        self._after_id = None

        self.root.title(t("app.window_title", lang))
        self.root.configure(bg=BG0)
        center_window(self.root, 1280, 780)

        self._apply_style()
        self._build()
        self._refresh()

    # ── Style ────────────────────────────────────────────────────────────────

    def _apply_style(self):
        s = ttk.Style()
        s.theme_use("clam")
        s.configure("Treeview",
                    background=BG1, foreground=TEXT,
                    fieldbackground=BG1, rowheight=30,
                    font=FONT, borderwidth=0)
        s.configure("Treeview.Heading",
                    background=BG2, foreground=TEXT2,
                    font=FONT_B, borderwidth=0, relief="flat")
        s.map("Treeview",
              background=[("selected", ACC2)],
              foreground=[("selected", "white")])
        s.configure("Vertical.TScrollbar",
                    background=BG2, troughcolor=BG1,
                    arrowcolor=TEXT2, borderwidth=0)
        s.configure("TSeparator", background=BG3)

    # ── Build UI ─────────────────────────────────────────────────────────────

    def _build(self):
        lang = self.lang

        # ── Top bar ──────────────────────────────────────────────────────────
        topbar = tk.Frame(self.root, bg=BG1, height=52)
        topbar.pack(fill="x")
        topbar.pack_propagate(False)

        tk.Label(topbar, text="AI-Monitor", font=("Segoe UI", 14, "bold"),
                 bg=BG1, fg=ACC).pack(side="left", padx=(16, 4), pady=12)
        tk.Label(topbar, text=f"v{config.VERSION}", font=("Segoe UI", 8),
                 bg=BG1, fg=TEXT2).pack(side="left", pady=16)

        self.stats_var = tk.StringVar()
        tk.Label(topbar, textvariable=self.stats_var, font=FONT,
                 bg=BG1, fg=TEXT2).pack(side="left", padx=10)

        # Right buttons
        for label, cmd in [
            (t("app.export_csv", lang), self._export_csv),
            (t("app.ack_all", lang),    self._ack_all),
            (t("app.refresh", lang),    self._refresh),
        ]:
            tk.Button(topbar, text=label, command=cmd,
                      bg=BG2, fg=TEXT, font=FONT, relief="flat",
                      padx=10, pady=6, cursor="hand2",
                      activebackground=BG3).pack(side="right", padx=4, pady=8)

        make_lang_switch(topbar, lang, self.on_set_lang, BG1).pack(
            side="right", padx=8, pady=14)

        tk.Label(topbar, text=t("app.signed_in_as", lang, name=self.admin),
                 font=("Segoe UI", 9), bg=BG1, fg=TEXT2).pack(
                     side="right", padx=12)

        # ── Filter bar ────────────────────────────────────────────────────────
        fbar = tk.Frame(self.root, bg=BG0, height=40)
        fbar.pack(fill="x", padx=10, pady=(6, 0))

        tk.Label(fbar, text=t("app.filter", lang), font=FONT_B, bg=BG0, fg=TEXT2).pack(
            side="left", padx=(4, 10))

        self._filter_btns: dict[str, tk.Button] = {}
        filters = ["all", "network", "browser", "process", "clipboard"]
        for f in filters:
            btn = tk.Button(fbar, text=t(f"type.{f}", lang), font=FONT,
                            bg=BG2, fg=TEXT, relief="flat",
                            padx=12, pady=4, cursor="hand2",
                            command=lambda x=f: self._set_filter(x))
            btn.pack(side="left", padx=2)
            self._filter_btns[f] = btn
        self._highlight_filter()

        # Auto-refresh toggle
        self.ar_var = tk.BooleanVar(value=True)
        chk = tk.Checkbutton(fbar, text=t("app.auto_refresh", lang),
                              variable=self.ar_var, font=FONT,
                              bg=BG0, fg=TEXT2, selectcolor=BG2,
                              activebackground=BG0,
                              command=self._toggle_autorefresh)
        chk.pack(side="right", padx=10)

        # ── Main split ────────────────────────────────────────────────────────
        pane = tk.PanedWindow(self.root, orient="vertical",
                              bg=BG0, sashwidth=4, sashrelief="flat")
        pane.pack(fill="both", expand=True, padx=10, pady=6)

        # ── Events list ───────────────────────────────────────────────────────
        list_frame = tk.Frame(pane, bg=BG0)
        pane.add(list_frame, height=470, minsize=150)

        self._cols = ("time", "type", "severity", "description", "status")
        self.tree = ttk.Treeview(list_frame, columns=self._cols,
                                  show="headings", selectmode="browse")

        widths = {"time": 155, "type": 115, "severity": 95,
                  "description": 760, "status": 90}
        for col in self._cols:
            self.tree.heading(col, text=t(f"col.{col}", lang),
                              command=lambda c=col: self._sort_column(c))
            self.tree.column(col, width=widths[col], anchor="w",
                             minwidth=50, stretch=(col == "description"))

        vsb = ttk.Scrollbar(list_frame, orient="vertical",
                            command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")

        self.tree.tag_configure("critical", foreground=CRIT)
        self.tree.tag_configure("warning",  foreground=WARN)
        self.tree.tag_configure("info",     foreground=INFO_C)
        self.tree.tag_configure("acked",    foreground=TEXT2)

        self.tree.bind("<<TreeviewSelect>>", self._on_select)
        self.tree.bind("<Delete>",           self._delete_selected)

        # ── Detail panel ──────────────────────────────────────────────────────
        detail_frame = tk.Frame(pane, bg=BG1)
        pane.add(detail_frame, height=220, minsize=80)

        header_row = tk.Frame(detail_frame, bg=BG1)
        header_row.pack(fill="x", padx=12, pady=(8, 0))
        tk.Label(header_row, text=t("app.details", lang), font=FONT_B, bg=BG1, fg=ACC).pack(side="left")

        self.ack_btn = tk.Button(header_row, text=t("app.acknowledge", lang),
                                  command=self._ack_selected,
                                  bg=BG2, fg=TEXT, font=FONT,
                                  relief="flat", padx=8, pady=2,
                                  cursor="hand2")
        self.ack_btn.pack(side="right")

        self.shot_btn = tk.Button(header_row, text=t("app.show_screenshot", lang),
                                   command=self._show_screenshot,
                                   bg=BG2, fg=TEXT, font=FONT,
                                   relief="flat", padx=8, pady=2,
                                   cursor="hand2", state="disabled")
        self.shot_btn.pack(side="right", padx=6)

        self.detail_text = tk.Text(detail_frame, bg=BG2, fg=TEXT,
                                   font=MONO, relief="flat",
                                   padx=12, pady=8, wrap="word",
                                   state="disabled")
        detail_sb = ttk.Scrollbar(detail_frame, orient="vertical",
                                   command=self.detail_text.yview)
        self.detail_text.configure(yscrollcommand=detail_sb.set)
        detail_sb.pack(side="right", fill="y", padx=(0, 4))
        self.detail_text.pack(fill="both", expand=True, padx=(8, 0), pady=(4, 8))

        # ── Status bar ────────────────────────────────────────────────────────
        sbar = tk.Frame(self.root, bg=BG2, height=24)
        sbar.pack(fill="x", side="bottom")
        sbar.pack_propagate(False)
        self.sbar_var = tk.StringVar()
        tk.Label(sbar, textvariable=self.sbar_var, font=("Segoe UI", 8),
                 bg=BG2, fg=TEXT2).pack(side="left", padx=10)

    # ── Filter ───────────────────────────────────────────────────────────────

    def _set_filter(self, f):
        self._filter = f
        self._highlight_filter()
        self._refresh()

    def _highlight_filter(self):
        for key, btn in self._filter_btns.items():
            btn.configure(bg=ACC if key == self._filter else BG2,
                          fg="white" if key == self._filter else TEXT)

    # ── Refresh ──────────────────────────────────────────────────────────────

    def _refresh(self):
        lang = self.lang
        if self._after_id:
            self.root.after_cancel(self._after_id)
            self._after_id = None

        events = db.get_events(event_type=self._filter)

        sel_id = None
        sel = self.tree.selection()
        if sel:
            d = self._event_map.get(sel[0])
            if d:
                sel_id = d["id"]

        self._event_map.clear()
        for item in self.tree.get_children():
            self.tree.delete(item)

        new_sel = None
        for row in events:
            eid, ts, etype, sev, title, details, shot, acked = row
            try:
                dt = datetime.fromisoformat(ts)
                ts_fmt = dt.strftime("%d.%m.%Y  %H:%M:%S")
            except Exception:
                ts_fmt = ts

            icon    = TYPE_ICONS.get(etype, "")
            etype_l = t(f"type.{etype}", lang)
            if etype_l == f"type.{etype}":       # no translation for this type
                etype_l = etype
            sev_l   = t(f"sev.{sev}", lang)
            tag     = "acked" if acked else sev

            item = self.tree.insert("", "end", values=(
                ts_fmt,
                f"{icon} {etype_l}",
                sev_l,
                title,
                "✓" if acked else "•",
            ), tags=(tag,))

            self._event_map[item] = {
                "id": eid, "details": details,
                "screenshot": shot, "acked": bool(acked),
            }

            if eid == sel_id:
                new_sel = item

        if new_sel:
            self.tree.selection_set(new_sel)
            self.tree.see(new_sel)

        # Stats
        stats = db.get_stats()
        if stats:
            total, crit, warn, unread = stats
            self.stats_var.set(t("app.stats", lang, total=total, crit=crit,
                                 warn=warn, unread=unread))
        ts_now = datetime.now().strftime("%H:%M:%S")
        self.sbar_var.set(t("app.status_bar", lang, time=ts_now))

        if self._auto_refresh:
            self._after_id = self.root.after(30_000, self._refresh)

    def _toggle_autorefresh(self):
        self._auto_refresh = self.ar_var.get()
        if self._auto_refresh:
            self._after_id = self.root.after(30_000, self._refresh)
        elif self._after_id:
            self.root.after_cancel(self._after_id)
            self._after_id = None

    # ── Selection ────────────────────────────────────────────────────────────

    def _on_select(self, _event=None):
        sel = self.tree.selection()
        if not sel:
            return
        data = self._event_map.get(sel[0])
        if not data:
            return

        self.detail_text.configure(state="normal")
        self.detail_text.delete("1.0", "end")
        self.detail_text.insert("end", data["details"] or t("app.no_details", self.lang))
        if data["screenshot"]:
            self.detail_text.insert(
                "end", "\n\n" + t("app.screenshot_line", self.lang, path=data["screenshot"]))
        self.detail_text.configure(state="disabled")

        has_shot = bool(data["screenshot"]) and Path(data["screenshot"]).exists()
        self.shot_btn.configure(state="normal" if has_shot else "disabled")

    # ── Actions ──────────────────────────────────────────────────────────────

    def _ack_selected(self):
        sel = self.tree.selection()
        if not sel:
            return
        data = self._event_map.get(sel[0])
        if data:
            db.acknowledge_event(data["id"])
            self._refresh()

    def _ack_all(self):
        if messagebox.askyesno(t("dlg.ack_all_title", self.lang),
                               t("dlg.ack_all_msg", self.lang)):
            db.acknowledge_all()
            self._refresh()

    def _delete_selected(self, _event=None):
        sel = self.tree.selection()
        if not sel:
            return
        data = self._event_map.get(sel[0])
        if data and messagebox.askyesno(t("dlg.delete_title", self.lang),
                                        t("dlg.delete_msg", self.lang)):
            db.delete_event(data["id"])
            self._refresh()

    def _show_screenshot(self):
        sel = self.tree.selection()
        if not sel:
            return
        data = self._event_map.get(sel[0])
        if not data or not data["screenshot"]:
            return
        path = data["screenshot"]
        if not Path(path).exists():
            messagebox.showwarning(t("dlg.screenshot_title", self.lang),
                                   t("dlg.screenshot_missing", self.lang))
            return

        win = tk.Toplevel(self.root)
        win.title(t("dlg.screenshot_window", self.lang, name=Path(path).name))
        win.configure(bg=BG0)
        try:
            from PIL import Image, ImageTk
            img = Image.open(path)
            img.thumbnail((1200, 800))
            photo = ImageTk.PhotoImage(img)
            lbl = tk.Label(win, image=photo, bg=BG0)
            lbl.image = photo
            lbl.pack(padx=10, pady=10)
        except Exception as e:
            tk.Label(win, text=t("dlg.screenshot_load_err", self.lang, error=e),
                     bg=BG0, fg=TEXT).pack()

    # ── Export ───────────────────────────────────────────────────────────────

    def _export_csv(self):
        lang = self.lang
        path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[(t("dlg.csv_files", lang), "*.csv"),
                       (t("dlg.all_files", lang), "*.*")],
            title=t("dlg.export_title", lang),
            initialfile=f"ai_monitor_export_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
        )
        if not path:
            return
        import csv
        events = db.get_events(event_type=self._filter)
        with open(path, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f, delimiter=";")
            w.writerow([t("csv.timestamp", lang), t("csv.type", lang),
                        t("csv.severity", lang), t("csv.title", lang),
                        t("csv.details", lang), t("csv.screenshot", lang),
                        t("csv.acknowledged", lang)])
            for row in events:
                eid, ts, etype, sev, title, details, shot, acked = row
                w.writerow([ts, t(f"type.{etype}", lang),
                             t(f"sev.{sev}", lang),
                             title, details or "", shot or "",
                             t("csv.yes", lang) if acked else t("csv.no", lang)])
        messagebox.showinfo(t("dlg.export_ok_title", lang),
                            t("dlg.export_ok_msg", lang, path=path))

    # ── Sort ─────────────────────────────────────────────────────────────────

    _sort_reverse: dict[str, bool] = {}

    def _sort_column(self, col):
        rev = self._sort_reverse.get(col, False)
        items = [(self.tree.set(k, col), k) for k in self.tree.get_children("")]
        items.sort(reverse=rev)
        for i, (_, k) in enumerate(items):
            self.tree.move(k, "", i)
        self._sort_reverse[col] = not rev


# ── App shell (owns the root, current language and current screen) ────────────

class App:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.lang = i18n.normalize(db.get_setting("language", config.DEFAULT_LANGUAGE))
        self.admin = None
        self._show_login()

    def set_lang(self, lang: str):
        self.lang = i18n.normalize(lang)
        db.set_setting("language", self.lang)
        if self.admin:
            self._show_viewer()
        else:
            self._show_login()

    def _clear(self):
        for w in self.root.winfo_children():
            w.destroy()

    def _show_login(self):
        self._clear()
        LoginWindow(self.root, self.lang, self.set_lang, self._on_login)

    def _on_login(self, username: str):
        self.admin = username
        self._show_viewer()

    def _show_viewer(self):
        self._clear()
        ViewerWindow(self.root, self.lang, self.set_lang, self.admin)


# ── Entry point ───────────────────────────────────────────────────────────────

def _attach_console():
    """AIMonitorDashboard.exe is built as a windowed (no-console) app for the
    normal double-click use case. --set-credentials is a CLI action though,
    so borrow the caller's console (e.g. the installer's PowerShell window)
    to print/prompt on, falling back to a fresh console window if none."""
    import ctypes
    ATTACH_PARENT_PROCESS = 0xFFFFFFFF
    kernel32 = ctypes.windll.kernel32
    if not kernel32.AttachConsole(ATTACH_PARENT_PROCESS):
        kernel32.AllocConsole()
    sys.stdout = open("CONOUT$", "w")
    sys.stderr = open("CONOUT$", "w")
    sys.stdin = open("CONIN$", "r")


def _set_credentials_cli():
    """Seed the admin login during installation, so the dashboard never has
    an unclaimed first-run state that whoever opens it first could grab."""
    import getpass
    _attach_console()
    db.init_db()
    lang = i18n.normalize(db.get_setting("language", config.DEFAULT_LANGUAGE))
    username = sys.argv[2] if len(sys.argv) > 2 else input(t("cli.username", lang)).strip()
    if len(username) < 2:
        print(t("cli.err_user_short", lang), file=sys.stderr)
        sys.exit(1)
    password = getpass.getpass(t("cli.password", lang))
    password2 = getpass.getpass(t("cli.confirm", lang))
    if len(password) < 6:
        print(t("cli.err_pw_short", lang), file=sys.stderr)
        sys.exit(1)
    if password != password2:
        print(t("cli.err_pw_match", lang), file=sys.stderr)
        sys.exit(1)
    db.set_credentials(username, password)
    print(t("cli.ok", lang, username=username))
    sys.exit(0)


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--set-credentials":
        _set_credentials_cli()

    if len(sys.argv) > 1 and sys.argv[1] == "--version":
        _attach_console()
        print(config.VERSION)
        sys.exit(0)

    if len(sys.argv) > 1 and sys.argv[1] == "--has-credentials":
        # Silent probe for the installer: exit 0 if an admin login is already
        # configured, 1 if not. Lets a re-install skip the password prompt.
        db.init_db()
        sys.exit(0 if db.has_credentials() else 1)

    db.init_db()

    root = tk.Tk()
    root.configure(bg=BG0)
    App(root)

    try:
        root.mainloop()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
