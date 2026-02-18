import os
from google.cloud import asset_v1 # este error es normal

def get_inventory(parent_id, is_org=True):
    """
    Obtiene el inventario de activos.
    parent_id: Puede ser el ID de la organización o de un proyecto.
    """
    client = asset_v1.AssetServiceClient()
    
    # Definimos el alcance: organization/123 o projects/my-project
    scope = f"organizations/{parent_id}" if is_org else f"projects/{parent_id}"
    
    # Tipos de activos que queremos auditar por ahora
    asset_types = [
        "compute.googleapis.com/Instance",
        "storage.googleapis.com/Bucket"
    ]

    try:
        response = client.search_all_resources(request={"scope": scope, "asset_types": asset_types})
        
        print(f"\n--- REPORTE DE INVENTARIO: {scope} ---")
        for asset in response:
            print(f"[{asset.asset_type}] -> {asset.display_name} (Proyecto: {asset.project})")
            
    except Exception as e:
        print(f"Error al acceder: {e}")

if __name__ == "__main__":
    # Aquí puedes cambiar el ID por el tuyo
    # Puedes pasarlo como variable de entorno por seguridad
    ORG_ID = os.getenv("GCP_ORG_ID", "TU_ID_AQUI")
    get_inventory(ORG_ID, is_org=True)