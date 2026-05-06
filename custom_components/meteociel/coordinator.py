"""Coordinator Météociel pour Home Assistant."""
from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN, SCAN_INTERVAL
from .meteociel_scraper import MeteocielScraper

_LOGGER = logging.getLogger(__name__)


class MeteocielCoordinator(DataUpdateCoordinator):
    """Coordinator de mise à jour des données Météociel."""

    def __init__(self, hass: HomeAssistant, station_code: str) -> None:
        """Initialisation du coordinator."""
        self._scraper = MeteocielScraper(station_code)

        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{station_code}",
            update_interval=timedelta(seconds=SCAN_INTERVAL),
        )

    async def _async_update_data(self) -> dict:
        """Récupère les données depuis Météociel."""
        try:
            return await self.hass.async_add_executor_job(
                self._scraper.fetch_yesterday_rain
            )
        except Exception as exc:
            raise UpdateFailed(f"Erreur lors du scraping Météociel : {exc}") from exc
