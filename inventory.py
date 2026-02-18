import os
import csv
from datetime import datetime
from google.cloud import asset_v1

def load_projects(filename="projects.txt", separator=","):
    """Carga pares de (Nombre, ID) desde el archivo txt"""
    projects = []
    try:
        with open(filename, "r") as f:
            for line in f:
                line = line.strip()
                # Ignoramos comentarios y líneas vacías o sin el separador
                if line and not line.startswith("#") and separator in line:
                    parts = line.split(separator)
                    if len(parts) >= 2:
                        name = parts[0].strip()
                        p_id = parts[1].strip()
                        projects.append((name, p_id))
        return projects
    except FileNotFoundError:
        print(f"⚠️ Archivo {filename} no encontrado.")
        return []

def load_asset_types(filename="assets.txt"):
    """Lee los tipos de activos desde assets.txt"""
    asset_types = []
    try:
        with open(filename, "r") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    asset_types.append(line)
        return asset_types
    except FileNotFoundError:
        return ["compute.googleapis.com/Instance", "storage.googleapis.com/Bucket"]

def export_inventory_to_csv():
    client = asset_v1.AssetServiceClient()
    
    # Cargamos configuraciones
    projects_data = load_projects()
    asset_types = load_asset_types()

    if not projects_data:
        print("❌ Error: projects.txt está vacío o mal formateado (usa: Nombre,ID).")
        return

    # Nombre de archivo solicitado: YYYYMMDD_HHMM_inventory.csv
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    filename = f"{timestamp}_inventory.csv"

    try:
        with open(filename, mode='w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            # Encabezados limpios
            writer.writerow(["PROJECT_NAME", "RESOURCE_NAME", "SERVICE"])

            total_count = 0
            for p_name, p_id in projects_data:
                print(f"🔍 Auditando: {p_name} ({p_id})...")
                scope = f"projects/{p_id}"
                
                try:
                    response = client.search_all_resources(
                        request={"scope": scope, "asset_types": asset_types}
                    )

                    for asset in response:
                        writer.writerow([
                            p_name,              # Coloca el nombre amigable del TXT
                            asset.display_name,  # Nombre del recurso
                            asset.asset_type     # Tipo de servicio
                        ])
                        total_count += 1
                except Exception as e:
                    print(f"⚠️ Error en {p_id}: {e}")

        print(f"✅ Éxito: Se exportaron {total_count} recursos a '{filename}'")
        
    except Exception as e:
        print(f"❌ Error al crear el archivo: {e}")

if __name__ == "__main__":
    export_inventory_to_csv()