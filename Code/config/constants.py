"""
Constants and configuration values for the MakerStop Controller application.
"""
from PyQt5.QtGui import QFont

# Application Settings
APP_TITLE = 'MakerStop'
APP_WIDTH = 800
APP_HEIGHT = 600

# Fonts
MAIN_FONT = QFont('Proxima Nova', 10)
LARGE_FONT = QFont('Proxima Nova', 60)
BUTTON_FONT = QFont('Proxima Nova', 20)
NUMPAD_FONT = QFont('Proxima Nova', 28)
TERMINAL_FONT = QFont('Consolas', 10)

# Button Dimensions
BUTTON_WIDTH = 90
BUTTON_HEIGHT = 90
BUTTON_SIZE_Y = 60
BUTTON_SPACING = 5
EXPANDED_BUTTON_SPACING = 7

# Numpad Configuration
NUMPAD_START_X = 10
NUMPAD_START_Y = 205

# File Paths
PRESETS_FILE = "presets.json"
CALIBRATION_FILE = "calibration_data.json"
BT_DEVICE_FILE = "last_bt_device.txt"

# Bluetooth Configuration
BT_SERVICE_UUID = "00001101-0000-1000-8000-00805F9B34FB"

# Machine Limits
MAX_MACHINE_DISTANCE = 2680  # mm

# Colors
COLORS = {
    'primary': '#74b72e',
    'danger': '#ff746c', 
    'warning': '#ffa500',
    'info': '#24a0ed',
    'success': '#74b72e',
    'secondary': '#666',
    'light': '#f0f0f0',
    'white': '#ffffff',
    'background': '#1e1e1e',
    'input_background': '#1e1e1e',
}

# Numpad Button Layout
NUMPAD_BUTTONS = [
    ('7', (0, 0)), ('8', (0, 1)), ('9', (0, 2)), ('/', (0, 3)),
    ('4', (1, 0)), ('5', (1, 1)), ('6', (1, 2)), ('*', (1, 3)),
    ('1', (2, 0)), ('2', (2, 1)), ('3', (2, 2)), ('-', (2, 3)),
    (':', (3, 0)), ('0', (3, 1)), ('.', (3, 2)), ('+', (3, 3)), 
    ('C', (2, 4)), ('←', (1, 4)), ('=', (3, 4))
]

# Default Values
DEFAULT_STEPS_PER_MM = 49

# Application-wide stylesheets
APP_STYLESHEET = f"""
    QMainWindow {{
        background-color: {COLORS['background']};
    }}
    
    QLineEdit {{
        background-color: {COLORS['white']};
        border: 2px solid {COLORS['secondary']};
        border-radius: 5px;
        padding: 10px;
    }}
"""