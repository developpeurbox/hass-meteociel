"""Sensor pluviométrie Météociel pour Home Assistant."""
from __future__ import annotations

import logging
from datetime import date, timedelta

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, SENSOR_UNIQUE_ID_PREFIX

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Création du sensor depuis la config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([MeteocielRainSensor(coordinator, entry)])


class MeteocielRainSensor(CoordinatorEntity, SensorEntity):
    """Sensor représentant la pluviométrie du jour précédent."""

    _attr_name = "Pluie Hier"
    _attr_native_unit_of_measurement = "mm"
    _attr_device_class = SensorDeviceClass.PRECIPITATION
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:weather-rainy"

    def __init__(self, coordinator, entry: ConfigEntry) -> None:
        """Initialisation du sensor."""
        super().__init__(coordinator)
        station_code = entry.data["station_code"]
        self._attr_unique_id = f"{SENSOR_UNIQUE_ID_PREFIX}_{station_code}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, station_code)},
            "name": f"Météociel Station {station_code}",
            "manufacturer": "Météociel",
            "model": "Scraper Pluviométrie",
        }

    @property
    def native_value(self) -> float | None:
        """Valeur du sensor = mm de pluie d'hier."""
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.get("pluie_mm")

    @property
    def extra_state_attributes(self) -> dict:
        """Attributs supplémentaires."""
        if self.coordinator.data is None:
            return {}
        yesterday = (date.today() - timedelta(days=1)).strftime("%Y-%m-%d")
        return {
            "date_mesure": self.coordinator.data.get("date", yesterday),
            "station_code": self.coordinator.data.get("station_code"),
            "source": "meteociel.fr
            ",
        }
