"""
GPIO and button handling - Fixed Long Press + Single Click Conflict
"""
import time
import threading
from utils.helpers import HARDWARE_AVAILABLE, PLAY_PAUSE_PIN, PREV_PIN, NEXT_PIN

# Fix Pylint error by defining wiringpi as None initially
wiringpi = None

if HARDWARE_AVAILABLE:
    try:
        import wiringpi
    except ImportError:
        wiringpi = None
        print("⚠️ WiringPi library not available")

class GPIOHandler:
    def __init__(self, callback_handler):
        self.callback_handler = callback_handler
        self.stop_monitoring_flag = False
        self.button_thread = None
        self.last_play_pause_press_time = 0
        self.double_click_threshold = 0.4
        self.pending_single_click = False
        self.single_click_timer = None
        self.long_press_triggered = False  # New flag to track long press
        
        if HARDWARE_AVAILABLE and wiringpi is not None:
            self.setup_gpio()
    
    def setup_gpio(self):
        """Setup GPIO pins for buttons"""
        if wiringpi is None:
            print("❌ WiringPi not available")
            return False
        
        try:
            if wiringpi.wiringPiSetup() == -1:
                print("❌ WiringPi setup failed")
                return False
            
            for pin in [PLAY_PAUSE_PIN, PREV_PIN, NEXT_PIN]:
                wiringpi.pinMode(pin, wiringpi.INPUT)
                wiringpi.pullUpDnControl(pin, wiringpi.PUD_UP)
            
            print("✅ GPIO pins configured successfully")
            return True
        except Exception as e:
            print(f"❌ GPIO setup error: {e}")
            return False
    
    def start_monitoring(self):
        """Start button monitoring thread"""
        if not HARDWARE_AVAILABLE or wiringpi is None:
            print("⚠️ Hardware not available - button monitoring disabled")
            return
        
        self.stop_monitoring_flag = False
        self.button_thread = threading.Thread(target=self._monitor_buttons, daemon=True)
        self.button_thread.start()
        print("🎮 Button monitoring started")
    
    def stop_monitoring(self):
        """Stop button monitoring"""
        self.stop_monitoring_flag = True
        print("🎮 Button monitoring stopped")
    
    def _monitor_buttons(self):
        """Monitor physical button presses"""
        if wiringpi is None:
            return
        
        prev_states = [1, 1, 1]
        play_button_press_start = 0
        
        while not self.stop_monitoring_flag:
            try:
                current_states = [
                    wiringpi.digitalRead(PLAY_PAUSE_PIN),
                    wiringpi.digitalRead(PREV_PIN),
                    wiringpi.digitalRead(NEXT_PIN)
                ]
                
                # Play/Pause button with hold detection
                if current_states[0] == 0 and prev_states[0] == 1:
                    # Button pressed down
                    play_button_press_start = time.time()
                    self.long_press_triggered = False  # Reset flag on new press
                elif current_states[0] == 0 and time.time() - play_button_press_start > 2.0:
                    # Long press detected while button is still held
                    if not self.long_press_triggered:  # Only trigger once
                        self.long_press_triggered = True
                        self._cancel_pending_single_click()
                        self.callback_handler.on_menu_enter()
                        print("🎯 Long press detected - menu entered")
                elif prev_states[0] == 0 and current_states[0] == 1:
                    # Button released
                    hold_duration = time.time() - play_button_press_start
                    
                    # Only process as click if it was NOT a long press
                    if hold_duration < 2.0 and not self.long_press_triggered:
                        self._handle_play_pause_click()
                    elif self.long_press_triggered:
                        print("🎯 Long press release - ignoring click")
                
                # Previous button
                if prev_states[1] == 1 and current_states[1] == 0:
                    self.callback_handler.on_previous_button()
                    time.sleep(0.3)
                
                # Next button
                if prev_states[2] == 1 and current_states[2] == 0:
                    self.callback_handler.on_next_button()
                    time.sleep(0.3)
                
                prev_states = current_states
                time.sleep(0.05)
                
            except Exception as e:
                print(f"❌ Button monitoring error: {e}")
                time.sleep(1)
    
    def _handle_play_pause_click(self):
        """Handle play/pause button click with proper double-click detection"""
        current_time = time.time()
        
        # Check if this is a double-click
        if current_time - self.last_play_pause_press_time < self.double_click_threshold:
            # This is a double-click - cancel pending single click and execute double-click
            self._cancel_pending_single_click()
            self.callback_handler.on_play_pause_double_click()
            self.last_play_pause_press_time = 0  # Reset to prevent triple-click issues
            print("🎯 Double-click detected")
        else:
            # This might be a single click - but wait to see if another click comes
            self.last_play_pause_press_time = current_time
            self.pending_single_click = True
            
            # Start timer to execute single click if no second click comes
            if self.single_click_timer:
                self.single_click_timer.cancel()
            
            self.single_click_timer = threading.Timer(
                self.double_click_threshold, 
                self._execute_pending_single_click
            )
            self.single_click_timer.start()
    
    def _execute_pending_single_click(self):
        """Execute the pending single click after timeout"""
        if self.pending_single_click:
            self.pending_single_click = False
            self.callback_handler.on_play_pause_single_click()
            print("🎯 Single-click executed")
    
    def _cancel_pending_single_click(self):
        """Cancel any pending single click"""
        if self.single_click_timer:
            self.single_click_timer.cancel()
            self.single_click_timer = None
        self.pending_single_click = False
