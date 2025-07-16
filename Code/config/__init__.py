def _init_window(self):
    """Initialize main window properties."""
    self.setWindowTitle(APP_TITLE)
    self.setGeometry(0, 0, APP_WIDTH, APP_HEIGHT)
    self.setFixedSize(APP_WIDTH, APP_HEIGHT)
    self.setStyleSheet(f"QMainWindow {{ background-color: {COLORS['background']}; }}")