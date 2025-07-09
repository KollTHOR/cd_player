"""
Menu system for CD player - Complete Implementation with Track Selection Menu
"""
import time
from .bluetooth_menu import BluetoothMenu

class MenuSystem:
    def __init__(self, lcd_display, audio_manager, cd_player):
        self.lcd = lcd_display
        self.audio_manager = audio_manager
        self.cd_player = cd_player
        self.bluetooth_menu = BluetoothMenu(lcd_display)
        
        # Menu state
        self.in_menu = False
        self.in_submenu = False
        self.in_action_menu = False
        self.in_tracks_menu = False
        self.selected_track_index = 0
        self.menu_timeout = 0
        
        # Menu items
        self.menu_items = [
            "Tracks",
            "Audio Output",
            "Bluetooth", 
            "Exit Menu"
        ]
        self.current_menu_item = 0
        
        # Selection indices
        self.selected_audio_device_index = 0
        self.selected_bluetooth_device_index = 0
        self.selected_action_index = 0
        self.selected_track_index = 0
        
        # Current action context
        self.current_actions = []
        self.current_device = None

    def enter_menu(self):
        self.in_menu = True
        self.in_submenu = False
        self.in_action_menu = False
        self.in_tracks_menu = False
        self.current_menu_item = 0
        self.menu_timeout = time.time() + 30
        print("📋 Entering menu system")
        self.update_menu_display()
    
    def exit_menu(self):
        self.in_menu = False
        self.in_submenu = False
        self.in_action_menu = False
        self.in_tracks_menu = False
        self.menu_timeout = 0
        print("📋 Exiting menu system")
        if self.lcd:
            self.lcd.clear_cache()
    
    def enter_submenu(self, submenu_type):
        self.in_submenu = True
        self.in_action_menu = False
        self.in_tracks_menu = False
        self.menu_timeout = time.time() + 30
        
        if submenu_type == "Audio Output":
            self.show_message("Audio Devices", "Scanning...")
            self.audio_manager.refresh_devices()
            self.selected_audio_device_index = 0
            print("📋 Entering Audio Output submenu")
        elif submenu_type == "Bluetooth":
            self.show_message("Bluetooth", "Scanning...")
            devices = self.bluetooth_menu.scan_devices()
            if devices:
                self.selected_bluetooth_device_index = 0
                print("📋 Entering Bluetooth submenu")
            else:
                self.show_message("No Bluetooth", "Devices Found")
                time.sleep(2)
                self.exit_submenu()
                return
        elif submenu_type == "Tracks":
            if self.cd_player.total_tracks > 0:
                self.in_tracks_menu = True
                self.selected_track_index = 0
                print("📋 Entering Tracks menu")
                self.update_tracks_display()
            else:
                self.show_message("No CD", "Insert Disc")
                time.sleep(2)
                self.exit_submenu()
                return
            
        self.update_submenu_display()
    
    def exit_submenu(self):
        self.in_submenu = False
        self.in_action_menu = False
        self.in_tracks_menu = False
        self.menu_timeout = time.time() + 30
        print("📋 Exiting submenu")
        self.update_menu_display()
    
    def enter_action_menu(self, device, actions):
        self.in_action_menu = True
        self.current_device = device
        self.current_actions = actions
        self.selected_action_index = 0
        self.menu_timeout = time.time() + 30
        print(f"📋 Entering action menu for {device['name']}")
        self.update_action_display()
    
    def exit_action_menu(self):
        self.in_action_menu = False
        self.current_device = None
        self.current_actions = []
        self.selected_action_index = 0
        self.menu_timeout = time.time() + 30
        print("📋 Exiting action menu")
        self.update_submenu_display()
    
    def menu_next(self):
        if self.in_menu and not self.in_submenu and not self.in_action_menu and not self.in_tracks_menu:
            self.current_menu_item = (self.current_menu_item + 1) % len(self.menu_items)
            self.menu_timeout = time.time() + 30
            self.update_menu_display()
    
    def menu_previous(self):
        if self.in_menu and not self.in_submenu and not self.in_action_menu and not self.in_tracks_menu:
            self.current_menu_item = (self.current_menu_item - 1) % len(self.menu_items)
            self.menu_timeout = time.time() + 30
            self.update_menu_display()
    
    def submenu_next(self):
        if self.in_action_menu:
            if self.current_actions:
                self.selected_action_index = (self.selected_action_index + 1) % len(self.current_actions)
                self.menu_timeout = time.time() + 30
                self.update_action_display()
        elif self.in_tracks_menu:
            if self.cd_player.total_tracks > 0:
                self.selected_track_index = (self.selected_track_index + 1) % self.cd_player.total_tracks
                self.menu_timeout = time.time() + 30
                self.update_tracks_display()
        elif self.in_submenu:
            current_item = self.menu_items[self.current_menu_item]
            if current_item == "Audio Output":
                if self.audio_manager.available_devices:
                    self.selected_audio_device_index = (self.selected_audio_device_index + 1) % len(self.audio_manager.available_devices)
            elif current_item == "Bluetooth":
                if self.bluetooth_menu.bluetooth_devices:
                    self.selected_bluetooth_device_index = (self.selected_bluetooth_device_index + 1) % len(self.bluetooth_menu.bluetooth_devices)
            self.menu_timeout = time.time() + 30
            self.update_submenu_display()
    
    def submenu_previous(self):
        if self.in_action_menu:
            if self.current_actions:
                self.selected_action_index = (self.selected_action_index - 1) % len(self.current_actions)
                self.menu_timeout = time.time() + 30
                self.update_action_display()
        elif self.in_tracks_menu:
            if self.cd_player.total_tracks > 0:
                self.selected_track_index = (self.selected_track_index - 1) % self.cd_player.total_tracks
                self.menu_timeout = time.time() + 30
                self.update_tracks_display()
        elif self.in_submenu:
            current_item = self.menu_items[self.current_menu_item]
            if current_item == "Audio Output":
                if self.audio_manager.available_devices:
                    self.selected_audio_device_index = (self.selected_audio_device_index - 1) % len(self.audio_manager.available_devices)
            elif current_item == "Bluetooth":
                if self.bluetooth_menu.bluetooth_devices:
                    self.selected_bluetooth_device_index = (self.selected_bluetooth_device_index - 1) % len(self.bluetooth_menu.bluetooth_devices)
            self.menu_timeout = time.time() + 30
            self.update_submenu_display()
    
    def menu_select(self):
        if not self.in_menu or self.in_submenu or self.in_action_menu or self.in_tracks_menu:
            return
        selected_item = self.menu_items[self.current_menu_item]
        print(f"📋 Selected: {selected_item}")
        if selected_item == "Tracks":
            self.enter_submenu("Tracks")
        elif selected_item == "Audio Output":
            self.enter_submenu("Audio Output")
        elif selected_item == "Bluetooth":
            self.enter_submenu("Bluetooth")
        elif selected_item == "Exit Menu":
            self.exit_menu()
    
    def submenu_select(self):
        if self.in_action_menu:
            self.execute_bluetooth_action()
        
        elif self.in_tracks_menu:
            track_num = self.selected_track_index + 1
            if self.cd_player.load_track(track_num):
                self.show_message("Playing", f"Track {track_num}")
                time.sleep(1)
                self.exit_menu()  # Stay in track list
            else:
                self.show_message("Load Failed", f"Track {track_num}")
                time.sleep(1)
        elif self.in_submenu:
            current_item = self.menu_items[self.current_menu_item]
            if current_item == "Audio Output":
                if self.audio_manager.available_devices:
                    device = self.audio_manager.available_devices[self.selected_audio_device_index]
                    self.show_message("Use Audio:", device['name'][:16])
                    time.sleep(1)
                    self.audio_manager.set_device(device['id'])
                    self.show_message("Audio Set:", device['name'][:16])
                    time.sleep(1)
                    self.exit_submenu()
            elif current_item == "Bluetooth":
                if self.bluetooth_menu.bluetooth_devices:
                    device = self.bluetooth_menu.bluetooth_devices[self.selected_bluetooth_device_index]
                    actions = self.bluetooth_menu.get_available_actions(device['mac'])
                    if actions:
                        self.enter_action_menu(device, actions)
                    else:
                        self.show_message("No Actions", "Available")
                        time.sleep(2)
    
    def update_tracks_display(self):
        if not self.lcd or not self.in_tracks_menu:
            return
        total = self.cd_player.total_tracks
        idx = self.selected_track_index
        length = self.cd_player.track_lengths.get(idx+1, 0)
        mins = length // 60
        secs = length % 60
        time_str = f"{mins}:{secs:02d}" if length else ""
        self.lcd.show_message(
            f"Track {idx+1}/{total}",
            time_str
        )


    def execute_bluetooth_action(self):
        if not self.current_device or not self.current_actions:
            return
        action = self.current_actions[self.selected_action_index].lower()
        device = self.current_device
        success = False
        self.show_message(f"{action.title()}ing...", device['name'][:16])
        if action == "pair":
            success = self.bluetooth_menu.pair_device(device['mac'], device['name'])
        elif action == "connect":
            success = self.bluetooth_menu.connect_device(device['mac'], device['name'])
        elif action == "disconnect":
            success = self.bluetooth_menu.disconnect_device(device['mac'], device['name'])
        elif action == "forget":
            success = self.bluetooth_menu.forget_device(device['mac'], device['name'])
        if success:
            print(f"✅ {action.title()} operation completed successfully")
        else:
            print(f"❌ {action.title()} operation failed")
        self.exit_menu()
    
    def show_message(self, line1, line2):
        if self.lcd:
            self.lcd.show_message(line1, line2)
    
    def update_menu_display(self):
        if not self.lcd or not self.in_menu or self.in_submenu or self.in_action_menu or self.in_tracks_menu:
            return
        try:
            current_item = self.menu_items[self.current_menu_item]
            self.lcd.show_message("MENU", f"> {current_item}")
        except Exception as e:
            print(f"❌ Menu display error: {e}")
    
    def update_submenu_display(self):
        if not self.lcd or not self.in_submenu or self.in_action_menu or self.in_tracks_menu:
            return
        try:
            current_item = self.menu_items[self.current_menu_item]
            if current_item == "Audio Output" and self.audio_manager.available_devices:
                device = self.audio_manager.available_devices[self.selected_audio_device_index]
                device_count = len(self.audio_manager.available_devices)
                self.lcd.show_message(
                    f"Audio {self.selected_audio_device_index + 1}/{device_count}", 
                    f"> {device['name'][:14]}"
                )
            elif current_item == "Bluetooth" and self.bluetooth_menu.bluetooth_devices:
                device = self.bluetooth_menu.bluetooth_devices[self.selected_bluetooth_device_index]
                device_name = device['name'][:14] if device['name'] else device['mac'][:14]
                device_count = len(self.bluetooth_menu.bluetooth_devices)
                status = "●" if device.get('connected', False) else "○"
                self.lcd.show_message(
                    f"BT {self.selected_bluetooth_device_index + 1}/{device_count}", 
                    f"{status} {device_name}"
                )
        except Exception as e:
            print(f"❌ Submenu display error: {e}")

    def update_action_display(self):
        if not self.lcd or not self.in_action_menu or not self.current_device or not self.current_actions:
            return
        try:
            device_name = self.current_device['name'][:12] if self.current_device['name'] else self.current_device['mac'][:12]
            action_name = self.current_actions[self.selected_action_index]
            action_count = len(self.current_actions)
            self.lcd.show_message(
                f"BT: {device_name}",
                f"> {action_name} {self.selected_action_index + 1}/{action_count}"
            )
        except Exception as e:
            print(f"❌ Action display error: {e}")
    
    def check_timeout(self):
        if self.in_menu and time.time() > self.menu_timeout:
            print("📋 Menu timeout - exiting")
            self.exit_menu()
            return True
        return False
    
    def get_menu_status(self):
        return {
            'in_menu': self.in_menu,
            'in_submenu': self.in_submenu,
            'in_action_menu': self.in_action_menu,
            'in_tracks_menu': self.in_tracks_menu,
            'current_item': self.menu_items[self.current_menu_item] if self.in_menu else None,
            'timeout_remaining': max(0, self.menu_timeout - time.time()) if self.in_menu else 0
        }
    
    def force_exit(self):
        self.in_menu = False
        self.in_submenu = False
        self.in_action_menu = False
        self.in_tracks_menu = False
        self.menu_timeout = 0
        print("📋 Force exiting menu system")
        if self.lcd:
            self.lcd.clear_cache()
    
    def add_menu_item(self, item_name, callback=None):
        if item_name not in self.menu_items:
            self.menu_items.insert(-1, item_name)
            print(f"📋 Added menu item: {item_name}")
    
    def remove_menu_item(self, item_name):
        if item_name in self.menu_items and item_name != "Exit Menu":
            self.menu_items.remove(item_name)
            if self.current_menu_item >= len(self.menu_items):
                self.current_menu_item = len(self.menu_items) - 1
            print(f"📋 Removed menu item: {item_name}")
    
    def get_audio_device_name(self, device_id):
        for device in self.audio_manager.available_devices:
            if device['id'] == device_id:
                return device['name']
        return "Unknown Device"
    
    def get_bluetooth_device_name(self, mac_address):
        for device in self.bluetooth_menu.bluetooth_devices:
            if device['mac'] == mac_address:
                return device['name'] if device['name'] else mac_address
        return "Unknown Device"
    
    def refresh_devices(self):
        print("📋 Refreshing device lists...")
        self.audio_manager.scan_devices()
        self.bluetooth_menu.scan_devices()
        if self.selected_audio_device_index >= len(self.audio_manager.available_devices):
            self.selected_audio_device_index = 0
        if self.selected_bluetooth_device_index >= len(self.bluetooth_menu.bluetooth_devices):
            self.selected_bluetooth_device_index = 0
        if self.in_submenu:
            self.update_submenu_display()
        elif self.in_action_menu:
            self.update_action_display()
