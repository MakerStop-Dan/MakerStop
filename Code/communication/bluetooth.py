"""
Bluetooth communication module for MakerStop Controller.
Handles all Bluetooth connectivity and command transmission.
"""
# At the top of your communication/bluetooth.py file, replace:
# import bluetooth

# With this:
# try:
#     import bluetooth
# except ImportError:
#     print("Creating mock bluetooth for development...")
#     class MockBluetooth:
#         RFCOMM = "RFCOMM"
#         class BluetoothSocket:
#             def __init__(self, protocol): pass
#             def connect(self, addr): print(f"Mock connect: {addr}")
#             def send(self, data): print(f"Mock send: {data.decode('utf-8', errors='ignore').strip()}"); return len(data)
#             def recv(self, size): return b""
#             def settimeout(self, timeout): pass
#             def close(self): pass
#         @staticmethod
#         def discover_devices(duration=10, lookup_names=True):
#             mock_devices = [("00:11:22:33:44:55", "Mock FluidNC")]
#             return mock_devices if lookup_names else [addr for addr, name in mock_devices]
    
#     bluetooth = MockBluetooth()
import bluetooth    
import threading
import socket
import time
from PyQt5.QtCore import QObject, pyqtSignal

from config.constants import BT_SERVICE_UUID, BT_DEVICE_FILE


class BluetoothManager(QObject):
    """Manages Bluetooth communication with ESP32/FluidNC devices."""
    
    # Signals for UI updates
    message_received = pyqtSignal(str)
    connection_status_changed = pyqtSignal(bool, str)
    device_found = pyqtSignal(str, str)  # name, address
    
    def __init__(self):
        super().__init__()
        self.bt_socket = None
        self.bt_read_thread = None
        self.bt_running = False
        self.bt_device_address = None
        
    def scan_devices(self, duration=10):
        """Scan for nearby Bluetooth devices."""
        try:
            self.message_received.emit("🔍 Scanning for Bluetooth devices...")
            
            nearby_devices = bluetooth.discover_devices(duration=duration, lookup_names=True)
            
            if nearby_devices:
                self.message_received.emit(f"Found {len(nearby_devices)} device(s):")
                for addr, name in nearby_devices:
                    self.message_received.emit(f"  {name} - {addr}")
                    self.device_found.emit(name, addr)
                    
                    if "FluidNC" in name or "ESP32" in name:
                        self.message_received.emit(f"✅ Found ESP32 device: {name}")
            else:
                self.message_received.emit("No Bluetooth devices found")
                
        except Exception as e:
            self.message_received.emit(f"Bluetooth scan error: {e}")
    
    def connect(self, device_name_or_addr="FluidNC"):
        """Connect to ESP32 via Bluetooth."""
        try:
            if self.bt_socket:
                self.disconnect()
            
            self.message_received.emit(f"🔵 Connecting to {device_name_or_addr}...")
            
            if ":" not in device_name_or_addr:
                self.message_received.emit("Searching for device by name...")
                nearby_devices = bluetooth.discover_devices(duration=10, lookup_names=True)
                
                device_addr = None
                for addr, name in nearby_devices:
                    if device_name_or_addr.lower() in name.lower():
                        device_addr = addr
                        self.message_received.emit(f"Found {name} at {addr}")
                        break
                
                if not device_addr:
                    raise Exception(f"Device '{device_name_or_addr}' not found")
            else:
                device_addr = device_name_or_addr
            
            self.bt_socket = bluetooth.BluetoothSocket(bluetooth.RFCOMM)
            self.bt_socket.connect((device_addr, 1))
            self.bt_socket.settimeout(5.0)
            
            self.bt_device_address = device_addr
            
            self.bt_running = True
            self.bt_read_thread = threading.Thread(target=self._read_worker, daemon=True)
            self.bt_read_thread.start()
            
            self.message_received.emit(f"✅ Connected to ESP32 via Bluetooth!")
            self.connection_status_changed.emit(True, device_addr)
            
            time.sleep(1)
            self.send_command("?")
            
            self._save_device(device_addr)
            return True
            
        except Exception as e:
            self.message_received.emit(f"❌ Bluetooth connection failed: {e}")
            self.connection_status_changed.emit(False, str(e))
            if self.bt_socket:
                try:
                    self.bt_socket.close()
                except:
                    pass
                self.bt_socket = None
            return False
    
    def disconnect(self):
        """Disconnect from ESP32 Bluetooth."""
        self.bt_running = False
        if self.bt_read_thread and self.bt_read_thread.is_alive():
            self.bt_read_thread.join(timeout=2)
        
        if self.bt_socket:
            try:
                self.bt_socket.close()
            except:
                pass
            self.bt_socket = None
        
        self.message_received.emit("Disconnected from ESP32 Bluetooth")
        self.connection_status_changed.emit(False, "Disconnected")
    
    def send_command(self, command):
        """Send command to ESP32 via Bluetooth."""
        if not self.bt_socket:
            self.message_received.emit("Bluetooth not connected. Command not sent.")
            return False
            
        try:
            command = command.rstrip('\r\n') + '\n'
            self.bt_socket.send(command.encode('utf-8'))
            self.message_received.emit(f"📤 Sent: {command.strip()}")
            return True
            
        except Exception as e:
            self.message_received.emit(f"Failed to send Bluetooth command: {e}")
            return False
    
    def is_connected(self):
        """Check if Bluetooth is connected."""
        return self.bt_socket is not None
    
    def _read_worker(self):
        """Bluetooth reading thread."""
        buffer = ""
        
        while self.bt_running and self.bt_socket:
            try:
                data = self.bt_socket.recv(1024)
                if not data:
                    break
                    
                text = data.decode('utf-8', errors='ignore')
                buffer += text
                
                while '\n' in buffer or '\r' in buffer:
                    if '\n' in buffer:
                        line, buffer = buffer.split('\n', 1)
                    else:
                        line, buffer = buffer.split('\r', 1)
                    
                    line = line.strip()
                    if line:
                        self.message_received.emit(f"ESP32: {line}")
                        
            except socket.timeout:
                continue
            except Exception as e:
                if self.bt_running:
                    self.message_received.emit(f"Bluetooth read error: {e}")
                break
    
    def _save_device(self, address):
        """Save Bluetooth device address."""
        try:
            with open(BT_DEVICE_FILE, 'w') as file:
                file.write(address)
        except Exception as e:
            self.message_received.emit(f"Could not save device address: {e}")
    
    def load_last_device(self):
        """Load last used Bluetooth device."""
        try:
            with open(BT_DEVICE_FILE, 'r') as file:
                address = file.read().strip()
            return address
        except FileNotFoundError:
            return None
        except Exception as e:
            self.message_received.emit(f"Could not load device address: {e}")
            return None
    
    def auto_connect(self):
        """Attempt to automatically connect to last used device."""
        saved_device = self.load_last_device()
        
        if saved_device:
            self.message_received.emit(f"🔍 Attempting auto-connect to {saved_device}")
            return self.connect(saved_device)
        else:
            self.message_received.emit("No saved Bluetooth device found")
            return False
