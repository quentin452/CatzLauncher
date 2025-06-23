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
    
    def get_github_last_commit(self):
        """Get the latest commit from GitHub"""
        repo_info = self._get_github_repo_info(self.launcher_repo_url)
        if not repo_info:
            return None
            
        try:
            api_url = f"https://api.github.com/repos/{repo_info['owner']}/{repo_info['repo']}/commits/{repo_info['branch']}"
            headers = _get_github_auth_headers()
            
            response = requests.get(api_url, headers=headers, timeout=10)
            response.raise_for_status()
            
            commit_data = response.json()
            return {
                'sha': commit_data['sha'],
                'short_sha': commit_data['sha'][:8],
                'date': commit_data['commit']['author']['date'],
                'message': commit_data['commit']['message'],
                'url': commit_data['html_url']
            }
        except Exception as e:
            print(f"Error getting GitHub commit: {e}")
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
        """Check if a launcher update is available"""
        if not is_connected_to_internet():
            return False, None
            
        try:
            # Get latest commit from GitHub
            latest_commit = self.get_github_last_commit()
            if not latest_commit:
                return False, None
            
            # Get local update info
            local_info = self.get_local_update_info()
            
            # If no local info or different commit, update is available
            if not local_info or local_info.get('sha') != latest_commit['sha']:
                update_info = {
                    'current_version': self.current_version,
                    'new_version': latest_commit['short_sha'],
                    'commit_sha': latest_commit['sha'],
                    'commit_date': latest_commit['date'],
                    'commit_message': latest_commit['message'],
                    'commit_url': latest_commit['url'],
                    'repo_url': self.launcher_repo_url
                }
                return True, update_info
            
            return False, None
            
        except Exception as e:
            print(f"Error checking for updates: {e}")
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
    
    def download_full_update(self, progress_callback=None):
        """Download full launcher update as ZIP"""
        repo_info = self._get_github_repo_info(self.launcher_repo_url)
        if not repo_info:
            return False
            
        try:
            # Create temporary directory for update
            temp_dir = tempfile.mkdtemp()
            zip_path = os.path.join(temp_dir, "launcher_update.zip")
            
            # Download ZIP from GitHub
            zip_url = f"https://github.com/{repo_info['owner']}/{repo_info['repo']}/archive/refs/heads/{repo_info['branch']}.zip"
            
            self.signals.status.emit("Downloading launcher update...")
            
            response = requests.get(zip_url, stream=True, timeout=30)
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0
            
            with open(zip_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if progress_callback and total_size > 0:
                            progress_callback(downloaded, total_size)
            
            # Extract ZIP
            self.signals.status.emit("Extracting update...")
            launcher_dir = os.path.dirname(os.path.dirname(__file__))
            
            with ZipFile(zip_path, 'r') as zip_ref:
                # Get the root folder name from the ZIP
                root_folder = zip_ref.namelist()[0].split('/')[0]
                
                # Extract to temporary location first
                extract_temp = os.path.join(temp_dir, "extracted")
                zip_ref.extractall(extract_temp)
                
                # Move files from extracted folder to launcher directory
                extracted_root = os.path.join(extract_temp, root_folder)
                
                # Copy files, preserving structure
                for root, dirs, files in os.walk(extracted_root):
                    # Calculate relative path
                    rel_path = os.path.relpath(root, extracted_root)
                    target_dir = os.path.join(launcher_dir, rel_path)
                    
                    # Create directories
                    os.makedirs(target_dir, exist_ok=True)
                    
                    # Copy files
                    for file in files:
                        src_file = os.path.join(root, file)
                        dst_file = os.path.join(target_dir, file)
                        shutil.copy2(src_file, dst_file)
            
            # Cleanup
            shutil.rmtree(temp_dir)
            return True
            
        except Exception as e:
            print(f"Error downloading full update: {e}")
            return False
    
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
    
    def perform_update(self, update_info, use_incremental=True, progress_callback=None):
        """Perform the launcher update"""
        try:
            new_sha = update_info['commit_sha']
            local_info = self.get_local_update_info()
            
            if use_incremental and local_info and local_info.get('sha'):
                # Try incremental update
                changes = self.get_update_changes(local_info['sha'], new_sha)
                if changes:
                    self.signals.status.emit("Applying incremental update...")
                    success = self.apply_incremental_update(changes, new_sha, progress_callback)
                else:
                    # Fallback to full update
                    success = self.download_full_update(progress_callback)
            else:
                # Full update
                success = self.download_full_update(progress_callback)
            
            if success:
                # Save new update info
                self.save_local_update_info({
                    'sha': new_sha,
                    'version': update_info['new_version'],
                    'date': update_info['commit_date'],
                    'message': update_info['commit_message']
                })
                
                # Create restart script
                restart_script = self.create_update_script(new_sha)
                
                return True, restart_script
            else:
                return False, None
                
        except Exception as e:
            print(f"Error performing update: {e}")
            return False, None

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
