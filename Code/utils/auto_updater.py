"""
GitHub Auto-Updater Module for MakerStop Controller
Checks for updates and downloads new releases from GitHub
"""
import requests
import json
import os
import sys
import subprocess
import zipfile
import shutil
from packaging import version
from PyQt5.QtWidgets import QDialog, QLabel, QPushButton, QProgressBar, QTextEdit, QMessageBox
from PyQt5.QtCore import QThread, pyqtSignal, QTimer
from PyQt5.QtGui import QFont

# Configuration
GITHUB_REPO = "MakerStop-Dan/MakerStop"  # Replace with your repo
CURRENT_VERSION = "v1.0.3"  # Update this with each release
STARTUP_CHECK_DELAY = 3000  # 3 seconds after startup (in milliseconds)


class UpdateChecker(QThread):
    """Thread for checking GitHub releases"""
    update_available = pyqtSignal(dict)  # Emits release info
    no_update = pyqtSignal()
    error_occurred = pyqtSignal(str)
    
    def __init__(self, repo_name):
        super().__init__()
        self.repo_name = repo_name
        
    def run(self):
        """Check for latest release on GitHub"""
        try:
            url = f"https://api.github.com/repos/{self.repo_name}/releases/latest"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                release_data = response.json()
                latest_version = release_data.get('tag_name', '').lstrip('v')
                
                if version.parse(latest_version) > version.parse(CURRENT_VERSION):
                    self.update_available.emit(release_data)
                else:
                    self.no_update.emit()
            else:
                self.error_occurred.emit(f"GitHub API error: {response.status_code}")
                
        except requests.exceptions.RequestException as e:
            self.error_occurred.emit(f"Network error: {str(e)}")
        except Exception as e:
            self.error_occurred.emit(f"Update check failed: {str(e)}")


class UpdateDownloader(QThread):
    """Thread for downloading updates"""
    progress_update = pyqtSignal(int)  # Download progress percentage
    download_complete = pyqtSignal(str)  # Local file path
    download_failed = pyqtSignal(str)  # Error message
    
    def __init__(self, download_url, filename):
        super().__init__()
        self.download_url = download_url
        self.filename = filename
        
    def run(self):
        """Download the update file"""
        try:
            response = requests.get(self.download_url, stream=True, timeout=30)
            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0
            
            with open(self.filename, 'wb') as file:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        file.write(chunk)
                        downloaded += len(chunk)
                        if total_size > 0:
                            progress = int((downloaded / total_size) * 100)
                            self.progress_update.emit(progress)
            
            self.download_complete.emit(self.filename)
            
        except Exception as e:
            self.download_failed.emit(str(e))


