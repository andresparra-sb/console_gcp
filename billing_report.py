import os
import csv
from datetime import datetime
from google.cloud import asset_v1
from google.cloud import bigquery

# --- CONFIGURACIÓN ---
BILLING_TABLE = "sb-ecosistemaanalitico-lago.daily_cost.gcp_billing_export_v1_01C684_6EFEC0_1C9725"

def load_projects(filename="projects.txt", separator=","):
    """Carga la lista de proyectos desde el archivo TXT"""
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

def get_total_resources(project_id):
    """Cuenta recursos usando Cloud Asset API"""
    client = asset_v1.AssetServiceClient()
    scope = f"projects/{project_id}"
    try:
        # Timeout de 60s para evitar errores de red en proyectos grandes
        response = client.search_all_resources(request={"scope": scope}, timeout=60)
        return sum(1 for _ in response)
    except Exception:
        return 0

def get_project_costs(project_id):
    """Consulta costos históricos en BigQuery"""
    client = bigquery.Client()
    # Meses solicitados: Enero 2026, Diciembre 2025, Noviembre 2025
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
    """Función principal que genera el archivo consolidado"""
    raw_data = load_projects()
    if not raw_data:
        return

    projects_list = list(raw_data)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    filename = f"reporte_consolidado_costos_{timestamp}.csv"

    print(f"🚀 Iniciando reporte consolidado para {len(projects_list)} proyectos...")

    try:
        with open(filename, mode='w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow(["PROJECT_NAME", "TOTAL_RESOURCES", "COST_JAN_2026", "COST_DEC_2025", "COST_NOV_2025"])

            for p_name, p_id in projects_list:
                print(f"📊 Procesando: {p_name}...")
                total_res = get_total_resources(p_id)
                costs = get_project_costs(p_id)
                
                writer.writerow([
                    p_name, 
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