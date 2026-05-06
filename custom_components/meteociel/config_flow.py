"""Config Flow pour l'intégration Météociel."""
from __future__ import annotations

import json
import os
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant

from .const import DEFAULT_STATION_CODE, DOMAIN
from .meteociel_scraper import MeteocielScraper


def _load_cities() -> dict[str, str]:
    """
    Charge cities_database.json et retourne un dict {code: "Nom (dept) [type]"}
    trié par nom, en excluant les stations inactives.
    """
    db_path = os.path.join(os.path.dirname(__file__), "cities_database.json")
    with open(db_path, encoding="utf-8") as f:
        cities = json.load(f)

    return {
        city["code"]: f"{city['nom']} ({city['departement']})"
        for city in sorted(cities, key=lambda c: c["nom"])
        if city["type"] != "inactive"
    }


async def validate_input(hass: HomeAssistant, data: dict) -> dict:
    """Valide la config en testant un vrai appel au scraper."""
    scraper = MeteocielScraper(data["station_code"])
    await hass.async_add_executor_job(scraper.fetch_yesterday_rain)

    # Retrouver le nom de la ville pour le titre
    cities = await hass.async_add_executor_job(_load_cities)
    city_label = cities.get(data["station_code"], data["station_code"])
    return {"title": f"Météociel – {city_label}"}


class MeteocielConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Flux de configuration de l'intégration Météociel."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Étape de saisie par l'utilisateur."""
        errors: dict[str, str] = {}

        # Chargement des villes pour le sélecteur
        cities = await self.hass.async_add_executor_job(_load_cities)

        schema = vol.Schema(
            {
                vol.Required("station_code", default=DEFAULT_STATION_CODE): vol.In(cities),
            }
        )

        if user_input is not None:
            try:
                info = await validate_input(self.hass, user_input)
            except Exception:  # noqa: BLE001
                errors["base"] = "cannot_connect"
            else:
                return self.async_create_entry(title=info["title"], data=user_input)

        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=errors,
        )