class UpdateDialog(QDialog):
    """Dialog for handling updates"""
    
    def __init__(self, release_data, parent=None):
        super().__init__(parent)
        self.release_data = release_data
        self.download_thread = None
        self.init_ui()
        
    def init_ui(self):
        """Initialize update dialog UI"""
        self.setWindowTitle("MakerStop Update Available")
        self.setFixedSize(500, 400)
        
        # Release info
        version_text = self.release_data.get('tag_name', 'Unknown')
        release_name = self.release_data.get('name', 'New Release')
        
        self.title_label = QLabel(f"Update Available: {release_name}", self)
        self.title_label.setGeometry(20, 20, 460, 30)
        self.title_label.setFont(QFont('Arial', 14, QFont.Bold))
        
        self.version_label = QLabel(f"Current: v{CURRENT_VERSION} → New: {version_text}", self)
        self.version_label.setGeometry(20, 55, 460, 25)
        self.version_label.setFont(QFont('Arial', 11))
        
        # Release notes
        self.notes_label = QLabel("Release Notes:", self)
        self.notes_label.setGeometry(20, 90, 460, 20)
        self.notes_label.setFont(QFont('Arial', 11, QFont.Bold))
        
        self.release_notes = QTextEdit(self)
        self.release_notes.setGeometry(20, 115, 460, 150)
        self.release_notes.setReadOnly(True)
        self.release_notes.setPlainText(self.release_data.get('body', 'No release notes available.'))
        
        # Progress bar (initially hidden)
        self.progress_bar = QProgressBar(self)
        self.progress_bar.setGeometry(20, 280, 460, 25)
        self.progress_bar.setVisible(False)
        
        # Status label
        self.status_label = QLabel("", self)
        self.status_label.setGeometry(20, 310, 460, 20)
        
        # Buttons
        self.download_button = QPushButton("Download & Install", self)
        self.download_button.setGeometry(20, 340, 150, 40)
        self.download_button.clicked.connect(self.start_download)
        self.download_button.setStyleSheet("""
            background-color: #74b72e;
            color: white;
            border-radius: 5px;
            font-weight: bold;
        """)
        
        self.later_button = QPushButton("Remind Later", self)
        self.later_button.setGeometry(180, 340, 120, 40)
        self.later_button.clicked.connect(self.remind_later)
        
        self.skip_button = QPushButton("Skip Version", self)
        self.skip_button.setGeometry(310, 340, 120, 40)
        self.skip_button.clicked.connect(self.skip_version)
        
        self.cancel_button = QPushButton("Cancel", self)
        self.cancel_button.setGeometry(440, 340, 80, 40)
        self.cancel_button.clicked.connect(self.reject)
    
    def start_download(self):
        """Start downloading the update"""
        try:
            # Find the appropriate asset (ZIP file for source code)
            assets = self.release_data.get('assets', [])
            download_url = None
            filename = None
            
            # Look for a ZIP asset first, then fallback to source code
            for asset in assets:
                if asset['name'].endswith('.zip'):
                    download_url = asset['browser_download_url']
                    filename = asset['name']
                    break
            
            if not download_url:
                # Use source code ZIP
                download_url = self.release_data.get('zipball_url')
                version_tag = self.release_data.get('tag_name', 'latest')
                filename = f"makerstop-{version_tag}.zip"
            
            if not download_url:
                QMessageBox.warning(self, "Error", "No download URL found in release.")
                return
            
            # Disable buttons and show progress
            self.download_button.setEnabled(False)
            self.later_button.setEnabled(False)
            self.skip_button.setEnabled(False)
            self.progress_bar.setVisible(True)
            self.status_label.setText("Downloading update...")
            
            # Start download thread
            self.download_thread = UpdateDownloader(download_url, filename)
            self.download_thread.progress_update.connect(self.update_progress)
            self.download_thread.download_complete.connect(self.download_finished)
            self.download_thread.download_failed.connect(self.download_error)
            self.download_thread.start()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to start download: {e}")
    
    def update_progress(self, percentage):
        """Update download progress"""
        self.progress_bar.setValue(percentage)
        self.status_label.setText(f"Downloading... {percentage}%")
    
    def download_finished(self, filepath):
        """Handle completed download"""
        self.status_label.setText("Download complete! Preparing installation...")
        
        try:
            # Extract and install
            self.install_update(filepath)
        except Exception as e:
            QMessageBox.critical(self, "Installation Error", f"Failed to install update: {e}")
    
    def download_error(self, error_msg):
        """Handle download error"""
        self.status_label.setText("Download failed!")
        QMessageBox.critical(self, "Download Error", f"Download failed: {error_msg}")
        self.reset_buttons()
    
    def install_update(self, zip_filepath):
        """Install the downloaded update"""
        try:
            # Create backup of current installation
            backup_dir = "backup_" + CURRENT_VERSION
            if os.path.exists(backup_dir):
                shutil.rmtree(backup_dir)
            
            # Backup current files
            current_dir = os.getcwd()
            shutil.copytree(current_dir, backup_dir, ignore=shutil.ignore_patterns('*.zip', 'backup_*', '__pycache__'))
            
            # Extract new version
            with zipfile.ZipFile(zip_filepath, 'r') as zip_ref:
                # Extract to temporary directory first
                temp_dir = "temp_update"
                if os.path.exists(temp_dir):
                    shutil.rmtree(temp_dir)
                zip_ref.extractall(temp_dir)
                
                # Find the actual code directory (GitHub ZIP has extra folder)
                extracted_items = os.listdir(temp_dir)
                if len(extracted_items) == 1 and os.path.isdir(os.path.join(temp_dir, extracted_items[0])):
                    source_dir = os.path.join(temp_dir, extracted_items[0])
                else:
                    source_dir = temp_dir
                
                # Copy new files over current installation
                for item in os.listdir(source_dir):
                    src_path = os.path.join(source_dir, item)
                    dst_path = os.path.join(current_dir, item)
                    
                    if os.path.isdir(src_path):
                        if os.path.exists(dst_path):
                            shutil.rmtree(dst_path)
                        shutil.copytree(src_path, dst_path)
                    else:
                        shutil.copy2(src_path, dst_path)
            
            # Cleanup
            os.remove(zip_filepath)
            shutil.rmtree(temp_dir)
            
            # Show success message
            reply = QMessageBox.information(
                self, 
                "Update Complete", 
                "Update installed successfully!\n\nThe application will restart now.",
                QMessageBox.Ok
            )
            
            # Restart application
            self.restart_application()
            
        except Exception as e:
            QMessageBox.critical(self, "Installation Error", 
                               f"Failed to install update: {e}\n\n"
                               f"Your backup is saved in: {backup_dir}")
    
    def restart_application(self):
        """Restart the application"""
        try:
            # Get the current script path
            script_path = sys.argv[0]
            
            # Start new instance
            if sys.platform.startswith('win'):
                subprocess.Popen([sys.executable, script_path])
            else:
                subprocess.Popen([sys.executable, script_path])
            
            # Exit current instance
            QTimer.singleShot(1000, sys.exit)
            
        except Exception as e:
            QMessageBox.critical(self, "Restart Error", 
                               f"Please restart the application manually: {e}")
    
    def remind_later(self):
        """Remind about update later"""
        # Could implement a delayed reminder here
        self.reject()
    
    def skip_version(self):
        """Skip this version"""
        # Could implement version skipping logic here
        self.reject()
    
    def reset_buttons(self):
        """Reset button states after error"""
        self.download_button.setEnabled(True)
        self.later_button.setEnabled(True)
        self.skip_button.setEnabled(True)
        self.progress_bar.setVisible(False)


