"""Scraper Météociel - Récupération des données pluviométriques."""
from __future__ import annotations

import logging
from datetime import date, timedelta

import urllib3
import requests
from bs4 import BeautifulSoup

# Supprime le warning SSL car meteociel.fr a un certificat non vérifié
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

from .const import METEOCIEL_BASE_URL

_LOGGER = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) "
        "Gecko/20100101 Firefox/113.0"
    )
}


class MeteocielScraper:
    """Portage Python de la logique de scraping meteociel.php."""

    def __init__(self, station_code: str) -> None:
        self._station_code = station_code

    def fetch_yesterday_rain(self) -> dict:
        """
        Scrape la page Météociel du mois en cours et retourne
        la pluviométrie de la veille.

        Retourne un dict :
          {
            "date": "2025-03-14",
            "pluie_mm": 3.2,
            "station_code": "482",
          }
        ou lève une exception en cas d'erreur.
        """
        yesterday = date.today() - timedelta(days=1)
        mois = yesterday.month
        annee = yesterday.year
        yesterday_str = yesterday.strftime("%Y-%m-%d")

        url = (
            f"{METEOCIEL_BASE_URL}"
            f"?code={self._station_code}&mois={mois}&annee={annee}"
        )
        _LOGGER.debug("Météociel fetch URL: %s", url)

        try:
            response = requests.get(url, headers=HEADERS, timeout=30, verify=False)
            response.raise_for_status()
        except requests.RequestException as exc:
            raise Exception(f"Erreur HTTP Météociel: {exc}") from exc

        soup = BeautifulSoup(response.text, "html.parser")

        # Logique identique au PHP :
        # table index 3 → 1er td → table interne index 1 → lignes
        tables = soup.find_all("table")
        if len(tables) < 4:
            raise Exception("Structure HTML Météociel inattendue (table[3] absente)")

        outer_table = tables[3]
        trtds = outer_table.find_all("td", recursive=False)
        if not trtds:
            # Certaines versions ont les td en profondeur
            trtds = outer_table.find_all("td")

        inner_table = None
        for td in trtds:
            inner_tables = td.find_all("table")
            if len(inner_tables) >= 2:
                inner_table = inner_tables[1]
                break

        if inner_table is None:
            raise Exception("Table interne de données introuvable")

        rows = inner_table.find_all("tr")

        # Première ligne = en-têtes, on saute
        for row in rows[1:]:
            cols = row.find_all("td")
            if len(cols) < 4:
                continue

            # Colonne 0 : lien avec la date (paramètre jour2/mois2/annee2)
            date_cell = cols[0]
            link_tag = date_cell.find("a")
            if not link_tag or not link_tag.get("href"):
                continue

            href = link_tag["href"]
            row_date = self._parse_date_from_href(href)
            if row_date is None:
                continue

            # Colonne 3 : pluviométrie
            rain_text = cols[3].get_text(strip=True)
            rain_value = self._parse_rain_value(rain_text)

            if rain_value is None:
                # Données non numériques = fin des données disponibles
                _LOGGER.debug(
                    "Valeur non numérique à la date %s, arrêt du parsing", row_date
                )
                break

            _LOGGER.debug("Date: %s | Pluie: %s mm", row_date, rain_value)

            if row_date == yesterday_str:
                _LOGGER.info(
                    "Pluie hier (%s) : %s mm (station %s)",
                    yesterday_str,
                    rain_value,
                    self._station_code,
                )
                return {
                    "date": row_date,
                    "pluie_mm": rain_value,
                    "station_code": self._station_code,
                }

        raise Exception(
            f"Aucune donnée trouvée pour hier ({yesterday_str}) "
            f"sur la station {self._station_code}"
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_date_from_href(href: str) -> str | None:
        """
        Extrait la date depuis un href du type :
        ...code2=482&jour2=14&mois2=2&annee2=2025
        Retourne une chaîne 'YYYY-MM-DD' ou None.

        Note : Météociel stocke mois2 décalé de -1 (janvier = 0),
        comme dans le PHP original : mktime(..., $match[3] + 1, ...)
        """
        import re
        pattern = r"code2=(\d+)&jour2=(\d+)&mois2=(\d+)&annee2=(\d+)"
        match = re.search(pattern, href)
        if not match:
            return None

        jour = int(match.group(2))
        mois = int(match.group(3)) + 1  # décalage identique au PHP
        annee = int(match.group(4))

        try:
            return date(annee, mois, jour).strftime("%Y-%m-%d")
        except ValueError:
            return None

    @staticmethod
    def _parse_rain_value(text: str) -> float | None:
        """Extrait la valeur numérique depuis '3.2 mm' ou '0' ou '-'."""
        # Supprime ' mm' et espaces
        cleaned = text.replace(" mm", "").replace("\xa0", "").strip()
        try:
            return float(cleaned)
        except (ValueError, TypeError):
            return None
