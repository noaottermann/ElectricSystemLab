import json
import logging
import os
from typing import Optional


class Translator:
    """Gestionnaire d'internationalisation basé sur des fichiers de localisation JSON.

    Permet de charger des traductions à la volée et d'obtenir les chaînes
    traduites correspondant à des clés données.
    """

    _translations: dict[str, str] = {}
    _current_lang: str = "fr"

    BASE_DIR: str = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    LOCALES_DIR: str = os.path.join(BASE_DIR, "locales")

    @classmethod
    def load_language(cls, lang_code: str) -> bool:
        """Charge le fichier JSON de la langue demandée.

        Args:
            lang_code: Code ISO de la langue (ex: 'fr', 'en').

        Returns:
            True si le chargement a réussi.

        Raises:
            FileNotFoundError: Si le fichier de langue correspondant est introuvable.
            json.JSONDecodeError: Si le fichier JSON est malformé.
            RuntimeError: Si une autre erreur survient lors du chargement.
        """
        filepath = os.path.join(cls.LOCALES_DIR, f"{lang_code}.json")
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Language file not found: {filepath}")
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                cls._translations = json.load(f)

            cls._current_lang = lang_code
            logging.info(f"Language loaded: {lang_code}")
            return True
        except json.JSONDecodeError as e:
            raise json.JSONDecodeError(f"The {lang_code}.json file is malformed", e.doc, e.pos)
        except Exception as e:
            raise RuntimeError(f"Unable to load language: {e}")

    @classmethod
    def tr(cls, key: str) -> str:
        """Retourne la traduction de la clé ou la clé elle-même si elle est absente.

        Args:
            key: Identifiant de la chaîne à traduire.

        Returns:
            Texte traduit ou clé brute par défaut.
        """
        return cls._translations.get(key, key)

    @classmethod
    def get_current_lang(cls) -> str:
        """Retourne le code de la langue courante active.

        Returns:
            Code de langue (ex: 'fr').
        """
        return cls._current_lang