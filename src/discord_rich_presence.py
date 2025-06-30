from pypresence import Presence
import time
import threading

CLIENT_ID = "1389266601693679838"  # Remplace par ton Application ID

class DiscordRichPresence:
    def __init__(self):
        self.rpc = Presence(CLIENT_ID)
        self.connected = False
        self.thread = None

    def connect(self):
        try:
            self.rpc.connect()
            self.connected = True
            self.update_presence()
            # Lancer un thread pour garder la connexion vivante
            self.thread = threading.Thread(target=self._keep_alive, daemon=True)
            self.thread.start()
        except Exception as e:
            print(f"Erreur de connexion à Discord Rich Presence : {e}")

    def update_presence(self, details="Sur le launcher", state="Prêt à jouer !"):
        if self.connected:
            try:
                self.rpc.update(
                    details=details,
                    state=state,
                    large_image="logo",  # Doit être uploadé dans le portail Discord (Assets)
                    large_text="CatzLauncher"
                )
            except Exception as e:
                print(f"Erreur lors de la mise à jour de la Rich Presence : {e}")

    def _keep_alive(self):
        while self.connected:
            try:
                self.rpc.update()
            except Exception:
                pass
            time.sleep(15)

    def disconnect(self):
        self.connected = False
        try:
            self.rpc.close()
        except Exception:
            pass 