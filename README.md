# GIS Werkleitungs-Import Tool

Ein Python-Tool zum Import von Werkleitungsdaten aus Excel in PostgreSQL/PostGIS mit umfassender Validierung und Fehlerbehandlung.

## Features

✅ Import von Werkleitungsdaten aus Excel-Dateien  
✅ Validierung von Schweizer Koordinaten (LV95/EPSG:2056)  
✅ Geometrie-Erstellung und -Validierung  
✅ Automatische Fehlererkennung und Reporting  
✅ Transaction-basierter Import (Alles oder Nichts)  
✅ Detailliertes Logging  
✅ Test-Daten Generator  

## Voraussetzungen

- Python 3.8+
- PostgreSQL 12+ mit PostGIS Extension
- Benötigte Python-Pakete (siehe `requirements.txt`)

## Installation

```bash
# Repository klonen
git clone https://github.com/dein-username/gis-werkleitungs-import.git
cd gis-werkleitungs-import

# Virtual Environment erstellen (empfohlen)
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# oder: venv\Scripts\activate  # Windows

# Dependencies installieren
pip install -r requirements.txt
```

## Datenbank Setup

```bash
# PostgreSQL Datenbank erstellen
createdb -U postgres gis_production

# PostGIS Extension und Tabellen erstellen
psql -U postgres -d gis_production -f setup_database.sql
```

## Konfiguration

Erstelle eine `.env` Datei mit deinen Datenbank-Credentials:

```bash
DB_HOST=localhost
DB_NAME=gis_production
DB_USER=dein_username
DB_PASSWORD=dein_passwort
```

## Verwendung

### Test-Daten generieren

```bash
python3 generate_test_data.py
```

Dies erstellt verschiedene Excel-Dateien:
- `test_klein_gueltig.xlsx` - 10 gültige Datensätze
- `test_mittel_mit_fehlern.xlsx` - 50+ Datensätze mit einigen Fehlern
- `test_gross_performance.xlsx` - 500 Datensätze für Performance-Tests
- `test_spezialfaelle.xlsx` - Edge Cases und Sonderfälle

### Import ausführen

```bash
# Einfacher Import
python3 werkleitungs_importer.py test_klein_gueltig.xlsx

# Import mit Fehlern (erstellt Fehlerbericht)
python3 werkleitungs_importer.py test_mittel_mit_fehlern.xlsx
```

### Ergebnisse prüfen

```sql
-- In PostgreSQL
SELECT COUNT(*) FROM werkleitungen;

SELECT 
    material,
    COUNT(*) as anzahl,
    ROUND(AVG(durchmesser)) as durchschnitt_durchmesser
FROM werkleitungen
GROUP BY material;
```

## Datenformat

Die Excel-Datei muss folgende Spalten enthalten:

| Spalte | Typ | Beschreibung |
|--------|-----|--------------|
| Leitung_ID | String | Eindeutige Leitungs-ID |
| Material | String | PE, PVC, Grauguss, Stahl, etc. |
| Durchmesser_mm | Integer | Nennweite in Millimetern |
| X_Start | Float | Start X-Koordinate (LV95) |
| Y_Start | Float | Start Y-Koordinate (LV95) |
| X_End | Float | End X-Koordinate (LV95) |
| Y_End | Float | End Y-Koordinate (LV95) |
| Verlegedatum | Date | Datum der Verlegung |
| Bemerkung | String | Optional |

## Validierungen

Das Tool prüft automatisch:
- ✅ Koordinaten im gültigen Schweizer Bereich (LV95)
- ✅ Minimale Leitungslänge (> 0.5m)
- ✅ Gültige Geometrien
- ✅ Vollständigkeit der Pflichtfelder
- ✅ Gültige Datumsformate

## Fehlerbehandlung

Bei Fehlern wird ein CSV-Bericht erstellt:
- Zeigt die Zeilennummer des Fehlers
- Beschreibt den Fehlergrund
- Ermöglicht manuelle Korrektur

Fehlerhafte Datensätze werden übersprungen, gültige Daten werden trotzdem importiert.

## Logging

Alle Imports werden in Log-Dateien protokolliert:
- Format: `import_YYYYMMDD_HHMMSS.log`
- Enthält alle Schritte und Entscheidungen
- Hilfreich für Debugging und Nachvollziehbarkeit

## Projektstruktur

```
gis-werkleitungs-import/
├── werkleitungs_importer.py    # Haupt-Import-Skript
├── generate_test_data.py       # Test-Daten Generator
├── setup_database.sql          # Datenbank-Setup
├── requirements.txt            # Python Dependencies
├── .env.example               # Beispiel-Konfiguration
├── .gitignore                 # Git-Ignorierungen
└── README.md                  # Diese Datei
```

## Entwicklung

### Tests ausführen

```bash
# Kleiner Test
python3 werkleitungs_importer.py test_klein_gueltig.xlsx

# Test mit Fehlern
python3 werkleitungs_importer.py test_mittel_mit_fehlern.xlsx

# Performance-Test
python3 werkleitungs_importer.py test_gross_performance.xlsx
```

### Erweiterungen

Das Tool kann erweitert werden für:
- Andere Koordinatensysteme
- Zusätzliche Validierungen
- Export in andere Formate (GeoJSON, Shapefile, etc.)
- REST API Integration
- Automatische Backups

## Lizenz

MIT License - siehe LICENSE Datei

## Autor

[Dein Name]

## Kontakt

Bei Fragen oder Problemen erstelle bitte ein Issue auf GitHub.

---

**Entwickelt für die Verwaltung von Werkleitungsnetzen in Schweizer Gemeinden und Städten.**
