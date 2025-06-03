import requests
import time
from typing import List, Dict, Optional
from config import API_URL_EMPRISES

class EmprisesFetcher:
    def __init__(self, api_url: str = API_URL_EMPRISES):
        """
        Initialise le récupérateur d'emprises avec l'URL de l'API.

        Args:
            api_url (str): L'URL de l'API pour récupérer les emprises.
        """
        self.api_url = api_url
        self.session = requests.Session()

    def fetch_emprises(self, limit: Optional[int] = None, offset: int = 0, filters: Dict = None) -> List[Dict]:
        """
        Récupère les emprises de stationnement avec pagination et filtres.

        Args:
            limit (Optional[int]): Nombre maximum d'enregistrements à récupérer.
            offset (int): Décalage pour la pagination.
            filters (Dict): Dictionnaire de filtres (arrondissement, type, etc.).

        Returns:
            List[Dict]: Liste des emprises récupérées.
        """
        params = {"offset": offset}
        if limit:
            params["limit"] = limit

        if filters:
            if "arrondissement" in filters:
                params["where"] = f"arrond = {filters['arrondissement']}"
            if "regpri" in filters:
                regpri_filter = f"regpri = '{filters['regpri']}'"
                if "where" in params:
                    params["where"] += f" AND {regpri_filter}"
                else:
                    params["where"] = regpri_filter

        try:
            response = self.session.get(self.api_url, params=params)
            response.raise_for_status()
            data = response.json()
            return data.get("results", [])
        except requests.RequestException as e:
            print(f"Erreur lors de la récupération des emprises: {e}")
            return []

    def fetch_all_emprises(self, batch_size: int = 100) -> List[Dict]:
        """
        Récupère toutes les emprises par batches.

        Args:
            batch_size (int): Taille des batches pour la récupération des données.

        Returns:
            List[Dict]: Liste complète des emprises récupérées.
        """
        all_emprises = []
        offset = 0

        while True:
            batch = self.fetch_emprises(limit=batch_size, offset=offset)
            if not batch:
                break

            all_emprises.extend(batch)
            print(f"Récupéré {len(all_emprises)} emprises...")

            if len(batch) < batch_size:
                break

            offset += batch_size
            time.sleep(0.1)  # Éviter de surcharger l'API

        return all_emprises
