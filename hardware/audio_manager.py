"""
Audio device management - ALSA + PulseAudio hybrid approach
"""
import subprocess
import re
import pwd
import os
from typing import Optional, Callable

class AudioManager:
    def __init__(self):
        self.available_devices = []
        self.current_device = "hw=0,0"
        self.user_name = "orangepi"
        
        # Initialize callback attribute with proper typing
        self.cd_player_callback: Optional[Callable[[], None]] = None
        
        self.scan_devices()
        self.restore_last_device()
    
    def set_audio_change_callback(self, callback: Callable[[], None]) -> None:
        """Register callback for audio device changes"""
        if callable(callback):
            self.cd_player_callback = callback
            print("✅ Audio change callback registered")
        else:
            print("❌ Invalid callback provided")
            self.cd_player_callback = None

    def restore_last_device(self):
        try:
            with open("/tmp/last_audio_device.txt", "r") as f:
                last_device_id = f.read().strip()
            # Check if device is still available
            for device in self.available_devices:
                if device['id'] == last_device_id:
                    print(f"🔄 Restoring last audio device: {last_device_id}")
                    self.set_device(last_device_id)
                    break
        except Exception:
            print("ℹ️ No last audio device to restore")
    
    def _run_as_user(self, command, timeout=10):
        """Run command as orangepi user for PulseAudio access"""
        try:
            uid = pwd.getpwnam('orangepi').pw_uid
            xdg_runtime_dir = f"/run/user/{uid}"

            env = {
                'HOME': f'/home/{self.user_name}',
                'USER': self.user_name,
                'XDG_RUNTIME_DIR': xdg_runtime_dir,
                'PULSE_RUNTIME_PATH': '/run/user/1000/pulse',
                'PULSE_SERVER': 'unix:/run/user/1000/pulse/native',
                'PIPEWIRE_RUNTIME_DIR': '/run/user/1000/pipewire-0'
            }
            
            result = subprocess.run(
                ['sudo', '-u', self.user_name, '-E'] + command,
                capture_output=True,
                text=True,
                timeout=timeout,
                env=env
            )
            return result
        except Exception as e:
            print(f"❌ Error running command as user: {e}")
            return None
    
    def scan_devices(self):
        """Scan for both ALSA and PulseAudio devices"""
        self.available_devices = []
        
        # Scan ALSA hardware devices
        self._scan_alsa_devices()
        
        # Scan PulseAudio sinks (includes Bluetooth)
        self._scan_pulseaudio_sinks()
        
        print(f"🔊 Found {len(self.available_devices)} total audio devices")
        for device in self.available_devices:
            print(f"  - {device['name']} ({device['id']}) [{device['type']}]")
    
    def _scan_alsa_devices(self):
        """Scan for ALSA hardware devices"""
        try:
            result = subprocess.run(['aplay', '-l'], capture_output=True, text=True)
            if result.returncode == 0:
                lines = result.stdout.split('\n')
                for line in lines:
                    if 'card' in line and ':' in line:
                        card_match = re.search(r'card (\d+): ([^,]+)', line)
                        if card_match:
                            card_num = card_match.group(1)
                            card_name = card_match.group(2).strip()
                            device_id = f"hw={card_num},0"
                            self.available_devices.append({
                                'id': device_id,
                                'name': f"{card_name} (Hardware)",
                                'type': 'ALSA',
                                'connected': True
                            })
        except Exception as e:
            print(f"❌ Error scanning ALSA devices: {e}")
    
    def _scan_pulseaudio_sinks(self):
        """Scan for PipeWire/PulseAudio sinks including Bluetooth devices"""
        try:
            # Test PipeWire access as orangepi user
            result = self._run_as_user(['pactl', 'info'], timeout=5)

            if not result or result.returncode != 0:
                print("⚠️ PipeWire/PulseAudio not accessible - skipping sink scan")
                return

            print("✅ PipeWire/PulseAudio detected and accessible")

            # Get list of sinks
            result = self._run_as_user(['pactl', 'list', 'short', 'sinks'], timeout=10)

            if result and result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                for line in lines:
                    if line.strip():
                        parts = line.split('\t')
                        if len(parts) >= 2:
                            sink_name = parts[1]
                            sink_description = self._get_sink_description(sink_name)

                            # Determine device type
                            if 'bluez' in sink_name.lower():
                                device_type = 'Bluetooth'
                                device_id = f"pulse:{sink_name}"
                                display_name = f"{sink_description} (Bluetooth)"
                            elif 'alsa' in sink_name.lower():
                                device_type = 'PipeWire-ALSA'
                                device_id = f"pulse:{sink_name}"
                                display_name = f"{sink_description} (Audio)"
                            else:
                                device_type = 'PipeWire'
                                device_id = f"pulse:{sink_name}"
                                display_name = sink_description

                            self.available_devices.append({
                                'id': device_id,
                                'name': display_name,
                                'type': device_type,
                                'connected': True,
                                'sink_name': sink_name
                            })

            # Add generic PipeWire default
            self.available_devices.append({
                'id': 'pulse',
                'name': 'PipeWire Default',
                'type': 'PipeWire',
                'connected': True
            })

        except Exception as e:
            print(f"❌ Error scanning PipeWire sinks: {e}")
    
    def _get_sink_description(self, sink_name):
        """Get human-readable description for a PulseAudio sink"""
        try:
            result = self._run_as_user(['pactl', 'list', 'sinks'], timeout=10)
            
            if result and result.returncode == 0:
                lines = result.stdout.split('\n')
                found_sink = False
                
                for line in lines:
                    if f"Name: {sink_name}" in line:
                        found_sink = True
                    elif found_sink and line.strip().startswith('Description:'):
                        description = line.split('Description:', 1)[1].strip()
                        return description
                    elif found_sink and line.strip().startswith('Name:') and f"Name: {sink_name}" not in line:
                        break
            
            return sink_name.replace('_', ' ').title()
            
        except Exception as e:
            print(f"❌ Error getting sink description: {e}")
            return sink_name
    
    def set_device(self, device_id):
        """Set the current audio device and notify CD player"""
        old_device = self.current_device
        self.current_device = device_id

        try:
            with open("/tmp/last_audio_device.txt", "w") as f:
                f.write(device_id)
        except Exception as e:
            print(f"❌ Failed to save last audio device: {e}")

        # Handle PulseAudio sink switching
        if device_id.startswith('pulse:'):
            sink_name = device_id.replace('pulse:', '')
            try:
                result = self._run_as_user(['pactl', 'set-default-sink', sink_name], timeout=5)
                if result and result.returncode == 0:
                    print(f"🔊 Set PulseAudio default sink to: {sink_name}")
                else:
                    print(f"❌ Failed to set PulseAudio sink: {sink_name}")
            except Exception as e:
                print(f"❌ Error setting PulseAudio sink: {e}")
        elif device_id == 'pulse':
            print("🔊 Using PulseAudio default output")

        print(f"🔊 Audio device changed from {old_device} to {device_id}")

        # Safe callback execution with proper type checking
        if self.cd_player_callback is not None and callable(self.cd_player_callback):
            try:
                self.cd_player_callback()
                print("✅ CD player notified of audio output change")
            except Exception as e:
                print(f"⚠️ Audio change callback failed: {e}")
    
    def refresh_devices(self):
        """Refresh device list"""
        print("🔄 Refreshing audio device list...")
        self.scan_devices()
    
    def get_device_name(self, device_id):
        """Get device name by ID"""
        for device in self.available_devices:
            if device['id'] == device_id:
                return device['name']
        return "Unknown Device"
    
    def get_current_device(self):
        """Get the currently selected audio device"""
        return self.current_device
    
    def is_bluetooth_device(self, device_id):
        """Check if a device is a Bluetooth audio device"""
        for device in self.available_devices:
            if device['id'] == device_id:
                return device['type'] == 'Bluetooth'
        return False
    
    def get_bluetooth_devices(self):
        """Get only Bluetooth audio devices"""
        return [device for device in self.available_devices if device['type'] == 'Bluetooth']
