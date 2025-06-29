import os
import json

class TranslationManager:
    """Gestionnaire de traductions pour le launcher."""
    
    def __init__(self):
        self.translations = {}
        self.current_language = "fr"
        self.languages_dir = os.path.join(os.path.dirname(__file__), "../assets/languages/")
        self.load_language("fr")  # Langue par défaut
    
    def get_available_languages(self):
        """Retourne la liste des langues disponibles."""
        try:
            languages = []
            for file in os.listdir(self.languages_dir):
                if file.endswith('.json'):
                    lang_code = file.replace('.json', '')
                    languages.append(lang_code)
            return languages
        except FileNotFoundError:
            return ["fr", "en"]
    
    def load_language(self, language_code):
        """Charge les traductions pour une langue donnée."""
        try:
            lang_file = os.path.join(self.languages_dir, f"{language_code}.json")
            with open(lang_file, 'r', encoding='utf-8') as f:
                self.translations = json.load(f)
            self.current_language = language_code
            return True
        except Exception as e:
            print(f"Erreur lors du chargement de la langue {language_code}: {e}")
            # Fallback vers français
            try:
                lang_file = os.path.join(self.languages_dir, "fr.json")
                with open(lang_file, 'r', encoding='utf-8') as f:
                    self.translations = json.load(f)
                self.current_language = "fr"
                return True
            except:
                return False
    
    def tr(self, key, **kwargs):
        """Traduit une clé avec formatage optionnel."""
        try:
            # Navigation dans la structure JSON (ex: "main.modpacks_title")
            keys = key.split('.')
            value = self.translations
            for k in keys:
                value = value[k]
            
            # Si la valeur est une chaîne, on applique le formatage éventuel
            if isinstance(value, str):
                if kwargs:
                    return value.format(**kwargs)
                return value
            # Sinon, on retourne la valeur brute (ex: liste pour 'tips')
            return value
        except (KeyError, TypeError):
            # Retourne la clé si la traduction n'est pas trouvée
            return key

# Instance globale du gestionnaire de traductions
translations = TranslationManager() 