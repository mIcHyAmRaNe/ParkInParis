from flask import Flask, render_template, request, jsonify
from .map import ParkingService
from config import *

app = Flask(__name__)
app.secret_key = "paris_parking_secret_key"

parking_service = ParkingService()

@app.route("/")
def index():
    """
    Page d'accueil de l'application.
    Affiche les filtres disponibles pour la recherche d'emplacements de stationnement
    et initialise les valeurs uniques pour les types de règlement, types de stationnement
    et zones de règlement.
    Returns:
        Rendered HTML template for the index page.
    """
    arrondissements = list(range(1, 21))
    types_reglement = parking_service.get_unique_values("regpri")
    types_station = parking_service.get_unique_values("typsta")
    zones = parking_service.get_unique_values("zoneres")

    return render_template("index.html",
                         arrondissements=arrondissements,
                         types_reglement=types_reglement,
                         types_station=types_station,
                         zones=zones)

@app.route("/search", methods=["POST"])
def search():
    """
    Recherche des emplacements de stationnement en fonction des filtres fournis par l'utilisateur.
    Cette méthode récupère les filtres depuis le formulaire de recherche, effectue une requête dans la base de données
    MongoDB pour récupérer les emplacements de stationnement correspondants, et crée une carte
    avec les résultats. Elle utilise la classe ParkingService pour gérer les opérations de recherche
    et de création de carte.
    Args:
        request (Flask Request): La requête contenant les données du formulaire de recherche.
    Returns:
        Rendered HTML template for the index page with search results.
    """
    # Récupération des filtres depuis le formulaire
    filters = {
        "arrondissement": request.form.get("arrondissement"),
        "regpri": request.form.get("regpri"),
        "typsta": request.form.get("typsta"),
        "zoneres": request.form.get("zoneres"),
        "nomvoie": request.form.get("nomvoie"),
        "address": request.form.get("address")
    }

    # Filtrer les valeurs vides pour éviter les requêtes inutiles
    filters = {k: v for k, v in filters.items() if v}
    results = parking_service.search_emplacements(filters)

    # Si aucun résultat n'est trouvé, on utilise Paris comme centre par défaut
    center = [48.8566, 2.3522]
    if results and results[0].get("geo_point_2d"):
        geo = results[0]["geo_point_2d"]
        if "lat" in geo and "lon" in geo:
            center = [geo["lat"], geo["lon"]]

    # Création de la carte avec les résultats
    parking_service.create_map(results, center)

    return render_template("index.html",
                         results=results,
                         nb_results=len(results),
                         filters=filters,
                         arrondissements=list(range(1, 21)),
                         types_reglement=parking_service.get_unique_values("regpri"),
                         types_station=parking_service.get_unique_values("typsta"),
                         zones=parking_service.get_unique_values("zoneres"))

@app.route("/api/zones/<int:arrondissement>")
def get_zones_by_arrondissement(arrondissement):
    """
    Récupère les zones de règlement pour un arrondissement spécifique.
    Cette route API interroge la base de données Neo4j pour obtenir les zones de règlement
    associées à un arrondissement donné. Elle renvoie les résultats sous forme de liste JSON.
    Args:
        arrondissement (int): Le numéro de l'arrondissement pour lequel récupérer les zones.
    Returns:
        JSON: Liste des zones de règlement pour l'arrondissement spécifié.
    """
    # Vérification que l'arrondissement est valide
    query = """
    MATCH (a:Arrondissement {number: $arrond})<-[:APPARTIENT_A]-(z:Zone)
    RETURN z.name as zone
    """
    with parking_service.neo4j_driver.session() as session:
        result = session.run(query, arrond=arrondissement)
        zones = [record["zone"] for record in result]
    return jsonify(zones)

@app.route("/map")
def show_map():
    """
    Affiche la carte des emplacements de stationnement.
    Cette route génère une carte interactive avec les emplacements de stationnement
    disponibles dans la base de données. Elle utilise la classe ParkingService pour créer
    la carte et l'enregistrer dans un fichier HTML.
    Returns:
        Rendered HTML template for the map page.
    """
    return render_template("map.html")

if __name__ == "__main__":
    app.run(host=FLASK_HOST, port=FLASK_PORT, debug=FLASK_DEBUG)
