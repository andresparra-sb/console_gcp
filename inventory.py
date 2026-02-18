import os
import csv
from google.cloud import asset_v1

def export_inventory_to_csv(parent_id, filename="inventario_gobierno.csv"):
    client = asset_v1.AssetServiceClient()
    scope = f"organizations/{821680696172}" # ID ORGANIZATION
    
    # Tipos de activos a auditar
    asset_types = [
        "compute.googleapis.com/Instance",
        "storage.googleapis.com/Bucket",
        "sqladmin.googleapis.com/Instance",
        "cloudfunctions.googleapis.com/CloudFunction"
    ]

    try:
        # Buscamos los recursos
        response = client.search_all_resources(
            request={
                "scope": scope, 
                "asset_types": asset_types
            }
        )

        # Preparamos el archivo CSV
        with open(filename, mode='w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            # Definimos las columnas que pediste
            writer.writerow(["PROJECT_NAME", "PROJECT_ID", "SERVICE"])

            count = 0
            for asset in response:
                # El campo 'project' suele venir como 'projects/12345' o 'projects/id-nombre'
                # Extraemos solo el ID/Nombre del string
                p_id_raw = asset.project.split('/')[-1]
                
                # En la API de Assets:
                # display_name es el nombre del recurso (ej: vm-produccion)
                # asset_type es el servicio (ej: compute.googleapis.com/Instance)
                
                writer.writerow([
                    asset.display_name, # Usamos el nombre del recurso como nombre descriptivo
                    p_id_raw,           # ID del proyecto
                    asset.asset_type    # El servicio/tipo
                ])
                count += 1
        
        print(f"✅ Éxito: Se exportaron {count} recursos a {filename}")

    except Exception as e:
        print(f"❌ Error al generar inventario: {e}")

if __name__ == "__main__":
    ORG_ID = os.getenv("821680696172")
    if ORG_ID:
        export_inventory_to_csv(ORG_ID)
    else:
        print("Error: Configura la variable GCP_ORG_ID (ej: export GCP_ORG_ID=821680696172)")