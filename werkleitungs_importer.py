import os
os.environ['USE_PYGEOS'] = '0'

import pandas as pd
import geopandas as gpd
from shapely.geometry import LineString, Point
import psycopg2
from psycopg2 import sql
import logging
from datetime import datetime
import os
from pathlib import Path

# Logging konfigurieren damit wir nachvollziehen können was passiert
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'import_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
        logging.StreamHandler()
    ]
)

class WerkleitungsImporter:
    """
    Diese Klasse importiert Werkleitungsdaten aus Excel in PostgreSQL/PostGIS.
    Sie validiert die Daten, erstellt Geometrien und schreibt alles sauber in die DB.
    """
    
    def __init__(self, db_config):
        """
        db_config ist ein Dictionary mit host, database, user, password
        """
        self.db_config = db_config
        self.conn = None
        self.error_records = []
        
    def connect_db(self):
        """Stellt Verbindung zur PostgreSQL-Datenbank her"""
        try:
            self.conn = psycopg2.connect(**self.db_config)
            logging.info("Datenbankverbindung erfolgreich hergestellt")
            return True
        except Exception as e:
            logging.error(f"Datenbankverbindung fehlgeschlagen: {e}")
            return False
    
    def validate_coordinates(self, x, y):
        """
        Prüft ob Koordinaten im plausiblen Bereich liegen (Schweizer LV95)
        LV95: X zwischen 2480000 und 2840000, Y zwischen 1070000 und 1300000
        """
        if not (2480000 <= x <= 2840000):
            return False, f"X-Koordinate {x} außerhalb Schweizer Bereich"
        if not (1070000 <= y <= 1300000):
            return False, f"Y-Koordinate {y} außerhalb Schweizer Bereich"
        return True, "OK"
    
    def create_line_geometry(self, x_start, y_start, x_end, y_end):
        """
        Erstellt eine LineString-Geometrie aus Start- und Endpunkt
        """
        # Beide Punkte validieren
        valid_start, msg_start = self.validate_coordinates(x_start, y_start)
        valid_end, msg_end = self.validate_coordinates(x_end, y_end)
        
        if not valid_start:
            raise ValueError(f"Startpunkt ungültig: {msg_start}")
        if not valid_end:
            raise ValueError(f"Endpunkt ungültig: {msg_end}")
        
        # LineString erstellen
        line = LineString([(x_start, y_start), (x_end, y_end)])
        
        # Minimallänge prüfen (0.5 Meter) um Fehleingaben zu erkennen
        if line.length < 0.5:
            raise ValueError(f"Leitung zu kurz ({line.length:.2f}m), wahrscheinlich Fehleingabe")
        
        return line
    
    def read_excel(self, filepath):
        """
        Liest Excel-Datei ein und validiert ob alle Spalten vorhanden sind
        """
        logging.info(f"Lese Excel-Datei: {filepath}")
        
        try:
            df = pd.read_excel(filepath)
            logging.info(f"{len(df)} Datensätze eingelesen")
        except Exception as e:
            logging.error(f"Fehler beim Einlesen: {e}")
            return None
        
        # Erforderliche Spalten prüfen
        required_columns = ['Leitung_ID', 'Material', 'Durchmesser_mm', 
                          'X_Start', 'Y_Start', 'X_End', 'Y_End', 
                          'Verlegedatum', 'Bemerkung']
        
        missing = [col for col in required_columns if col not in df.columns]
        if missing:
            logging.error(f"Fehlende Spalten: {missing}")
            logging.info(f"Vorhandene Spalten: {list(df.columns)}")
            return None
        
        # Whitespace aus allen String-Spalten entfernen (häufiges Problem bei Excel)
        for col in df.select_dtypes(include=['object']).columns:
            df[col] = df[col].str.strip() if df[col].dtype == 'object' else df[col]
        
        return df
    
    def process_records(self, df):
        """
        Verarbeitet alle Datensätze und erstellt GeoDataFrame mit Geometrien
        """
        valid_records = []
        
        for idx, row in df.iterrows():
            try:
                # Geometrie erstellen
                geom = self.create_line_geometry(
                    row['X_Start'], row['Y_Start'],
                    row['X_End'], row['Y_End']
                )
                
                # Datensatz mit Geometrie speichern
                record = {
                    'leitung_id': row['Leitung_ID'],
                    'material': row['Material'],
                    'durchmesser': int(row['Durchmesser_mm']),
                    'verlegedatum': pd.to_datetime(row['Verlegedatum']),
                    'bemerkung': row['Bemerkung'] if pd.notna(row['Bemerkung']) else '',
                    'geometry': geom,
                    'import_datum': datetime.now()
                }
                valid_records.append(record)
                
            except Exception as e:
                error_info = {
                    'zeile': idx + 2,  # +2 weil Excel bei 1 startet und Header
                    'leitung_id': row.get('Leitung_ID', 'UNBEKANNT'),
                    'fehler': str(e)
                }
                self.error_records.append(error_info)
                logging.warning(f"Zeile {idx+2}: {e}")
        
        logging.info(f"{len(valid_records)} gültige Datensätze verarbeitet")
        logging.info(f"{len(self.error_records)} fehlerhafte Datensätze übersprungen")
        
        # GeoDataFrame erstellen mit korrektem CRS (LV95)
        gdf = gpd.GeoDataFrame(valid_records, crs='EPSG:2056')
        
        return gdf
    
    def write_to_database(self, gdf):
        """
        Schreibt GeoDataFrame in PostgreSQL mit Transaction
        """
        if self.conn is None:
            logging.error("Keine Datenbankverbindung")
            return False
        
        cursor = self.conn.cursor()
        
        try:
            # Transaction starten
            logging.info("Starte Datenbank-Transaction")
            
            # SQL für Insert vorbereiten
            insert_sql = """
                INSERT INTO werkleitungen 
                (leitung_id, material, durchmesser, verlegedatum, bemerkung, 
                 geom, import_datum)
                VALUES (%s, %s, %s, %s, %s, ST_GeomFromText(%s, 2056), %s)
                ON CONFLICT (leitung_id) 
                DO UPDATE SET 
                    material = EXCLUDED.material,
                    durchmesser = EXCLUDED.durchmesser,
                    verlegedatum = EXCLUDED.verlegedatum,
                    bemerkung = EXCLUDED.bemerkung,
                    geom = EXCLUDED.geom,
                    import_datum = EXCLUDED.import_datum
            """
            
            # Alle Datensätze einfügen
            for idx, row in gdf.iterrows():
                cursor.execute(insert_sql, (
                    row['leitung_id'],
                    row['material'],
                    row['durchmesser'],
                    row['verlegedatum'],
                    row['bemerkung'],
                    row['geometry'].wkt,  # WKT = Well-Known-Text Format
                    row['import_datum']
                ))
            
            # Commit nur wenn alles geklappt hat
            self.conn.commit()
            logging.info(f"{len(gdf)} Datensätze erfolgreich importiert")
            return True
            
        except Exception as e:
            # Bei Fehler alles zurückrollen
            self.conn.rollback()
            logging.error(f"Fehler beim Schreiben in DB: {e}")
            return False
        finally:
            cursor.close()
    
    def save_error_report(self, output_path):
        """
        Speichert Fehlerbericht als CSV damit Kunde nachvollziehen kann was schief ging
        """
        if not self.error_records:
            logging.info("Keine Fehler aufgetreten, kein Fehlerbericht notwendig")
            return
        
        error_df = pd.DataFrame(self.error_records)
        error_df.to_csv(output_path, index=False, encoding='utf-8-sig')
        logging.info(f"Fehlerbericht gespeichert: {output_path}")
    
    def run_import(self, excel_path):
        """
        Hauptfunktion die den gesamten Import-Prozess durchführt
        """
        logging.info("="*60)
        logging.info("Starte Werkleitungs-Import")
        logging.info("="*60)
        
        # Excel einlesen
        df = self.read_excel(excel_path)
        if df is None:
            return False
        
        # Datensätze verarbeiten
        gdf = self.process_records(df)
        if gdf.empty:
            logging.error("Keine gültigen Datensätze zum Importieren")
            return False
        
        # In Datenbank schreiben
        if not self.connect_db():
            return False
        
        success = self.write_to_database(gdf)
        
        # Fehlerbericht speichern wenn es Fehler gab
        error_file = excel_path.replace('.xlsx', '_fehler.csv')
        self.save_error_report(error_file)
        
        # Statistik ausgeben
        logging.info("="*60)
        logging.info("Import abgeschlossen")
        logging.info(f"Erfolgreich: {len(gdf)}")
        logging.info(f"Fehler: {len(self.error_records)}")
        logging.info("="*60)
        
        return success


if __name__ == "__main__":
    import sys
    
    # Konfiguration aus Umgebungsvariablen lesen (sicherer als Hardcoding)
    db_config = {
        'host': os.getenv('DB_HOST', 'localhost'),
        'database': os.getenv('DB_NAME', 'basler_hofmann'),
        'user': os.getenv('DB_USER', 'tomo'),
        'password': os.getenv('DB_PASSWORD', 'tomo')
    }
    
    # Excel-Datei aus Command Line Argument
    if len(sys.argv) > 1:
        excel_file = sys.argv[1]
    else:
        print("Bitte Excel-Datei angeben: python3 werkleitungs_importer.py <datei.xlsx>")
        sys.exit(1)
    
    # Importer erstellen und ausführen
    importer = WerkleitungsImporter(db_config)
    importer.run_import(excel_file)