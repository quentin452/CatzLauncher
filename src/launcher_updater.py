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
            print(f"Error fetching remote version via API: {e}")
            return False, None
    
    def perform_update(self, update_info, progress_callback=None):
        """Performs a full update by downloading and extracting the main branch zip."""
        zip_url = update_info.get('zip_url')
        if not zip_url:
            raise ValueError("L'URL de téléchargement est manquante.")

        temp_dir = tempfile.mkdtemp(prefix="catzlauncher_update_")
        
        try:
            self.signals.status.emit("Téléchargement de la mise à jour...")
            zip_path = self.download_full_update(zip_url, temp_dir, progress_callback)
            
            self.signals.status.emit("Extraction des fichiers...")
            extract_dir = os.path.join(temp_dir, "extracted")
            with ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)

            extracted_content_dir = os.path.join(extract_dir, os.listdir(extract_dir)[0])
            restart_script = self.create_update_script(extracted_content_dir)
            
            self.save_local_update_info({'version': update_info['new_version']})
            return True, restart_script
            
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

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

    def create_update_script(self, new_content_dir):
        launcher_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        script_path = os.path.join(launcher_dir, "update_and_restart.bat" if sys.platform == "win32" else "update_and_restart.sh")
        python_executable = sys.executable.replace("\\", "/")
        main_script = os.path.join(launcher_dir, "main.py").replace("\\", "/")
        new_content_dir_norm = new_content_dir.replace("\\", "/")
        launcher_dir_norm = launcher_dir.replace("\\", "/")

        if sys.platform == "win32":
            script_content = f'''@echo off
echo Mise a jour des fichiers...
timeout /t 2 /nobreak > NUL
xcopy "{new_content_dir_norm}" "{launcher_dir_norm}" /E /H /C /I /Y > NUL
echo Nettoyage...
rd /s /q "{os.path.dirname(new_content_dir_norm)}"
echo Redemarrage...
start "" "{python_executable}" "{main_script}"
del "%~f0"
'''
        else: # Linux/macOS
            script_content = f'''#!/bin/bash
echo "Mise a jour des fichiers..."
sleep 2
cp -r "{new_content_dir_norm}/." "{launcher_dir_norm}/"
echo "Nettoyage..."
rm -rf "{os.path.dirname(new_content_dir_norm)}"
echo "Redemarrage..."
nohup "{python_executable}" "{main_script}" &
rm "$0"
'''
        with open(script_path, "w") as f:
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
