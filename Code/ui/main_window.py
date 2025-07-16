# Main Window 
import re
import sys
import os

from ui.dialogs.wifi_wizard import WiFiWizardDialog
from PyQt5.QtGui import QIcon, QPixmap
from ui.dialogs.calibration import CalibrationDialog
from PyQt5.QtWidgets import (QMainWindow, QPushButton, QLineEdit, QTextEdit, QLabel, QMessageBox, QFileDialog, QDialog, QWidget)
from PyQt5.QtGui import QFont
from PyQt5.QtCore import QTimer, pyqtSignal, QSize, Qt

# Auto-updater import (add this)
try:
    from utils.auto_updater import AutoUpdater
    AUTO_UPDATER_AVAILABLE = True
except ImportError:
    print("Auto-updater not available - continuing without it")
    AUTO_UPDATER_AVAILABLE = False

from config.constants import (APP_TITLE, APP_WIDTH, APP_HEIGHT, MAIN_FONT, 
                             LARGE_FONT, BUTTON_FONT, NUMPAD_FONT, TERMINAL_FONT,
                             BUTTON_WIDTH, BUTTON_HEIGHT, BUTTON_SPACING,
                             NUMPAD_START_X, NUMPAD_START_Y, NUMPAD_BUTTONS,
                             MAX_MACHINE_DISTANCE, COLORS)
from communication.bluetooth import BluetoothManager

ASSETS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets")
WIFI_ICON_PATH = os.path.join(ASSETS_DIR, "wifi.png")
BLUETOOTH_ICON_PATH = os.path.join(ASSETS_DIR, "bluetooth.png")
CALIBRATE_ICON_PATH = os.path.join(ASSETS_DIR, "calibrate.png")


class FocusLineEdit(QLineEdit):
    """Custom QLineEdit that emits focused signal."""
    focused = pyqtSignal()

    def focusInEvent(self, e):
        super().focusInEvent(e)
        self.focused.emit()


