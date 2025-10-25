-- ======================================================================
-- POSTGRESQL/POSTGIS SETUP FÜR WERKLEITUNGS-IMPORT TEST
-- ======================================================================

-- 1. PostGIS Extension aktivieren (falls noch nicht geschehen)
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS postgis_topology;

-- 2. Test-Datenbank erstellen (optional, falls du eine neue DB willst)
-- CREATE DATABASE gis_test;
-- \c gis_test
-- CREATE EXTENSION IF NOT EXISTS postgis;

-- 3. Tabelle für Werkleitungen erstellen
DROP TABLE IF EXISTS werkleitungen CASCADE;

CREATE TABLE werkleitungen (
    id SERIAL PRIMARY KEY,
    leitung_id VARCHAR(50) UNIQUE NOT NULL,
    material VARCHAR(50),
    durchmesser INTEGER,
    verlegedatum DATE,
    bemerkung TEXT,
    geom GEOMETRY(LineString, 2056),  -- LV95 Koordinatensystem
    import_datum TIMESTAMP,
    erstellt_am TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Constraints
    CONSTRAINT chk_durchmesser CHECK (durchmesser > 0 AND durchmesser <= 2000),
    CONSTRAINT chk_material CHECK (material IN (
        'PE', 'PVC', 'Grauguss', 'Stahl', 'Asbestzement', 
        'Polyethylen', 'Polyvinylchlorid', 'unbekannt'
    ))
);

-- 4. Räumlicher Index für Performance
CREATE INDEX idx_werkleitungen_geom 
ON werkleitungen 
USING GIST(geom);

-- 5. Index auf leitung_id für schnelle Lookups
CREATE INDEX idx_werkleitungen_leitung_id 
ON werkleitungen(leitung_id);

-- 6. Index auf Material für Filterungen
CREATE INDEX idx_werkleitungen_material 
ON werkleitungen(material);

-- 7. Index auf Verlegedatum für zeitliche Abfragen
CREATE INDEX idx_werkleitungen_verlegedatum 
ON werkleitungen(verlegedatum);

-- 8. Kommentare für Dokumentation
COMMENT ON TABLE werkleitungen IS 'Werkleitungskataster mit geometrischen Informationen';
COMMENT ON COLUMN werkleitungen.leitung_id IS 'Eindeutige Leitungs-Identifikation';
COMMENT ON COLUMN werkleitungen.material IS 'Leitungsmaterial (PE, PVC, Grauguss, etc.)';
COMMENT ON COLUMN werkleitungen.durchmesser IS 'Nennweite in Millimetern';
COMMENT ON COLUMN werkleitungen.verlegedatum IS 'Datum der Verlegung';
COMMENT ON COLUMN werkleitungen.geom IS 'Geometrie als LineString in LV95 (EPSG:2056)';
COMMENT ON COLUMN werkleitungen.import_datum IS 'Zeitpunkt des Imports/letzten Updates';

-- 9. Beispiel-Abfragen zur Verifikation

-- Anzahl Leitungen
SELECT COUNT(*) as anzahl_leitungen FROM werkleitungen;

-- Leitungen nach Material
SELECT 
    material, 
    COUNT(*) as anzahl,
    ROUND(AVG(durchmesser)) as durchschnitt_durchmesser,
    SUM(ST_Length(geom)) as gesamtlaenge_meter
FROM werkleitungen
GROUP BY material
ORDER BY anzahl DESC;

-- Leitungen nach Alter
SELECT 
    CASE 
        WHEN EXTRACT(YEAR FROM AGE(CURRENT_DATE, verlegedatum)) < 20 THEN 'Neu (< 20 Jahre)'
        WHEN EXTRACT(YEAR FROM AGE(CURRENT_DATE, verlegedatum)) < 50 THEN 'Mittel (20-50 Jahre)'
        ELSE 'Alt (> 50 Jahre)'
    END as altersklasse,
    COUNT(*) as anzahl,
    ROUND(AVG(EXTRACT(YEAR FROM AGE(CURRENT_DATE, verlegedatum)))) as durchschnittsalter
FROM werkleitungen
GROUP BY altersklasse
ORDER BY durchschnittsalter;

-- Längste Leitungen
SELECT 
    leitung_id,
    material,
    durchmesser,
    ROUND(ST_Length(geom)::numeric, 2) as laenge_meter
FROM werkleitungen
ORDER BY ST_Length(geom) DESC
LIMIT 10;

-- Geometrie-Validierung
SELECT 
    leitung_id,
    ST_IsValid(geom) as ist_gueltig,
    ST_IsValidReason(geom) as grund
FROM werkleitungen
WHERE NOT ST_IsValid(geom);

-- ======================================================================
-- ZUSÄTZLICHE TABELLEN FÜR ERWEITERTE TESTS
-- ======================================================================

-- Tabelle für Import-Statistiken
DROP TABLE IF EXISTS import_statistik CASCADE;

CREATE TABLE import_statistik (
    id SERIAL PRIMARY KEY,
    import_datum TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    dateiname VARCHAR(255),
    anzahl_datensaetze INTEGER,
    anzahl_erfolgreich INTEGER,
    anzahl_fehler INTEGER,
    dauer_sekunden NUMERIC,
    bemerkung TEXT
);

