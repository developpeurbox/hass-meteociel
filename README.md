
[![GitHub Release][releases-shield]][releases]
[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg?style=for-the-badge)](https://github.com/hacs/integration)

[![Community Forum][forum-shield]][forum]

# ha-meteociel — Intégration Home Assistant Pluviométrie

Intégration custom pour Home Assistant qui scrape [Météociel](https://www.meteociel.fr)
et expose un sensor `sensor.pluie_hier` avec la pluviométrie du jour précédent.

---

## Installation

### Via HACS (recommandé)

1. Dans HACS → **Intégrations** → menu ⋮ → **Dépôts personnalisés**
2. Ajouter l'URL de ce repo, catégorie **Intégration**
3. Installer "Météociel Pluviométrie"
4. Redémarrer Home Assistant

### Manuelle

```bash
cp -r custom_components/meteociel /config/custom_components/
```
Redémarre Home Assistant.

---

## Configuration

1. **Paramètres** → **Appareils et services** → **Ajouter une intégration**
2. Cherche **"Météociel"**
3. Renseigne le **code station** (ex: `482` pour Lyon-Bron)

> Pour trouver le code de ta station, va sur `meteociel.fr/climatologie/obs_villes.php`
> et récupère le paramètre `code=XXXX` dans l'URL.

---

## Sensor créé

| Propriété | Valeur |
|-----------|--------|
| `entity_id` | `sensor.pluie_hier` |
| `unit` | `mm` |
| `device_class` | `precipitation` |
| `state_class` | `measurement` |
| `update_interval` | toutes les 6h |

### Attributs

| Attribut | Description |
|----------|-------------|
| `date_mesure` | Date au format `YYYY-MM-DD` (= hier) |
| `station_code` | Code station Météociel |
| `source` | `meteociel.fr` |

---


## Automatisation conseillée

Pour t'assurer que la valeur du jour est récupérée tôt le matin :

```yaml
automation:
  - alias: "Refresh pluie hier (matin)"
    trigger:
      - platform: time
        at: "06:00:00"
    action:
      - service: homeassistant.update_entity
        target:
          entity_id: sensor.pluie_hier
```

---

## Notes techniques

- Le scraping cible le **tableau index 3** de la page, puis la **table interne index 1**,
  conformément à la structure observée sur Météociel (logique identique au script PHP original).
- Le mois dans l'URL de lien Météociel est décalé de +1 (`mois2 + 1`), comme dans le PHP.
- `verify=False` est conservé pour contourner les soucis de certificat de Météociel.


[commits-shield]: https://img.shields.io/github/commit-activity/y/custom-components/readme.svg?style=for-the-badge
[commits]: https://github.com/developpeurbox/hass-footao/readme/commits/main
[hacs]: https://github.com/hacs/integration
[hacsbadge]: https://img.shields.io/badge/HACS-Default-orange.svg?style=for-the-badge
[exampleimg]: example.png
[forum-shield]: https://img.shields.io/badge/community-forum-brightgreen.svg?style=for-the-badge
[forum]: https://community.home-assistant.io/
[releases-shield]: https://img.shields.io/github/v/release/developpeurbox/hass-meteociel?style=for-the-badge
[releases]: https://github.com/developpeurbox/hass-meteociel/releases
