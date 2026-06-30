"""
AI-Monitor Viewer - Passwortgeschütztes Dashboard
Starte mit:  python viewer.py
"""

import os
import sys
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime
from pathlib import Path

import database as db

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

TYPE_LABELS = {
    "network":   "Netzwerk",
    "browser":   "Browser",
    "process":   "Prozess",
    "clipboard": "Zwischenablage",
    "all":       "Alle",
}
SEV_LABELS = {
    "critical": "Kritisch",
    "warning":  "Warnung",
    "info":     "Info",
}
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


# ── Login Window ──────────────────────────────────────────────────────────────

class LoginWindow:
    def __init__(self, root: tk.Tk, on_success):
        self.root = root
        self.on_success = on_success
        self.root.title("AI-Monitor · Anmeldung")
        self.root.configure(bg=BG0)
        self.root.resizable(False, False)
        center_window(self.root, 420, 340)
        self._build()

    def _build(self):
        # Header
        hdr = tk.Frame(self.root, bg=BG0)
        hdr.pack(fill="x", pady=(30, 0))
        tk.Label(hdr, text="AI-Monitor", font=("Segoe UI", 22, "bold"),
                 bg=BG0, fg=ACC).pack()
        tk.Label(hdr, text="Berufsweltmeisterschaften · Überwachungssystem",
                 font=("Segoe UI", 9), bg=BG0, fg=TEXT2).pack(pady=(2, 0))

        # Card
        card = tk.Frame(self.root, bg=BG1, bd=0, relief="flat")
        card.pack(padx=40, pady=20, fill="x")

        first_run = not db.has_credentials()
        if first_run:
            tk.Label(card, text="Ersteinrichtung — Zugangsdaten festlegen",
                     font=FONT, bg=BG1, fg=WARN).grid(
                         row=0, column=0, columnspan=2, pady=(12, 4), padx=20)

        tk.Label(card, text="Benutzername", font=FONT, bg=BG1, fg=TEXT2).grid(
            row=1, column=0, sticky="w", padx=20, pady=(12, 2))
        self.user_var = tk.StringVar(value="admin")
        user_e = tk.Entry(card, textvariable=self.user_var, font=FONT,
                          bg=BG2, fg=TEXT, insertbackground=TEXT,
                          relief="flat", bd=6, width=26)
        user_e.grid(row=2, column=0, padx=20, sticky="ew")

        tk.Label(card, text="Passwort", font=FONT, bg=BG1, fg=TEXT2).grid(
            row=3, column=0, sticky="w", padx=20, pady=(10, 2))
        self.pw_var = tk.StringVar()
        pw_e = tk.Entry(card, textvariable=self.pw_var, show="•", font=FONT,
                        bg=BG2, fg=TEXT, insertbackground=TEXT,
                        relief="flat", bd=6, width=26)
        pw_e.grid(row=4, column=0, padx=20, sticky="ew")
        pw_e.bind("<Return>", lambda _: self._login())

        if first_run:
            tk.Label(card, text="Passwort bestätigen", font=FONT, bg=BG1, fg=TEXT2).grid(
                row=5, column=0, sticky="w", padx=20, pady=(10, 2))
            self.pw2_var = tk.StringVar()
            pw2_e = tk.Entry(card, textvariable=self.pw2_var, show="•", font=FONT,
                             bg=BG2, fg=TEXT, insertbackground=TEXT,
                             relief="flat", bd=6, width=26)
            pw2_e.grid(row=6, column=0, padx=20, sticky="ew")
            pw2_e.bind("<Return>", lambda _: self._login())
        else:
            self.pw2_var = None

        btn = tk.Button(card, text="Anmelden", command=self._login,
                        bg=ACC, fg="white", font=FONT_B, relief="flat",
                        bd=0, padx=10, pady=8, cursor="hand2",
                        activebackground="#c73652", activeforeground="white")
        btn.grid(row=7, column=0, padx=20, pady=16, sticky="ew")

        card.columnconfigure(0, weight=1)

        self.status_var = tk.StringVar()
        tk.Label(self.root, textvariable=self.status_var, font=FONT,
                 bg=BG0, fg=CRIT).pack()

        pw_e.focus_set()
        self.first_run = first_run

    def _login(self):
        username = self.user_var.get().strip()
        password = self.pw_var.get()

        if self.first_run:
            pw2 = self.pw2_var.get()
            if len(username) < 2:
                self.status_var.set("Benutzername zu kurz (min. 2 Zeichen)")
                return
            if len(password) < 6:
                self.status_var.set("Passwort zu kurz (min. 6 Zeichen)")
                return
            if password != pw2:
                self.status_var.set("Passwörter stimmen nicht überein")
                return
            db.set_credentials(username, password)
            self.on_success(username)
        else:
            if db.verify_credentials(username, password):
                self.on_success(username)
            else:
                self.status_var.set("Falscher Benutzername oder Passwort")
                self.pw_var.set("")


