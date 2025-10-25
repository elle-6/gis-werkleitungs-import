import pandas as pd
import random
from datetime import datetime, timedelta

# ======================================================================
# DUMMY-DATEN GENERATOR FÜR WERKLEITUNGS-IMPORT TEST
# ======================================================================

def generate_test_data(num_records=50, include_errors=True):
    """
    Generiert Test-Daten für den Werkleitungs-Import.
    
    Args:
        num_records: Anzahl Datensätze
        include_errors: Wenn True, werden auch fehlerhafte Datensätze eingefügt
    """
    
    # Materialien für Leitungen
    materials = ['PE', 'PVC', 'Grauguss', 'Stahl', 'Asbestzement']
    
    # Durchmesser in mm
    durchmesser = [80, 100, 150, 200, 250, 300, 400]
    
    # Zürich Koordinaten (LV95)
    # Zentrum Zürich ungefähr: X: 2683000, Y: 1248000
    zurich_x_center = 2683000
    zurich_y_center = 1248000
    radius = 5000  # 5km Radius
    
    records = []
    
    for i in range(num_records):
        # Startpunkt generieren
        x_start = zurich_x_center + random.randint(-radius, radius)
        y_start = zurich_y_center + random.randint(-radius, radius)
        
        # Endpunkt in der Nähe generieren (10-200m Leitungslänge)
        length = random.randint(10, 200)
        angle = random.uniform(0, 360)
        import math
        x_end = x_start + length * math.cos(math.radians(angle))
        y_end = y_start + length * math.sin(math.radians(angle))
        
        # Verlegedatum (zwischen 1950 und heute)
        start_date = datetime(1950, 1, 1)
        end_date = datetime.now()
        time_between_dates = end_date - start_date
        days_between_dates = time_between_dates.days
        random_days = random.randrange(days_between_dates)
        verlegedatum = start_date + timedelta(days=random_days)
        
        record = {
            'Leitung_ID': f'L_{i+1:05d}',
            'Material': random.choice(materials),
            'Durchmesser_mm': random.choice(durchmesser),
            'X_Start': round(x_start, 2),
            'Y_Start': round(y_start, 2),
            'X_End': round(x_end, 2),
            'Y_End': round(y_end, 2),
            'Verlegedatum': verlegedatum.strftime('%Y-%m-%d'),
            'Bemerkung': random.choice([
                'Hauptleitung Quartier',
                'Hausanschluss',
                'Erneuerung 2020',
                'Sanierungsbedürftig',
                '',  # Manchmal leer
                'Neue Leitung',
                'Ersatz für alte GG-Leitung'
            ])
        }
        
        records.append(record)
    
    # Fehlerhafte Datensätze einfügen wenn gewünscht
    if include_errors and num_records >= 10:
        # Fehler 1: Koordinaten außerhalb Schweiz
        error_record_1 = records[5].copy()
        error_record_1['Leitung_ID'] = 'L_ERR01'
        error_record_1['X_Start'] = 1000000  # Viel zu klein
        error_record_1['Bemerkung'] = 'FEHLER: Koordinate außerhalb'
        records.append(error_record_1)
        
        # Fehler 2: Leitung zu kurz (< 0.5m)
        error_record_2 = records[10].copy()
        error_record_2['Leitung_ID'] = 'L_ERR02'
        error_record_2['X_End'] = error_record_2['X_Start'] + 0.1
        error_record_2['Y_End'] = error_record_2['Y_Start'] + 0.1
        error_record_2['Bemerkung'] = 'FEHLER: Zu kurz'
        records.append(error_record_2)
        
        # Fehler 3: Fehlende Koordinate
        error_record_3 = records[15].copy()
        error_record_3['Leitung_ID'] = 'L_ERR03'
        error_record_3['X_End'] = None
        error_record_3['Bemerkung'] = 'FEHLER: Fehlende Koordinate'
        records.append(error_record_3)
        
        # Fehler 4: Ungültiges Datum
        error_record_4 = records[20].copy()
        error_record_4['Leitung_ID'] = 'L_ERR04'
        error_record_4['Verlegedatum'] = '32.13.2020'  # Ungültiges Datum
        error_record_4['Bemerkung'] = 'FEHLER: Ungültiges Datum'
        records.append(error_record_4)
    
    return pd.DataFrame(records)


