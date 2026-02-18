import os
import csv
import subprocess
from datetime import datetime
from google.cloud import asset_v1

def load_list_from_file(filename):
    """Carga una lista desde un archivo (proyectos o activos)"""
    items = []
    try:
        with open(filename, "r") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    items.append(line)
        return items
    except FileNotFoundError:
        print(f"⚠️ Archivo {filename} no encontrado.")
        return []

def export_inventory_to_csv():
    client = asset_v1.AssetServiceClient()
    
    # Insumos desde tus archivos de texto
    projects_list = load_list_from_file("projects.txt")
    asset_types = load_list_from_file("assets.txt")

    if not projects_list:
        print("❌ Error: projects.txt está vacío o no existe.")
        return

    # Formato solicitado: YYYYMMDD_HHMM_inventory.csv
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    filename = f"{timestamp}_inventory.csv"

    try:
        with open(filename, mode='w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            # Definimos las columnas según tu requerimiento
            writer.writerow(["PROJECT_NAME", "RESOURCE_NAME", "SERVICE"])

            total_count = 0
            for p_id in projects_list:
                print(f"🔍 Auditando: {p_id}")
                scope = f"projects/{p_id}"
                
                try:
                    response = client.search_all_resources(
                        request={"scope": scope, "asset_types": asset_types}
                    )

                    for asset in response:
                        writer.writerow([
                            p_id,                # Usamos el ID del TXT como PROJECT_NAME
                            asset.display_name,  # Nombre del recurso individual
                            asset.asset_type     # Tipo de servicio
                        ])
                        total_count += 1
                except Exception as e:
                    print(f"⚠️ Sin acceso o error en proyecto {p_id}: {e}")

        print(f"✅ Éxito: Se exportaron {total_count} recursos a '{filename}'")
        
    except Exception as e:
        print(f"❌ Error al crear el archivo CSV: {e}")

if __name__ == "__main__":
    export_inventory_to_csv()