from pypresence import Presence
import time

CLIENT_ID = "1389266601693679838"

rpc = Presence(CLIENT_ID)
rpc.connect()
rpc.update(
    details="Test bouton",
    state="Test bouton GitHub",
    large_image="logo",
    buttons=[{"label": "Voir sur GitHub", "url": "https://github.com/Locktix/CatzLauncher"}]
)
print("Regarde sur ton profil Discord (grande carte) !")
time.sleep(60)
rpc.close() 