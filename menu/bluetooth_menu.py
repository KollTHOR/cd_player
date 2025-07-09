"""
Bluetooth-specific menu actions and management - Fixed Version
"""
import subprocess
import time

class BluetoothMenu:
    def __init__(self, lcd_display):
        self.lcd = lcd_display
        self.bluetooth_devices = []
        self.connected_device = None
        self.scanning = False
    
    def scan_devices(self):
        """Scan for available Bluetooth devices with extended scan time"""
        self.bluetooth_devices = []
        self.scanning = True
        
        try:
            print("🔍 Scanning for Bluetooth devices...")
            if self.lcd:
                self.lcd.show_message("Bluetooth", "Scanning...")
            
            # Use bluetoothctl to scan for devices
            scan_process = subprocess.Popen(['bluetoothctl'],
                                          stdin=subprocess.PIPE,
                                          stdout=subprocess.PIPE,
                                          stderr=subprocess.PIPE,
                                          text=True)
            
            # Start scanning with extended time
            scan_process.stdin.write("scan on\n")
            scan_process.stdin.flush()
            
            # Extended scanning time - scan for 8 seconds instead of 3
            for i in range(8):
                if self.lcd:
                    dots = "." * ((i % 3) + 1)
                    self.lcd.show_message("Bluetooth", f"Scanning{dots}")
                time.sleep(1)
            
            # Get device list multiple times to catch more devices
            all_devices = {}
            
            for scan_round in range(2):  # Two rounds of device listing
                scan_process.stdin.write("devices\n")
                scan_process.stdin.flush()
                time.sleep(1)
                
                # Also try to get paired devices
                scan_process.stdin.write("paired-devices\n")
                scan_process.stdin.flush()
                time.sleep(1)
            
            # Stop scanning and quit
            scan_process.stdin.write("scan off\n")
            scan_process.stdin.write("quit\n")
            scan_process.stdin.flush()
            
            # Parse output
            output, _ = scan_process.communicate(timeout=15)
            
            # Parse all device entries
            for line in output.split('\n'):
                if line.startswith('Device '):
                    parts = line.split(' ', 2)
                    if len(parts) >= 3:
                        mac = parts[1]
                        raw_name = parts[2] if len(parts) > 2 else ""
                        
                        # Get detailed device info to get proper name and status
                        device_info = self.get_device_info(mac)
                        if device_info and device_info['name'] != 'Unknown':
                            name = device_info['name']
                        else:
                            # Fallback to raw name or generate from MAC
                            name = raw_name if raw_name and raw_name != "Unknown Device" else self._generate_device_name(mac)
                        
                        # Get current connection and pairing status
                        is_connected = device_info['connected'] if device_info else False
                        is_paired = device_info['paired'] if device_info else False
                        
                        # Store unique devices (avoid duplicates)
                        all_devices[mac] = {
                            'mac': mac,
                            'name': name,
                            'connected': is_connected,
                            'paired': is_paired
                        }
            
            # Convert to list and sort by name (prioritize names over MAC addresses)
            self.bluetooth_devices = list(all_devices.values())
            self.bluetooth_devices.sort(key=lambda x: (x['name'].lower(), x['mac']))
            
            print(f"📱 Found {len(self.bluetooth_devices)} Bluetooth devices")
            for device in self.bluetooth_devices:
                status = "●" if device['connected'] else ("○" if device['paired'] else "◦")
                print(f"  {status} {device['name']} ({device['mac']})")
            
        except Exception as e:
            print(f"❌ Error scanning Bluetooth: {e}")
        finally:
            self.scanning = False
        
        return self.bluetooth_devices
    
    def _generate_device_name(self, mac_address):
        """Generate a friendly device name from MAC address if no name available"""
        # Take last 4 characters of MAC for identification
        mac_suffix = mac_address.replace(':', '')[-4:].upper()
        return f"Device-{mac_suffix}"
    
    def check_device_connected(self, mac_address):
        """Check if a specific device is connected"""
        try:
            result = subprocess.run(['bluetoothctl', 'info', mac_address],
                                  capture_output=True, text=True, timeout=5)
            return "Connected: yes" in result.stdout
        except:
            return False
    
    def pair_device(self, mac_address, device_name=None):
        """Pair with a Bluetooth device and auto-connect if successful"""
        display_name = device_name if device_name else mac_address[:16]
        
        try:
            print(f"📱 Pairing with {display_name}")
            if self.lcd:
                self.lcd.show_message("Pairing...", display_name[:16])
            
            result = subprocess.run(['bluetoothctl', 'pair', mac_address],
                                  capture_output=True, text=True, timeout=30)
            
            success = result.returncode == 0 or "successful" in result.stdout.lower()
            
            if success:
                print(f"✅ Successfully paired with {display_name}")
                if self.lcd:
                    self.lcd.show_message("Paired!", display_name[:16])
                time.sleep(1)
                
                # Automatically attempt to connect after successful pairing
                print(f"🔗 Auto-connecting to {display_name}...")
                if self.lcd:
                    self.lcd.show_message("Auto-connecting", display_name[:16])
                
                connect_success = self.connect_device(mac_address, device_name, auto_connect=True)
                if connect_success:
                    if self.lcd:
                        self.lcd.show_message("Paired & Connected", "Success!")
                else:
                    if self.lcd:
                        self.lcd.show_message("Paired Only", "Connect manually")
                
                time.sleep(2)
                return True
            else:
                print(f"❌ Failed to pair with {display_name}")
                if self.lcd:
                    self.lcd.show_message("Pair Failed", display_name[:16])
                time.sleep(2)
                return False
            
        except Exception as e:
            print(f"❌ Error pairing device: {e}")
            if self.lcd:
                self.lcd.show_message("Pair Error", display_name[:16])
            time.sleep(2)
            return False
    
    def connect_device(self, mac_address, device_name=None, auto_connect=False):
        """Connect to a paired Bluetooth device"""
        display_name = device_name if device_name else mac_address[:16]
        
        try:
            if not auto_connect:
                print(f"📱 Connecting to {display_name}")
            if self.lcd and not auto_connect:
                self.lcd.show_message("Connecting...", display_name[:16])
            
            result = subprocess.run(['bluetoothctl', 'connect', mac_address],
                                  capture_output=True, text=True, timeout=20)
            
            success = result.returncode == 0 or "successful" in result.stdout.lower()
            
            if success:
                print(f"✅ Successfully connected to {display_name}")
                self.connected_device = mac_address
                if self.lcd and not auto_connect:
                    self.lcd.show_message("Connected!", display_name[:16])
                    time.sleep(2)
            else:
                print(f"❌ Failed to connect to {display_name}")
                if self.lcd and not auto_connect:
                    self.lcd.show_message("Connect Failed", display_name[:16])
                    time.sleep(2)
            
            return success
            
        except Exception as e:
            print(f"❌ Error connecting device: {e}")
            if self.lcd and not auto_connect:
                self.lcd.show_message("Connect Error", display_name[:16])
                time.sleep(2)
            return False
    
    def disconnect_device(self, mac_address, device_name=None):
        """Disconnect from a Bluetooth device"""
        display_name = device_name if device_name else mac_address[:16]
        
        try:
            print(f"📱 Disconnecting from {display_name}")
            if self.lcd:
                self.lcd.show_message("Disconnecting", display_name[:16])
            
            result = subprocess.run(['bluetoothctl', 'disconnect', mac_address],
                                  capture_output=True, text=True, timeout=10)
            
            success = result.returncode == 0 or "successful" in result.stdout.lower()
            
            if success:
                print(f"✅ Successfully disconnected from {display_name}")
                if self.connected_device == mac_address:
                    self.connected_device = None
                if self.lcd:
                    self.lcd.show_message("Disconnected", display_name[:16])
            else:
                print(f"❌ Failed to disconnect from {display_name}")
                if self.lcd:
                    self.lcd.show_message("Disconnect Failed", display_name[:16])
            
            time.sleep(2)
            return success
            
        except Exception as e:
            print(f"❌ Error disconnecting device: {e}")
            if self.lcd:
                self.lcd.show_message("Disconnect Error", display_name[:16])
            time.sleep(2)
            return False
    
    def forget_device(self, mac_address, device_name=None):
        """Remove/forget a Bluetooth device"""
        display_name = device_name if device_name else mac_address[:16]
        
        try:
            print(f"📱 Forgetting device {display_name}")
            if self.lcd:
                self.lcd.show_message("Forgetting...", display_name[:16])
            
            result = subprocess.run(['bluetoothctl', 'remove', mac_address],
                                  capture_output=True, text=True, timeout=10)
            
            success = result.returncode == 0 or "successful" in result.stdout.lower()
            
            if success:
                print(f"✅ Successfully forgot device {display_name}")
                if self.connected_device == mac_address:
                    self.connected_device = None
                if self.lcd:
                    self.lcd.show_message("Forgotten", display_name[:16])
            else:
                print(f"❌ Failed to forget device {display_name}")
                if self.lcd:
                    self.lcd.show_message("Forget Failed", display_name[:16])
            
            time.sleep(2)
            return success
            
        except Exception as e:
            print(f"❌ Error forgetting device: {e}")
            if self.lcd:
                self.lcd.show_message("Forget Error", display_name[:16])
            time.sleep(2)
            return False
    
    def get_device_info(self, mac_address):
        """Get detailed information about a Bluetooth device"""
        try:
            result = subprocess.run(['bluetoothctl', 'info', mac_address],
                                  capture_output=True, text=True, timeout=5)
            
            info = {
                'name': 'Unknown',
                'connected': False,
                'paired': False,
                'trusted': False
            }
            
            for line in result.stdout.split('\n'):
                line = line.strip()
                if line.startswith('Name:'):
                    info['name'] = line.split(':', 1)[1].strip()
                elif line.startswith('Connected:'):
                    info['connected'] = 'yes' in line.lower()
                elif line.startswith('Paired:'):
                    info['paired'] = 'yes' in line.lower()
                elif line.startswith('Trusted:'):
                    info['trusted'] = 'yes' in line.lower()
            
            return info
            
        except Exception as e:
            print(f"❌ Error getting device info: {e}")
            return None
    
    def get_available_actions(self, mac_address):
        """Simplified actions - always show Connect for paired devices"""
        info = self.get_device_info(mac_address)
        if not info:
            return ["Pair"]
        
        actions = []
        
        if not info['paired']:
            actions.append("Pair")
        else:
            # For paired devices, always show all options
            actions.append("Connect")
            actions.append("Disconnect") 
            actions.append("Forget")
        
        return actions
    
    def get_device_display_name(self, mac_address):
        """Get the best display name for a device"""
        for device in self.bluetooth_devices:
            if device['mac'] == mac_address:
                return device['name']
        
        # Fallback to getting info directly
        info = self.get_device_info(mac_address)
        if info and info['name'] != 'Unknown':
            return info['name']
        
        return self._generate_device_name(mac_address)
