from neo4j import GraphDatabase
from typing import List, Dict
from config import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD, NEO4J_DATABASE

class Neo4jQueries:
    def __init__(self):
        """
        Initialise la connexion à la base de données Neo4j.
        """
        self.driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD), database=NEO4J_DATABASE)

    def get_nearby_alternatives(self, lat: float, lon: float, radius: int = 100) -> List[Dict]:
        """
        Récupère les emplacements de stationnement à proximité d'une position géographique donnée.
        Args:
            lat (float): Latitude de la position.
            lon (float): Longitude de la position.
            radius (int): Rayon en mètres pour la recherche des emplacements à proximité.
        Returns:
            List[Dict]: Liste de dictionnaires contenant les informations des emplacements à proximité.
        """
        query = """
        MATCH (emp:Emplacement)
        WHERE emp.latitude IS NOT NULL AND emp.longitude IS NOT NULL
        AND point.distance(
            point({latitude: $lat, longitude: $lon}),
            point({latitude: emp.latitude, longitude: emp.longitude})
        ) < $radius
        MATCH (emp)-[:DE_TYPE]->(typ:Type)
        MATCH (emp)-[:SOUMIS_A]->(reg:Reglement)
        MATCH (emp)-[:SUR_VOIE]->(voie:Voie)
        RETURN
            emp.id as id,
            voie.name as voie,
            typ.name as type,
            reg.name as reglement,
            emp.places_calcul as places,
            emp.latitude as lat,
            emp.longitude as lon,
            point.distance(
                point({latitude: $lat, longitude: $lon}),
                point({latitude: emp.latitude, longitude: emp.longitude})
            ) as distance
        ORDER BY distance ASC
        LIMIT 20
        """
        with self.driver.session() as session:
            result = session.run(query, lat=lat, lon=lon, radius=radius)
            return [dict(record) for record in result]

    def get_zones_by_arrondissement(self, arrondissement: int) -> List[Dict]:
        """
        Récupère les zones de règlement pour un arrondissement spécifique.
        Args:
            arrondissement (int): Le numéro de l'arrondissement pour lequel récupérer les zones.
        Returns:
            List[Dict]: Liste des zones de règlement pour l'arrondissement spécifié.
        """
        query = """
        MATCH (a:Arrondissement {number: $arrond})<-[:APPARTIENT_A]-(z:Zone)
        RETURN z.name as zone
        """
        with self.driver.session() as session:
            result = session.run(query, arrond=arrondissement)
            return [record["zone"] for record in result]

    def close(self):
        """
        Ferme la connexion à la base de données Neo4j.
        """
        self.driver.close()
