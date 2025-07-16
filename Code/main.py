#!/usr/bin/env python3
"""
Main entry point for the MakerStop Controller application.
"""

import sys
from PyQt5.QtWidgets import QApplication
from ui.dialogs.calibration import CalibrationDialog
from ui.main_window import MakerStopController
from ui.dialogs.wifi_wizard import WiFiWizardDialog


def main():
    """Main application entry point."""
    app = QApplication.instance() or QApplication(sys.argv)
    
    # Set application properties
    app.setApplicationName("MakerStop Controller")
    app.setApplicationVersion("2.0")
    app.setOrganizationName("MakerStop")
    
    # Create and show main window
    main_window = MakerStopController()
    main_window.show()
    
    # Start event loop
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
