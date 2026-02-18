import os
import csv
import subprocess
from datetime import datetime
from google.cloud import asset_v1
from google.cloud import resourcemanager_v3

def load_asset_types(filename="assets.txt"):
    """Lee los tipos de activos desde un archivo externo"""
    asset_types = []
    try:
        with open(filename, "r") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    asset_types.append(line)
        return asset_types
    except FileNotFoundError:
        print(f"⚠️ Archivo {filename} no encontrado. Usando lista por defecto.")
        return ["compute.googleapis.com/Instance", "storage.googleapis.com/Bucket"]

def get_organization_id():
    """Detecta automáticamente el ID de la organización del proyecto actual"""
    try:
        client = resourcemanager_v3.ProjectsClient()
        project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
        if not project_id:
            project_id = subprocess.getoutput("gcloud config get-value project").strip()

        if not project_id or "(unset)" in project_id:
            print("❌ Error: No se pudo detectar un proyecto activo.")
            return None

        request = resourcemanager_v3.GetProjectRequest(name=f"projects/{project_id}")
        project = client.get_project(request=request)
        parent = project.parent
        
        if parent.startswith("organizations/"):
            org_id = parent.split("/")[-1]
            print(f"🏢 Organización detectada: {org_id}")
            return org_id
        else:
            print(f"⚠️ El proyecto no pertenece a una organización.")
            return None
    except Exception as e:
        print(f"❌ Error al detectar organización: {e}")
        return None

def export_inventory_to_csv(org_id):
    """Consulta los activos y genera el CSV con formato: fecha_hora_inventory.csv"""
    client = asset_v1.AssetServiceClient()
    scope = f"organizations/{org_id}"
    
    # NUEVO FORMATO: AñoMesDia_HoraMinuto (20260218_1423)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    filename = f"{timestamp}_inventory.csv"
    
    asset_types = load_asset_types()

    try:
        response = client.search_all_resources(
            request={
                "scope": scope, 
                "asset_types": asset_types
            }
        )

        with open(filename, mode='w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow(["PROJECT_NAME", "PROJECT_ID", "SERVICE"])

            count = 0
            for asset in response:
                p_id = asset.project.split('/')[-1]
                writer.writerow([asset.display_name, p_id, asset.asset_type])
                count += 1
        
        print(f"✅ Éxito: Se exportaron {count} recursos a '{filename}'")
    except Exception as e:
        print(f"❌ Error al consultar activos: {e}")

if __name__ == "__main__":
    organization_id = get_organization_id()
    if organization_id:
        export_inventory_to_csv(organization_id)