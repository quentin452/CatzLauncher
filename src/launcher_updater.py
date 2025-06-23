#test
print("test")
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
from PyQt5.QtCore import QObject, pyqtSignal, QThread
from PyQt5.QtWidgets import QMessageBox, QProgressDialog
from packaging import version as semver
import time
import base64

# Import existing utilities
try:
    from .utils import (
        _get_github_auth_headers, 
        is_connected_to_internet,
    )
except ImportError:
    from utils import _get_github_auth_headers, is_connected_to_internet

class LauncherUpdaterSignals(QObject):
    """Signals for launcher updater thread communication"""
    progress = pyqtSignal(int, int)
    status = pyqtSignal(str)
    update_available = pyqtSignal(dict)
    update_complete = pyqtSignal(bool, str)
    error = pyqtSignal(str)

class LauncherUpdateManager:
    """Manages launcher updates based on a remote version.txt file via the GitHub API."""
    
    def __init__(self, launcher_repo_url, current_version=None):
        self.launcher_repo_url = launcher_repo_url
        self.api_version_url = "https://api.github.com/repos/quentin452/CatzLauncher/contents/version.txt"
        self.zip_url = f"{launcher_repo_url}/archive/refs/heads/main.zip"
        self.current_version = current_version or self._get_current_version()
        self.signals = LauncherUpdaterSignals()
        self.saves_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "saves")
        self.update_file = os.path.join(self.saves_dir, "launcher_update_info.json")
        os.makedirs(self.saves_dir, exist_ok=True)
    
    def _get_current_version(self):
        version_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), "version.txt")
        try:
            with open(version_file, 'r') as f:
                return f.read().strip()
        except FileNotFoundError:
            return "0.0.0"

    def check_launcher_update(self):
        """Compares local version.txt with the remote one via GitHub API to bypass cache."""
        if not is_connected_to_internet():
            return False, None
            
        try:
            # 1. Fetch remote version content from API
            headers = { 'Accept': 'application/vnd.github.v3+json' }
            response = requests.get(self.api_version_url, timeout=10, headers=headers)
            response.raise_for_status()
            
            # Decode the content from Base64
            api_response = response.json()
            if 'content' not in api_response:
                raise ValueError("API response did not contain file content.")
                
            content_b64 = api_response['content']
            decoded_content = base64.b64decode(content_b64).decode('utf-8')
            remote_version_str = decoded_content.strip()

            # 2. Safely parse remote version
            try:
                remote_version = semver.parse(remote_version_str)
            except semver.InvalidVersion:
                print(f"WARNING: Remote version from GitHub API is invalid: '{remote_version_str}'. Aborting.")
                return False, None

            # 3. Safely parse local version
            try:
                local_version = semver.parse(self.current_version)
            except semver.InvalidVersion:
                print(f"WARNING: Local version is invalid: '{self.current_version}'. Defaulting to 0.0.0.")
                local_version = semver.parse("0.0.0")
            
            # 4. Compare
            if remote_version > local_version:
                return True, {
                    'current_version': str(local_version),
                    'new_version': str(remote_version),
                    'zip_url': self.zip_url
                }
            
            return False, None

        except (requests.RequestException, ValueError, KeyError) as e:
            return False, None
    
    def perform_update(self, update_info, progress_callback=None):
        """
        Performs a full update by downloading, extracting the main branch zip,
        and creating a script to perform the file operations after the app closes.
        Returns (success, message) where message is the script_path on success,
        or an error string on failure.
        """
        zip_url = update_info.get('zip_url')
        if not zip_url:
            return False, "L'URL de téléchargement est manquante dans les informations de mise à jour."

        temp_dir = tempfile.mkdtemp(prefix="catzlauncher_update_")
        
        try:
            # 1. Download
            self.signals.status.emit("Téléchargement de la mise à jour...")
            zip_path = self.download_full_update(zip_url, temp_dir, progress_callback)
            
            # 2. Extract
            self.signals.status.emit("Extraction des fichiers...")
            extract_dir = os.path.join(temp_dir, "extracted")
            with ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)

            # 3. Find content directory
            extracted_subfolders = os.listdir(extract_dir)
            if not extracted_subfolders:
                raise IOError("Le fichier de mise à jour (zip) est vide ou corrompu.")
            extracted_content_dir = os.path.join(extract_dir, extracted_subfolders[0])
            
            # 4. Create update script
            restart_script = self.create_update_script(extracted_content_dir, temp_dir)
            
            # 5. Finalize
            self.save_local_update_info({'version': update_info['new_version']})
            return True, restart_script

        except (requests.RequestException, IOError) as e:
            # Catch specific, expected errors and return a user-friendly message
            shutil.rmtree(temp_dir, ignore_errors=True)
            return False, f"Échec de l'opération de fichier/réseau: {e}"
        except Exception as e:
            # Catch any other unexpected error
            shutil.rmtree(temp_dir, ignore_errors=True)
            # Re-raise the exception to be handled by the main UI thread, which will show a traceback
            raise e

    def download_full_update(self, zip_url, temp_dir, progress_callback):
        zip_path = os.path.join(temp_dir, "launcher.zip")
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
        return zip_path

    def create_update_script(self, new_content_dir, temp_dir_to_delete):
        launcher_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        script_path = os.path.join(launcher_dir, "updater.py")
        python_executable = os.path.normpath(sys.executable)
        
        norm_new_content_dir = os.path.normpath(new_content_dir)
        norm_launcher_dir = os.path.normpath(launcher_dir)
        norm_temp_dir_to_delete = os.path.normpath(temp_dir_to_delete)

        # Create a self-contained Python script to perform the update.
        # This avoids all issues with batch files, special path characters, and shell interpretation.
        script_content = f'''# -*- coding: utf-8 -*-
import sys, os, time, shutil, subprocess, traceback

def main():
    # Create a log file immediately to trace execution.
    log_path = os.path.join(r'{norm_launcher_dir}', "updater.log")
    with open(log_path, "w", encoding="utf-8") as f:
        f.write("Updater script started at " + time.ctime() + "\\n")
        
        try:
            source_dir = r'{norm_new_content_dir}'
            f.write(f"Source: {{source_dir}}\\n")
            target_dir = r'{norm_launcher_dir}'
            f.write(f"Target: {{target_dir}}\\n")
            temp_root_to_delete = r'{norm_temp_dir_to_delete}'
            python_exe = r'{python_executable}'
            f.write(f"Python exe: {{python_exe}}\\n")
            launcher_main_script = os.path.join(target_dir, 'main.py')
            f.write(f"Launcher main script: {{launcher_main_script}}\\n")

            # 1. Wait
            f.write("Waiting for launcher to close...\\n")
            time.sleep(3)

            # 2. Copy
            f.write("Copying files...\\n")
            shutil.copytree(source_dir, target_dir, dirs_exist_ok=True)
            f.write("Copy complete.\\n")

            # 3. Clean
            f.write("Cleaning up temp folder...\\n")
            shutil.rmtree(temp_root_to_delete, ignore_errors=True)
            f.write("Cleanup complete.\\n")
            
            # 4. Restart
            f.write("Restarting launcher...\\n")
            DETACHED_PROCESS = 0x00000008 if sys.platform == 'win32' else 0
            subprocess.Popen([python_exe, launcher_main_script], cwd=target_dir, creationflags=DETACHED_PROCESS)
            f.write("Restart command sent.\\n")
            
            # 5. Self-delete
            f.write("Attempting to self-delete...\\n")
            f.close() # Close the log file before trying to delete the script
            time.sleep(1)
            os.remove(__file__)

        except Exception as e:
            # In case of any error, write it to a log file for debugging.
            f.write(f"\\n--- ERROR --- \\n")
            f.write(f"An error occurred: {{str(e)}}\\n")
            f.write(traceback.format_exc())

if __name__ == "__main__":
    main()
'''
        with open(script_path, "w", encoding="utf-8") as f:
            f.write(script_content)
        return script_path
        
    def save_local_update_info(self, data):
        with open(self.update_file, 'w') as f:
            json.dump(data, f, indent=4)

class LauncherUpdater(QThread):
    def __init__(self, launcher_repo_url, current_version=None):
        super().__init__()
        self.manager = LauncherUpdateManager(launcher_repo_url, current_version)
        self.signals = self.manager.signals

    def run(self):
        try:
            update_available, update_info = self.manager.check_launcher_update()
            if update_available:
                self.signals.update_available.emit(update_info)
        except Exception as e:
            self.signals.error.emit(f"Update check failed: {str(e)}")

def check_launcher_updates(launcher_repo_url, current_version=None):
    manager = LauncherUpdateManager(launcher_repo_url, current_version)
    return manager.check_launcher_update()

def perform_launcher_update(launcher_repo_url, update_info, progress_callback=None):
    manager = LauncherUpdateManager(launcher_repo_url)
    return manager.perform_update(update_info, progress_callback)

def is_git_repo():
    return os.path.isdir('.git')
