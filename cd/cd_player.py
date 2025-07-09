#!/usr/bin/env python3
"""
Core CD Player functionality - Fixed MPlayer Silent Exit Issues
"""
import os
import subprocess
import time
import threading
import signal
import sys
from utils.helpers import *
from hardware.gpio_handler import GPIOHandler
from hardware.lcd_display import LCDDisplay
from hardware.audio_manager import AudioManager
from menu.menu_system import MenuSystem
from cd.cd_detector import CDDetector

class CDPlayer:
    def __init__(self):
        # Core state
        self.mplayer_process = None
        self.current_track = 1
        self.total_tracks = 1
        self.is_playing = False
        self.track_lengths = {}
        
        # Timing variables
        self.playback_start_time = None
        self.current_track_start = None
        self.pause_start_time = None
        self.total_pause_duration = 0
        self.mplayer_ready = False
        self.startup_check_count = 0
        
        # Components initialization
        self.lcd = LCDDisplay()
        self.audio_manager = AudioManager()
        self.menu_system = MenuSystem(self.lcd, self.audio_manager)
        self.gpio_handler = GPIOHandler(self)
        self.cd_detector = CDDetector(self)

        # Set up audio change callback using the proper method
        self.audio_manager.set_audio_change_callback(self.on_audio_output_changed)
        
        # Setup
        setup_temp_files()
        self.setup_fifo()
        
        print("🎮 CD Player initialized")
    
    def on_audio_output_changed(self):
        """Handle audio output device change by reloading MPlayer"""
        if not self.is_mplayer_alive():
            return

        # Store current state
        current_track = self.current_track
        was_playing = self.is_playing
        current_position = self.get_elapsed_time()

        print(f"🔄 Audio output changed - reloading MPlayer for track {current_track}")

        # Stop current playback
        self.stop_playback()

        # Small delay to ensure clean shutdown
        time.sleep(0.5)

        # Reload with new audio output
        if was_playing:
            success = self.load_track(current_track)
            if success and current_position > 0:
                # Seek to approximate previous position
                time.sleep(2)
                self.send_command(f"seek {current_position} 2")
        else:
            success = self.load_track_paused(current_track)
            if success and current_position > 0:
                time.sleep(2)
                self.send_command(f"seek {current_position} 2")

        if success:
            print(f"✅ Successfully reloaded track {current_track} with new audio output")
        else:
            print(f"❌ Failed to reload track {current_track}")
            # Fallback: reload from beginning
            self.load_track_paused(current_track)
    
    def setup_fifo(self):
        """Setup MPlayer control FIFO with safe testing"""
        try:
            if os.path.exists(FIFO_PATH):
                os.remove(FIFO_PATH)

            # Create FIFO with world-writable permissions from start
            os.mkfifo(FIFO_PATH)
            os.chmod(FIFO_PATH, 0o666)

            print("✅ FIFO setup complete with world-writable permissions")

            # Safe FIFO testing without blocking
            self._test_fifo_access()

        except Exception as e:
            print(f"❌ FIFO setup error: {e}")

    def _test_fifo_access(self):
        """Test FIFO accessibility without blocking operations"""
        try:
            # Test 1: Check if FIFO exists and has correct permissions
            if os.path.exists(FIFO_PATH):
                fifo_stat = os.stat(FIFO_PATH)
                print(f"✅ FIFO exists with permissions: {oct(fifo_stat.st_mode)}")
            else:
                print("❌ FIFO file not created")
                return

            # Test 2: Check write permissions without actually writing
            if os.access(FIFO_PATH, os.W_OK):
                print("✅ FIFO is writable")
            else:
                print("❌ FIFO is not writable")

            # Test 3: Verify user can access FIFO
            try:
                result = subprocess.run([
                    'sudo', '-u', 'orangepi', 'test', '-w', FIFO_PATH
                ], capture_output=True, timeout=2)
                if result.returncode == 0:
                    print("✅ User can access FIFO")
                else:
                    print("❌ User cannot access FIFO")
            except:
                print("⚠️ User access test failed")

        except Exception as e:
            print(f"⚠️ FIFO access test failed: {e}")

    # Button callback methods
    def on_menu_enter(self):
        """Handle menu entry from long press"""
        if not self.menu_system.in_menu:
            self.menu_system.enter_menu()
    
    def on_play_pause_single_click(self):
        """Handle single click on play/pause button"""
        if self.menu_system.in_submenu:
            self.menu_system.submenu_select()
        elif self.menu_system.in_menu:
            self.menu_system.menu_select()
        else:
            self.play_pause()
    
    def on_play_pause_double_click(self):
        """Handle double click on play/pause button"""
        if self.menu_system.in_submenu:
            self.menu_system.exit_submenu()
        elif self.menu_system.in_menu:
            self.menu_system.exit_menu()
    
    def on_previous_button(self):
        """Handle previous button press"""
        if self.menu_system.in_submenu:
            self.menu_system.submenu_previous()
        elif self.menu_system.in_menu:
            self.menu_system.menu_previous()
        else:
            self.previous_track()
    
    def on_next_button(self):
        """Handle next button press"""
        if self.menu_system.in_submenu:
            self.menu_system.submenu_next()
        elif self.menu_system.in_menu:
            self.menu_system.menu_next()
        else:
            self.next_track()

    # Core playback methods
    def load_cd_paused(self):
        """Load CD with proper state initialization"""
        self.stop_playback()
        print("⏸️ Loading CD in paused state")

        if self.lcd:
            self.lcd.show_message("CD Detected", "Reading...")
            time.sleep(0.5)

        # Detect tracks
        self.total_tracks, self.track_lengths = self.cd_detector.detect_cd_tracks()

        # Reset state completely
        self.current_track = 1
        self.is_playing = False
        self.reset_timing()

        # Setup FIFO and ensure clean state
        self.setup_fifo()

        # Force track 1 in state file
        safe_write_file(TRACK_FILE, "1")

        # Load track 1 in paused state
        success = self.load_track_paused(1)

        if success:
            if self.lcd:
                self.lcd.show_message("CD Ready", "Press Play")
        else:
            if self.lcd:
                self.lcd.show_message("CD Error", "Try Again")
    
    def _get_audio_output(self):
        """Determine correct audio output based on current device"""
        current_device = self.audio_manager.current_device
        
        if current_device.startswith('pulse:') or current_device == 'pulse':
            return "pulse"
        elif current_device.startswith('hw='):
            return f"alsa:device={current_device}"
        else:
            # Fallback to pulse for compatibility
            return "pulse"
    
    def load_track_paused(self, track_number):
        """Load track with comprehensive error handling and monitoring"""
        if not (1 <= track_number <= self.total_tracks):
            return False

        self.stop_playback()

        try:
            # Determine correct audio output
            audio_output = self._get_audio_output()
            print(f"🔊 Using audio output: {audio_output}")

            log_file = open(LOG_FILE, 'a')

            # Set PulseAudio environment
            env = os.environ.copy()
            env["XDG_RUNTIME_DIR"] = "/run/user/1000"
            env["PULSE_SERVER"] = "unix:/run/user/1000/pulse/native"
            if "bluez_sink" in self.audio_manager.current_device:
                env["PULSE_SINK"] = self.audio_manager.current_device
                # Prime Bluetooth sink with short sound
                subprocess.run([
                    "paplay", "/usr/share/sounds/alsa/Front_Center.wav",
                    "--device", self.audio_manager.current_device
                ], env=env)

            # Start MPlayer
            self.mplayer_process = subprocess.Popen([
                'mplayer', '-cdrom-device', '/dev/sr0',
                '-cache', '8192',
                '-ao', audio_output,
                '-vo', 'null', '-slave', '-quiet',
                '-input', f'file={FIFO_PATH}',
                f'cdda://{track_number}'
            ], stdin=subprocess.DEVNULL, stdout=log_file, stderr=log_file, env=env)

            self.current_track = track_number
            self.is_playing = False
            self.reset_timing()
            safe_write_file(TRACK_FILE, track_number)

            print(f"🎵 MPlayer started with PID: {self.mplayer_process.pid}")

            for i in range(10):
                time.sleep(1)
                if not self.is_mplayer_alive():
                    exit_code = self.mplayer_process.returncode
                    print(f"❌ MPlayer terminated after {i+1} seconds with exit code: {exit_code}")
                    self._diagnose_mplayer_failure()
                    return False

                if i == 2:
                    print("⏸️ Sending initial pause command to MPlayer")
                    if self.send_command("pause"):
                        self.pause_start_time = time.time()
                        print(f"✅ Track {track_number} paused successfully")
                    else:
                        print("⚠️ Pause command failed")

                if i < 5:
                    print(f"✅ MPlayer alive after {i+1} seconds")

            if self.is_mplayer_alive():
                print(f"✅ Track {track_number} loaded and stable")
                self.lcd.start_display_thread(self.update_display)
                return True
            else:
                print("❌ MPlayer died during final verification")
                return False

        except Exception as e:
            print(f"❌ Error loading track {track_number}: {e}")
            return False
        
    def _test_mplayer_command_readiness(self):
        """Test if MPlayer is ready to accept commands"""
        try:
            # Send a harmless query command to test readiness
            result = subprocess.run([
                'timeout', '2', 'bash', '-c', f'echo "get_property pause" > {FIFO_PATH}'
            ], capture_output=True, text=True)

            if result.returncode == 0:
                time.sleep(0.5)  # Give MPlayer time to process
                return True
            return False
        except:
            return False

    def load_track(self, track_number):
        """Load and play track with enhanced monitoring"""
        if not (1 <= track_number <= self.total_tracks):
            return False
    
        self.stop_playback()
    
        try:
            audio_output = self._get_audio_output()
            print(f"🔊 Using audio output: {audio_output}")
    
            log_file = open(LOG_FILE, 'a')
    
            # Set PulseAudio environment
            env = os.environ.copy()
            env["XDG_RUNTIME_DIR"] = "/run/user/1000"
            env["PULSE_SERVER"] = "unix:/run/user/1000/pulse/native"
            if "bluez_sink" in self.audio_manager.current_device:
                env["PULSE_SINK"] = self.audio_manager.current_device
                subprocess.run([
                    "paplay", "/usr/share/sounds/alsa/Front_Center.wav",
                    "--device", self.audio_manager.current_device
                ], env=env)
    
            self.mplayer_process = subprocess.Popen([
                'mplayer', '-cdrom-device', '/dev/sr0',
                '-cache', '8192',
                '-ao', audio_output,
                '-vo', 'null', '-slave', '-quiet',
                '-input', f'file={FIFO_PATH}',
                f'cdda://{track_number}'
            ], stdin=subprocess.DEVNULL, stdout=log_file, stderr=log_file, env=env)
    
            self.current_track = track_number
            self.is_playing = True
            self.reset_timing()
            safe_write_file(TRACK_FILE, track_number)
    
            time.sleep(2)
            if not self.is_mplayer_alive():
                print(f"❌ MPlayer died immediately for track {track_number}")
                return False
    
            self.lcd.start_display_thread(self.update_display)
            print(f"✅ Track {track_number} playing with {audio_output}")
            return True
    
        except Exception as e:
            print(f"❌ Error loading track {track_number}: {e}")
            return False
    
    def _diagnose_mplayer_failure(self):
        """Diagnose why MPlayer failed"""
        try:
            print("🔍 Diagnosing MPlayer failure...")
            
            # Check recent MPlayer logs
            if os.path.exists(LOG_FILE):
                with open(LOG_FILE, 'r') as f:
                    recent_logs = f.readlines()[-10:]
                
                print("📋 Recent MPlayer logs:")
                for line in recent_logs:
                    if line.strip():
                        print(f"  {line.strip()}")
            else:
                print("❌ MPlayer log file not found")
                
            # Check FIFO status
            if os.path.exists(FIFO_PATH):
                fifo_stat = os.stat(FIFO_PATH)
                print(f"📋 FIFO status: mode={oct(fifo_stat.st_mode)}, owner={fifo_stat.st_uid}")
            else:
                print("❌ FIFO file missing")
                
            # Check CD drive accessibility
            try:
                result = subprocess.run(['ls', '-la', '/dev/sr0'], capture_output=True, text=True)
                print(f"📋 CD drive status: {result.stdout.strip()}")
            except:
                print("❌ Cannot access CD drive")
                
            # Check audio device status
            current_device = self.audio_manager.current_device
            print(f"📋 Current audio device: {current_device}")
                
        except Exception as e:
            print(f"❌ Diagnosis failed: {e}")
    
    def stop_playback(self):
        """Enhanced stop playback with better process cleanup"""
        self.lcd.stop_display_thread()
        
        if self.mplayer_process:
            try:
                # Try graceful termination first
                self.mplayer_process.terminate()
                try:
                    self.mplayer_process.wait(timeout=3)
                    print("✅ MPlayer terminated gracefully")
                except subprocess.TimeoutExpired:
                    # Force kill if graceful termination fails
                    self.mplayer_process.kill()
                    self.mplayer_process.wait(timeout=2)
                    print("⚠️ MPlayer force killed")
            except Exception as e:
                print(f"❌ Error stopping MPlayer: {e}")
        
        self.mplayer_process = None
        self.is_playing = False
        self.reset_timing()
    
    def reset_timing(self):
        """Reset all timing variables"""
        self.playback_start_time = None
        self.current_track_start = None
        self.pause_start_time = None
        self.total_pause_duration = 0
        self.mplayer_ready = False
        self.startup_check_count = 0
    
    def play_pause(self):
        """Enhanced play/pause with proper state synchronization"""
        if not self.is_mplayer_alive():
            print("❌ Cannot play/pause - MPlayer not running")
            return

        if not self.mplayer_ready:
            print("⚠️ MPlayer not ready for commands")
            return

        # Send pause command
        if self.send_command("pause"):
            current_time = time.time()

            if self.is_playing:
                # Currently playing -> pause
                self.pause_start_time = current_time
                self.is_playing = False
                print("⏸️ Paused")

            else:
                # Currently paused -> play
                if self.pause_start_time:
                    pause_duration = current_time - self.pause_start_time
                    self.total_pause_duration += pause_duration
                    self.pause_start_time = None

                self.is_playing = True
                print("▶️ Playing")

            # Force display update to reflect new state
            if self.lcd:
                self.lcd.clear_cache()

            # Verify state change took effect
            time.sleep(0.3)
            print(f"🔍 State verified: {'Playing' if self.is_playing else 'Paused'}")

        else:
            print("❌ Play/pause command failed")
    
    def previous_track(self):
        """Go to previous track"""
        if self.current_track > 1:
            new_track = self.current_track - 1
            if self.load_track(new_track):
                print(f"⏮️ Previous track: {new_track}")
    
    def next_track(self):
        """Go to next track"""
        if self.current_track < self.total_tracks:
            new_track = self.current_track + 1
            if self.load_track(new_track):
                print(f"⏭️ Next track: {new_track}")
    
    def send_command(self, cmd):
        """Send command directly to MPlayer without readiness check"""
        if not self.is_mplayer_alive():
            print("❌ Cannot send command - MPlayer not running")
            return False

        # Method 1: Direct write (most reliable)
        try:
            with open(FIFO_PATH, 'w') as fifo:
                fifo.write(f'{cmd}\n')
                fifo.flush()
            print(f"✅ Command '{cmd}' sent directly to MPlayer")
            return True
        except Exception as e:
            print(f"⚠️ Direct command failed: {e}")

        # Method 2: User context (fallback)
        try:
            result = subprocess.run([
                'sudo', '-u', 'orangepi',
                'bash', '-c', f'echo "{cmd}" > {FIFO_PATH}'
            ], capture_output=True, text=True, timeout=3)

            if result.returncode == 0:
                print(f"✅ Command '{cmd}' sent via user context")
                return True
        except Exception as e:
            print(f"❌ All direct command methods failed: {e}")

        return False
    
    def is_mplayer_alive(self):
        """Enhanced MPlayer process checking"""
        if not self.mplayer_process:
            return False
        
        poll_result = self.mplayer_process.poll()
        if poll_result is not None:
            if poll_result != 0:
                print(f"⚠️ MPlayer process ended with code: {poll_result}")
            return False
        
        return True
    
    def check_mplayer_ready(self):
        """Simplified MPlayer readiness check"""
        if not self.is_mplayer_alive():
            return False

        # If mplayer_ready is already set, we're good
        if self.mplayer_ready:
            return True

        # Auto-set readiness after minimal checks
        if self.startup_check_count < 2:
            self.startup_check_count += 1
            return False

        # Set ready after 2 display updates
        self.mplayer_ready = True
        if self.current_track_start is None:
            self.current_track_start = time.time()

        return True
    
    def get_current_track(self):
        """Get current track number from state file"""
        try:
            with open(TRACK_FILE, 'r') as f:
                self.current_track = int(f.read().strip())
        except:
            self.current_track = 1
        return self.current_track
    
    def get_elapsed_time(self):
        """Get elapsed time with accurate pause handling"""
        if not self.mplayer_ready or self.current_track_start is None:
            return 0

        current_time = time.time()

        # Calculate total elapsed time since track start
        total_elapsed = current_time - self.current_track_start

        # Subtract all pause duration
        elapsed_minus_pauses = total_elapsed - self.total_pause_duration

        # If currently paused, subtract current pause time
        if not self.is_playing and self.pause_start_time:
            current_pause_duration = current_time - self.pause_start_time
            elapsed_minus_pauses -= current_pause_duration

        return max(0, int(elapsed_minus_pauses))

    
    def update_display(self):
        """Update LCD display callback with enhanced error handling"""
        if self.menu_system.in_menu:
            return
        
        try:
            track = self.get_current_track()
            
            # Check if MPlayer is still alive
            if not self.is_mplayer_alive():
                self.lcd.show_message(f"Loading {track:02d}/{self.total_tracks:02d}", "Please wait...")
                return
            
            if not self.check_mplayer_ready():
                self.lcd.show_message(f"Loading {track:02d}/{self.total_tracks:02d}", "Please wait...")
                return
            
            elapsed = self.get_elapsed_time()
            track_length = self.track_lengths.get(track, 180)
            
            if elapsed > track_length:
                elapsed = track_length
            
            self.lcd.update_track_display(
                track, self.total_tracks,
                elapsed, track_length,
                self.is_playing, self.is_mplayer_alive()
            )
            
        except Exception as e:
            print(f"❌ Display update error: {e}")
    
    def run(self):
        """Main run loop"""
        print("🚀 Starting CD Player")
        
        # Setup signal handlers
        def signal_handler(signum, frame):
            print("\n👋 Shutting down...")
            self.shutdown()
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        # Start components
        self.cd_detector.setup_monitoring()
        self.cd_detector.check_startup_cd()
        self.gpio_handler.start_monitoring()
        
        print("✅ CD Player ready!")
        print("🎮 Hold Play/Pause (2s) to enter menu")
        print("🔄 Double-click Play/Pause to go back in menu")
        print("⏮️⏭️ Use Prev/Next to navigate")
        
        try:
            self.cd_detector.run_loop()
        except KeyboardInterrupt:
            self.shutdown()
    
    def shutdown(self):
        """Clean shutdown"""
        print("🛑 Shutting down CD Player...")
        self.gpio_handler.stop_monitoring()
        self.stop_playback()
        self.lcd.stop_display_thread()
        
        if self.lcd.lcd:
            self.lcd.show_message("CD Player", "Stopped")
            time.sleep(1)
