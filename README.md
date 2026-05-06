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

## Import de l'historique SQL

Si tu possèdes un historique dans une table MySQL `Pluie` (champs `date`, `pluie`),
utilise le script fourni pour injecter ces données dans les statistiques long-terme de HA.

```bash
cd tools/
pip install mysql-connector-python requests
```

Édite les variables dans `import_pluie_history.py` :

```python
DB_CONFIG = {
    "host": "192.168.0.12",
    "user": "TON_USER_SQL",
    "password": "TON_MOT_DE_PASSE",
    "database": "TA_BASE",
}
HA_URL   = "http://192.168.0.12:8123"
HA_TOKEN = "TON_LONG_LIVED_ACCESS_TOKEN"
```

> **Token HA** : Profil utilisateur → bas de page → **Jetons d'accès longue durée**

Lance ensuite :

```bash
python3 import_pluie_history.py
```

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
