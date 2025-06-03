from neo4j import GraphDatabase
from pymongo import MongoClient
from typing import Dict, List
from config import *

class Neo4jLoader:
    def __init__(self):
        self.driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD), database=NEO4J_DATABASE)
        self.mongo_client = MongoClient(MONGO_URI)
        self.db = self.mongo_client[DB_NAME]

    def clean_database(self):
        with self.driver.session() as session:
            session.run("MATCH (n) DETACH DELETE n")
            print("🧹 Base Neo4j nettoyée")

    def create_constraints(self):
        constraints = [
            "CREATE CONSTRAINT arrond_name IF NOT EXISTS FOR (a:Arrondissement) REQUIRE a.name IS UNIQUE",
            "CREATE CONSTRAINT type_name IF NOT EXISTS FOR (t:Type) REQUIRE t.name IS UNIQUE",
            "CREATE CONSTRAINT reglement_name IF NOT EXISTS FOR (r:Reglement) REQUIRE r.name IS UNIQUE",
            "CREATE CONSTRAINT zone_name IF NOT EXISTS FOR (z:Zone) REQUIRE z.name IS UNIQUE",
            "CREATE CONSTRAINT voie_name IF NOT EXISTS FOR (v:Voie) REQUIRE v.name IS UNIQUE",
            "CREATE CONSTRAINT emplacement_id IF NOT EXISTS FOR (e:Emplacement) REQUIRE e.id IS UNIQUE"
        ]

        with self.driver.session() as session:
            for constraint in constraints:
                try:
                    session.run(constraint)
                except Exception as e:
                    print(f"Contrainte déjà existante ou erreur: {e}")

        print("✅ Contraintes créées")

    def load_nodes(self):
        with self.driver.session() as session:
            emplacements = list(self.db[COLLECTION_EMPLACEMENTS].find())
            print(f"🔄 Chargement de {len(emplacements)} emplacements...")
            batch_size = 100
            for i in range(0, len(emplacements), batch_size):
                batch = emplacements[i:i + batch_size]
                self._process_batch(session, batch)
                print(f"  Traité {min(i + batch_size, len(emplacements))}/{len(emplacements)} emplacements")

    def _process_batch(self, session, batch: List[Dict]):
        for emplacement in batch:
            self._create_emplacement_graph(session, emplacement)

    def _create_emplacement_graph(self, session, emplacement: Dict):
        arrond = str(emplacement.get("arrond", "Inconnu"))
        regpri = emplacement.get("regpri", "Inconnu")
        typsta = emplacement.get("typsta", "Inconnu")
        zoneres = emplacement.get("zoneres", "Inconnu")
        nomvoie = emplacement.get("nomvoie", "Inconnue")
        emp_id = str(emplacement.get("id", ""))
        geo_point = emplacement.get("geo_point_2d", {})
        lat = geo_point.get("lat") if geo_point else None
        lon = geo_point.get("lon") if geo_point else None
        placal = emplacement.get("placal", 0)
        surface = emplacement.get("surface_calculee", 0)
        signvert = emplacement.get("signvert", "Inconnue")
        datereleve = emplacement.get("datereleve", "Inconnue")

        query = """
        MERGE (arr:Arrondissement {name: $arrond})
        ON CREATE SET arr.number = toInteger($arrond)

        MERGE (reg:Reglement {name: $regpri})
        ON CREATE SET reg.description = $regpri

        MERGE (typ:Type {name: $typsta})
        ON CREATE SET typ.category = $typsta

        MERGE (zone:Zone {name: $zoneres})
        ON CREATE SET zone.code = $zoneres

        MERGE (voie:Voie {name: $nomvoie})
        ON CREATE SET voie.full_name = $nomvoie

        MERGE (emp:Emplacement {id: $emp_id})
        ON CREATE SET
            emp.places_calcul = $placal,
            emp.surface = $surface,
            emp.signalisation_verticale = $signvert,
            emp.date_releve = $datereleve,
            emp.latitude = $lat,
            emp.longitude = $lon

        MERGE (emp)-[:SITUE_DANS]->(arr)
        MERGE (emp)-[:SOUMIS_A]->(reg)
        MERGE (emp)-[:DE_TYPE]->(typ)
        MERGE (emp)-[:DANS_ZONE]->(zone)
        MERGE (emp)-[:SUR_VOIE]->(voie)

        MERGE (zone)-[:APPARTIENT_A]->(arr)
        MERGE (voie)-[:TRAVERSE]->(arr)
        """

        try:
            session.run(query, {
                "arrond": arrond,
                "regpri": regpri,
                "typsta": typsta,
                "zoneres": zoneres,
                "nomvoie": nomvoie,
                "emp_id": emp_id,
                "placal": placal or 0,
                "surface": surface or 0,
                "signvert": signvert,
                "datereleve": datereleve,
                "lat": lat,
                "lon": lon
            })
        except Exception as e:
            print(f"Erreur lors de la création du graphe pour l'emplacement {emp_id}: {e}")

    def create_advanced_relationships(self):
        print("🔗 Création des relations avancées...")
        advanced_queries = [
            """
            MATCH (e1:Emplacement), (e2:Emplacement)
            WHERE e1 <> e2
                AND e1.latitude IS NOT NULL AND e1.longitude IS NOT NULL
                AND e2.latitude IS NOT NULL AND e2.longitude IS NOT NULL
                AND point.distance(
                    point({latitude: e1.latitude, longitude: e1.longitude}),
                    point({latitude: e2.latitude, longitude: e2.longitude})
                ) < 50
            MERGE (e1)-[:PROCHE_DE {distance: point.distance(
                point({latitude: e1.latitude, longitude: e1.longitude}),
                point({latitude: e2.latitude, longitude: e2.longitude})
            )}]->(e2)
            """,
            """
            MATCH (e1:Emplacement)-[:DE_TYPE]->(t:Type)<-[:DE_TYPE]-(e2:Emplacement)
            WHERE e1 <> e2
            MERGE (e1)-[:MEME_TYPE]->(e2)
            """,
            """
            MATCH (e1:Emplacement)-[:SUR_VOIE]->(v:Voie)<-[:SUR_VOIE]-(e2:Emplacement)
            MATCH (e1)-[:DE_TYPE]->(t1:Type), (e2)-[:DE_TYPE]->(t2:Type)
            WHERE e1 <> e2 AND t1 <> t2
            MERGE (e1)-[:COMPLEMENTAIRE]->(e2)
            """,
            """
            MATCH (arr:Arrondissement)<-[:SITUE_DANS]-(emp:Emplacement)
            WITH arr, count(emp) as nb_emplacements, sum(emp.places_calcul) as total_places
            SET arr.nb_emplacements = nb_emplacements,
                arr.total_places = total_places
            """
        ]

        with self.driver.session() as session:
            for i, query in enumerate(advanced_queries):
                try:
                    session.run(query)
                    print(f"  ✅ Relation avancée {i+1}/{len(advanced_queries)} créée")
                except Exception as e:
                    print(f"  ❌ Erreur relation {i+1}: {e}")

    def load_all_data(self):
        try:
            self.clean_database()
            self.create_constraints()
            self.load_nodes()
            self.create_advanced_relationships()
            print("✅ Chargement Neo4j terminé avec succès")
        except Exception as e:
            print(f"❌ Erreur lors du chargement Neo4j: {e}")
        finally:
            self.driver.close()
            self.mongo_client.close()

def insert_neo4j():
    loader = Neo4jLoader()
    loader.load_all_data()

if __name__ == "__main__":
    insert_neo4j()
