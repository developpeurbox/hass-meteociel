"""Coordinator Météociel pour Home Assistant."""
from __future__ import annotations

import logging
import re
from datetime import date, datetime, timedelta, timezone

from homeassistant.components.recorder import get_instance
from homeassistant.components.recorder.models import StatisticData, StatisticMetaData
from homeassistant.components.recorder.statistics import (
    async_import_statistics,
    get_last_statistics,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN, SCAN_INTERVAL
from .meteociel_scraper import MeteocielScraper

_LOGGER = logging.getLogger(__name__)

# Regex HA pour les statistic_id externes : "domain:object_id"
# Seuls minuscules, chiffres et underscores sont autorisés de chaque côté
_STATISTIC_ID_RE = re.compile(r"^[a-z0-9_]+:[a-z0-9_]+$")


def _make_statistic_id(station_code: str) -> str:
    """Génère un statistic_id valide pour HA (minuscules + chiffres + underscore)."""
    safe_code = re.sub(r"[^a-z0-9]", "_", station_code.lower())
    sid = f"{DOMAIN}:pluie_{safe_code}"
    if not _STATISTIC_ID_RE.match(sid):
        raise ValueError(f"statistic_id invalide généré : {sid!r}")
    return sid


class MeteocielCoordinator(DataUpdateCoordinator):
    """Coordinator de mise à jour des données Météociel."""

    def __init__(self, hass: HomeAssistant, station_code: str) -> None:
        """Initialisation du coordinator."""
        self._scraper = MeteocielScraper(station_code)
        self._station_code = station_code
        self._statistic_id = _make_statistic_id(station_code)
        _LOGGER.debug("statistic_id utilisé : %s", self._statistic_id)

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
        try:
            last_stats = await get_instance(self.hass).async_add_executor_job(
                get_last_statistics,
                self.hass,
                1,
                statistic_id,
                True,
                {"state"},
            )
            if last_stats and statistic_id in last_stats:
                last_start = last_stats[statistic_id][0].get("start")
                if last_start and abs((last_start - yesterday_utc).total_seconds()) < 3600:
                    _LOGGER.debug(
                        "Stat déjà présente pour hier (%s), pas de réinjection.",
                        yesterday_utc.date(),
                    )
                    return
        except Exception as exc:  # noqa: BLE001
            # Pas bloquant : on tente l'injection quand même
            _LOGGER.debug("Vérification doublon impossible : %s", exc)

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
        )

        async_import_statistics(self.hass, metadata, [stat])
        _LOGGER.info(
            "Stat injectée : %.1f mm pour %s (id: %s)",
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
