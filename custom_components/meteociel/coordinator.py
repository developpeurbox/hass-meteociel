"""Coordinator Météociel pour Home Assistant."""
from __future__ import annotations

import logging
from datetime import date, datetime, timedelta, timezone

from homeassistant.components.recorder import get_instance
from homeassistant.components.recorder.models import StatisticData, StatisticMetaData
from homeassistant.components.recorder.statistics import (
    async_import_statistics,
    get_last_statistics,
)
from homeassistant.const import UnitOfPrecipitationDepth
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN, SCAN_INTERVAL, SENSOR_UNIQUE_ID_PREFIX
from .meteociel_scraper import MeteocielScraper

_LOGGER = logging.getLogger(__name__)


class MeteocielCoordinator(DataUpdateCoordinator):
    """Coordinator de mise à jour des données Météociel."""

    def __init__(self, hass: HomeAssistant, station_code: str) -> None:
        """Initialisation du coordinator."""
        self._scraper = MeteocielScraper(station_code)
        self._station_code = station_code
        # Format valide HA : "domain:identifiant_snake_case_minuscules"
        self._statistic_id = f"{DOMAIN}:pluie_{station_code}"

        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{station_code}",
            update_interval=timedelta(seconds=SCAN_INTERVAL),
        )

    def _yesterday_midnight_utc(self) -> datetime:
        """Retourne minuit UTC du jour J-1 en tenant compte du timezone HA."""
        ha_tz = self.hass.config.time_zone
        try:
            from zoneinfo import ZoneInfo
            tz = ZoneInfo(ha_tz)
        except Exception:
            tz = timezone.utc

        yesterday = date.today() - timedelta(days=1)
        midnight_local = datetime(
            yesterday.year, yesterday.month, yesterday.day,
            0, 0, 0, tzinfo=tz
        )
        return midnight_local.astimezone(timezone.utc)

    async def _async_inject_statistic(self, pluie_mm: float) -> None:
        """
        Injecte la valeur dans les Long-Term Statistics de HA
        avec le bon timestamp (minuit d'hier).
        Evite les doublons en vérifiant si la stat du jour existe déjà.
        """
        statistic_id = self._statistic_id
        yesterday_utc = self._yesterday_midnight_utc()

        # Vérification doublon : stat déjà présente pour hier ?
        last_stats = await get_instance(self.hass).async_add_executor_job(
            get_last_statistics,
            self.hass,
            1,
            statistic_id,
            True,
            {"sum", "state"},
        )

        if last_stats and statistic_id in last_stats:
            last_start = last_stats[statistic_id][0].get("start")
            if last_start and abs((last_start - yesterday_utc).total_seconds()) < 3600:
                _LOGGER.debug(
                    "Stat déjà présente pour hier (%s), pas de réinjection.",
                    yesterday_utc.date(),
                )
                return

        metadata = StatisticMetaData(
            has_mean=False,
            has_sum=False,
            name="Pluie Hier",
            source=DOMAIN,
            statistic_id=statistic_id,
            unit_of_measurement="mm",
        )

        stat = StatisticData(
            start=yesterday_utc,
            state=pluie_mm,
            mean=None,
            sum=None,
        )

        async_import_statistics(self.hass, metadata, [stat])
        _LOGGER.info(
            "Stat injectée : %s mm pour %s (id: %s)",
            pluie_mm,
            yesterday_utc.date(),
            statistic_id,
        )

    async def _async_update_data(self) -> dict:
        """Récupère les données depuis Météociel et injecte la stat datée."""
        try:
            data = await self.hass.async_add_executor_job(
                self._scraper.fetch_yesterday_rain
            )
        except Exception as exc:
            raise UpdateFailed(f"Erreur lors du scraping Météociel : {exc}") from exc

        # Injection dans les statistiques long-terme avec le bon timestamp
        try:
            await self._async_inject_statistic(data["pluie_mm"])
        except Exception as exc:  # noqa: BLE001
            _LOGGER.warning("Impossible d'injecter la statistique : %s", exc)

        return data
