import os
import csv
import subprocess
from google.cloud import asset_v1
from google.cloud import resourcemanager_v3

def get_organization_id():
    """Detecta automáticamente el ID de la organización del proyecto actual"""
    try:
        client = resourcemanager_v3.ProjectsClient()
        
        # Intentamos obtener el Project ID del entorno o de gcloud
        project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
        if not project_id:
            project_id = subprocess.getoutput("gcloud config get-value project").strip()

        if not project_id or "(unset)" in project_id:
            print("❌ Error: No se pudo detectar un proyecto activo. Ejecuta 'gcloud config set project ID'")
            return None

        # Consultamos los detalles del proyecto para ver quién es su 'parent'
        request = resourcemanager_v3.GetProjectRequest(name=f"projects/{project_id}")
        project = client.get_project(request=request)
        
        parent = project.parent # Formato: 'organizations/12345678' o 'folders/123'
        
        if parent.startswith("organizations/"):
            org_id = parent.split("/")[-1]
            print(f"🏢 Organización detectada automáticamente: {org_id}")
            return org_id
        else:
            print(f"⚠️ El proyecto {project_id} no cuelga directamente de una organización.")
            return None
            
    except Exception as e:
        print(f"❌ Error al detectar la organización: {e}")
        return None

def export_inventory_to_csv(org_id, filename="inventario_gobierno.csv"):
    """Consulta los activos de la organización y genera el CSV"""
    client = asset_v1.AssetServiceClient()
    scope = f"organizations/{org_id}"
    
    # Lista de servicios a inventariar (puedes añadir más aquí)
    asset_types = [
        "compute.googleapis.com/Instance",
        "storage.googleapis.com/Bucket",
        "sqladmin.googleapis.com/Instance",
        "cloudfunctions.googleapis.com/CloudFunction",
        "container.googleapis.com/Cluster" # Kubernetes
    ]

    try:
        response = client.search_all_resources(
            request={
                "scope": scope, 
                "asset_types": asset_types
            }
        )

        with open(filename, mode='w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            # Tus columnas solicitadas
            writer.writerow(["PROJECT_NAME", "PROJECT_ID", "SERVICE"])

            count = 0
            for asset in response:
                # Extraemos el ID del proyecto del path (ej: projects/mi-proyecto)
                p_id = asset.project.split('/')[-1]
                
                writer.writerow([
                    asset.display_name, # Nombre del recurso
                    p_id,               # ID del proyecto
                    asset.asset_type    # Servicio (ej: compute.googleapis.com/Instance)
                ])
                count += 1
        
        print(f"✅ Éxito: Se exportaron {count} recursos a '{filename}'")

    except Exception as e:
        print(f"❌ Error al consultar activos: {e}")

if __name__ == "__main__":
    # Flujo automático
    organization_id = get_organization_id()
    
    if organization_id:
        export_inventory_to_csv(organization_id)
    else:
        print("No se pudo iniciar el inventario sin un ID de organización válido.")