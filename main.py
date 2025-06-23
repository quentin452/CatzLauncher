import sys
import os
import subprocess
from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QIcon
from src.launcher import MinecraftLauncher

def update_version_from_git():
    """
    If running from a git repository, update version.txt with the current commit hash.
    This function is intended for development environments.
    """
    if not os.path.isdir('.git'):
        return

    try:
        # First, verify it's a functional git repo.
        subprocess.run(
            ['git', 'rev-parse', '--is-inside-work-tree'],
            check=True, capture_output=True, text=True
        )
    except subprocess.CalledProcessError as e:
        # If the error is due to 'dubious ownership', try to fix it automatically.
        if "dubious ownership" in e.stderr:
            print("INFO: 'dubious ownership' detected. Attempting to run auto-fix.")
            try:
                repo_path = os.path.abspath(os.getcwd())
                subprocess.run(
                    ['git', 'config', '--global', '--add', 'safe.directory', repo_path],
                    check=True, capture_output=True
                )
                print(f"INFO: Successfully added '{repo_path}' to git's safe directories.")
                print("INFO: Please restart the application for the change to take effect.")
            except (subprocess.CalledProcessError, FileNotFoundError) as fix_e:
                # If the fix fails, print a warning.
                print(f"WARNING: Automatic fix for git ownership failed: {fix_e}")
        # For this or any other git error, we exit the function silently.
        return
    except FileNotFoundError:
        # Git not installed.
        return

    # If the check above passed, we can safely proceed to get the commit hash.
    try:
        commit_hash = subprocess.check_output(
            ['git', 'rev-parse', '--short', 'HEAD'],
            stderr=subprocess.DEVNULL
        ).strip().decode('utf-8')
        
        current_content = ""
        if os.path.exists('version.txt'):
            with open('version.txt', 'r', encoding='utf-8') as f:
                current_content = f.read().strip()
        
        if current_content != commit_hash:
            with open('version.txt', 'w', encoding='utf-8') as f:
                f.write(commit_hash)

    except (subprocess.CalledProcessError, FileNotFoundError):
        # This might happen if there are no commits yet. Safe to ignore.
        pass
    except IOError as e:
        print(f"WARNING: Could not write to version.txt: {e}")

def ensure_version_file_exists():
    """
    Ensures version.txt exists. If not, creates it with a default "0.0.0".
    This is a fallback for non-git users, ensuring the app has a version to read.
    """
    if not os.path.exists('version.txt'):
        try:
            with open('version.txt', 'w', encoding='utf-8') as f:
                f.write('0.0.0')
        except IOError as e:
            print(f"ERROR: Could not create a default version.txt: {e}")

def main():
    update_version_from_git()
    ensure_version_file_exists()
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon("assets/textures/logo.ico"))
    window = MinecraftLauncher()
    window.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()