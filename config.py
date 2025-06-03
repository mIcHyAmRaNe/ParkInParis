import os
from dotenv import load_dotenv

# Charger les variables d'environnement depuis le fichier .env
load_dotenv()

# MongoDB Configuration
MONGO_URI = os.getenv("MONGO_URI")
DB_NAME = os.getenv("DB_NAME")
COLLECTION_EMPRISES = "emprises"
COLLECTION_EMPLACEMENTS = "emplacements"

# Neo4j Configuration
NEO4J_URI = os.getenv("NEO4J_URI")
NEO4J_DATABASE = os.getenv("NEO4J_DATABASE")
NEO4J_USER = os.getenv("NEO4J_USER")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")

# API Configuration
API_URL_EMPRISES = "https://opendata.iledefrance.fr/api/explore/v2.1/catalog/datasets/stationnement-sur-voie-publique-emprises/records"
API_URL_EMPLACEMENTS = "https://opendata.iledefrance.fr/api/explore/v2.1/catalog/datasets/stationnement-sur-voie-publique-emplacements/records"

# Application Configuration
FLASK_HOST = "127.0.0.1"
FLASK_PORT = 8080
FLASK_DEBUG = True