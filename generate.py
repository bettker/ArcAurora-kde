#!/usr/bin/env python3
"""ArcAurora-kde theme color generator.

Reads colors.conf at the repo root and renders templates/ into the live
theme directories. Edit colors.conf, run this script, then `./install.sh`.

Usage:
    python3 generate.py             # render templates -> theme files
    python3 generate.py --check     # exit non-zero if outputs are stale
    python3 generate.py --bootstrap # rebuild templates/ from current files
"""

import argparse
import colorsys
import configparser
import gzip
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent

ORIG_ACCENT = "#58d147"
ORIG_BACKGROUND = "#052424"

TARGET_FILES = [
    "color-schemes/ArcAuroraDark.colors",
    "Kvantum/ArcAurora-dark/ArcAurora-dark.kvconfig",
    "Kvantum/ArcAurora-dark/ArcAurora-dark.svg",
    "aurorae/ArcAurora-dark/close.svg",
    "aurorae/ArcAurora-dark/decoration.svg",
    "aurorae/ArcAurora-dark/maximize.svg",
    "aurorae/ArcAurora-dark/minimize.svg",
    "aurorae/ArcAurora-dark/restore.svg",
    "plasma/desktoptheme/ArcAurora-dark/widgets/actionbutton.svg",
    "plasma/desktoptheme/ArcAurora-dark/widgets/action-overlays.svg",
    "plasma/desktoptheme/ArcAurora-dark/widgets/background.svg",
    "plasma/desktoptheme/ArcAurora-dark/widgets/bar_meter_horizontal.svg",
    "plasma/desktoptheme/ArcAurora-dark/widgets/bar_meter_vertical.svg",
    "plasma/desktoptheme/ArcAurora-dark/widgets/busywidget.svg",
    "plasma/desktoptheme/ArcAurora-dark/widgets/button.svg",
    "plasma/desktoptheme/ArcAurora-dark/widgets/calendar.svg",
    "plasma/desktoptheme/ArcAurora-dark/widgets/checkmarks.svg",
    "plasma/desktoptheme/ArcAurora-dark/widgets/clock.svg",
    "plasma/desktoptheme/ArcAurora-dark/widgets/containment-controls.svg",
    "plasma/desktoptheme/ArcAurora-dark/widgets/glowbar.svg",
    "plasma/desktoptheme/ArcAurora-dark/widgets/lineedit.svg",
    "plasma/desktoptheme/ArcAurora-dark/widgets/listitem.svg",
    "plasma/desktoptheme/ArcAurora-dark/widgets/notes.svg",
    "plasma/desktoptheme/ArcAurora-dark/widgets/pager.svg",
    "plasma/desktoptheme/ArcAurora-dark/widgets/slider.svg",
    "plasma/desktoptheme/ArcAurora-dark/widgets/tabbar.svg",
    "plasma/desktoptheme/ArcAurora-dark/widgets/tasks.svg",
    "plasma/desktoptheme/ArcAurora-dark/widgets/toolbar.svg",
    "plasma/desktoptheme/ArcAurora-dark/widgets/tooltip.svg",
    "plasma/desktoptheme/ArcAurora-dark/dialogs/background.svgz",
    "plasma/desktoptheme/ArcAurora-dark/widgets/panel-background.svgz",
    "plasma/desktoptheme/ArcAurora-dark/widgets/scrollbar.svgz",
]

PALETTE = {
    "#58d147": "accent_primary",
    "#4e9a06": "accent_secondary",
    "#3aa82a": "accent_dark_a",
    "#319324": "accent_dark_b",
    "#2a7a1f": "accent_dark_c",
    "#2a7620": "accent_dark_d",
    "#1c5115": "accent_dark_e",
    "#023812": "accent_dark_f",
    "#052424": "bg_base",
    "#074640": "bg_alt",
    "#073634": "bg_alt2",
    "#052726": "bg_dark",
    "#041b1a": "bg_darker",
    "#063f3a": "bg_mid",
    "#031c1b": "bg_deepest",
}


def hex_to_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def rgb_to_hex(r, g, b):
    return "#{:02x}{:02x}{:02x}".format(
        *(max(0, min(255, int(round(x)))) for x in (r, g, b))
    )


def hex_to_hsl(h):
    r, g, b = (c / 255.0 for c in hex_to_rgb(h))
    h_, l_, s_ = colorsys.rgb_to_hls(r, g, b)
    return (h_, s_, l_)


def hsl_to_hex(h, s, l):
    h = h % 1.0
    s = max(0.0, min(1.0, s))
    l = max(0.0, min(1.0, l))
    r, g, b = colorsys.hls_to_rgb(h, l, s)
    return rgb_to_hex(r * 255, g * 255, b * 255)


def derive(orig_satellite, orig_base, new_base):
    """Apply HSL offset (satellite - orig_base) to new_base; return hex."""
    if new_base.lower() == orig_base.lower():
        return orig_satellite.lower()
    sh, ss, sl = hex_to_hsl(orig_satellite)
    bh, bs, bl = hex_to_hsl(orig_base)
    nh, ns, nl = hex_to_hsl(new_base)
    new_h = (nh + (sh - bh)) % 1.0
    new_s = max(0.0, min(1.0, ns + (ss - bs)))
    new_l = max(0.0, min(1.0, nl + (sl - bl)))
    return hsl_to_hex(new_h, new_s, new_l)


