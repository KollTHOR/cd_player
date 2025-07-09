"""
LCD display management - Fixed Pylint Error
"""
import time
import threading
from utils.helpers import HARDWARE_AVAILABLE, format_time

# Fix Pylint error by defining CharLCD as None initially
CharLCD = None

if HARDWARE_AVAILABLE:
    try:
        from RPLCD.i2c import CharLCD
    except ImportError:
        CharLCD = None
        print("⚠️ RPLCD library not available")

class LCDDisplay:
    def __init__(self):
        self.lcd = None
        self.display_thread = None
        self.stop_display = False
        self.last_line1 = ""
        self.last_line2 = ""
        self.last_indicator = ""
        
        if HARDWARE_AVAILABLE and CharLCD is not None:
            self.init_lcd()
    
    def init_lcd(self):
        """Initialize the I2C LCD display"""
        if CharLCD is None:
            print("❌ CharLCD class not available")
            return False
        
        try:
            self.lcd = CharLCD(
                i2c_expander='PCF8574',
                address=0x27,
                port=2,
                cols=16,
                rows=2,
                dotsize=8,
                charmap='A02',
                auto_linebreaks=True
            )
            self.lcd.clear()
            self.show_message("CD Player Ready", "Insert CD...")
            print("✅ LCD initialized successfully")
            return True
        except Exception as e:
            print(f"❌ LCD initialization failed: {e}")
            self.lcd = None
            return False
    
    def show_message(self, line1, line2):
        """Show a message on LCD"""
        if not self.lcd:
            return
        
        try:
            self.lcd.clear()
            self.lcd.write_string(line1)
            self.lcd.cursor_pos = (1, 0)
            self.lcd.write_string(line2)
        except Exception as e:
            print(f"❌ LCD message error: {e}")
    
    def update_track_display(self, track, total_tracks, elapsed, track_length, is_playing, is_alive):
        if not self.lcd:
            return
    
        line1 = f"Track {track:02d}/{total_tracks:02d}".ljust(16)
        time_str = f"{format_time(elapsed)}/{format_time(track_length)}"
        indicator = ">" if is_alive and is_playing else "||" if is_alive else "X"
        line2 = time_str.ljust(15) + indicator
    
        # Only update if content changed
        if line1 != self.last_line1 or line2 != self.last_line2:
            # Only clear if major change (optional)
            # self.lcd.clear()
            self.lcd.cursor_pos = (0, 0)
            self.lcd.write_string(line1)
            self.lcd.cursor_pos = (1, 0)
            self.lcd.write_string(line2)
            self.last_line1 = line1
            self.last_line2 = line2
    
    def clear_cache(self):
        """Clear the LCD cache to force refresh"""
        self.last_line1 = ""
        self.last_line2 = ""
        self.last_indicator = ""
    
    def start_display_thread(self, update_callback):
        """Start the LCD display update thread"""
        if not self.lcd:
            return
        
        self.stop_display = False
        self.display_thread = threading.Thread(
            target=self._display_loop, 
            args=(update_callback,), 
            daemon=True
        )
        self.display_thread.start()
    
    def stop_display_thread(self):
        """Stop the LCD display thread"""
        self.stop_display = True
        if self.lcd:
            self.show_message("CD Player", "Stopped")
            self.clear_cache()
    
    def _display_loop(self, update_callback):
        """LCD display update loop"""
        while not self.stop_display:
            try:
                update_callback()
                time.sleep(1)
            except Exception as e:
                print(f"❌ Display thread error: {e}")
                time.sleep(2)
