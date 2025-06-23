import os
import json
import shutil
import requests
import hashlib
import subprocess
import sys
import tempfile
from datetime import datetime
from zipfile import ZipFile
from PyQt5.QtCore import QObject, pyqtSignal
from PyQt5.QtWidgets import QMessageBox, QProgressDialog
from PyQt5.QtCore import QThread
from packaging import version as semver

# Import existing utilities - handle both relative and absolute imports
try:
    from .utils import (
        _get_github_auth_headers, 
        is_connected_to_internet,
        show_error,
        show_message
    )
except ImportError:
    # Fallback for direct execution
    sys.path.insert(0, os.path.dirname(__file__))
    from utils import (
        _get_github_auth_headers, 
        is_connected_to_internet,
        show_error,
        show_message
    )

class LauncherUpdaterSignals(QObject):
    """Signals for launcher updater thread communication"""
    progress = pyqtSignal(int, int)  # current, total bytes
    status = pyqtSignal(str)
    update_available = pyqtSignal(dict)  # update info
    update_complete = pyqtSignal(bool, str)  # success, message
    error = pyqtSignal(str)

class LauncherUpdater(QThread):
    """Thread for handling launcher updates"""
    
    def __init__(self, launcher_repo_url, current_version=None):
        super().__init__()
        self.manager = LauncherUpdateManager(launcher_repo_url, current_version)
        self.signals = self.manager.signals

    def run(self):
        """Main update check thread execution"""
        try:
            self.signals.status.emit("Checking for launcher updates...")
            update_available, update_info = self.manager.check_launcher_update()
            
            if update_available:
                self.signals.update_available.emit(update_info)
            else:
                self.signals.status.emit("Launcher is up to date")
                self.signals.update_complete.emit(True, "No updates available")
                
        except Exception as e:
            self.signals.error.emit(f"Update check failed: {str(e)}")

class LauncherUpdateManager:
    """Manages launcher updates based on a remote version.txt file."""
    
    def __init__(self, launcher_repo_url, current_version=None):
        self.launcher_repo_url = launcher_repo_url
        self.version_url = "https://raw.githubusercontent.com/quentin452/CatzLauncher/main/version.txt"
        self.zip_url = f"{launcher_repo_url}/archive/refs/heads/main.zip"
        self.current_version = current_version or self._get_current_version()
        self.update_file = os.path.join(os.path.dirname(__file__), "../saves/launcher_update_info.json")
        self.signals = LauncherUpdaterSignals()
        
        os.makedirs(os.path.dirname(self.update_file), exist_ok=True)
    
    def _get_current_version(self):
        version_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), "version.txt")
        try:
            with open(version_file, 'r') as f:
                return f.read().strip()
        except FileNotFoundError:
            return "0.0.0" # Default if not found

    def check_launcher_update(self):
        """
        Compares local version.txt with the remote one.
        """
        if not is_connected_to_internet():
            return False, None
            
        try:
            response = requests.get(self.version_url, timeout=10)
            response.raise_for_status()
            remote_version_str = response.text.strip()

            local_version = semver.parse(self.current_version)
            remote_version = semver.parse(remote_version_str)
            
            if remote_version > local_version:
                return True, {
                    'current_version': str(local_version),
                    'new_version': str(remote_version),
                    'zip_url': self.zip_url
                }
            return False, None
        except (requests.RequestException, semver.InvalidVersion) as e:
            print(f"Error checking for manual version update: {e}")
            return False, None
    
    def perform_update(self, update_info, progress_callback=None):
        """
        Performs a full update by downloading and extracting the main branch zip.
        """
        zip_url = update_info.get('zip_url')
        if not zip_url:
            raise ValueError("L'URL de téléchargement est manquante dans les informations de mise à jour.")

        self.signals.status.emit("Téléchargement de la mise à jour...")
        zip_path = self.download_full_update(zip_url, progress_callback)
        temp_dir = os.path.dirname(zip_path)
        
        try:
            self.signals.status.emit("Extraction des fichiers...")
            extract_dir = os.path.join(temp_dir, "extracted")
            with ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)

            # Find the actual content directory inside the extracted folder
            # (e.g., CatzLauncher-main)
            extracted_content_dir = os.path.join(extract_dir, os.listdir(extract_dir)[0])
            
            restart_script = self.create_update_script(extracted_content_dir)
            
            # Save the new version number to local info file
            self.save_local_update_info({'version': update_info['new_version']})
            return True, restart_script
            
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def download_full_update(self, zip_url, progress_callback):
        """Downloads the full update zip from the given URL."""
        temp_dir = tempfile.mkdtemp(prefix="catzlauncher_update_")
        zip_path = os.path.join(temp_dir, "launcher.zip")
        
        try:
            response = requests.get(zip_url, stream=True, timeout=30)
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            bytes_downloaded = 0
            
            with open(zip_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
                    bytes_downloaded += len(chunk)
                    if progress_callback:
                        progress_callback(bytes_downloaded, total_size)
            
            if progress_callback:
                progress_callback(total_size, total_size)
            return zip_path
            
        except requests.RequestException as e:
            shutil.rmtree(temp_dir, ignore_errors=True)
            raise Exception(f"Le téléchargement a échoué: {e}")

    def create_update_script(self, new_content_dir):
        """Creates a script to copy new files and restart the launcher."""
        launcher_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        script_path = os.path.join(launcher_dir, "update_and_restart.bat" if sys.platform == "win32" else "update_and_restart.sh")
        
        python_executable = sys.executable
        main_script = os.path.join(launcher_dir, "main.py")

        if sys.platform == "win32":
            # Use xcopy to robustly copy files and directories
            script_content = f'''@echo off
echo Mise a jour des fichiers du launcher...
xcopy "{new_content_dir}" "{launcher_dir}" /E /H /C /I /Y > NUL
echo Nettoyage...
rd /s /q "{os.path.dirname(new_content_dir)}"
echo Redemarrage du launcher...
start "" "{python_executable}" "{main_script}"
del "%~f0"
exit
'''
        else:
            script_content = f'''#!/bin/bash
echo "Mise a jour des fichiers du launcher..."
cp -r "{new_content_dir}/." "{launcher_dir}/"
echo "Nettoyage..."
rm -rf "{os.path.dirname(new_content_dir)}"
echo "Redemarrage du launcher..."
nohup "{python_executable}" "{main_script}" &
rm "$0"
exit
'''
        with open(script_path, "w", newline='\\n') as f:
            f.write(script_content)
        return script_path
        
    def save_local_update_info(self, data):
        with open(self.update_file, 'w') as f:
            json.dump(data, f, indent=4)

def check_launcher_updates(launcher_repo_url, current_version=None):
    """Convenience function to check for launcher updates"""
    updater = LauncherUpdateManager(launcher_repo_url, current_version)
    return updater.check_launcher_update()

def perform_launcher_update(launcher_repo_url, update_info, use_incremental=True, progress_callback=None):
    """Convenience function to perform launcher update"""
    updater = LauncherUpdateManager(launcher_repo_url)
    return updater.perform_update(update_info, progress_callback)

def is_git_repo():
    main_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.isdir(os.path.join(main_dir, '.git'))
