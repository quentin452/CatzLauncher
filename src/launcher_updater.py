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
        self.launcher_repo_url = launcher_repo_url
        self.current_version = current_version
        self.signals = LauncherUpdaterSignals()
        self.update_info = None
        
    def run(self):
        """Main update thread execution"""
        try:
            # Check for updates
            self.signals.status.emit("Checking for launcher updates...")
            update_available, update_info = self.check_launcher_update()
            
            if update_available:
                self.update_info = update_info
                self.signals.update_available.emit(update_info)
            else:
                self.signals.status.emit("Launcher is up to date")
                self.signals.update_complete.emit(True, "No updates available")
                
        except Exception as e:
            self.signals.error.emit(f"Update check failed: {str(e)}")
    
    def perform_update(self):
        """Perform the actual update"""
        try:
            if not self.update_info:
                self.signals.error.emit("No update information available")
                return
                
            self.signals.status.emit("Starting launcher update...")
            success = self._download_and_apply_update()
            
            if success:
                self.signals.update_complete.emit(True, "Update completed successfully")
            else:
                self.signals.update_complete.emit(False, "Update failed")
                
        except Exception as e:
            self.signals.error.emit(f"Update failed: {str(e)}")

class LauncherUpdateManager:
    """Manages launcher updates with incremental download support"""
    
    def __init__(self, launcher_repo_url, current_version=None):
        self.launcher_repo_url = launcher_repo_url
        self.current_version = current_version or self._get_current_version()
        self.update_file = os.path.join(os.path.dirname(__file__), "../saves/launcher_update_info.json")
        self.signals = LauncherUpdaterSignals()
        
        # Ensure saves directory exists
        os.makedirs(os.path.dirname(self.update_file), exist_ok=True)
    
    def _get_current_version(self):
        """Get current launcher version from version file or git"""
        version_file = os.path.join(os.path.dirname(__file__), "../version.txt")
        
        # Try to read from version file
        if os.path.exists(version_file):
            try:
                with open(version_file, 'r') as f:
                    return f.read().strip()
            except:
                pass
        
        # Try to get from git
        try:
            result = subprocess.run(
                ['git', 'rev-parse', 'HEAD'], 
                capture_output=True, 
                text=True, 
                cwd=os.path.dirname(__file__)
            )
            if result.returncode == 0:
                return result.stdout.strip()[:8]  # Short SHA
        except:
            pass
        
        # Fallback to timestamp
        return datetime.now().strftime("%Y%m%d_%H%M%S")
    
    def _get_github_repo_info(self, repo_url):
        """Extract owner, repo, and branch from GitHub URL"""
        if 'github.com' not in repo_url:
            return None
            
        try:
            # Handle different GitHub URL formats
            if '/archive/refs/heads/' in repo_url:
                # Format: https://github.com/owner/repo/archive/refs/heads/branch.zip
                parts = repo_url.split('/')
                owner = parts[3]
                repo = parts[4]
                branch_start = repo_url.find('/archive/refs/heads/') + len('/archive/refs/heads/')
                branch_end = repo_url.find('.zip', branch_start)
                branch = repo_url[branch_start:branch_end]
            else:
                # Format: https://github.com/owner/repo
                parts = repo_url.split('/')
                owner = parts[3]
                repo = parts[4]
                branch = 'main'  # Default branch
                
            return {'owner': owner, 'repo': repo, 'branch': branch}
        except:
            return None
    
    def get_latest_github_release(self):
        """Get the latest release from GitHub."""
        repo_info = self._get_github_repo_info(self.launcher_repo_url)
        if not repo_info:
            return None
        
        try:
            api_url = f"https://api.github.com/repos/{repo_info['owner']}/{repo_info['repo']}/releases/latest"
            headers = _get_github_auth_headers()
            
            response = requests.get(api_url, headers=headers, timeout=10)
            response.raise_for_status()
            
            release_data = response.json()
            
            # Find the .zip asset in the release
            zip_asset = next((asset for asset in release_data.get('assets', []) if asset['name'].endswith('.zip')), None)

            return {
                'tag_name': release_data['tag_name'].lstrip('v'),
                'name': release_data['name'],
                'body': release_data['body'],
                'published_at': release_data['published_at'],
                'zipball_url': release_data['zipball_url'],
                'zip_asset_url': zip_asset['browser_download_url'] if zip_asset else None,
            }
        except Exception as e:
            print(f"Error getting GitHub release: {e}")
            return None
    
    def get_local_update_info(self):
        """Get locally stored update information"""
        if not os.path.exists(self.update_file):
            return None
            
        try:
            with open(self.update_file, 'r') as f:
                return json.load(f)
        except:
            return None
    
    def save_local_update_info(self, update_info):
        """Save update information locally"""
        try:
            with open(self.update_file, 'w') as f:
                json.dump(update_info, f, indent=4)
        except Exception as e:
            print(f"Error saving update info: {e}")
    
    def check_launcher_update(self):
        """Check if a launcher update is available using GitHub Releases."""
        if not is_connected_to_internet():
            return False, None
            
        latest_release = self.get_latest_github_release()
        if not latest_release:
            return False, None
            
        local_version = semver.parse(self.current_version)
        remote_version = semver.parse(latest_release['tag_name'])
        
        if remote_version > local_version:
            return True, {
                'current_version': str(local_version),
                'new_version': str(remote_version),
                'release_name': latest_release['name'],
                'release_body': latest_release['body'],
                'zip_url': latest_release['zip_asset_url'] or latest_release['zipball_url']
            }
        else:
            return False, None
    
    def get_update_changes(self, old_sha, new_sha):
        """Get list of changed files between two commits"""
        repo_info = self._get_github_repo_info(self.launcher_repo_url)
        if not repo_info:
            return None
            
        try:
            api_url = f"https://api.github.com/repos/{repo_info['owner']}/{repo_info['repo']}/compare/{old_sha}...{new_sha}"
            headers = _get_github_auth_headers()
            
            response = requests.get(api_url, headers=headers, timeout=15)
            response.raise_for_status()
            
            compare_data = response.json()
            files = compare_data.get('files', [])
            
            changes = {
                'added': [],
                'modified': [],
                'removed': [],
                'total_files': len(files)
            }
            
            for file_info in files:
                filename = file_info['filename']
                status = file_info['status']
                
                if status == 'added':
                    changes['added'].append(filename)
                elif status == 'modified':
                    changes['modified'].append(filename)
                elif status == 'removed':
                    changes['removed'].append(filename)
                elif status == 'renamed':
                    changes['removed'].append(file_info['previous_filename'])
                    changes['added'].append(filename)
            
            return changes
            
        except Exception as e:
            print(f"Error getting update changes: {e}")
            return None
    
    def download_file_from_github(self, file_path, commit_sha, destination_path):
        """Download a single file from GitHub at specific commit"""
        repo_info = self._get_github_repo_info(self.launcher_repo_url)
        if not repo_info:
            return False
            
        try:
            api_url = f"https://api.github.com/repos/{repo_info['owner']}/{repo_info['repo']}/contents/{file_path}?ref={commit_sha}"
            headers = _get_github_auth_headers()
            
            response = requests.get(api_url, headers=headers, timeout=10)
            response.raise_for_status()
            
            content_data = response.json()
            if 'content' in content_data:
                import base64
                content = base64.b64decode(content_data['content'])
                
                # Ensure directory exists
                os.makedirs(os.path.dirname(destination_path), exist_ok=True)
                
                with open(destination_path, 'wb') as f:
                    f.write(content)
                return True
                
        except Exception as e:
            print(f"Error downloading file {file_path}: {e}")
            return False
    
    def apply_incremental_update(self, changes, new_sha, progress_callback=None):
        """Apply incremental update by downloading only changed files"""
        launcher_dir = os.path.dirname(os.path.dirname(__file__))
        
        print(f"Applying incremental launcher update:")
        print(f"  - Files to add: {len(changes['added'])}")
        print(f"  - Files to modify: {len(changes['modified'])}")
        print(f"  - Files to remove: {len(changes['removed'])}")
        
        # Remove files first
        for file_path in changes['removed']:
            full_path = os.path.join(launcher_dir, file_path)
            if os.path.exists(full_path):
                try:
                    os.remove(full_path)
                    print(f"  Removed: {file_path}")
                except OSError as e:
                    print(f"Error removing {file_path}: {e}")
        
        # Update added/modified files
        files_to_update = changes['added'] + changes['modified']
        total_files = len(files_to_update)
        
        if files_to_update:
            success_count = 0
            for i, file_path in enumerate(files_to_update):
                dest_path = os.path.join(launcher_dir, file_path)
                
                if self.download_file_from_github(file_path, new_sha, dest_path):
                    success_count += 1
                    print(f"  Updated: {file_path}")
                else:
                    print(f"  Failed: {file_path}")
                
                if progress_callback:
                    progress_callback(i + 1, total_files)
            
            print(f"Incremental update completed: {success_count}/{total_files} files updated")
            return success_count == total_files
        else:
            print("No files to update (only deletions)")
            return True
    
    def download_full_update(self, update_info, progress_callback=None):
        """Download a full update from a release URL."""
        
        zip_url = update_info.get('zip_url')
        if not zip_url:
            raise Exception("URL de la release non trouvée.")

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
        except Exception as e:
            shutil.rmtree(temp_dir, ignore_errors=True)
            raise e
    
    def create_update_script(self, new_sha):
        """Create a script to restart the launcher after update"""
        launcher_dir = os.path.dirname(os.path.dirname(__file__))
        script_content = f"""@echo off
cd /d "{launcher_dir}"
python main.py
del "%~f0"
"""
        
        script_path = os.path.join(launcher_dir, "restart_launcher.bat")
        try:
            with open(script_path, 'w') as f:
                f.write(script_content)
            return script_path
        except Exception as e:
            print(f"Error creating restart script: {e}")
            return None
    
    def perform_update(self, update_info, progress_callback=None):
        """Perform a full update from a release."""
        self.signals.status.emit("Téléchargement de la mise à jour...")
        
        zip_path = self.download_full_update(update_info, progress_callback)
        temp_dir = os.path.dirname(zip_path)
        
        try:
            self.signals.status.emit("Extraction des fichiers...")
            
            extract_dir = os.path.join(temp_dir, "extracted")
            with ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)
            
            # The contents are often inside a single root folder in the zip
            extracted_content_dir = extract_dir
            if len(os.listdir(extract_dir)) == 1:
                possible_root = os.path.join(extract_dir, os.listdir(extract_dir)[0])
                if os.path.isdir(possible_root):
                    extracted_content_dir = possible_root

            self.signals.status.emit("Création du script de mise à jour...")
            
            # Use the new version tag for the script
            restart_script = self.create_update_script(extracted_content_dir, update_info['new_version'])
            
            self.signals.status.emit("Mise à jour terminée. Redémarrage en cours...")
            
            return True, restart_script
            
        finally:
            # Clean up the temp directory
            shutil.rmtree(temp_dir, ignore_errors=True)
            self.save_local_update_info({'last_successful_version': update_info['new_version']})

def check_launcher_updates(launcher_repo_url, current_version=None):
    """Convenience function to check for launcher updates"""
    updater = LauncherUpdateManager(launcher_repo_url, current_version)
    return updater.check_launcher_update()

def perform_launcher_update(launcher_repo_url, update_info, use_incremental=True, progress_callback=None):
    """Convenience function to perform launcher update"""
    updater = LauncherUpdateManager(launcher_repo_url)
    return updater.perform_update(update_info, use_incremental, progress_callback)

def is_git_repo():
    main_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.isdir(os.path.join(main_dir, '.git'))
