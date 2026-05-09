#!/usr/bin/env python3
"""ArcAurora-kde color picker GUI (PySide6).

Edits colors.conf, regenerates the theme, optionally installs it.

Setup (once):
    pip install --user PySide6

Run:
    python3 theme_gui.py
"""

import configparser
import re
import subprocess
import sys
from pathlib import Path

from PySide6.QtCore import QSize, QByteArray
from PySide6.QtGui import QColor, QPalette
from PySide6.QtSvgWidgets import QSvgWidget
from PySide6.QtWidgets import (
    QApplication, QColorDialog, QFrame, QGridLayout, QGroupBox, QHBoxLayout,
    QLabel, QLineEdit, QMainWindow, QMessageBox, QPushButton,
    QStatusBar, QVBoxLayout, QWidget,
)

import generate as g

REPO = Path(__file__).resolve().parent
CONF = REPO / "colors.conf"

ACCENT_TOKENS = [
    "accent_secondary",
    "accent_dark_a", "accent_dark_b", "accent_dark_c",
    "accent_dark_d", "accent_dark_e", "accent_dark_f",
]
BG_TOKENS = ["bg_alt", "bg_alt2", "bg_dark", "bg_darker", "bg_mid", "bg_deepest"]

HEX_RE = re.compile(r"^#[0-9a-fA-F]{6}$")


def swatch(initial="#000000", w=22, h=22):
    f = QFrame()
    f.setFixedSize(QSize(w, h))
    f.setFrameShape(QFrame.Box)
    f.setLineWidth(1)
    f.setAutoFillBackground(True)
    set_swatch_color(f, initial)
    return f


def set_swatch_color(frame, hex_str):
    pal = frame.palette()
    pal.setColor(QPalette.Window, QColor(hex_str))
    frame.setPalette(pal)


