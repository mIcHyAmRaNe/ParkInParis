import requests
import time
from typing import List, Dict, Optional
from config import API_URL_EMPLACEMENTS

class EmplacementsFetcher:
    def __init__(self, api_url: str = API_URL_EMPLACEMENTS):
        self.api_url = api_url
        self.session = requests.Session()

    def fetch_emplacements(self, limit: Optional[int] = None, offset: int = 0, filters: Dict = None) -> List[Dict]:
        params = {"offset": offset}
        if limit:
            params["limit"] = limit

        if filters:
            where_clauses = []
            if "arrondissement" in filters:
                where_clauses.append(f"arrond = {filters['arrondissement']}")
            if "regpri" in filters:
                where_clauses.append(f"regpri = '{filters['regpri']}'")
            if "zoneres" in filters:
                where_clauses.append(f"zoneres = '{filters['zoneres']}'")
            if "typsta" in filters:
                where_clauses.append(f"typsta = '{filters['typsta']}'")

            if where_clauses:
                params["where"] = " AND ".join(where_clauses)

        try:
            response = self.session.get(self.api_url, params=params)
            response.raise_for_status()
            data = response.json()
            return data.get("results", [])
        except requests.RequestException as e:
            print(f"Erreur lors de la récupération des emplacements: {e}")
            return []

    """
    Récupère tous les emplacements en effectuant des requêtes par lots.
    Cette méthode permet de récupérer tous les emplacements disponibles en effectuant des requêtes
    successives avec un paramètre de taille de lot (batch_size).
    Cette approche est utile pour éviter de surcharger le serveur avec une seule requête massive
    et pour gérer les limites d'API ou de mémoire.
    
    Args:
        batch_size (int): Nombre d'emplacements à récupérer par requête.
    Returns:
        List[Dict]: Liste de tous les emplacements récupérés.
    """
    def fetch_all_emplacements(self, batch_size: int = 100) -> List[Dict]:
        all_emplacements = []
        offset = 0

        while True:
            batch = self.fetch_emplacements(limit=batch_size, offset=offset)
            if not batch:
                break

            all_emplacements.extend(batch)
            print(f"Récupéré {len(all_emplacements)} emplacements...")

            if len(batch) < batch_size:
                break

            offset += batch_size
            time.sleep(0.1)

        return all_emplacements

    def get_unique_values(self, field: str) -> List[str]:
        try:
            sample = self.fetch_emplacements(limit=100)
            unique_values = list(set([item.get(field) for item in sample if item.get(field)]))
            return sorted(unique_values)
        except Exception as e:
            print(f"Erreur lors de la récupération des valeurs uniques: {e}")
            return []
