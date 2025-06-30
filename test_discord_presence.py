from pypresence import Presence
import time

CLIENT_ID = "1389266601693679838"  # Ton Application ID

try:
    rpc = Presence(CLIENT_ID)
    rpc.connect()
    print("Connexion à Discord réussie !")
    rpc.update(
        details="Test Rich Presence",
        state="Ça marche !",
        large_image="logo",
        large_text="CatzLauncher"
    )
    print("Rich Presence envoyée. Regarde Discord !")
    time.sleep(30)  # Laisse le temps de voir sur Discord
    rpc.close()
    print("Déconnexion propre.")
except Exception as e:
    print(f"Erreur : {e}") 