def compute_tokens(accent, background):
    tokens = {}
    for orig_hex, name in PALETTE.items():
        if name == "accent_primary":
            tokens[name] = accent.lower()
        elif name == "bg_base":
            tokens[name] = background.lower()
        elif name.startswith("accent_"):
            tokens[name] = derive(orig_hex, ORIG_ACCENT, accent)
        elif name.startswith("bg_"):
            tokens[name] = derive(orig_hex, ORIG_BACKGROUND, background)
    # Add RGB-decimal form for every palette token (used by .colors files).
    for name in list(tokens):
        r, g, b = hex_to_rgb(tokens[name])
        tokens[f"{name}_rgb"] = f"{r},{g},{b}"
    tokens["accent_primary_a50"] = accent.lower() + "80"
    return tokens


# Match palette hex codes but NOT 8-digit hex+alpha (e.g. #58d14780).
def make_palette_pattern():
    keys = sorted(PALETTE.keys(), key=len, reverse=True)
    pat = "|".join(re.escape(k) for k in keys)
    return re.compile(rf"({pat})(?![0-9a-fA-F])", re.IGNORECASE)


def bootstrap():
    palette_re = make_palette_pattern()
    a50_re = re.compile(r"#58d14780", re.IGNORECASE)

    # RGB-decimal substitutions used in .colors files: r,g,b -> {{token_rgb}}.
    # Build pattern from longest match first to avoid partial matches.
    rgb_map = {}
    for hexv, token in PALETTE.items():
        r, g, b = hex_to_rgb(hexv)
        rgb_map[f"{r},{g},{b}"] = f"{token}_rgb"
    rgb_keys = sorted(rgb_map.keys(), key=len, reverse=True)
    rgb_re = re.compile(
        r"(?<![0-9])(" + "|".join(re.escape(k) for k in rgb_keys) + r")(?![0-9])"
    )

    for rel in TARGET_FILES:
        src = REPO / rel
        if not src.exists():
            print(f"  WARN: missing {rel}", file=sys.stderr)
            continue
        is_svgz = rel.endswith(".svgz")
        if is_svgz:
            content = gzip.decompress(src.read_bytes()).decode("utf-8")
        else:
            content = src.read_text(encoding="utf-8")

        # Specials first (won't overlap palette since palette regex has lookahead).
        content = a50_re.sub("{{accent_primary_a50}}", content)
        if rel.endswith(".colors"):
            content = rgb_re.sub(lambda m: "{{" + rgb_map[m.group(0)] + "}}", content)

        content = palette_re.sub(
            lambda m: "{{" + PALETTE[m.group(0).lower()] + "}}", content
        )

        tmpl = REPO / "templates" / (rel + ".tmpl")
        tmpl.parent.mkdir(parents=True, exist_ok=True)
        tmpl.write_text(content, encoding="utf-8")
        print(f"  template: {tmpl.relative_to(REPO)}")


_TOKEN_RE = re.compile(r"\{\{\s*(\w+)\s*\}\}")


def render_text(text, tokens):
    def fn(m):
        name = m.group(1)
        if name not in tokens:
            raise KeyError(f"undefined token: {{{{{name}}}}}")
        return tokens[name]
    return _TOKEN_RE.sub(fn, text)


def load_colors_conf():
    cfg = configparser.ConfigParser()
    path = REPO / "colors.conf"
    if not path.exists():
        sys.exit(f"missing {path.relative_to(REPO)}")
    cfg.read(path, encoding="utf-8")
    accent = cfg.get("base", "accent").strip()
    background = cfg.get("base", "background").strip()
    if not re.fullmatch(r"#[0-9a-fA-F]{6}", accent):
        sys.exit(f"colors.conf: invalid accent hex: {accent!r}")
    if not re.fullmatch(r"#[0-9a-fA-F]{6}", background):
        sys.exit(f"colors.conf: invalid background hex: {background!r}")
    tokens = compute_tokens(accent, background)
    if cfg.has_section("overrides"):
        for k, v in cfg.items("overrides"):
            v = v.strip()
            if k in tokens:
                tokens[k] = v
            else:
                print(f"  WARN: unknown override {k}", file=sys.stderr)
    return tokens


def render(check=False):
    tokens = load_colors_conf()
    drift = []

    for rel in TARGET_FILES:
        tmpl = REPO / "templates" / (rel + ".tmpl")
        if not tmpl.exists():
            sys.exit(f"missing template: {tmpl.relative_to(REPO)}")
        rendered = render_text(tmpl.read_text(encoding="utf-8"), tokens)
        out = REPO / rel
        is_svgz = rel.endswith(".svgz")

        if is_svgz:
            existing_dec = ""
            if out.exists():
                try:
                    existing_dec = gzip.decompress(out.read_bytes()).decode("utf-8")
                except OSError:
                    existing_dec = ""
            if existing_dec != rendered:
                drift.append(rel)
                if not check:
                    out.write_bytes(
                        gzip.compress(rendered.encode("utf-8"), mtime=0, compresslevel=9)
                    )
                    print(f"  wrote: {rel}")
            elif not check:
                print(f"  unchanged: {rel}")
        else:
            existing = out.read_text(encoding="utf-8") if out.exists() else ""
            if existing != rendered:
                drift.append(rel)
                if not check:
                    out.parent.mkdir(parents=True, exist_ok=True)
                    out.write_text(rendered, encoding="utf-8")
                    print(f"  wrote: {rel}")
            elif not check:
                print(f"  unchanged: {rel}")

    if check:
        if drift:
            print("DRIFT detected:", file=sys.stderr)
            for d in drift:
                print(f"  - {d}", file=sys.stderr)
            sys.exit(1)
        print("OK: all generated files match templates+colors.conf")


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--bootstrap", action="store_true",
                   help="(re)generate templates/ from current theme files")
    p.add_argument("--check", action="store_true",
                   help="verify generated files match templates+colors.conf")
    args = p.parse_args()
    if args.bootstrap:
        bootstrap()
    else:
        render(check=args.check)


if __name__ == "__main__":
    main()