class BluetoothSettingsWindow(QDialog):
    """Separate window for Bluetooth settings and controls."""
    
    def __init__(self, parent=None, bluetooth_manager=None):
        super().__init__(parent)
        self.bluetooth_manager = bluetooth_manager
        self.setWindowTitle("Bluetooth Settings")
        self.setFixedSize(400, 300)
        self._init_ui()
        self._connect_signals()
    
    def _init_ui(self):
        """Initialize the Bluetooth settings UI."""
        # Bluetooth device input
        self.bt_device_input = QLineEdit(self)
        self.bt_device_input.setGeometry(10, 20, 280, 40)
        self.bt_device_input.setFont(MAIN_FONT)
        self.bt_device_input.setPlaceholderText("ESP32 Bluetooth Name/Address")
        self.bt_device_input.setText("FluidNC")
        
        # Scan button
        self.scan_bt_button = QPushButton('Scan BT', self)
        self.scan_bt_button.setGeometry(300, 20, 90, 40)
        self.scan_bt_button.setFont(MAIN_FONT)
        self.scan_bt_button.clicked.connect(self._scan_bluetooth)
        
        # Connection buttons
        self.connect_button = QPushButton('Connect BT', self)
        self.connect_button.setGeometry(10, 80, 120, 45)
        self.connect_button.setFont(MAIN_FONT)
        self.connect_button.clicked.connect(self._connect_bluetooth)
        
        self.disconnect_button = QPushButton('Disconnect BT', self)
        self.disconnect_button.setGeometry(140, 80, 120, 45)
        self.disconnect_button.setFont(MAIN_FONT)
        self.disconnect_button.clicked.connect(self._disconnect_bluetooth)
        self.disconnect_button.setEnabled(False)
        
        # Terminal output
        self.terminal_output = QTextEdit(self)
        self.terminal_output.setReadOnly(True)
        self.terminal_output.setGeometry(10, 140, 380, 120)
        self.terminal_output.setFont(TERMINAL_FONT)
        
        # Close button
        self.close_button = QPushButton('Close', self)
        self.close_button.setGeometry(270, 80, 120, 45)
        self.close_button.setFont(MAIN_FONT)
        self.close_button.clicked.connect(self.close)
    
    def _connect_signals(self):
        """Connect Bluetooth manager signals."""
        if self.bluetooth_manager:
            self.bluetooth_manager.message_received.connect(self.append_to_terminal)
            self.bluetooth_manager.connection_status_changed.connect(self._on_bluetooth_status_changed)
            self.bluetooth_manager.device_found.connect(self._on_device_found)
    
    def _scan_bluetooth(self):
        """Start Bluetooth device scan."""
        if self.bluetooth_manager:
            self.bluetooth_manager.scan_devices()
            self.append_to_terminal("Scanning for Bluetooth devices...")
    
    def _connect_bluetooth(self):
        """Connect to Bluetooth device."""
        if self.bluetooth_manager:
            device = self.bt_device_input.text() or "FluidNC"
            self.bluetooth_manager.connect(device)
            self.append_to_terminal(f"Attempting to connect to: {device}")
    
    def _disconnect_bluetooth(self):
        """Disconnect from Bluetooth device."""
        if self.bluetooth_manager:
            self.bluetooth_manager.disconnect()
            self.append_to_terminal("Disconnecting from Bluetooth device...")
    
    def _on_bluetooth_status_changed(self, connected, info):
        """Handle Bluetooth connection status changes."""
        self.disconnect_button.setEnabled(connected)
        self.connect_button.setEnabled(not connected)
        
        if connected:
            self.append_to_terminal(f"Connected: {info}")
        else:
            self.append_to_terminal("Disconnected from Bluetooth device")
    
    def _on_device_found(self, name, address):
        """Handle discovered Bluetooth device."""
        self.append_to_terminal(f"Found device: {name} ({address})")
        if "FluidNC" in name or "ESP32" in name:
            self.bt_device_input.setText(address)
    
    def append_to_terminal(self, message):
        """Append message to terminal output."""
        self.terminal_output.append(message)
        scrollbar = self.terminal_output.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())


