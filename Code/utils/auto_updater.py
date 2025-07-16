"""
GitHub Auto-Updater Module for MakerStop Controller
Checks for updates and downloads new releases from GitHub
Uses git tags for version detection instead of hardcoded versions
"""
import requests
import json
import os
import sys
import subprocess
import zipfile
import shutil
import re
from packaging import version
from PyQt5.QtWidgets import QDialog, QLabel, QPushButton, QProgressBar, QTextEdit, QMessageBox
from PyQt5.QtCore import QThread, pyqtSignal, QTimer
from PyQt5.QtGui import QFont

# Configuration
GITHUB_REPO = "MakerStop-Dan/MakerStop"
STARTUP_CHECK_DELAY = 3000  # 3 seconds after startup (in milliseconds)


def get_current_version():
    """Get current version from git tags with fallbacks"""
    try:
        # Get the directory where this script is located
        script_dir = os.path.dirname(os.path.abspath(__file__))
        
        # Method 1: Try to get the latest git tag
        try:
            result = subprocess.run(
                ['git', 'describe', '--tags', '--abbrev=0'], 
                capture_output=True, 
                text=True, 
                cwd=script_dir,
                timeout=5
            )
            
            if result.returncode == 0:
                version_tag = result.stdout.strip()
                # Remove 'v' prefix if present
                clean_version = version_tag.lstrip('v')
                print(f"Version from git tag: {clean_version}")
                return clean_version
        except Exception as e:
            print(f"Git tag method failed: {e}")
        
        # Method 2: Try git describe with more info
        try:
            result = subprocess.run(
                ['git', 'describe', '--tags', '--always'], 
                capture_output=True, 
                text=True, 
                cwd=script_dir,
                timeout=5
            )
            
            if result.returncode == 0:
                describe_output = result.stdout.strip()
                # Extract version number from describe output (e.g., "v1.0.3-5-g1234567")
                match = re.match(r'v?(\d+\.\d+\.\d+)', describe_output)
                if match:
                    clean_version = match.group(1)
                    print(f"Version from git describe: {clean_version}")
                    return clean_version
        except Exception as e:
            print(f"Git describe method failed: {e}")
        
        # Method 3: Check for VERSION file
        try:
            version_file_paths = [
                os.path.join(script_dir, '..', 'VERSION'),
                os.path.join(script_dir, 'VERSION'),
                os.path.join(os.getcwd(), 'VERSION')
            ]
            
            for version_file in version_file_paths:
                if os.path.exists(version_file):
                    with open(version_file, 'r') as f:
                        file_version = f.read().strip()
                        clean_version = file_version.lstrip('v')
                        print(f"Version from VERSION file: {clean_version}")
                        return clean_version
        except Exception as e:
            print(f"VERSION file method failed: {e}")
        
        # Method 4: Try to get version from latest commit
        try:
            result = subprocess.run(
                ['git', 'log', '--oneline', '-1'], 
                capture_output=True, 
                text=True, 
                cwd=script_dir,
                timeout=5
            )
            
            if result.returncode == 0:
                commit_msg = result.stdout.strip()
                # Look for version pattern in commit message
                version_match = re.search(r'v?(\d+\.\d+\.\d+)', commit_msg)
                if version_match:
                    clean_version = version_match.group(1)
                    print(f"Version from commit message: {clean_version}")
                    return clean_version
        except Exception as e:
            print(f"Git commit method failed: {e}")
            
        # Final fallback
        fallback_version = "1.0.0"
        print(f"All version detection methods failed, using fallback: {fallback_version}")
        return fallback_version
        
    except Exception as e:
        print(f"Error in get_current_version: {e}")
        return "1.0.0"


def save_version_to_file(version):
    """Save version to VERSION file for future reference"""
    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        version_file = os.path.join(script_dir, '..', 'VERSION')
        
        with open(version_file, 'w') as f:
            f.write(f"v{version}")
        print(f"Saved version {version} to VERSION file")
        
    except Exception as e:
        print(f"Failed to save version to file: {e}")


# Get current version dynamically
CURRENT_VERSION = get_current_version()


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
                current_version = CURRENT_VERSION.lstrip('v')
                
                print(f"Current version: {current_version}")
                print(f"Latest version: {latest_version}")
                
                try:
                    if version.parse(latest_version) > version.parse(current_version):
                        self.update_available.emit(release_data)
                    else:
                        self.no_update.emit()
                except Exception as ve:
                    print(f"Version comparison error: {ve}")
                    # Fallback to string comparison
                    if latest_version != current_version:
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
            # Get the new version from release data
            new_version = self.release_data.get('tag_name', 'unknown').lstrip('v')
            
            # Create backup of current installation
            backup_dir = f"backup_v{CURRENT_VERSION}"
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
            
            # Save the new version to VERSION file
            save_version_to_file(new_version)
            
            # Cleanup
            os.remove(zip_filepath)
            shutil.rmtree(temp_dir)
            
            # Show success message
            reply = QMessageBox.information(
                self, 
                "Update Complete", 
                f"Update to v{new_version} installed successfully!\n\nThe application will restart now.",
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
        self.reject()
    
    def skip_version(self):
        """Skip this version"""
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
            print(f"Checking for updates on startup... Current version: {CURRENT_VERSION}")
            QTimer.singleShot(STARTUP_CHECK_DELAY, self.perform_startup_check)
    
    def perform_startup_check(self):
        """Perform the actual startup update check"""
        self.startup_check_completed = True
        self.check_for_updates(silent=True)
    
    def check_for_updates(self, silent=True):
        """Check for updates (silent=True for automatic checks)"""
        print(f"Checking for updates... Current version: {CURRENT_VERSION} (silent: {silent})")
        self.checker = UpdateChecker(GITHUB_REPO)
        self.checker.update_available.connect(lambda data: self.show_update_dialog(data))
        
        if not silent:
            self.checker.no_update.connect(lambda: QMessageBox.information(
                self.parent_window, "No Updates", f"You're running the latest version! (v{CURRENT_VERSION})"))
            self.checker.error_occurred.connect(lambda err: QMessageBox.warning(
                self.parent_window, "Update Check Failed", f"Could not check for updates: {err}"))
        else:
            # For silent checks, just log errors
            self.checker.error_occurred.connect(lambda err: print(f"Update check failed: {err}"))
        
        self.checker.start()
    
    def show_update_dialog(self, release_data):
        """Show the update dialog"""
        new_version = release_data.get('tag_name', 'Unknown version')
        print(f"Update available: {CURRENT_VERSION} -> {new_version}")
        dialog = UpdateDialog(release_data, self.parent_window)
        dialog.exec_()


# Debug function to test version detection
def debug_version_detection():
    """Debug function to test all version detection methods"""
    print("=== Version Detection Debug ===")
    current_version = get_current_version()
    print(f"Final detected version: {current_version}")
    print("================================")


if __name__ == '__main__':
    # Test version detection
    debug_version_detection()