import sys
from utils import install

# Dépendances auto
try:
    import minecraft_launcher_lib
except ImportError:
    install("minecraft-launcher-lib")

try:
    from PIL import Image, ImageTk
except ImportError:
    install("pillow")

from ui import MinecraftLauncher

if __name__ == "__main__":
    app = MinecraftLauncher()
    app.mainloop()