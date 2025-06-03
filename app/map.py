from pymongo import MongoClient
import folium
from folium.plugins import MarkerCluster
from neo4j import GraphDatabase
from geopy.geocoders import Nominatim
from geopy.distance import geodesic
from config import *


# Initialisation du géolocalisateur
geolocator = Nominatim(user_agent="paris_parking_app")

class ParkingService:
    """Service for managing parking data and operations.
    Cette classe fournit des méthodes pour rechercher des emplacements de stationnement,
    filtrer par proximité, créer des cartes et obtenir des valeurs uniques pour certains champs.
    """
    def __init__(self):
        """Initialise le service avec les connexions à la base de données MongoDB et Neo4j."""
        self.mongo_client = MongoClient(MONGO_URI)
        self.db = self.mongo_client[DB_NAME]
        self.neo4j_driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD), database=NEO4J_DATABASE)

    def search_emplacements(self, filters: dict, limit: int = 500):
        """Recherche des emplacements de stationnement en fonction des filtres fournis.
        Args:
            filters (dict): Dictionnaire contenant les filtres de recherche.
            limit (int): Nombre maximum d'emplacements à retourner.
        Returns:
            List[Dict]: Liste des emplacements de stationnement correspondant aux filtres.
        """
        if filters.get("address"):
            location = geolocator.geocode(filters["address"])
            if location:
                user_coords = (location.latitude, location.longitude)
                # Recherche tous les emplacements
                emplacements = list(self.db[COLLECTION_EMPLACEMENTS].find({}))
                # Filtre par proximité
                return self.filter_by_proximity(emplacements, user_coords, radius=500)
            else:
                return []
        else:
            query = {}

            if filters.get("arrondissement"):
                query["arrond"] = int(filters["arrondissement"])

            if filters.get("regpri"):
                query["regpri"] = {"$regex": filters["regpri"], "$options": "i"}

            if filters.get("typsta"):
                query["typsta"] = {"$regex": filters["typsta"], "$options": "i"}

            if filters.get("zoneres"):
                query["zoneres"] = filters["zoneres"]

            if filters.get("nomvoie"):
                query["nomvoie"] = {"$regex": filters["nomvoie"], "$options": "i"}

            return list(self.db[COLLECTION_EMPLACEMENTS].find(query).limit(limit))

    def filter_by_proximity(self, emplacements, user_coords, radius=2000):
        """Filtre les emplacements de stationnement par proximité d'un point géographique.
        Args:
            emplacements (List[Dict]): Liste des emplacements de stationnement.
            user_coords (tuple): Coordonnées de l'utilisateur sous forme de tuple (latitude, longitude).
            radius (int): Rayon de filtrage en mètres.
        Returns:
            List[Dict]: Liste des emplacements filtrés par proximité.
        """
        filtered_emplacements = []
        for emp in emplacements:
            geo_point = emp.get("geo_point_2d")
            if geo_point and "lat" in geo_point and "lon" in geo_point:
                emp_coords = (geo_point["lat"], geo_point["lon"])
                distance = geodesic(user_coords, emp_coords).meters
                if distance <= radius:
                    filtered_emplacements.append(emp)
        return filtered_emplacements

    def get_unique_values(self, field: str):
        """
        Récupère les valeurs uniques d'un champ spécifique dans la collection des emplacements.
        Args:
            field (str): Le nom du champ pour lequel récupérer les valeurs uniques.
        Returns:
            List[str]: Liste des valeurs uniques pour le champ spécifié.
        Cette méthode interroge la collection des emplacements pour obtenir les valeurs uniques
        d'un champ donné. Elle utilise la méthode distinct de MongoDB pour récupérer les valeurs
        uniques, ce qui est efficace pour les champs indexés.
        Exemple d'utilisation:
            unique_regpri = parking_service.get_unique_values("regpri")
            unique_typsta = parking_service.get_unique_values("typsta")
        """
        return self.db[COLLECTION_EMPLACEMENTS].distinct(field)

    def create_map(self, emplacements, center=None, use_clusters=True):
        """
        Crée une carte Folium avec les emplacements de stationnement.
        Args:
            emplacements (List[Dict]): Liste des emplacements de stationnement à afficher.
            center (List[float]): Coordonnées [latitude, longitude] pour centrer la carte.
            use_clusters (bool): Indique si les marqueurs doivent être regroupés en clusters.
        Returns:
            str: Chemin vers le fichier HTML de la carte générée.
        Cette méthode crée une carte interactive en utilisant la bibliothèque Folium.
        Elle ajoute des marqueurs pour chaque emplacement de stationnement, avec des popups
        contenant des informations détaillées sur chaque emplacement.
        Si `use_clusters` est True et que le nombre d'emplacements dépasse 50, les marqueurs
        seront regroupés en clusters pour une meilleure visualisation.
        Si `center` n'est pas fourni, la carte sera centrée sur Paris (48.8566, 2.3522).
        Exemple d'utilisation:
            map_path = parking_service.create_map(emplacements, center=[48.8566, 2.3522], use_clusters=True)
            return render_template("map.html", map_path=map_path)
        """
        if not center:
            center = [48.8566, 2.3522]

        m = folium.Map(location=center, zoom_start=13)

        if use_clusters and len(emplacements) > 50:
            marker_cluster = MarkerCluster().add_to(m)
        else:
            marker_cluster = m

        color_map = {
            "PAYANT": "red",
            "GIG/GIC": "blue",
            "2 ROUES": "green",
            "LIVRAISON": "orange",
            "AUTOLIB": "purple",
            "TAXI": "yellow"
        }

        for emp in emplacements:
            geo_point = emp.get("geo_point_2d")
            if not geo_point or "lat" not in geo_point or "lon" not in geo_point:
                continue

            regpri = emp.get("regpri", "AUTRE")
            color = color_map.get(regpri, "gray")

            popup_html = f"""
            <div style="font-family: Arial; min-width: 200px;">
                <h4 style="margin: 0 0 10px 0; color: #2c3e50;">{emp.get('nomvoie', 'Voie inconnue')}</h4>
                <p><strong>Type:</strong> {emp.get('typsta', 'N/A')}</p>
                <p><strong>Règlement:</strong> {emp.get('regpri', 'N/A')}</p>
                <p><strong>Arrondissement:</strong> {emp.get('arrond', 'N/A')}</p>
                <p><strong>Zone:</strong> {emp.get('zoneres', 'N/A')}</p>
                <p><strong>Places:</strong> {emp.get('placal', 0)}</p>
                <p><strong>Surface:</strong> {emp.get('surface_calculee', 0):.1f} m²</p>
            </div>
            """

            folium.Marker(
                location=[geo_point["lat"], geo_point["lon"]],
                popup=folium.Popup(popup_html, max_width=300),
                icon=folium.Icon(color=color, icon="car", prefix="fa"),
                tooltip=f"{emp.get('nomvoie', 'Voie inconnue')} - {regpri}"
            ).add_to(marker_cluster)

        map_path = "app/templates/map.html"
        m.save(map_path)
        return map_path
