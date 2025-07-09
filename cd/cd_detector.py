"""
CD detection and D-Bus monitoring
"""
import os
import dbus
import subprocess
import time
import re
from gi.repository import GLib
from dbus.mainloop.glib import DBusGMainLoop
from utils.helpers import setup_temp_files

class CDDetector:
    def __init__(self, player_callback):
        self.player_callback = player_callback
        self.system_bus = None
        self.main_loop = None
        
        # Setup D-Bus
        DBusGMainLoop(set_as_default=True)
        try:
            self.system_bus = dbus.SystemBus()
            print("✅ D-Bus connection established")
        except Exception as e:
            print(f"❌ D-Bus connection failed: {e}")
    
    def setup_monitoring(self):
        """Setup D-Bus monitoring for CD events"""
        if not self.system_bus:
            return False
        
        try:
            udisk_proxy = self.system_bus.get_object(
                "org.freedesktop.UDisks2", 
                "/org/freedesktop/UDisks2"
            )
            
            # Connect to device addition/removal signals
            udisk_proxy.connect_to_signal(
                'InterfacesAdded', 
                self.device_added,
                dbus_interface='org.freedesktop.DBus.ObjectManager'
            )
            
            udisk_proxy.connect_to_signal(
                'InterfacesRemoved', 
                self.device_removed,
                dbus_interface='org.freedesktop.DBus.ObjectManager'
            )
            
            # Connect to property changes
            self.system_bus.add_signal_receiver(
                self.properties_changed,
                signal_name='PropertiesChanged',
                dbus_interface='org.freedesktop.DBus.Properties',
                path_keyword='object_path'
            )
            
            print("✅ D-Bus CD monitoring setup complete")
            return True
            
        except Exception as e:
            print(f"❌ D-Bus setup error: {e}")
            return False
    
    def check_startup_cd(self):
        """Check if CD is already inserted when script starts"""
        if not self.system_bus:
            return False
        
        try:
            print("🔍 Checking for existing CD at startup...")
            manager = self.system_bus.get_object(
                "org.freedesktop.UDisks2", 
                "/org/freedesktop/UDisks2"
            )
            manager_iface = dbus.Interface(manager, 'org.freedesktop.DBus.ObjectManager')
            objects = manager_iface.GetManagedObjects()
            
            for path, interfaces in objects.items():
                if 'org.freedesktop.UDisks2.Block' in interfaces:
                    props = interfaces['org.freedesktop.UDisks2.Block']
                    device_file = props.get('Device', [])
                    size = props.get('Size', 0)
                    
                    if device_file and size > 0:
                        device_file_str = ''.join([chr(b) for b in device_file if b != 0])
                        if '/dev/sr' in device_file_str or '/dev/cdrom' in device_file_str:
                            print(f"📀 CD already inserted at {path}")
                            self.player_callback.load_cd_paused()
                            return True
            
            print("📭 No CD detected at startup")
            return False
            
        except Exception as e:
            print(f"❌ Error checking CD insertion at startup: {e}")
            return False
    
    def device_added(self, object_path, interfaces_and_properties):
        """Called when a new device is added"""
        if 'org.freedesktop.UDisks2.Block' in interfaces_and_properties:
            device_path = str(object_path)
            if self.is_audio_cd_device(device_path):
                print(f"📀 Audio CD detected at {device_path}")
                self.player_callback.load_cd_paused()
    
    def device_removed(self, object_path, interfaces):
        """Called when a device is removed"""
        if 'org.freedesktop.UDisks2.Block' in interfaces:
            print("📤 Device removed - stopping playback")
            self.player_callback.stop_playback()
    
    def properties_changed(self, interface_name, changed_properties, invalidated_properties, object_path):
        """Called when device properties change"""
        if interface_name == 'org.freedesktop.UDisks2.Block':
            device_path = str(object_path)
            if 'IdType' in changed_properties or 'Size' in changed_properties:
                if self.is_audio_cd_device(device_path):
                    print(f"📀 Audio CD inserted at {device_path}")
                    self.player_callback.load_cd_paused()
                else:
                    print("📤 Media removed - stopping playback")
                    self.player_callback.stop_playback()
    
    def is_audio_cd_device(self, device_path):
        """Check if the device is an audio CD"""
        if not self.system_bus:
            return False
        
        try:
            device_obj = self.system_bus.get_object("org.freedesktop.UDisks2", device_path)
            device_props = dbus.Interface(device_obj, dbus.PROPERTIES_IFACE)
            
            device_file = device_props.Get('org.freedesktop.UDisks2.Block', 'Device')
            size = device_props.Get('org.freedesktop.UDisks2.Block', 'Size')
            
            device_file_str = ''.join([chr(b) for b in device_file if b != 0])
            is_cd_drive = '/dev/sr' in device_file_str or '/dev/cdrom' in device_file_str
            has_media = size > 0
            
            return is_cd_drive and has_media
            
        except Exception as e:
            print(f"❌ Error checking device {device_path}: {e}")
            return False
    
    def detect_cd_tracks(self):
        """Detect the actual number of tracks and their lengths on the CD"""
        total_tracks = 8
        track_lengths = {}
        
        try:
            print("🔍 Detecting CD tracks and lengths...")
            result = subprocess.run(
                ['cdparanoia', '-Q'],
                capture_output=True, 
                text=True, 
                timeout=15, 
                cwd='/tmp'
            )
            
            if result.returncode != 0:
                print("⚠️ No CD detected or CD not ready, using defaults")
                for i in range(1, total_tracks + 1):
                    track_lengths[i] = 180
                return total_tracks, track_lengths
            
            output = result.stderr
            tracks_found = []
            
            for line in output.split('\n'):
                match = re.match(r'^\s*(\d+)\.\s+(\d+)\s+\[(\d+):(\d+)\.(\d+)\]', line)
                if match:
                    track_num = int(match.group(1))
                    length_min = int(match.group(3))
                    length_sec = int(match.group(4))
                    length_total = length_min * 60 + length_sec
                    
                    tracks_found.append(track_num)
                    track_lengths[track_num] = max(1, length_total)
            
            if tracks_found:
                total_tracks = len(tracks_found)
                print(f"✅ Found {total_tracks} tracks with accurate lengths")
            else:
                # Fallback to defaults
                for i in range(1, total_tracks + 1):
                    track_lengths[i] = 180
            
            return total_tracks, track_lengths
            
        except Exception as e:
            print(f"❌ Error detecting CD tracks: {e}, using defaults")
            for i in range(1, total_tracks + 1):
                track_lengths[i] = 180
            return total_tracks, track_lengths
    
    def run_loop(self):
        """Start the main D-Bus event loop"""
        if not self.system_bus:
            print("❌ Cannot start D-Bus loop - no connection")
            return
        
        try:
            self.main_loop = GLib.MainLoop()
            print("🔄 Starting D-Bus event loop...")
            self.main_loop.run()
        except KeyboardInterrupt:
            print("\n🛑 D-Bus loop interrupted")
        except Exception as e:
            print(f"❌ D-Bus loop error: {e}")
        finally:
            if self.main_loop:
                self.main_loop.quit()
