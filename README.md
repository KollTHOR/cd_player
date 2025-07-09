<img src="https://r2cdn.perplexity.ai/pplx-full-logo-primary-dark%402x.png" class="logo" width="120"/>

# Orange Pi Zero 3 CD Player Project

A feature-rich, menu-driven audio CD player for the Orange Pi Zero 3 running Armbian. This project enables playback of audio CDs with hardware buttons, LCD display, Bluetooth and wired audio output selection, and robust menu navigation—all implemented in Python 3.

## Features

- **Physical Button Controls:** Play/Pause, Next, Previous, and Menu navigation using GPIO buttons.
- **LCD Display:** Real-time playback info, menu navigation, and system messages.
- **Audio Output Selection:** Switch between ALSA hardware, PipeWire/PulseAudio, and Bluetooth audio sinks.
- **Bluetooth Audio:** Scan, pair, connect, disconnect, and forget Bluetooth audio devices via menu.
- **Track List Navigation:** Browse CD tracks in a dedicated menu, select any track to play, and auto-advance through the CD.
- **Persistent Audio Device Selection:** Remembers your last-used audio output and restores it on startup.
- **Robust CD Detection:** Automatic detection and handling of CD insertion/removal via D-Bus.
- **MPlayer Backend:** Reliable playback with support for PipeWire/PulseAudio and ALSA.
- **Error Handling:** Clear user feedback for device errors, track limits, and playback issues.


## Hardware Requirements

- **Orange Pi Zero 3** (or compatible SBC)
- **I2C 16x2 LCD Display** (PCF8574 I2C backpack recommended)
- **Physical buttons** for Play/Pause, Next, Previous, and Menu (connected to GPIO)
- **CD-ROM drive** (connected via USB or SATA)
- **Audio output**: Wired (3.5mm jack, USB DAC, etc.) and/or Bluetooth speaker/headphones


## Software Requirements

- **Armbian** (Debian/Ubuntu-based, tested on recent versions)
- **Python 3.7+**
- **System Packages:**
    - `python3`, `python3-pip`, `python3-gi`, `python3-dbus`, `python3-setuptools`, `python3-wheel`
    - `python3-rplcd`, `wiringpi`
    - `mplayer`, `cdparanoia`
    - `pipewire`, `pipewire-audio`, `pipewire-pulse`, `pipewire-alsa`, `pipewire-jack`
    - `pulseaudio-utils`, `bluez`, `bluez-tools`
- **Python Libraries:**
    - `dbus-python`, `RPLCD`
- **Other:** D-Bus, systemd, working user environment for `orangepi` user


## Installation

### 1. System Preparation

```bash
sudo apt update
sudo apt install python3 python3-pip python3-gi python3-dbus python3-setuptools python3-wheel \
    python3-rplcd wiringpi mplayer cdparanoia \
    pipewire pipewire-audio pipewire-pulse pipewire-alsa pipewire-jack \
    pulseaudio-utils bluez bluez-tools
pip3 install dbus-python RPLCD
```


### 2. Hardware Setup

- Connect your LCD to I2C (default address: `0x27`, port 2).
- Connect buttons to GPIO pins defined in `utils/helpers.py` (`PLAY_PAUSE_PIN`, `PREV_PIN`, `NEXT_PIN`).
- Attach your CD-ROM drive.
- Ensure your user (`orangepi`) is in the `audio` and `bluetooth` groups.


### 3. Clone and Configure

```bash
git clone https://github.com/yourusername/orangepi-cdplayer.git
cd orangepi-cdplayer
```

- Edit `utils/helpers.py` if your hardware addresses or pins differ.


## Usage

### Running the Player

```bash
sudo python3 main.py
```

- The player will initialize the LCD and hardware.
- Insert an audio CD: the track selection menu will appear automatically.
- Use the buttons to navigate, select tracks, and control playback.


### Menu System

- **Hold Play/Pause (2s):** Enter menu
- **Prev/Next:** Navigate menu or track list
- **Play/Pause:** Select menu item or play/pause
- **Double-click Play/Pause:** Go back or exit menu


#### Main Menu Items

| Menu Item | Description |
| :-- | :-- |
| Tracks | Browse and select CD tracks |
| Audio Output | Select audio device (wired, Bluetooth, etc.) |
| Bluetooth | Scan, pair, connect, manage Bluetooth devices |
| Exit Menu | Leave the menu and return to playback display |

## Audio Output Persistence

- The last selected audio output (wired or Bluetooth) is saved and restored on startup.
- If the device is unavailable, the default output is used.


## Bluetooth Audio

- Scan for devices, pair, connect/disconnect, and forget devices from the menu.
- When a Bluetooth device is connected, it appears as an audio output option.


## Troubleshooting

- **No sound after changing output:** Ensure the correct sink is selected and the device is connected.
- **LCD shows stray characters:** All display lines are padded; if issues persist, check LCD wiring and library.
- **Menu or playback unresponsive:** Restart the script. Check for errors in the terminal.
- **Bluetooth device not listed:** Ensure the device is in pairing mode and close to the Orange Pi.


## Customization

- **GPIO Pins:** Edit `utils/helpers.py` to change button assignments.
- **LCD Address/Port:** Edit `hardware/lcd_display.py` if your I2C LCD uses a different address or port.
- **Menu Items:** Add or remove menu items in `menu/menu_system.py`.


## File Structure

| File/Folder | Purpose |
| :-- | :-- |
| `main.py` | Entry point for the application |
| `cd/` | CD detection and playback logic |
| `hardware/` | LCD, GPIO, and audio manager modules |
| `menu/` | Menu system and Bluetooth menu logic |
| `utils/` | Helpers, constants, utility functions |

## Credits

- Inspired by classic hardware CD players and modern Linux audio stacks.
- Uses open-source libraries: RPLCD, wiringpi, dbus-python, PipeWire, MPlayer, and more.


## License

This project is licensed under the MIT License. See `LICENSE` for details.

## Contributing

Contributions, bug reports, and feature requests are welcome! Please open an issue or submit a pull request.

## Acknowledgements

- Special thanks to the Linux audio and SBC community for inspiration and support.

<div style="text-align: center">⁂</div>

[^1]: main.py

[^2]: cd_detector.py

[^3]: cd_player.py

[^4]: audio_manager.py

[^5]: gpio_handler.py

[^6]: lcd_display.py

[^7]: bluetooth_menu.py

[^8]: menu_system.py

[^9]: helpers.py

