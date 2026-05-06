"""Constantes pour l'intégration Météociel."""

DOMAIN = "meteociel"

# Intervalle de mise à jour en secondes (toutes les 6 heures)
# La valeur d'hier ne change pas en journée, inutile de poller trop souvent
SCAN_INTERVAL = 6 * 3600

# URL de base Météociel
METEOCIEL_BASE_URL = "https://www.meteociel.fr/climatologie/obs_villes.php"

# Code station par défaut (Lyon-Bron = 482, comme dans ton script original)
DEFAULT_STATION_CODE = "482"

# Nom du sensor
SENSOR_NAME = "Pluie Hier"
SENSOR_UNIQUE_ID_PREFIX = "meteociel_pluie_hier"