class AutoUpdater:
    """Main auto-updater class"""
    
    def __init__(self, parent_window):
        self.parent_window = parent_window
        self.startup_check_completed = False
        
    def check_on_startup(self):
        """Check for updates on application startup"""
        if not self.startup_check_completed:
            print("Checking for updates on startup...")
            QTimer.singleShot(STARTUP_CHECK_DELAY, self.perform_startup_check)
    
    def perform_startup_check(self):
        """Perform the actual startup update check"""
        self.startup_check_completed = True
        self.check_for_updates(silent=True)
    
    def check_for_updates(self, silent=True):
        """Check for updates (silent=True for automatic checks)"""
        print(f"Checking for updates... (silent: {silent})")
        self.checker = UpdateChecker(GITHUB_REPO)
        self.checker.update_available.connect(lambda data: self.show_update_dialog(data))
        
        if not silent:
            self.checker.no_update.connect(lambda: QMessageBox.information(
                self.parent_window, "No Updates", "You're running the latest version!"))
            self.checker.error_occurred.connect(lambda err: QMessageBox.warning(
                self.parent_window, "Update Check Failed", f"Could not check for updates: {err}"))
        else:
            # For silent checks, just log errors
            self.checker.error_occurred.connect(lambda err: print(f"Update check failed: {err}"))
        
        self.checker.start()
    
    def show_update_dialog(self, release_data):
        """Show the update dialog"""
        print(f"Update available: {release_data.get('tag_name', 'Unknown version')}")
        dialog = UpdateDialog(release_data, self.parent_window)
        dialog.exec_()


# Integration example for main_window.py
def integrate_auto_updater(main_window_class):
    """Example of how to integrate into your main window"""
    
    # Add to your MakerStopController.__init__ method:
    def enhanced_init(self):
        # ... existing initialization code ...
        
        # Initialize auto-updater
        self.auto_updater = AutoUpdater(self)
        
        # Check for updates on startup (after UI is ready)
        self.auto_updater.check_on_startup()
        
        # Optional: Add manual update check button to settings
        self.manual_check_action = None  # Add this to a menu or button
    
    # Add this method to your main window class:
    def manual_update_check(self):
        """Manually check for updates"""
        self.auto_updater.check_for_updates(silent=False)


# Usage in main.py
if __name__ == '__main__':
    import sys
    from PyQt5.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    
    # Example of standalone usage for testing
    updater = AutoUpdater(None)
    updater.check_for_updates(silent=False)
    
    sys.exit(app.exec_())
