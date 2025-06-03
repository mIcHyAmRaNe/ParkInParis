from pymongo import MongoClient, IndexModel
from datetime import datetime
from typing import List, Dict
from config import MONGO_URI, DB_NAME, COLLECTION_EMPRISES, COLLECTION_EMPLACEMENTS
from .fetch_emprises import EmprisesFetcher
from .fetch_emplacements import EmplacementsFetcher

class MongoLoader:
    def __init__(self):
        self.client = MongoClient(MONGO_URI)
        self.db = self.client[DB_NAME]
        self.emprises_fetcher = EmprisesFetcher()
        self.emplacements_fetcher = EmplacementsFetcher()

    def create_indexes(self):
        """
        Crée les index pour optimiser les requêtes dans MongoDB.
        """
        emprises_indexes = [
            IndexModel([("arrond", 1)]),
            IndexModel([("regpri", 1)]),
            IndexModel([("typsta", 1)]),
            IndexModel([("zoneres", 1)]),
            IndexModel([("geo_point_2d", "2dsphere")]),
            IndexModel([("arrond", 1), ("regpri", 1)]),
            IndexModel([("datereleve", -1)])
        ]

        emplacements_indexes = [
            IndexModel([("arrond", 1)]),
            IndexModel([("regpri", 1)]),
            IndexModel([("typsta", 1)]),
            IndexModel([("zoneres", 1)]),
            IndexModel([("geo_point_2d", "2dsphere")]),
            IndexModel([("arrond", 1), ("regpri", 1)]),
            IndexModel([("nomvoie", "text")]),
            IndexModel([("datereleve", -1)])
        ]

        self.db[COLLECTION_EMPRISES].create_indexes(emprises_indexes)
        self.db[COLLECTION_EMPLACEMENTS].create_indexes(emplacements_indexes)
        print("✅ Index créés avec succès")

    def clean_data(self, data: List[Dict]) -> List[Dict]:
        """
        Nettoie et standardise les données avant de les insérer dans MongoDB.
        Args:
            data (List[Dict]): Liste des documents à nettoyer.
        Returns:
            List[Dict]: Liste des documents nettoyés.
        """
        cleaned_data = []
        for item in data:
            if "geo_point_2d" in item and item["geo_point_2d"]:
                geo_point = item["geo_point_2d"]
                if isinstance(geo_point, dict) and "lat" in geo_point and "lon" in geo_point:
                    lat, lon = geo_point["lat"], geo_point["lon"]
                    if 48.8 <= lat <= 48.9 and 2.2 <= lon <= 2.5:
                        item["location"] = {
                            "type": "Point",
                            "coordinates": [lon, lat]
                        }

            item["loaded_at"] = datetime.utcnow()
            item["arrond"] = int(item.get("arrond", 0)) if item.get("arrond") else None

            for field in ["regpri", "typsta", "nomvoie", "zoneres"]:
                if field in item and item[field]:
                    item[field] = str(item[field]).strip()

            cleaned_data.append(item)

        return cleaned_data

    def load_emprises(self, use_cache: bool = True) -> int:
        """
        Charge les emprises dans MongoDB.
        Args:
            use_cache (bool): Utiliser le cache si disponible.
        Returns:
            int: Nombre d'emprises chargées.
        """
        print("🔄 Chargement des emprises...")
        self.db[COLLECTION_EMPRISES].delete_many({})
        emprises = self.emprises_fetcher.fetch_all_emprises()

        if emprises:
            clean_emprises = self.clean_data(emprises)
            batch_size = 100
            for i in range(0, len(clean_emprises), batch_size):
                batch = clean_emprises[i:i + batch_size]
                self.db[COLLECTION_EMPRISES].insert_many(batch)
                print(f"  Inséré {min(i + batch_size, len(clean_emprises))}/{len(clean_emprises)} emprises")

        return len(emprises)

    def load_emplacements(self, use_cache: bool = True) -> int:
        """
        Charge les emplacements dans MongoDB.
        Args:
            use_cache (bool): Utiliser le cache si disponible.
        Returns:
            int: Nombre d'emplacements chargés.
        """
        print("🔄 Chargement des emplacements...")
        self.db[COLLECTION_EMPLACEMENTS].delete_many({})
        emplacements = self.emplacements_fetcher.fetch_all_emplacements()

        if emplacements:
            clean_emplacements = self.clean_data(emplacements)
            batch_size = 500
            for i in range(0, len(clean_emplacements), batch_size):
                batch = clean_emplacements[i:i + batch_size]
                self.db[COLLECTION_EMPLACEMENTS].insert_many(batch)
                print(f"  Inséré {min(i + batch_size, len(clean_emplacements))}/{len(clean_emplacements)} emplacements")

        return len(emplacements)

    def load_all_data(self):
        """
        Charge toutes les données dans MongoDB.
        """
        try:
            self.create_indexes()
            emprises_count = self.load_emprises()
            emplacements_count = self.load_emplacements()

            print(f"✅ Chargement terminé:")
            print(f"  - {emprises_count} emprises")
            print(f"  - {emplacements_count} emplacements")

        except Exception as e:
            print(f"❌ Erreur lors du chargement: {e}")
        finally:
            self.client.close()

def load_data():
    """
    Point d'entrée principal pour le chargement des données.
    """
    loader = MongoLoader()
    loader.load_all_data()

if __name__ == "__main__":
    load_data()