# ── Main Viewer Window ────────────────────────────────────────────────────────

class ViewerWindow:
    def __init__(self, root: tk.Tk, admin_name: str):
        self.root = root
        self.admin = admin_name
        self._event_map: dict[str, dict] = {}
        self._filter = "all"
        self._auto_refresh = True
        self._after_id = None

        self.root.title("AI-Monitor · Aktivitätsprotokoll")
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
        # ── Top bar ──────────────────────────────────────────────────────────
        topbar = tk.Frame(self.root, bg=BG1, height=52)
        topbar.pack(fill="x")
        topbar.pack_propagate(False)

        tk.Label(topbar, text="AI-Monitor", font=("Segoe UI", 14, "bold"),
                 bg=BG1, fg=ACC).pack(side="left", padx=16, pady=12)

        self.stats_var = tk.StringVar()
        tk.Label(topbar, textvariable=self.stats_var, font=FONT,
                 bg=BG1, fg=TEXT2).pack(side="left", padx=10)

        # Right buttons
        for label, cmd in [
            ("Exportieren (CSV)", self._export_csv),
            ("Alle bestätigen",   self._ack_all),
            ("Aktualisieren",     self._refresh),
        ]:
            tk.Button(topbar, text=label, command=cmd,
                      bg=BG2, fg=TEXT, font=FONT, relief="flat",
                      padx=10, pady=6, cursor="hand2",
                      activebackground=BG3).pack(side="right", padx=4, pady=8)

        tk.Label(topbar, text=f"Angemeldet als: {self.admin}",
                 font=("Segoe UI", 9), bg=BG1, fg=TEXT2).pack(
                     side="right", padx=12)

        # ── Filter bar ────────────────────────────────────────────────────────
        fbar = tk.Frame(self.root, bg=BG0, height=40)
        fbar.pack(fill="x", padx=10, pady=(6, 0))

        tk.Label(fbar, text="Filter:", font=FONT_B, bg=BG0, fg=TEXT2).pack(
            side="left", padx=(4, 10))

        self._filter_btns: dict[str, tk.Button] = {}
        filters = ["all", "network", "browser", "process", "clipboard"]
        for f in filters:
            lbl = TYPE_LABELS.get(f, f)
            btn = tk.Button(fbar, text=lbl, font=FONT,
                            bg=BG2, fg=TEXT, relief="flat",
                            padx=12, pady=4, cursor="hand2",
                            command=lambda x=f: self._set_filter(x))
            btn.pack(side="left", padx=2)
            self._filter_btns[f] = btn
        self._highlight_filter()

        # Auto-refresh toggle
        self.ar_var = tk.BooleanVar(value=True)
        chk = tk.Checkbutton(fbar, text="Auto-Refresh (30s)",
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

        cols = ("Zeit", "Typ", "Schwere", "Beschreibung", "Status")
        self.tree = ttk.Treeview(list_frame, columns=cols,
                                  show="headings", selectmode="browse")

        widths = {"Zeit": 155, "Typ": 115, "Schwere": 95,
                  "Beschreibung": 760, "Status": 90}
        for col in cols:
            self.tree.heading(col, text=col,
                              command=lambda c=col: self._sort_column(c))
            self.tree.column(col, width=widths[col], anchor="w",
                             minwidth=50, stretch=(col == "Beschreibung"))

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
        tk.Label(header_row, text="Details", font=FONT_B, bg=BG1, fg=ACC).pack(side="left")

        self.ack_btn = tk.Button(header_row, text="Bestätigen",
                                  command=self._ack_selected,
                                  bg=BG2, fg=TEXT, font=FONT,
                                  relief="flat", padx=8, pady=2,
                                  cursor="hand2")
        self.ack_btn.pack(side="right")

        self.shot_btn = tk.Button(header_row, text="Screenshot anzeigen",
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
        if self._after_id:
            self.root.after_cancel(self._after_id)
            self._after_id = None

        events = db.get_events(event_type=self._filter)
        self._event_map.clear()

        sel_id = None
        sel = self.tree.selection()
        if sel:
            d = self._event_map.get(sel[0])
            if d:
                sel_id = d["id"]

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
            etype_l = TYPE_LABELS.get(etype, etype)
            sev_l   = SEV_LABELS.get(sev, sev)
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
            self.stats_var.set(
                f"Gesamt: {total}  |  Kritisch: {crit}  |  Warnungen: {warn}  |  Ungelesen: {unread}"
            )
        ts_now = datetime.now().strftime("%H:%M:%S")
        self.sbar_var.set(f"Zuletzt aktualisiert: {ts_now}   —   Entf-Taste: Eintrag löschen")

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
        self.detail_text.insert("end", data["details"] or "Keine weiteren Details.")
        if data["screenshot"]:
            self.detail_text.insert("end", f"\n\n📷 Screenshot: {data['screenshot']}")
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
        if messagebox.askyesno("Bestätigen", "Alle Einträge als gesehen markieren?"):
            db.acknowledge_all()
            self._refresh()

    def _delete_selected(self, _event=None):
        sel = self.tree.selection()
        if not sel:
            return
        data = self._event_map.get(sel[0])
        if data and messagebox.askyesno("Löschen", "Diesen Eintrag wirklich löschen?"):
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
            messagebox.showwarning("Screenshot", "Datei nicht gefunden.")
            return

        win = tk.Toplevel(self.root)
        win.title(f"Screenshot – {Path(path).name}")
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
            tk.Label(win, text=f"Fehler beim Laden: {e}", bg=BG0, fg=TEXT).pack()

    # ── Export ───────────────────────────────────────────────────────────────

    def _export_csv(self):
        path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV-Datei", "*.csv"), ("Alle Dateien", "*.*")],
            title="Aktivitäten exportieren",
            initialfile=f"ai_monitor_export_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
        )
        if not path:
            return
        import csv
        events = db.get_events(event_type=self._filter)
        with open(path, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f, delimiter=";")
            w.writerow(["Zeitstempel", "Typ", "Schwere", "Titel", "Details", "Screenshot", "Bestätigt"])
            for row in events:
                eid, ts, etype, sev, title, details, shot, acked = row
                w.writerow([ts, TYPE_LABELS.get(etype, etype),
                             SEV_LABELS.get(sev, sev),
                             title, details or "", shot or "",
                             "Ja" if acked else "Nein"])
        messagebox.showinfo("Export erfolgreich", f"Datei gespeichert:\n{path}")

    # ── Sort ─────────────────────────────────────────────────────────────────

    _sort_reverse: dict[str, bool] = {}

    def _sort_column(self, col):
        rev = self._sort_reverse.get(col, False)
        items = [(self.tree.set(k, col), k) for k in self.tree.get_children("")]
        items.sort(reverse=rev)
        for i, (_, k) in enumerate(items):
            self.tree.move(k, "", i)
        self._sort_reverse[col] = not rev


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    db.init_db()

    root = tk.Tk()
    root.configure(bg=BG0)

    def on_login(username):
        for w in root.winfo_children():
            w.destroy()
        root.title("AI-Monitor · Aktivitätsprotokoll")
        ViewerWindow(root, username)

    LoginWindow(root, on_login)

    try:
        root.mainloop()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