COMMENT ON TABLE import_statistik IS 'Protokolliert alle Import-Vorgänge';

-- Tabelle für API-Keys (falls du die REST-API testen willst)
DROP TABLE IF EXISTS api_keys CASCADE;

CREATE TABLE api_keys (
    id SERIAL PRIMARY KEY,
    key VARCHAR(64) UNIQUE NOT NULL,
    user_id VARCHAR(50),
    organisation VARCHAR(100),
    aktiv BOOLEAN DEFAULT true,
    erstellt_am TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    letzte_verwendung TIMESTAMP
);

-- Test API-Key einfügen
INSERT INTO api_keys (key, user_id, organisation) 
VALUES ('test-api-key-12345', 'test_user', 'Test Organisation');

COMMENT ON TABLE api_keys IS 'API-Schlüssel für Authentifizierung';

-- Tabelle für Schadensmeldungen (falls du die Mobile-App testen willst)
DROP TABLE IF EXISTS schadensmeldungen CASCADE;

CREATE TABLE schadensmeldungen (
    id SERIAL PRIMARY KEY,
    schadentyp VARCHAR(100),
    beschreibung TEXT,
    geom GEOMETRY(Point, 4326),  -- WGS84 für GPS
    foto_pfad VARCHAR(500),
    user_id VARCHAR(50),
    organisation VARCHAR(100),
    zusatzdaten JSONB,
    hat_duplikate BOOLEAN DEFAULT false,
    status VARCHAR(50) DEFAULT 'neu',
    prioritaet VARCHAR(20) DEFAULT 'normal',
    erstellt TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    bearbeitet TIMESTAMP,
    bearbeiter_id VARCHAR(50)
);

CREATE INDEX idx_schadensmeldungen_geom 
ON schadensmeldungen 
USING GIST(geom);

CREATE INDEX idx_schadensmeldungen_status 
ON schadensmeldungen(status);

COMMENT ON TABLE schadensmeldungen IS 'Mobile Schadensmeldungen mit GPS-Position';

-- Tabelle für Duplikat-Verknüpfungen
DROP TABLE IF EXISTS schaden_duplikate CASCADE;

CREATE TABLE schaden_duplikate (
    id SERIAL PRIMARY KEY,
    schaden_id INTEGER REFERENCES schadensmeldungen(id) ON DELETE CASCADE,
    duplikat_id INTEGER REFERENCES schadensmeldungen(id) ON DELETE CASCADE,
    distanz_meter NUMERIC,
    erstellt TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabelle für Schadenstypen
DROP TABLE IF EXISTS schadenstypen CASCADE;

CREATE TABLE schadenstypen (
    typ_id SERIAL PRIMARY KEY,
    bezeichnung VARCHAR(100),
    beschreibung TEXT,
    icon_name VARCHAR(50),
    prioritaet VARCHAR(20),
    aktiv BOOLEAN DEFAULT true,
    sortierung INTEGER
);

-- Beispiel-Schadenstypen einfügen
INSERT INTO schadenstypen (bezeichnung, beschreibung, icon_name, prioritaet, sortierung) VALUES
('Schlagloch', 'Vertiefung oder Loch in der Fahrbahn', 'pothole', 'hoch', 1),
('Beschädigtes Schild', 'Verkehrsschild beschädigt oder unleserlich', 'sign-damage', 'mittel', 2),
('Defekte Beleuchtung', 'Straßenlaterne funktioniert nicht', 'light-off', 'mittel', 3),
('Verstopfter Gully', 'Strassenablauf verstopft', 'drain-blocked', 'hoch', 4),
('Lose Kanaldeckel', 'Kanaldeckel sitzt nicht richtig', 'manhole-loose', 'hoch', 5);

-- ======================================================================
-- HELPER FUNCTIONS
-- ======================================================================

-- Funktion um Import-Statistik zu speichern
CREATE OR REPLACE FUNCTION log_import_statistik(
    p_dateiname VARCHAR,
    p_anzahl_datensaetze INTEGER,
    p_anzahl_erfolgreich INTEGER,
    p_anzahl_fehler INTEGER,
    p_dauer_sekunden NUMERIC,
    p_bemerkung TEXT DEFAULT NULL
)
RETURNS INTEGER AS $$
DECLARE
    v_id INTEGER;
BEGIN
    INSERT INTO import_statistik (
        dateiname, 
        anzahl_datensaetze, 
        anzahl_erfolgreich, 
        anzahl_fehler, 
        dauer_sekunden, 
        bemerkung
    )
    VALUES (
        p_dateiname,
        p_anzahl_datensaetze,
        p_anzahl_erfolgreich,
        p_anzahl_fehler,
        p_dauer_sekunden,
        p_bemerkung
    )
    RETURNING id INTO v_id;
    
    RETURN v_id;
END;
$$ LANGUAGE plpgsql;

-- ======================================================================
-- FERTIG! Datenbank ist bereit für Import-Tests
-- ======================================================================

SELECT 'Datenbank erfolgreich eingerichtet!' as status;
SELECT 'Tabelle werkleitungen erstellt mit räumlichem Index' as info;
SELECT 'Führe jetzt den Python-Import aus' as naechster_schritt;