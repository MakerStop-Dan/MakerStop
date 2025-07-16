import subprocess
import time
from PyQt5.QtWidgets import (QDialog, QLabel, QLineEdit, QPushButton, QTextEdit, 
                             QWidget, QMessageBox, QInputDialog)
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt, QTimer
from functools import partial

class WiFiWizardDialog(QDialog):
    """
    WiFi Connection Wizard Dialog
    
    A standalone module for connecting to WiFi networks with the following features:
    - Network scanning with multiple methods (nmcli, iwlist, iw)
    - Enhanced on-screen keyboard with capitals and special characters
    - Manual network entry
    - Multiple connection methods
    - Current connection status display
    """
    
    def __init__(self, parent=None):
        try:
            super().__init__(parent)
            print("WiFiWizardDialog.__init__ started")
                
            self.setWindowTitle('WiFi Connection Wizard')
            self.setGeometry(0, 0, 800, 600)
            self.setFixedSize(800, 600)

            # Initialize variables
            self.available_networks = []
            self.selected_network = None
            self.keyboard_visible = False
            self.current_input = None
            self.shift_active = False  # Track shift state
            self.caps_lock = False     # Track caps lock state
            self.symbols_mode = False  # Track symbols mode
                
            print("About to initialize WiFi UI elements...")
            self.init_wifi_ui_elements()
            # Do NOT call self.scan_wifi_networks() here!

            print("WiFiWizardDialog.__init__ completed successfully")
                
        except Exception as e:
            print(f"Error in WiFiWizardDialog.__init__: {e}")
            raise

    def init_wifi_ui_elements(self):
        """Initialize WiFi wizard UI elements"""
        try:
            # Title
            self.title_label = QLabel("WiFi Connection Wizard", self)
            self.title_label.setGeometry(50, 20, 700, 40)
            self.title_label.setFont(QFont('Proxima Nova', 18, QFont.Bold))
            self.title_label.setAlignment(Qt.AlignCenter)
            self.title_label.setStyleSheet("color: #333; background-color: #f0f0f0; padding: 10px; border-radius: 10px;")

            # Status label
            self.status_label = QLabel("Scanning for WiFi networks...", self)
            self.status_label.setGeometry(50, 70, 700, 30)
            self.status_label.setFont(QFont('Proxima Nova', 12))
            self.status_label.setAlignment(Qt.AlignCenter)

            # Networks list
            self.networks_list = QTextEdit(self)
            self.networks_list.setGeometry(50, 110, 350, 300)
            self.networks_list.setReadOnly(True)
            self.networks_list.setFont(QFont('Proxima Nova', 11))
            self.networks_list.setStyleSheet("border: 2px solid #ccc; border-radius: 5px;")

            # Connection panel
            self.connection_label = QLabel("Connect to Network:", self)
            self.connection_label.setGeometry(420, 110, 330, 30)
            self.connection_label.setFont(QFont('Proxima Nova', 14, QFont.Bold))

            # Network name input
            self.network_name_label = QLabel("Network Name (SSID):", self)
            self.network_name_label.setGeometry(420, 150, 200, 25)
            self.network_name_label.setFont(QFont('Proxima Nova', 11))

            self.network_name_input = QLineEdit(self)
            self.network_name_input.setGeometry(420, 175, 330, 40)
            self.network_name_input.setFont(QFont('Proxima Nova', 12))
            self.network_name_input.setStyleSheet("padding: 8px; border: 2px solid #ccc; border-radius: 5px;")

            # Password input
            self.password_label = QLabel("Password:", self)
            self.password_label.setGeometry(420, 225, 200, 25)
            self.password_label.setFont(QFont('Proxima Nova', 11))

            self.password_input = QLineEdit(self)
            self.password_input.setGeometry(420, 250, 330, 40)
            self.password_input.setFont(QFont('Proxima Nova', 12))
            self.password_input.setEchoMode(QLineEdit.Password)
            self.password_input.setStyleSheet("padding: 8px; border: 2px solid #ccc; border-radius: 5px;")
            
            # Connect focus events to set current input for keyboard
            self.network_name_input.focusInEvent = lambda e: self.set_keyboard_target(self.network_name_input, e)
            self.password_input.focusInEvent = lambda e: self.set_keyboard_target(self.password_input, e)

            # Show/Hide password checkbox
            self.show_password_checkbox = QPushButton("👁 Show Password", self)
            self.show_password_checkbox.setGeometry(420, 300, 150, 30)
            self.show_password_checkbox.setFont(QFont('Proxima Nova', 10))
            self.show_password_checkbox.setCheckable(True)
            self.show_password_checkbox.clicked.connect(self.toggle_password_visibility)
            self.show_password_checkbox.setStyleSheet("""
                QPushButton {
                    background-color: #e0e0e0;
                    border: 1px solid #ccc;
                    border-radius: 5px;
                    padding: 5px;
                }
                QPushButton:checked {
                    background-color: #d0d0d0;
                }
            """)

            # Keyboard toggle button
            self.keyboard_button = QPushButton("📱 Show Keyboard", self)
            self.keyboard_button.setGeometry(580, 300, 150, 30)
            self.keyboard_button.setFont(QFont('Proxima Nova', 10))
            self.keyboard_button.clicked.connect(self.toggle_keyboard)
            self.keyboard_button.setStyleSheet("""
                background-color: #4a90e2;
                color: white;
                border-radius: 5px;
                padding: 5px;
                font-weight: bold;
            """)

            # Action buttons
            self.connect_button = QPushButton("Connect to WiFi", self)
            self.connect_button.setGeometry(420, 350, 150, 50)
            self.connect_button.setFont(QFont('Proxima Nova', 12, QFont.Bold))
            self.connect_button.setStyleSheet("""
                background-color: #74b72e;
                color: white;
                border-radius: 8px;
                padding: 10px;
                font-weight: bold;
            """)
            self.connect_button.clicked.connect(self.connect_to_wifi)

            self.refresh_button = QPushButton("🔄 Refresh", self)
            self.refresh_button.setGeometry(580, 350, 90, 50)
            self.refresh_button.setFont(QFont('Proxima Nova', 11))
            self.refresh_button.setStyleSheet("""
                background-color: #ffa500;
                color: white;
                border-radius: 8px;
                padding: 10px;
            """)
            self.refresh_button.clicked.connect(self.scan_wifi_networks)

            self.cancel_button = QPushButton("Cancel", self)
            self.cancel_button.setGeometry(680, 350, 80, 50)
            self.cancel_button.setFont(QFont('Proxima Nova', 11))
            self.cancel_button.setStyleSheet("""
                background-color: #ff746c;
                color: white;
                border-radius: 8px;
                padding: 10px;
            """)
            self.cancel_button.clicked.connect(self.reject)

            # Current connection info
            self.current_connection_label = QLabel("Current Connection:", self)
            self.current_connection_label.setGeometry(50, 420, 700, 25)
            self.current_connection_label.setFont(QFont('Proxima Nova', 12, QFont.Bold))

            self.current_connection_info = QLabel("Checking current connection...", self)
            self.current_connection_info.setGeometry(50, 445, 700, 60)
            self.current_connection_info.setFont(QFont('Proxima Nova', 11))
            self.current_connection_info.setWordWrap(True)
            self.current_connection_info.setStyleSheet("background-color: #f9f9f9; padding: 10px; border-radius: 5px;")

            # On-screen keyboard (initially hidden)
            self.create_onscreen_keyboard()

            # Check current connection
            self.check_current_connection()

        except Exception as e:
            print(f"Error in init_wifi_ui_elements: {e}")
            raise

    def set_keyboard_target(self, target_input, event):
        """Set the target input for the on-screen keyboard"""
        self.current_input = target_input
        # Call the original focusInEvent
        QLineEdit.focusInEvent(target_input, event)

    def create_onscreen_keyboard(self):
        """Create an enhanced on-screen keyboard with capitals and special characters"""
        try:
            # Keyboard container (initially hidden)
            self.keyboard_widget = QWidget(self)
            self.keyboard_widget.setGeometry(50, 300, 700, 180)
            self.keyboard_widget.setStyleSheet("background-color: #f0f0f0; border: 2px solid #ccc; border-radius: 10px;")
            self.keyboard_widget.setVisible(False)

            # Define keyboard layouts
            self.letters_layout = [
                ['1', '2', '3', '4', '5', '6', '7', '8', '9', '0', '←'],
                ['q', 'w', 'e', 'r', 't', 'y', 'u', 'i', 'o', 'p'],
                ['a', 's', 'd', 'f', 'g', 'h', 'j', 'k', 'l'],
                ['⇧', 'z', 'x', 'c', 'v', 'b', 'n', 'm', '⇧'],
                ['123', 'Space', '⌘', 'Done']
            ]
            
            self.symbols_layout = [
                ['!', '@', '#', '$', '%', '^', '&', '*', '(', ')', '←'],
                ['-', '_', '=', '+', '[', ']', '{', '}', '\\', '|'],
                [';', ':', "'", '"', ',', '.', '<', '>', '/', '?'],
                ['~', '`', '', '', '', '', '', '', '~'],
                ['ABC', 'Space', '⌘', 'Done']
            ]

            self.keyboard_buttons = []
            self.create_keyboard_layout()

            print(f"Created enhanced keyboard with {len(self.keyboard_buttons)} buttons")

        except Exception as e:
            print(f"Error creating keyboard: {e}")
            import traceback
            traceback.print_exc()

    def create_keyboard_layout(self):
        """Create the keyboard layout based on current mode"""
        # Clear existing buttons
        for button in self.keyboard_buttons:
            button.deleteLater()
        self.keyboard_buttons = []
        
        # Force process pending deletions
        from PyQt5.QtWidgets import QApplication
        QApplication.processEvents()

        # Choose layout based on mode
        layout = self.symbols_layout if self.symbols_mode else self.letters_layout
        
        button_width = 55
        button_height = 30
        start_x = 10
        start_y = 10

        for row_idx, row in enumerate(layout):
            for col_idx, key in enumerate(row):
                if not key:  # Skip empty keys
                    continue
                    
                # Calculate position
                if row_idx == 4:  # Bottom row with special keys
                    if key == 'Space':
                        x = start_x + 50
                        width = button_width * 4
                    elif key in ['123', 'ABC']:
                        x = start_x
                        width = button_width
                    elif key == '⌘':  # Caps lock
                        x = start_x + 50 + (button_width * 4) + 5
                        width = button_width
                    else:  # Done
                        x = start_x + 50 + (button_width * 5) + 10
                        width = button_width * 2
                elif row_idx == 3 and key == '⇧':  # Shift keys
                    if col_idx == 0:  # Left shift
                        x = start_x
                        width = button_width
                    else:  # Right shift
                        x = start_x + (len(row) - 1) * (button_width + 2)
                        width = button_width
                else:
                    x = start_x + col_idx * (button_width + 2)
                    width = button_width
                    if key == '←':
                        width = button_width + 15
                
                y = start_y + row_idx * (button_height + 3)

                # Create button
                button = QPushButton(self.get_display_key(key), self.keyboard_widget)
                button.setGeometry(x, y, width, button_height)
                button.setFont(QFont('Proxima Nova', 9))
                
                # Style special keys differently
                if key in ['Done', '←', 'Space', '⇧', '123', 'ABC', '⌘']:
                    if key == '⇧' and (self.shift_active or self.caps_lock):
                        # Highlight active shift/caps
                        button.setStyleSheet("""
                            background-color: #4a90e2;
                            color: white;
                            border-radius: 5px;
                            font-weight: bold;
                        """)
                    elif key == '⌘' and self.caps_lock:
                        # Highlight caps lock
                        button.setStyleSheet("""
                            background-color: #e74c3c;
                            color: white;
                            border-radius: 5px;
                            font-weight: bold;
                        """)
                    else:
                        button.setStyleSheet("""
                            background-color: #666;
                            color: white;
                            border-radius: 5px;
                            font-weight: bold;
                        """)
                else:
                    button.setStyleSheet("""
                        background-color: white;
                        border: 1px solid #ccc;
                        border-radius: 5px;
                    """)
                
                # Connect button to handler
                button.clicked.connect(partial(self.keyboard_key_pressed, key))
                self.keyboard_buttons.append(button)
                
                # Ensure button is visible if keyboard is visible
                if self.keyboard_visible:
                    button.show()

    def get_display_key(self, key):
        """Get the display text for a key based on current state"""
        if key == '⌘':
            return 'CAPS' if self.caps_lock else 'caps'
        elif key == '123':
            return '123'
        elif key == 'ABC':
            return 'ABC'
        elif key == '⇧':
            return '⇧'
        elif key in ['←', 'Space', 'Done']:
            return key
        elif not self.symbols_mode and key.isalpha():
            if self.caps_lock or self.shift_active:
                return key.upper()
            else:
                return key.lower()
        else:
            return key

    def keyboard_key_pressed(self, key):
        """Handle enhanced keyboard key press"""
        try:
            if not self.current_input:
                return

            current_text = self.current_input.text()

            if key == '←':  # Backspace
                self.current_input.setText(current_text[:-1])
                
            elif key == 'Space':
                self.current_input.setText(current_text + ' ')
                
            elif key == 'Done':
                self.toggle_keyboard()
                
            elif key == '⇧':  # Shift
                if self.caps_lock:
                    # If caps lock is on, shift toggles it off
                    self.caps_lock = False
                    self.shift_active = False
                else:
                    # Toggle shift
                    self.shift_active = not self.shift_active
                # Update keyboard layout while preserving visibility
                self.update_keyboard_layout()
                
            elif key == '⌘':  # Caps Lock
                self.caps_lock = not self.caps_lock
                self.shift_active = False  # Reset shift when caps lock changes
                # Update keyboard layout while preserving visibility
                self.update_keyboard_layout()
                
            elif key == '123':  # Switch to symbols
                self.symbols_mode = True
                # Update keyboard layout while preserving visibility
                self.update_keyboard_layout()
                
            elif key == 'ABC':  # Switch to letters
                self.symbols_mode = False
                # Update keyboard layout while preserving visibility
                self.update_keyboard_layout()
                
            else:  # Regular character
                char_to_add = key
                
                # Apply case transformation for letters
                if not self.symbols_mode and key.isalpha():
                    if self.caps_lock or self.shift_active:
                        char_to_add = key.upper()
                    else:
                        char_to_add = key.lower()
                
                self.current_input.setText(current_text + char_to_add)
                
                # Reset shift after character (but not caps lock)
                if self.shift_active and not self.caps_lock:
                    self.shift_active = False
                    # Update keyboard layout while preserving visibility
                    self.update_keyboard_layout()

        except Exception as e:
            print(f"Error in keyboard_key_pressed: {e}")

    def update_keyboard_layout(self):
        """Update keyboard layout while preserving visibility state"""
        try:
            # Store current visibility state
            was_visible = self.keyboard_visible and self.keyboard_widget.isVisible()
            
            # Recreate the layout
            self.create_keyboard_layout()
            
            # Restore visibility if it was visible before
            if was_visible:
                self.keyboard_widget.setVisible(True)
                self.keyboard_widget.show()
                
        except Exception as e:
            print(f"Error in update_keyboard_layout: {e}")

    def toggle_keyboard(self):
        """Toggle on-screen keyboard visibility"""
        try:
            print(f"Toggle keyboard called, current visibility: {getattr(self, 'keyboard_visible', False)}")
            
            if not hasattr(self, 'keyboard_visible'):
                self.keyboard_visible = False
            
            self.keyboard_visible = not self.keyboard_visible
            print(f"Setting keyboard visibility to: {self.keyboard_visible}")
            
            if hasattr(self, 'keyboard_widget'):
                self.keyboard_widget.setVisible(self.keyboard_visible)
                print(f"Keyboard widget visibility set to: {self.keyboard_visible}")
            else:
                print("ERROR: keyboard_widget not found!")
                return
                
            if self.keyboard_visible:
                self.keyboard_button.setText("📱 Hide Keyboard")
                self.setFixedSize(800, 620)
                print("Dialog resized to 800x620")
                
                # Move other elements up to make room
                self.current_connection_label.setGeometry(50, 360, 700, 25)
                self.current_connection_info.setGeometry(50, 385, 700, 30)
                
                # Set current input focus
                if not self.current_input:
                    self.current_input = self.network_name_input
                    print("Set default current_input to network_name_input")
            else:
                self.keyboard_button.setText("📱 Show Keyboard")
                self.setFixedSize(800, 600)
                print("Dialog resized to 800x600")
                
                # Move elements back to original positions
                self.current_connection_label.setGeometry(50, 420, 700, 25)
                self.current_connection_info.setGeometry(50, 445, 700, 60)

        except Exception as e:
            print(f"Error toggling keyboard: {e}")
            import traceback
            traceback.print_exc()

    def toggle_password_visibility(self):
        """Toggle password visibility"""
        try:
            if self.show_password_checkbox.isChecked():
                self.password_input.setEchoMode(QLineEdit.Normal)
                self.show_password_checkbox.setText("🙈 Hide Password")
            else:
                self.password_input.setEchoMode(QLineEdit.Password)
                self.show_password_checkbox.setText("👁 Show Password")
        except Exception as e:
            print(f"Error toggling password visibility: {e}")

    def scan_wifi_networks(self):
        """Scan for available WiFi networks using multiple methods"""
        try:
            self.status_label.setText("Scanning for WiFi networks...")
            self.networks_list.clear()
            self.refresh_button.setEnabled(False)

            # Try different methods to scan for networks
            networks_found = False
            
            # Method 1: Try nmcli first (NetworkManager)
            try:
                result = subprocess.run(['nmcli', '--version'], 
                                      capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    # NetworkManager is available, try scanning
                    result = subprocess.run(['nmcli', 'dev', 'wifi', 'rescan'], 
                                          capture_output=True, text=True, timeout=10)
                    time.sleep(2)  # Wait for scan to complete

                    # Use standard nmcli output 
                    result = subprocess.run(['nmcli', 'dev', 'wifi', 'list'], 
                                          capture_output=True, text=True, timeout=10)

                    if result.returncode == 0:
                        self.parse_wifi_networks(result.stdout)
                        networks_found = True
                    else:
                        print(f"nmcli scan failed: {result.stderr}")
            except Exception as e:
                print(f"nmcli not available or failed: {e}")

            # Method 2: Try iwlist if nmcli failed
            if not networks_found:
                try:
                    # First, try to find wireless interface
                    result = subprocess.run(['iwconfig'], capture_output=True, text=True, timeout=5)
                    wireless_interface = None
                    
                    for line in result.stdout.split('\n'):
                        if 'IEEE 802.11' in line:
                            wireless_interface = line.split()[0]
                            break
                    
                    if wireless_interface:
                        # Scan using iwlist
                        result = subprocess.run(['sudo', 'iwlist', wireless_interface, 'scan'], 
                                              capture_output=True, text=True, timeout=15)
                        
                        if result.returncode == 0:
                            self.parse_iwlist_networks(result.stdout)
                            networks_found = True
                        else:
                            print(f"iwlist scan failed: {result.stderr}")
                    else:
                        print("No wireless interface found")
                        
                except Exception as e:
                    print(f"iwlist method failed: {e}")

            # Method 3: Try iw command if iwlist failed
            if not networks_found:
                try:
                    # Find wireless interface using ip command
                    result = subprocess.run(['ip', 'link', 'show'], capture_output=True, text=True, timeout=5)
                    wireless_interface = None
                    
                    for line in result.stdout.split('\n'):
                        if 'wlan' in line or 'wlp' in line:
                            wireless_interface = line.split(':')[1].strip()
                            break
                    
                    if wireless_interface:
                        # Scan using iw
                        result = subprocess.run(['sudo', 'iw', wireless_interface, 'scan'], 
                                              capture_output=True, text=True, timeout=15)
                        
                        if result.returncode == 0:
                            self.parse_iw_networks(result.stdout)
                            networks_found = True
                        else:
                            print(f"iw scan failed: {result.stderr}")
                            
                except Exception as e:
                    print(f"iw method failed: {e}")

            if not networks_found:
                self.status_label.setText("Unable to scan networks - trying manual connection")
                self.networks_list.setHtml("""
                    <h3>Network Scanning Failed</h3>
                    <p><b>NetworkManager not running or wireless tools unavailable.</b></p>
                    <p>You can still try to connect manually:</p>
                    <ol>
                        <li>Enter the network name (SSID) manually</li>
                        <li>Enter the password</li>
                        <li>Click Connect to try connecting</li>
                    </ol>
                    <p><b>Alternative methods to enable NetworkManager:</b></p>
                    <ul>
                        <li><code>sudo systemctl start NetworkManager</code></li>
                        <li><code>sudo systemctl enable NetworkManager</code></li>
                    </ul>
                """)

        except Exception as e:
            print(f"Error in scan_wifi_networks: {e}")
            self.status_label.setText("Scan failed - manual connection available")
            self.networks_list.setText(f"Error scanning: {e}\n\nYou can still enter network details manually.")
        finally:
            self.refresh_button.setEnabled(True)

    def parse_wifi_networks(self, nmcli_output):
        """Parse nmcli output and display networks"""
        try:
            lines = nmcli_output.strip().split('\n')
            if len(lines) < 2:
                self.networks_list.setText("No networks found")
                return

            networks_html = "<h3>Available Networks:</h3>"
            self.available_networks = []
            
            for line in lines[1:]:  # Skip header
                if not line.strip():
                    continue
                    
                try:
                    # Check if currently connected (starts with *)
                    is_connected = line.strip().startswith('*')
                    
                    if is_connected:
                        line_without_star = line[1:].strip()
                        parts = line_without_star.split()
                    else:
                        parts = line.split()
                    
                    if len(parts) < 8:
                        continue
                    
                    ssid = parts[1]
                    signal = parts[5] if len(parts) > 5 else 'Unknown'
                    security = parts[7] if len(parts) > 7 else 'Unknown'
                    
                    ssid = ssid.strip()
                    if not ssid or ssid == '--' or ssid == 'SSID':
                        continue
                    
                    if ssid.startswith('<') and ssid.endswith('>'):
                        continue
                    
                    if is_connected:
                        networks_html += f"<p><b>🟢 {ssid}</b> (Connected)<br/>Signal: {signal}, Security: {security}</p><hr/>"
                    else:
                        networks_html += f"<p><b>{ssid}</b><br/>Signal: {signal}, Security: {security}</p><hr/>"
                        self.available_networks.append({
                            'ssid': ssid,
                            'signal': signal,
                            'security': security
                        })
                        
                except Exception as e:
                    print(f"Error parsing line '{line}': {e}")
                    continue

            self.networks_list.setHtml(networks_html)
            self.status_label.setText(f"Found {len(self.available_networks)} networks. Click a network name to select it.")
            self.networks_list.mousePressEvent = self.network_clicked

        except Exception as e:
            print(f"Error parsing networks: {e}")
            self.networks_list.setText(f"Error parsing networks: {e}")

    def network_clicked(self, event):
        """Handle network selection from list"""
        try:
            cursor = self.networks_list.cursorForPosition(event.pos())
            cursor.select(cursor.WordUnderCursor)
            selected_text = cursor.selectedText()
                
            for network in self.available_networks:
                if network['ssid'] in selected_text or selected_text in network['ssid']:
                    self.network_name_input.setText(network['ssid'])
                    self.status_label.setText(f"Selected: {network['ssid']} - Enter password and click Connect")
                    break
                        
        except Exception as e:
            print(f"Error in network selection: {e}")

    def check_current_connection(self):
        """Check current WiFi connection status"""
        try:
            result = subprocess.run(['nmcli', 'connection', 'show', '--active'], 
                                  capture_output=True, text=True, timeout=5)
                
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                wifi_connections = [line for line in lines if 'wifi' in line.lower()]
                    
                if wifi_connections:
                    connection_info = wifi_connections[0].split()
                    if len(connection_info) >= 1:
                        network_name = connection_info[0]
                        self.current_connection_info.setText(f"✅ Connected to: {network_name}")
                    else:
                        self.current_connection_info.setText("✅ WiFi connected")
                else:
                    self.current_connection_info.setText("❌ Not connected to WiFi")
            else:
                self.current_connection_info.setText("❓ Unable to check connection status")
                    
        except Exception as e:
            print(f"Error checking connection: {e}")
            self.current_connection_info.setText(f"❓ Error checking connection: {e}")

    def parse_iwlist_networks(self, iwlist_output):
        """Parse iwlist scan output"""
        try:
            networks_html = "<h3>Available Networks (iwlist):</h3>"
            self.available_networks = []
            
            current_network = {}
            
            for line in iwlist_output.split('\n'):
                line = line.strip()
                
                if 'ESSID:' in line:
                    essid = line.split('ESSID:')[1].strip().strip('"')
                    if essid and essid != '<hidden>':
                        current_network['ssid'] = essid
                
                elif 'Quality=' in line and 'Signal level=' in line:
                    parts = line.split()
                    for part in parts:
                        if 'Quality=' in part:
                            quality = part.split('=')[1]
                            current_network['signal'] = quality
                            break
                
                elif 'Encryption key:' in line:
                    if 'off' in line:
                        current_network['security'] = 'Open'
                    else:
                        current_network['security'] = 'Secured'
                
                elif line.startswith('Cell ') and current_network.get('ssid'):
                    self.available_networks.append(current_network.copy())
                    networks_html += f"<p><b>{current_network['ssid']}</b><br/>"
                    networks_html += f"Signal: {current_network.get('signal', 'Unknown')}, "
                    networks_html += f"Security: {current_network.get('security', 'Unknown')}</p><hr/>"
                    current_network = {}
            
            # Don't forget the last network
            if current_network.get('ssid'):
                self.available_networks.append(current_network)
                networks_html += f"<p><b>{current_network['ssid']}</b><br/>"
                networks_html += f"Signal: {current_network.get('signal', 'Unknown')}, "
                networks_html += f"Security: {current_network.get('security', 'Open')}</p><hr/>"
            
            self.networks_list.setHtml(networks_html)
            self.status_label.setText(f"Found {len(self.available_networks)} networks (iwlist). Click a network to select.")
            self.networks_list.mousePressEvent = self.network_clicked
            
        except Exception as e:
            print(f"Error parsing iwlist output: {e}")

    def parse_iw_networks(self, iw_output):
        """Parse iw scan output"""
        try:
            networks_html = "<h3>Available Networks (iw):</h3>"
            self.available_networks = []

            current_network = {}

            for line in iw_output.split('\n'):
                line = line.strip()

                if line.startswith('BSS '):
                    # New network entry
                    if current_network.get('ssid'):
                        self.available_networks.append(current_network.copy())
                        networks_html += f"<p><b>{current_network['ssid']}</b><br/>"
                        networks_html += f"Signal: {current_network.get('signal', 'Unknown')}, "
                        networks_html += f"Security: {current_network.get('security', 'Unknown')}</p><hr/>"
                    current_network = {}

                elif line.startswith('SSID: '):
                    ssid = line.split('SSID: ')[1].strip()
                    if ssid:
                        current_network['ssid'] = ssid

                elif 'signal:' in line:
                    signal = line.split('signal:')[1].strip().split()[0]
                    current_network['signal'] = signal

                elif 'Privacy' in line or 'RSN:' in line or 'WPA:' in line:
                    current_network['security'] = 'Secured'

            # Don't forget the last network
            if current_network.get('ssid'):
                self.available_networks.append(current_network)
                networks_html += f"<p><b>{current_network['ssid']}</b><br/>"
                networks_html += f"Signal: {current_network.get('signal', 'Unknown')}, "
                networks_html += f"Security: {current_network.get('security', 'Unknown')}</p><hr/>"

            self.networks_list.setHtml(networks_html)
            self.status_label.setText(f"Found {len(self.available_networks)} networks (iw). Click a network to select.")
            self.networks_list.mousePressEvent = self.network_clicked

        except Exception as e:
            print(f"Error parsing iw output: {e}")

    def connect_to_wifi(self):
        """Connect to the selected WiFi network with multiple methods"""
        try:
            ssid = self.network_name_input.text().strip()
            password = self.password_input.text().strip()

            if not ssid:
                QMessageBox.warning(self, "Missing Information", "Please enter a network name (SSID)")
                return

            self.status_label.setText("Connecting to WiFi...")
            self.connect_button.setEnabled(False)
            self.connect_button.setText("Connecting...")

            connected = False

            # Method 1: Try nmcli first (NetworkManager)
            try:
                result = subprocess.run(['nmcli', '--version'], capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    if password:
                        result = subprocess.run([
                            'nmcli', 'dev', 'wifi', 'connect', ssid, 'password', password
                        ], capture_output=True, text=True, timeout=30)
                    else:
                        result = subprocess.run([
                            'nmcli', 'dev', 'wifi', 'connect', ssid
                        ], capture_output=True, text=True, timeout=30)

                    if result.returncode == 0:
                        connected = True
                        self.status_label.setText("✅ Connected via NetworkManager!")
                    else:
                        print(f"nmcli connection failed: {result.stderr}")
            except Exception as e:
                print(f"nmcli connection attempt failed: {e}")

            # Method 2: Try wpa_supplicant method if nmcli failed
            if not connected:
                try:
                    self.status_label.setText("Trying wpa_supplicant method...")
                    
                    # Create wpa_supplicant config
                    if password:
                        wpa_config = f'''
network={{
    ssid="{ssid}"
    psk="{password}"
}}
'''
                    else:
                        wpa_config = f'''
network={{
    ssid="{ssid}"
    key_mgmt=NONE
}}
'''
                    
                    # Write config to temporary file
                    with open('/tmp/wpa_temp.conf', 'w') as f:
                        f.write(wpa_config)
                    
                    # Find wireless interface
                    result = subprocess.run(['ip', 'link', 'show'], capture_output=True, text=True, timeout=5)
                    wireless_interface = None
                    
                    for line in result.stdout.split('\n'):
                        if 'wlan' in line or 'wlp' in line:
                            wireless_interface = line.split(':')[1].strip()
                            break
                    
                    if wireless_interface:
                        # Try to connect using wpa_supplicant
                        result = subprocess.run([
                            'sudo', 'wpa_supplicant', '-B', '-i', wireless_interface, 
                            '-c', '/tmp/wpa_temp.conf'
                        ], capture_output=True, text=True, timeout=15)
                        
                        if result.returncode == 0:
                            # Get IP address
                            time.sleep(3)
                            result = subprocess.run([
                                'sudo', 'dhclient', wireless_interface
                            ], capture_output=True, text=True, timeout=10)
                            
                            connected = True
                            self.status_label.setText("✅ Connected via wpa_supplicant!")
                        else:
                            print(f"wpa_supplicant failed: {result.stderr}")
                    
                    # Clean up temp file
                    try:
                        subprocess.run(['rm', '/tmp/wpa_temp.conf'], timeout=5)
                    except:
                        pass
                        
                except Exception as e:
                    print(f"wpa_supplicant method failed: {e}")

            if connected:
                QMessageBox.information(self, "Success", f"Successfully connected to {ssid}")
                self.check_current_connection()
                
                # Option to close dialog
                reply = QMessageBox.question(self, "Connection Successful", 
                                          "WiFi connected successfully! Close this wizard?",
                                          QMessageBox.Yes | QMessageBox.No)
                if reply == QMessageBox.Yes:
                    self.accept()
            else:
                self.status_label.setText("❌ All connection methods failed")
                QMessageBox.warning(self, "Connection Failed", 
                                  f"Could not connect to {ssid}.\n\n"
                                  f"Possible solutions:\n"
                                  f"• Check password is correct\n"
                                  f"• Enable NetworkManager: sudo systemctl start NetworkManager\n"
                                  f"• Check network is in range\n"
                                  f"• Try connecting manually via command line")

        except Exception as e:
            print(f"Error connecting to WiFi: {e}")
            QMessageBox.critical(self, "Error", f"Error connecting to WiFi:\n{e}")
        finally:
            self.connect_button.setEnabled(True)
            self.connect_button.setText("Connect to WiFi")

    def showEvent(self, event):
        """Start network scan when dialog is shown"""
        super().showEvent(event)
        QTimer.singleShot(0, self.scan_wifi_networks)


# Example usage and testing
if __name__ == '__main__':
    import sys
    from PyQt5.QtWidgets import QApplication, QDialog

    app = QApplication(sys.argv)

    # Create and show the WiFi wizard
    wifi_wizard = WiFiWizardDialog()
    result = wifi_wizard.exec_()

    if result == QDialog.Accepted:
        print("WiFi wizard completed successfully")
    else:
        print("WiFi wizard was cancelled")

    sys.exit()