def generate_multiple_files():
    """
    Generiert mehrere Test-Dateien für verschiedene Szenarien
    """
    
    # 1. Kleine Datei mit nur gültigen Daten
    df_small_valid = generate_test_data(num_records=10, include_errors=False)
    df_small_valid.to_excel('test_klein_gueltig.xlsx', index=False)
    print("✓ test_klein_gueltig.xlsx erstellt (10 Datensätze, alle gültig)")
    
    # 2. Mittlere Datei mit einigen Fehlern
    df_medium = generate_test_data(num_records=50, include_errors=True)
    df_medium.to_excel('test_mittel_mit_fehlern.xlsx', index=False)
    print("✓ test_mittel_mit_fehlern.xlsx erstellt (50+ Datensätze, mit Fehlern)")
    
    # 3. Große Datei für Performance-Test
    df_large = generate_test_data(num_records=500, include_errors=False)
    df_large.to_excel('test_gross_performance.xlsx', index=False)
    print("✓ test_gross_performance.xlsx erstellt (500 Datensätze für Performance-Test)")
    
    # 4. Datei mit speziellen Testfällen
    special_cases = []
    
    # Extremwerte Durchmesser
    special_cases.append({
        'Leitung_ID': 'L_SPECIAL_01',
        'Material': 'PE',
        'Durchmesser_mm': 800,  # Sehr groß
        'X_Start': 2683000,
        'Y_Start': 1248000,
        'X_End': 2683100,
        'Y_End': 1248100,
        'Verlegedatum': '2020-01-15',
        'Bemerkung': 'Haupttransportleitung - sehr großer Durchmesser'
    })
    
    # Sehr alte Leitung
    special_cases.append({
        'Leitung_ID': 'L_SPECIAL_02',
        'Material': 'Grauguss',
        'Durchmesser_mm': 150,
        'X_Start': 2683500,
        'Y_Start': 1248500,
        'X_End': 2683600,
        'Y_End': 1248600,
        'Verlegedatum': '1895-06-20',
        'Bemerkung': 'Historische Leitung aus Gründerzeit'
    })
    
    # Leitung mit Sonderzeichen
    special_cases.append({
        'Leitung_ID': 'L_SPECIAL_03',
        'Material': 'PE',
        'Durchmesser_mm': 100,
        'X_Start': 2684000,
        'Y_Start': 1249000,
        'X_End': 2684150,
        'Y_End': 1249150,
        'Verlegedatum': '2015-12-31',
        'Bemerkung': 'Leitung mit Spezialzeichen: äöü ÄÖÜ & < > " \' / \\'
    })
    
    # Sehr lange Leitung
    special_cases.append({
        'Leitung_ID': 'L_SPECIAL_04',
        'Material': 'Stahl',
        'Durchmesser_mm': 400,
        'X_Start': 2683000,
        'Y_Start': 1248000,
        'X_End': 2685000,  # 2km lang
        'Y_End': 1250000,
        'Verlegedatum': '2018-08-01',
        'Bemerkung': 'Fernleitung zwischen zwei Stadtteilen'
    })
    
    df_special = pd.DataFrame(special_cases)
    df_special.to_excel('test_spezialfaelle.xlsx', index=False)
    print("✓ test_spezialfaelle.xlsx erstellt (Spezielle Testfälle)")
    
    # 5. CSV-Version für FME-Tests
    df_medium.to_csv('test_mittel_mit_fehlern.csv', index=False, encoding='utf-8-sig')
    print("✓ test_mittel_mit_fehlern.csv erstellt (CSV-Format)")
    
    print("\n" + "="*60)
    print("ALLE TEST-DATEIEN ERFOLGREICH ERSTELLT")
    print("="*60)
    print("\nVerwendung:")
    print("  python werkleitungs_importer.py test_klein_gueltig.xlsx")
    print("  python werkleitungs_importer.py test_mittel_mit_fehlern.xlsx")
    print("\nErwartete Ergebnisse:")
    print("  - test_klein_gueltig.xlsx: 10/10 erfolgreich")
    print("  - test_mittel_mit_fehlern.xlsx: ~50/54 erfolgreich, 4 Fehler")
    print("  - Fehlerbericht wird als *_fehler.csv gespeichert")


def show_sample_data():
    """Zeigt Beispieldaten zur Ansicht"""
    df = generate_test_data(num_records=5, include_errors=False)
    print("\n" + "="*60)
    print("BEISPIEL-DATEN (erste 5 Zeilen)")
    print("="*60)
    print(df.to_string(index=False))
    print("\nSpalten:", list(df.columns))
    print("\nDatentypen:")
    print(df.dtypes)


if __name__ == "__main__":
    print("="*60)
    print("DUMMY-DATEN GENERATOR FÜR WERKLEITUNGS-IMPORT")
    print("="*60)
    print()
    
    # Zeige Beispieldaten
    show_sample_data()
    
    print("\n")
    input("Drücke Enter um Test-Dateien zu generieren...")
    
    # Generiere alle Test-Dateien
    generate_multiple_files()
    
    print("\n✓ FERTIG! Du kannst jetzt den Import testen.")