class App(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ArcAurora colors")
        self.resize(720, 600)

        self.accent = g.ORIG_ACCENT
        self.background = g.ORIG_BACKGROUND
        self.overrides = {}

        self._load_conf()

        central = QWidget()
        self.setCentralWidget(central)
        outer = QVBoxLayout(central)

        cols = QHBoxLayout()
        outer.addLayout(cols, stretch=1)

        # ── BASE column ────────────────────────────────────────────────
        base_box = QGroupBox("BASE")
        base_layout = QVBoxLayout(base_box)
        self.accent_swatch, self.accent_edit = self._build_base(
            base_layout, "accent", self.accent, self._on_accent_changed,
            self._pick_accent)
        self.bg_swatch, self.bg_edit = self._build_base(
            base_layout, "background", self.background,
            self._on_background_changed, self._pick_background)
        base_layout.addStretch(1)
        cols.addWidget(base_box, stretch=1)

        # ── DERIVED column ─────────────────────────────────────────────
        d_box = QGroupBox("DERIVED (live preview)")
        d_layout = QVBoxLayout(d_box)
        d_layout.addWidget(self._heading("accent family"))
        self.derived_swatches = {}
        self.derived_value = {}
        self.override_buttons = {}
        d_layout.addLayout(self._build_derived_grid(ACCENT_TOKENS))
        d_layout.addSpacing(10)
        d_layout.addWidget(self._heading("background family"))
        d_layout.addLayout(self._build_derived_grid(BG_TOKENS))
        d_layout.addStretch(1)
        cols.addWidget(d_box, stretch=2)

        # ── preview ────────────────────────────────────────────────────
        outer.addWidget(self._build_preview())

        # ── buttons ────────────────────────────────────────────────────
        btns = QHBoxLayout()
        btn_reset = QPushButton("Reset to defaults")
        btn_reset.clicked.connect(self._reset)
        btns.addWidget(btn_reset)
        btns.addStretch(1)
        btn_gen = QPushButton("Generate")
        btn_gen.clicked.connect(self._generate_only)
        btns.addWidget(btn_gen)
        btn_install = QPushButton("Generate + Install")
        btn_install.setDefault(True)
        btn_install.clicked.connect(self._generate_install)
        btns.addWidget(btn_install)
        outer.addLayout(btns)

        self.setStatusBar(QStatusBar())
        self.statusBar().showMessage("Ready.")

        self._refresh_derived()

    # ── persistence ────────────────────────────────────────────────────
    def _load_conf(self):
        if not CONF.exists():
            return
        cfg = configparser.ConfigParser()
        try:
            cfg.read(CONF, encoding="utf-8")
        except Exception:
            return
        if cfg.has_option("base", "accent"):
            v = cfg.get("base", "accent").strip()
            if HEX_RE.match(v):
                self.accent = v.lower()
        if cfg.has_option("base", "background"):
            v = cfg.get("base", "background").strip()
            if HEX_RE.match(v):
                self.background = v.lower()
        if cfg.has_section("overrides"):
            for k, v in cfg.items("overrides"):
                v = v.strip()
                if HEX_RE.match(v):
                    self.overrides[k] = v.lower()

    def _save_conf(self):
        lines = [
            "# ArcAurora-kde color palette",
            "# Edit with theme_gui.py or by hand.",
            "",
            "[base]",
            f"accent     = {self.accent}",
            f"background = {self.background}",
            "",
        ]
        if self.overrides:
            lines.append("[overrides]")
            for k in sorted(self.overrides):
                lines.append(f"{k} = {self.overrides[k]}")
            lines.append("")
        CONF.write_text("\n".join(lines), encoding="utf-8")

    # ── ui builders ────────────────────────────────────────────────────
    def _heading(self, text):
        lbl = QLabel(text)
        f = lbl.font()
        f.setBold(True)
        lbl.setFont(f)
        return lbl

    def _build_base(self, parent_layout, label_text, value, on_change, on_pick):
        parent_layout.addWidget(self._heading(label_text))
        sw = QFrame()
        sw.setFixedHeight(46)
        sw.setMinimumWidth(220)
        sw.setFrameShape(QFrame.Box)
        sw.setAutoFillBackground(True)
        set_swatch_color(sw, value)
        parent_layout.addWidget(sw)

        row = QHBoxLayout()
        edit = QLineEdit(value)
        edit.setMaxLength(7)
        edit.setMaximumWidth(110)
        edit.textChanged.connect(on_change)
        row.addWidget(edit)
        btn = QPushButton("Pick…")
        btn.clicked.connect(on_pick)
        row.addWidget(btn)
        row.addStretch(1)
        parent_layout.addLayout(row)
        parent_layout.addSpacing(8)
        return sw, edit

    # ── preview ────────────────────────────────────────────────────────
    def _build_preview(self):
        """Mock window. Title-bar buttons are the *actual* Aurorae SVGs from
        the theme, re-rendered live with the chosen palette. Body rows are
        synthetic QLabels so contrast is easy to read at a glance.

        Foreground colors mirror the kvconfig defaults (text=#dfdfdf,
        highlight text=#ffffff).
        """
        box = QGroupBox("PREVIEW")
        outer = QVBoxLayout(box)

        self.preview_rows = {}      # role -> QWidget colored via _style_widget
        self.preview_buttons = {}   # name -> QSvgWidget for Aurorae icons

        # ── title bar: bg_alt + title text + 4 real Aurorae SVG buttons ──
        title_bar = QWidget()
        title_bar.setAutoFillBackground(True)
        tlay = QHBoxLayout(title_bar)
        tlay.setContentsMargins(10, 4, 4, 4)
        tlay.setSpacing(2)
        title_lbl = QLabel("ArcAurora — Sample Window")
        tlay.addWidget(title_lbl)
        tlay.addStretch(1)
        # Order matches a typical KDE title bar (left→right).
        for name in ("minimize", "restore", "maximize", "close"):
            sw = QSvgWidget()
            sw.setFixedSize(QSize(26, 26))
            self.preview_buttons[name] = sw
            tlay.addWidget(sw)
        self.preview_rows["titlebar"] = title_bar
        self.preview_rows["titlebar_text"] = title_lbl
        outer.addWidget(title_bar)

        # ── body: list-like rows on bg_base ──────────────────────────────
        def row(role, text, height=26):
            lbl = QLabel(text)
            lbl.setAutoFillBackground(True)
            lbl.setMargin(6)
            lbl.setMinimumHeight(height)
            self.preview_rows[role] = lbl
            return lbl

        outer.addWidget(row("body",     "  Window content — normal text", 28))
        outer.addWidget(row("alt_row",  "  Alternate row"))
        outer.addWidget(row("hovered",  "  Hovered item"))
        outer.addWidget(row("selected", "  Selected item"))
        outer.addWidget(row("body2",    "  Another normal item"))

        outer.setSpacing(0)
        outer.setContentsMargins(10, 14, 10, 10)
        return box

    def _style_widget(self, w, bg, fg="#dfdfdf"):
        pal = w.palette()
        pal.setColor(QPalette.Window, QColor(bg))
        pal.setColor(QPalette.WindowText, QColor(fg))
        w.setPalette(pal)

    def _render_template_to_bytes(self, rel_path, tokens):
        """Render templates/<rel_path>.tmpl with current tokens → bytes."""
        tmpl = REPO / "templates" / (rel_path + ".tmpl")
        if not tmpl.exists():
            return None
        rendered = g.render_text(tmpl.read_text(encoding="utf-8"), tokens)
        return QByteArray(rendered.encode("utf-8"))

    def _refresh_preview(self, tokens):
        text_fg = "#dfdfdf"
        highlight_fg = "#ffffff"
        roles = {
            "titlebar":      (tokens["bg_alt"],          text_fg),
            "titlebar_text": (tokens["bg_alt"],          text_fg),
            "body":          (tokens["bg_base"],         text_fg),
            "alt_row":       (tokens["bg_alt2"],         text_fg),
            "hovered":       (tokens["accent_secondary"], highlight_fg),
            "selected":      (tokens["accent_primary"],   highlight_fg),
            "body2":         (tokens["bg_base"],         text_fg),
        }
        for role, (bg, fg) in roles.items():
            self._style_widget(self.preview_rows[role], bg, fg)

        # Re-render the four Aurorae SVGs against the new palette.
        for name, widget in self.preview_buttons.items():
            data = self._render_template_to_bytes(
                f"aurorae/ArcAurora-dark/{name}.svg", tokens)
            if data is not None:
                widget.load(data)

    def _build_derived_grid(self, tokens):
        grid = QGridLayout()
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(4)
        for r, tok in enumerate(tokens):
            sw = swatch()
            grid.addWidget(sw, r, 0)
            lbl = QLabel(tok)
            lbl.setMinimumWidth(140)
            grid.addWidget(lbl, r, 1)
            val_edit = QLineEdit("#000000")
            val_edit.setReadOnly(True)
            val_edit.setMaximumWidth(90)
            grid.addWidget(val_edit, r, 2)
            btn = QPushButton("Override…")
            btn.setFixedWidth(110)
            btn.setToolTip(
                "Pin this token to a specific hex value. "
                "It will stop auto-deriving from the base color.")
            btn.clicked.connect(lambda _=False, t=tok: self._toggle_override(t))
            grid.addWidget(btn, r, 3)
            self.derived_swatches[tok] = sw
            self.derived_value[tok] = val_edit
            self.override_buttons[tok] = btn
        grid.setColumnStretch(4, 1)
        return grid

    # ── color pickers ──────────────────────────────────────────────────
    def _pick_color(self, current_hex):
        c = QColorDialog.getColor(QColor(current_hex), self)
        if c.isValid():
            return c.name().lower()
        return None

    def _pick_accent(self):
        new = self._pick_color(self.accent)
        if new:
            self.accent_edit.setText(new)

    def _pick_background(self):
        new = self._pick_color(self.background)
        if new:
            self.bg_edit.setText(new)

    def _on_accent_changed(self, text):
        text = text.strip().lower()
        if HEX_RE.match(text):
            self.accent = text
            set_swatch_color(self.accent_swatch, text)
            self._set_invalid(self.accent_edit, False)
            self._refresh_derived()
        else:
            self._set_invalid(self.accent_edit, True)

    def _on_background_changed(self, text):
        text = text.strip().lower()
        if HEX_RE.match(text):
            self.background = text
            set_swatch_color(self.bg_swatch, text)
            self._set_invalid(self.bg_edit, False)
            self._refresh_derived()
        else:
            self._set_invalid(self.bg_edit, True)

    def _set_invalid(self, edit, invalid):
        edit.setStyleSheet(
            "QLineEdit { border: 2px solid #c0392b; }" if invalid else ""
        )

    # ── overrides ──────────────────────────────────────────────────────
    def _toggle_override(self, token):
        if token in self.overrides:
            del self.overrides[token]
            self._refresh_derived()
            self.statusBar().showMessage(f"{token}: reverted to auto.", 4000)
            return
        cur = self.derived_value[token].text()
        new = self._pick_color(cur)
        if new:
            self.overrides[token] = new
            self._refresh_derived()
            self.statusBar().showMessage(f"{token}: pinned to {new}.", 4000)

    def _refresh_derived(self):
        if not (HEX_RE.match(self.accent) and HEX_RE.match(self.background)):
            return
        try:
            tokens = g.compute_tokens(self.accent, self.background)
        except Exception:
            return
        for k, v in self.overrides.items():
            tokens[k] = v
        for tok in ACCENT_TOKENS + BG_TOKENS:
            val = tokens.get(tok, "#000000")
            set_swatch_color(self.derived_swatches[tok], val)
            self.derived_value[tok].setText(val)
            pinned = tok in self.overrides
            btn = self.override_buttons[tok]
            if pinned:
                btn.setText("Reset auto")
                btn.setToolTip(
                    "Remove the manual override and resume auto-deriving "
                    "this tone from the base color.")
            else:
                btn.setText("Override…")
                btn.setToolTip(
                    "Pin this token to a specific hex value. "
                    "It will stop auto-deriving from the base color.")
        self._refresh_preview(tokens)

    def _reset(self):
        self.accent = g.ORIG_ACCENT
        self.background = g.ORIG_BACKGROUND
        self.overrides.clear()
        self.accent_edit.setText(self.accent)
        self.bg_edit.setText(self.background)
        self._refresh_derived()
        self.statusBar().showMessage("Reset to default ArcAurora green.", 4000)

    # ── actions ────────────────────────────────────────────────────────
    def _validate(self):
        # Read live from the edit fields so half-typed / invalid text is caught
        # rather than silently committing the previously valid cached value.
        for label, edit in (("accent", self.accent_edit),
                            ("background", self.bg_edit)):
            v = edit.text().strip()
            if not HEX_RE.match(v):
                self._set_invalid(edit, True)
                QMessageBox.critical(
                    self, "Invalid color",
                    f"{label} must be a 6-digit hex like #58d147 (got {v!r}).")
                edit.setFocus()
                return False
        return True

    def _run_generate(self):
        self._save_conf()
        r = subprocess.run(
            [sys.executable, str(REPO / "generate.py")],
            capture_output=True, text=True, cwd=str(REPO))
        if r.returncode != 0:
            QMessageBox.critical(self, "generate.py failed",
                                 (r.stderr or r.stdout).strip())
            return False
        return True

    def _generate_only(self):
        if not self._validate():
            return
        self.statusBar().showMessage("Generating…")
        QApplication.processEvents()
        if self._run_generate():
            self.statusBar().showMessage(
                "Generated. Run ./install.sh to apply.", 6000)

    def _generate_install(self):
        if not self._validate():
            return
        ok = QMessageBox.question(
            self, "Confirm install",
            "This will run ./install.sh and copy the theme to "
            "~/.local/share (or system dirs if run as root).\n\nContinue?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)
        if ok != QMessageBox.Yes:
            return
        self.statusBar().showMessage("Generating + installing…")
        QApplication.processEvents()
        if not self._run_generate():
            self.statusBar().showMessage("Failed.")
            return
        r = subprocess.run(
            ["bash", str(REPO / "install.sh")],
            capture_output=True, text=True, cwd=str(REPO))
        if r.returncode != 0:
            QMessageBox.critical(self, "install.sh failed",
                                 (r.stderr or r.stdout).strip())
            self.statusBar().showMessage("Install failed.")
            return
        self.statusBar().showMessage("Installed.", 8000)
        QMessageBox.information(
            self, "Done",
            "Theme generated and installed.\n\n"
            "Re-apply the theme in System Settings (or log out / log in) "
            "to see the new colors.")


def main():
    app = QApplication(sys.argv)
    w = App()
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