class MakerStopController(QMainWindow):
    """Main MakerStop Controller window with all original features."""
    
    def __init__(self):
        super().__init__()
        self._init_window()
        self._init_variables()
        self._init_ui()
        self._connect_signals()
        self._attempt_auto_connect()
        
        # Initialize auto-updater
        self._init_auto_updater()

    def _init_window(self):
        """Initialize main window properties."""
        self.setWindowTitle(APP_TITLE)
        self.setGeometry(0, 0, APP_WIDTH, APP_HEIGHT)
        self.setFixedSize(APP_WIDTH, APP_HEIGHT)
        # Set up central widget for background color
        central = QWidget(self)
        central.setStyleSheet("background-color: #222428;")
        self.setCentralWidget(central)
        
    def _init_variables(self):
        """Initialize instance variables."""
        self.bluetooth_manager = BluetoothManager()
        self.start_pressed = False
        self.cut_list_settings_visible = False
        self.current_input_target = None
        self.bluetooth_settings_window = None
        
        # Cut list management
        self.cutList = []
        self.currentIndex = -1

    def _init_auto_updater(self):
        """Initialize the auto-updater"""
        try:
            if AUTO_UPDATER_AVAILABLE:
                print("Initializing auto-updater...")
                self.auto_updater = AutoUpdater(self)
                
                # Check for updates on startup (after UI is fully loaded)
                self.auto_updater.check_on_startup()
            else:
                self.auto_updater = None
                print("Auto-updater not available")
                
        except Exception as e:
            print(f"Failed to initialize auto-updater: {e}")
            # Don't let updater failure crash the app
            self.auto_updater = None

    def _init_ui(self):
        """Initialize all UI components."""
        self._create_input_fields()
        self._create_cut_list_panel()
        self._create_control_buttons()
        self._create_numpad()
        self._create_settings_buttons()
        
        # Set initial visibility
        self._toggle_cut_list_settings()

    def _create_input_fields(self):
        """Create measurement input field."""
        # Main measurement input
        self.measurement_input = self._create_focus_line_edit(
            10, 50, 375, 150, LARGE_FONT, "0.00mm",
        )

        self.measurement_input.setStyleSheet(
            """
            QLineEdit {
                background-color: #303236;
                color: white;
                border-radius: 10px;
            }
            QLineEdit::placeholder {
                color: white;
            }
            """
        )
        
        # Add "MakerStop" label at the top left
        self.makerstop_label = QLabel("MakerStop", self)
        self.makerstop_label.setStyleSheet("color: white; font-size: 28pt; font-weight: bold;")
        self.makerstop_label.setGeometry(10, 5, 250, 40)

        self.measurement_input.focused.connect(
            lambda: self.set_current_input_target(self.measurement_input)
        )

        # Set default target
        self.set_current_input_target(self.measurement_input)

    def _create_cut_list_panel(self):
        """Create cut list display and controls."""
        self.cut_list_panel = QWidget(self)
        self.cut_list_panel.setGeometry(390, 50, 205, 245)
        self.cut_list_panel.setStyleSheet("background-color: #303236; border-radius: 10px;")

        # Cut list display
        self.cutListDisplay = QTextEdit(self.cut_list_panel)
        self.cutListDisplay.setReadOnly(False)
        self.cutListDisplay.setFont(MAIN_FONT)
        self.cutListDisplay.setPlaceholderText("")
        self.cutListDisplay.setStyleSheet("color: white; background: transparent;")

        # Cut list control buttons
        self.loadCutListButton = self._create_button(
            'Load Cut List', 600, 50, self.openFileDialog, 190, 50, BUTTON_FONT
        )
        self.loadCutListButton.setStyleSheet("""
            background-color: #303236;
            color: white;
            border-radius: 10px;
            font-size: 10pt;
        }
        QPushButton:pressed {
            background-color: #d3d3d3;
            color: black;
        }
        """)

        self.prevButton = self._create_button(
            'Previous Cut', 600, 215, self.prevCut, 190, 50, BUTTON_FONT
        )
        self.prevButton.setStyleSheet("""
            background-color: #303236;
            color: white;
            border-radius: 10px;
            font-size: 10pt;
        }
        QPushButton:pressed {
            background-color: #d3d3d3;
            color: black;
        }
        """)

        self.nextButton = self._create_button(
            'Next Cut', 600, 160, self.nextCut, 190, 50, BUTTON_FONT
        )
        self.nextButton.setStyleSheet("""
            background-color: #303236;
            color: white;
            border-radius: 10px;
            font-size: 10pt;
        }
        QPushButton:pressed {
            background-color: #d3d3d3;
            color: black;
        }
        """)

        self.clearCutListButton = self._create_button(
            'Clear Cut List', 600, 105, self.clearCutList, 190, 50, BUTTON_FONT
        )
        self.clearCutListButton.setStyleSheet("""
            background-color: #303236;
            color: white;
            border-radius: 10px;
            font-size: 10pt;
        }
        QPushButton:pressed {
            background-color: #d3d3d3;
            color: black;
        }
        """)

    def _create_control_buttons(self):
        """Create main control buttons."""
        # Main control buttons
        self.homing_button = self._create_button(
            'Home', 600, 275, self.homing_command, 190, 90, BUTTON_FONT
        )
        self.homing_button.setEnabled(False)
        self.homing_button.setStyleSheet(f"""
            background-color: {COLORS['warning']};
            color: white;
            border-radius: 10px;
            font-size: {BUTTON_FONT.pointSize()}pt;
        }}
        QPushButton:pressed {{
            background-color: #d3d3d3;
            color: black;
        }}
        """)

        self.stop_button = self._create_button(
            'Stop', 600, 375, self.stop_command, 190, 100, BUTTON_FONT
        )
        self.stop_button.setEnabled(False)
        self.stop_button.setStyleSheet(f"""
            background-color: {COLORS['danger']};
            color: white;
            border-radius: 10px;
            font-size: {BUTTON_FONT.pointSize()}pt;
        }}
        QPushButton:pressed {{
            background-color: #d3d3d3;
            color: black;
        }}
        """)

        self.start_button = self._create_button(
            'Start', 600, 485, self.start_command, 190, 100, BUTTON_FONT
        )
        self.start_button.setStyleSheet(f"""
            background-color: {COLORS['success']};
            color: white;
            border-radius: 10px;
            font-size: {BUTTON_FONT.pointSize()}pt;
        }}
        QPushButton:pressed {{
            background-color: #d3d3d3;
            color: black;
        }}
        """)

        # Utility buttons
        self.calibrate_button = self._create_button(
            '', 700, 0, self.start_calibration, 40, 50, MAIN_FONT
        )
        self.calibrate_button.setIcon(QIcon(CALIBRATE_ICON_PATH))
        self.calibrate_button.setIconSize(QSize(32, 32))
        self.calibrate_button.setStyleSheet("""
            background-color: #222428;
            color: white;
            border-radius: 10px;
        }
        QPushButton:pressed {
            background-color: #d3d3d3;
            color: black;
        }
        """)

        self.wifi_button = self._create_button(
            '', 750, 0, self.start_wifi_wizard, 40, 50, MAIN_FONT
        )
        self.wifi_button.setIcon(QIcon(WIFI_ICON_PATH))
        self.wifi_button.setIconSize(QSize(32, 32))
        self.wifi_button.setStyleSheet("""
            background-color: #222428;
            color: white;
            border-radius: 10px;
        }
        QPushButton:pressed {
            background-color: #d3d3d3;
            color: black;
        }
        """)

    def _create_numpad(self):
        """Create calculator numpad."""
        self.button_objects = {}
        
        for btn_text, pos in NUMPAD_BUTTONS:
            button = QPushButton(btn_text, self)
            button.setObjectName(btn_text)
            
            # Calculate position
            button_x = NUMPAD_START_X + (BUTTON_WIDTH + BUTTON_SPACING) * pos[1]
            button_y = NUMPAD_START_Y + (BUTTON_HEIGHT + BUTTON_SPACING) * pos[0]
            
            # Set geometry based on button type
            if btn_text == "=":
                button.setGeometry(button_x, button_y, BUTTON_WIDTH * 2 + BUTTON_SPACING, BUTTON_HEIGHT)
                button.setStyleSheet(f"""
                    background-color: {COLORS['info']};
                    color: white;
                    border-radius: 10px;
                    font-size: {NUMPAD_FONT.pointSize()}pt;
                    font-weight: bold;
                """)
            else:
                button.setGeometry(button_x, button_y, BUTTON_WIDTH, BUTTON_HEIGHT)
                button.setStyleSheet("""
                    background-color: #303236;
                    color: white;
                    border-radius: 10px;
                    font-size: 18pt;
                }
                QPushButton:pressed {
                    background-color: #d3d3d3;
                    color: black;
                }
                """)

            button.clicked.connect(lambda checked, text=btn_text: self.on_calculator_button_clicked(text))
            self.button_objects[btn_text] = button

    def _create_settings_buttons(self):
        """Create settings toggle buttons."""
        self.bluetooth_settings_button = self._create_button(
            '', 650, 0, self.open_bluetooth_settings, 40, 50, MAIN_FONT
        )
        self.bluetooth_settings_button.setIcon(QIcon(BLUETOOTH_ICON_PATH))
        self.bluetooth_settings_button.setIconSize(QSize(32, 32))
        self.bluetooth_settings_button.setStyleSheet("""
            background-color: #222428;
            color: white;
            border-radius: 10px;
        }
        QPushButton:pressed {
            background-color: #d3d3d3;
            color: black;
        }
        """)

        # ADD THIS: Manual update check button with visual feedback
        if AUTO_UPDATER_AVAILABLE:
            self.update_button = self._create_button(
                '🔄', 600, 0, self.manual_update_check, 40, 50, MAIN_FONT
            )
            self.update_button_default_style = """
                background-color: #222428;
                color: white;
                border-radius: 10px;
                font-size: 16pt;
            }
            QPushButton:pressed {
                background-color: #d3d3d3;
                color: black;
            }
            """
            
            self.update_button_checking_style = """
                background-color: #ffa500;
                color: white;
                border-radius: 10px;
                font-size: 16pt;
            }
            QPushButton:pressed {
                background-color: #d3d3d3;
                color: black;
            }
            """
            
            self.update_button.setStyleSheet(self.update_button_default_style)
            self.update_button.setToolTip("Check for updates")

    def set_update_status(self, status):
        """Set visual feedback for update checking status"""
        if not hasattr(self, 'update_button'):
            return
            
        if status == "checking":
            # Change button appearance when checking
            self.update_button.setText('⏳')
            self.update_button.setStyleSheet(self.update_button_checking_style)
            self.update_button.setEnabled(False)
            self.update_button.setToolTip("Checking for updates...")
            
        elif status == "idle":
            # Reset button to normal state
            self.update_button.setText('🔄')
            self.update_button.setStyleSheet(self.update_button_default_style)
            self.update_button.setEnabled(True)
            self.update_button.setToolTip("Check for updates")

    def manual_update_check(self):
        """Manually check for updates"""
        try:
            if hasattr(self, 'auto_updater') and self.auto_updater:
                self.append_to_terminal("🔍 Manually checking for updates...")
                self.auto_updater.check_for_updates(silent=False)
            else:
                self.append_to_terminal("❌ Auto-updater not available")
        except Exception as e:
            self.append_to_terminal(f"❌ Update check failed: {e}")

    def _connect_signals(self):
        """Connect signals between components."""
        self.bluetooth_manager.connection_status_changed.connect(self._on_bluetooth_status_changed)

    def _create_focus_line_edit(self, x, y, w, h, font, placeholder):
        """Create a FocusLineEdit with specified properties."""
        line_edit = FocusLineEdit(self)
        line_edit.setGeometry(x, y, w, h)
        line_edit.setFont(font)
        line_edit.setPlaceholderText(placeholder)
        return line_edit

    def _create_button(self, text, x, y, callback, w=100, h=45, font=MAIN_FONT):
        """Create a button with specified properties."""
        button = QPushButton(text, self)
        button.setGeometry(x, y, w, h)
        button.setFont(font)
        button.clicked.connect(callback)
        return button

    def set_current_input_target(self, target):
        """Set the target input field for calculator operations."""
        self.current_input_target = target

    def on_calculator_button_clicked(self, value):
        """Handle calculator button clicks."""
        if not self.current_input_target:
            return
            
        current_text = self.current_input_target.text()
        
        if value == 'C':  # Clear
            self.current_input_target.clear()
        elif value == '←':  # Backspace
            self.current_input_target.setText(current_text[:-1])
        elif value in {'+', '-', '*', '/', ':'}:  # Operators
            if current_text and current_text[-1] not in {'+', '-', '*', '/', ':'}:
                self.current_input_target.setText(current_text + value)
        elif value == '=':  # Calculate
            try:
                expression = current_text.replace(':', '/')
                result = eval(expression)
                self.current_input_target.setText(str(result))
            except Exception:
                self.current_input_target.setText("Error")
        else:  # Numbers and decimal point
            self.current_input_target.setText(current_text + value)

    # === Settings and UI Toggle Methods ===
    def open_bluetooth_settings(self):
        """Open Bluetooth settings window."""
        if self.bluetooth_settings_window is None:
            self.bluetooth_settings_window = BluetoothSettingsWindow(self, self.bluetooth_manager)
        
        self.bluetooth_settings_window.show()
        self.bluetooth_settings_window.raise_()
        self.bluetooth_settings_window.activateWindow()

    def _toggle_cut_list_settings(self):
        """Toggle cut list settings visibility."""
        self.cut_list_settings_visible = not self.cut_list_settings_visible

        self.cutListDisplay.setVisible(self.cut_list_settings_visible)
        self.loadCutListButton.setVisible(self.cut_list_settings_visible)
        self.prevButton.setVisible(self.cut_list_settings_visible)
        self.nextButton.setVisible(self.cut_list_settings_visible)
        self.clearCutListButton.setVisible(self.cut_list_settings_visible)

        self.update()

    # === Bluetooth Methods ===
    def _attempt_auto_connect(self):
        """Attempt automatic Bluetooth connection on startup."""
        self.bluetooth_manager.auto_connect()

    def _on_bluetooth_status_changed(self, connected, info):
        """Handle Bluetooth connection status changes."""
        self.homing_button.setEnabled(connected)
        self.stop_button.setEnabled(connected)
        self.start_button.setEnabled(True)

    # === CNC Command Methods ===
    def homing_command(self):
        """Send homing command to CNC."""
        reply = QMessageBox.question(
            self, 'Confirm Homing', 'Is the saw bed clear?',
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.send_command_to_cnc("$H")
            self.append_to_terminal("Homing command sent.")

    def stop_command(self):
        """Send emergency stop command to CNC."""
        self.send_command_to_cnc("M112")
        self.append_to_terminal("Emergency stop command sent.")

    def start_command(self):
        """Send start/move command to CNC."""
        measurement = self.measurement_input.text()
        try:
            value = float(measurement)
            if value > MAX_MACHINE_DISTANCE:
                QMessageBox.warning(
                    self, "Measurement Error",
                    f"The measurement exceeds the limit of {MAX_MACHINE_DISTANCE}mm."
                )
                return

            gcode_command = f"G0 X{value}"
            self.send_command_to_cnc(gcode_command)
            self.append_to_terminal(f"Move command sent: {gcode_command}")
            self.start_pressed = True

        except ValueError:
            self.append_to_terminal("Invalid measurement input")

    def send_command_to_cnc(self, command):
        """Send command to CNC via Bluetooth."""
        success = self.bluetooth_manager.send_command(command)
        if not success:
            self.append_to_terminal("Failed to send command - check connection")

    # === Cut List Methods ===
    def openFileDialog(self):
        """Open file dialog to load cut list."""
        filePath, _ = QFileDialog.getOpenFileName(
            self, "Open Cut List", "", "Text Files (*.txt);;All Files (*)"
        )
        if filePath:
            self.loadCutList(filePath)

    def loadCutList(self, filePath):
        """Load cut list from file."""
        try:
            with open(filePath, 'r') as file:
                self.cutList = [line.strip() for line in file.readlines()]
            self.currentIndex = -1
            self.findNextCutWithNumber(initial=True)
            self.append_to_terminal(f"Cut list loaded: {filePath}")
        except Exception as e:
            self.append_to_terminal(f"Error loading cut list: {e}")

    def findNextCutWithNumber(self, initial=False):
        """Find next cut that contains a number."""
        start_index = self.currentIndex + 1 if not initial else 0
        for i in range(start_index, len(self.cutList)):
            if re.search(r'\d+(\.\d+)?', self.cutList[i]):
                self.currentIndex = i
                self.displayCurrentCut()
                return
        if initial:
            self.append_to_terminal("No valid cuts found in the list.")

    def displayCurrentCut(self):
        """Display current cut in UI."""
        if 0 <= self.currentIndex < len(self.cutList):
            currentCut = self.cutList[self.currentIndex]
            match = re.search(r'\d+(\.\d+)?', currentCut)
            if match:
                measurement = match.group()
                self.measurement_input.setText(measurement)
            else:
                self.measurement_input.setText("")
        self.updateCutListDisplay()

    def updateCutListDisplay(self):
        """Update cut list display with highlighting."""
        content = ""
        for i, cut in enumerate(self.cutList):
            if i == self.currentIndex:
                content += f"<div style='background-color: orange;'>{cut}</div>"
            else:
                content += f"<div>{cut}</div>"
        self.cutListDisplay.setHtml(content)
        
        # Update scroll position
        scroll_position = self.calculateScrollPosition(self.currentIndex, len(self.cutList))
        self.cutListDisplay.verticalScrollBar().setValue(scroll_position)

    def calculateScrollPosition(self, currentIndex, totalCuts):
        """Calculate scroll position for current cut."""
        positionPercentage = currentIndex / totalCuts if totalCuts else 0
        maxScrollValue = self.cutListDisplay.verticalScrollBar().maximum()
        return int(maxScrollValue * positionPercentage)

    def nextCut(self):
        """Move to next cut in list."""
        if self.currentIndex < len(self.cutList) - 1:
            currentCut = self.cutList[self.currentIndex]
            match = re.search(r': (\d+) cuts', currentCut)
            if match:
                quantity = int(match.group(1))
                if quantity > 1:
                    reply = QMessageBox.question(
                        self, 'Confirm Cut Completion',
                        f'Have all {quantity} cuts been made for this line?',
                        QMessageBox.Yes | QMessageBox.No, QMessageBox.No
                    )
                    if reply == QMessageBox.No:
                        return
            self.currentIndex += 1
            self.displayCurrentCut()
            self.sendCurrentCutToController()

    def prevCut(self):
        """Move to previous cut in list."""
        if self.currentIndex > 0:
            self.currentIndex -= 1
            self.displayCurrentCut()
            self.sendCurrentCutToController()

    def sendCurrentCutToController(self):
        """Send current cut measurement to CNC."""
        if self.bluetooth_manager.is_connected():
            currentCut = self.cutList[self.currentIndex]
            match = re.search(r'\d+(\.\d+)?', currentCut)
            if match:
                value = float(match.group())
                if value > MAX_MACHINE_DISTANCE:
                    QMessageBox.warning(
                        self, "Measurement Error",
                        f"The measurement exceeds the limit of {MAX_MACHINE_DISTANCE}mm."
                    )
                    return
                command = f"G0 X{value}"
                self.send_command_to_cnc(command)

    def clearCutList(self):
        """Clear the cut list."""
        reply = QMessageBox.question(
            self, 'Clear Cut List', 'Are you sure you want to clear the cut list?',
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.cutList = []
            self.currentIndex = -1
            self.cutListDisplay.clear()
            self.measurement_input.clear()
            self.append_to_terminal("Cut list cleared.")

    # === Dialog Methods ===
    def start_wifi_wizard(self):
        """Open WiFi wizard dialog."""
        dialog = WiFiWizardDialog(self)
        result = dialog.exec_()
        if result == QDialog.Accepted:
            print("WiFi connection successful")
        
    def start_calibration(self):
        """Open calibration wizard dialog."""
        try:
            self.append_to_terminal("Opening calibration wizard...")
            dialog = CalibrationDialog(self)
            result = dialog.exec_()
            if result == QDialog.Accepted:
                self.append_to_terminal("Calibration completed successfully!")
            else:
                self.append_to_terminal("Calibration cancelled.")
        except Exception as e:
            self.append_to_terminal(f"Error opening calibration dialog: {e}")
            print(f"Calibration error: {e}")

    # === Utility Methods ===
    def append_to_terminal(self, message):
        """Append message to terminal output."""
        # If bluetooth settings window is open, also append there
        if self.bluetooth_settings_window and self.bluetooth_settings_window.isVisible():
            self.bluetooth_settings_window.append_to_terminal(message)
        print(message)

    def closeEvent(self, event):
        """Handle application close event."""
        # Close bluetooth settings window if open
        if self.bluetooth_settings_window:
            self.bluetooth_settings_window.close()
        
        self.bluetooth_manager.disconnect()
        event.accept()