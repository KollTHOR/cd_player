"""
Utility functions and constants
"""
import os
import time

# Hardware availability check
try:
    import wiringpi
    from RPLCD.i2c import CharLCD
    HARDWARE_AVAILABLE = True
except ImportError:
    HARDWARE_AVAILABLE = False

# Constants
TEMP_DIR = "/tmp"
STATE_FILE = "/tmp/cd_player_state.json"
TRACK_FILE = "/tmp/current_track.txt"
FIFO_PATH = '/tmp/mplayer_control.fifo'
LOG_FILE = '/home/orangepi/mplayer.log'

# GPIO Pins
PLAY_PAUSE_PIN = 2
PREV_PIN = 5
NEXT_PIN = 8

def setup_temp_files():
    """Setup temporary files with proper permissions"""
    try:
        os.makedirs(TEMP_DIR, exist_ok=True)
        with open(TRACK_FILE, "w") as f:
            f.write("1")
        os.chmod(TRACK_FILE, 0o666)
        return True
    except Exception as e:
        print(f"❌ Error setting up temp files: {e}")
        return False

def format_time(seconds):
    """Format seconds as M:SS"""
    if seconds <= 0:
        return "0:00"
    minutes = seconds // 60
    secs = seconds % 60
    return f"{minutes}:{secs:02d}"

def safe_write_file(filepath, content):
    """Safely write content to file"""
    try:
        with open(filepath, 'w') as f:
            f.write(str(content))
        os.chmod(filepath, 0o666)
        return True
    except Exception:
        return False
