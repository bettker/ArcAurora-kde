## ArcAurora-dark KDE Theme

ArcAurora-dark kde is a light clean theme for KDE Plasma desktop.

In this repository you'll find:

- Aurorae Themes
- Kvantum Themes
- Plasma Color Schemes
- Plasma Desktop Themes
- Plasma Look-and-Feel Settings

- Added a desktop layout, just like the desktop layout in the figure, people who need can use

  Usage:
  
  Replacement:/.config/plasma-org.kde.plasma.desktop-appletsrc

- Prompt
  
  Before replacement, save the current desktop , to avoid losses
  
 
 - Fix lock screen black screen problem
 -  Add wallpapers and configuration files
    After selecting your favorite color wallpaper, remove the suffix color abbreviation and install it
  

## Installation

```sh
./install.sh
```

## Customizing colors

The theme's accent (default green `#58d147`) and background (default teal-dark
`#052424`) are centralized in [colors.conf](colors.conf). All other tones used
across Aurorae, Kvantum, Plasma widgets and the color scheme are derived from
those two by preserving each tone's HSL relationship to the originals.

```sh
# 1. edit the two values in colors.conf
# 2. regenerate every theme file from templates/
python3 generate.py
# 3. install
./install.sh
```

Or use the graphical color picker (requires
[PySide6](https://pypi.org/project/PySide6/)):

```sh
pip install --user PySide6
python3 theme_gui.py
```

The GUI shows the two base colors plus every auto-derived tone with a live
preview, lets you override any individual tone, and can run the install
step for you.

If a derived tone doesn't look right, pin it to an explicit hex via the
`[overrides]` section in `colors.conf`. To re-extract templates after editing
files in place, run `python3 generate.py --bootstrap`. CI/pre-commit can use
`python3 generate.py --check` to detect drift between `colors.conf`,
`templates/`, and the generated files.

## License

GNU GPL v3

## view
![view](View-1.png?raw=true)
![view](View-2.png?raw=true)
![view](View-3.png?raw=true)
![view](View-4.png?raw=true)


