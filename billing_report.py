import os
import csv
from datetime import datetime
from google.cloud import asset_v1
from google.cloud import bigquery
from google.cloud import resourcemanager_v3  # Nueva librería necesaria

# --- CONFIGURACIÓN ---
BILLING_TABLE = "sb-ecosistemaanalitico-lago.daily_cost.gcp_billing_export_v1_01C684_6EFEC0_1C9725"

def load_projects(filename="projects.txt", separator=","):
    projects = []
    try:
        with open(filename, "r") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and separator in line:
                    parts = line.split(separator)
                    projects.append((parts[0].strip(), parts[1].strip()))
        return projects
    except FileNotFoundError:
        print(f"❌ Archivo {filename} no encontrado.")
        return []

def get_project_creation_date(project_id):
    """Obtiene la fecha de creación del proyecto"""
    client = resourcemanager_v3.ProjectsClient()
    try:
        # El nombre del recurso debe ser 'projects/PROJECT_ID'
        name = f"projects/{project_id}"
        project = client.get_project(name=name)
        # Formateamos la fecha a algo legible (YYYY-MM-DD)
        return project.create_time.strftime('%Y-%m-%d')
    except Exception as e:
        print(f"  ⚠️ No se pudo obtener fecha para {project_id}")
        return "N/A"

def get_total_resources(project_id):
    """Cuenta recursos usando Cloud Asset API"""
    client = asset_v1.AssetServiceClient()
    scope = f"projects/{project_id}"
    try:
        response = client.search_all_resources(request={"scope": scope}, timeout=60)
        return sum(1 for _ in response)
    except Exception:
        return 0

def get_project_costs(project_id):
    """Consulta costos históricos en BigQuery"""
    client = bigquery.Client()
    months = ["202601", "202512", "202511"]
    costs = {m: 0.0 for m in months}

    query = f"""
        SELECT 
            invoice.month as month, 
            SUM(cost) as total_cost
        FROM `{BILLING_TABLE}`
        WHERE project.id = '{project_id}'
        AND invoice.month IN ({','.join([f"'{m}'" for m in months])})
        GROUP BY 1
    """
    try:
        query_job = client.query(query)
        for row in query_job:
            costs[row.month] = round(row.total_cost, 2)
    except Exception as e:
        print(f"  ⚠️ Error BigQuery para {project_id}: {e}")
    return costs

def generate_billing_report():
    raw_data = load_projects()
    if not raw_data: return

    projects_list = list(raw_data)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    filename = f"reporte_consolidado_costos_{timestamp}.csv"

    print(f"🚀 Iniciando reporte consolidado para {len(projects_list)} proyectos...")

    try:
        with open(filename, mode='w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            # Nueva estructura de columnas
            writer.writerow([
                "PROJECT_NAME", 
                "CREATED_AT",  # Nueva columna
                "TOTAL_RESOURCES", 
                "COST_JAN_2026", 
                "COST_DEC_2025", 
                "COST_NOV_2025"
            ])

            for p_name, p_id in projects_list:
                print(f"📊 Procesando: {p_name}...")
                
                # Paso 1: Fecha de creación
                creation_date = get_project_creation_date(p_id)
                
                # Paso 2: Conteo de recursos
                total_res = get_total_resources(p_id)
                
                # Paso 3: Costos
                costs = get_project_costs(p_id)
                
                writer.writerow([
                    p_name, 
                    creation_date, 
                    total_res, 
                    costs.get("202601", 0), 
                    costs.get("202512", 0), 
                    costs.get("202511", 0)
                ])

        print(f"✅ Reporte finalizado con éxito: {filename}")
    except Exception as e:
        print(f"❌ Error al generar el CSV: {e}")

if __name__ == "__main__":
    generate_billing_report()