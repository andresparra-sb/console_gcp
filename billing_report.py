import os
import csv
from datetime import datetime
from google.cloud import asset_v1
from google.cloud import bigquery
from google.cloud import resourcemanager_v3
from google.cloud import billing_v1

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

def get_billing_details(project_id):
    """Obtiene el ID y el Nombre de la cuenta de facturación"""
    client = billing_v1.CloudBillingClient()
    try:
        name = f"projects/{project_id}"
        info = client.get_project_billing_info(name=name)
        if info.billing_enabled:
            # Obtenemos el ID de la cuenta
            billing_id = info.billing_account_name.split('/')[-1]
            # Consultamos el nombre amigable de esa cuenta
            account_info = client.get_billing_account(name=f"billingAccounts/{billing_id}")
            return account_info.display_name, billing_id
        return "Facturación Desactivada", "N/A"
    except Exception:
        return "Sin Acceso", "N/A"

def get_project_details(project_id):
    client = resourcemanager_v3.ProjectsClient()
    try:
        name = f"projects/{project_id}"
        project = client.get_project(name=name)
        return project.create_time.strftime('%Y-%m-%d')
    except Exception:
        return "N/A"

def get_total_resources(project_id):
    client = asset_v1.AssetServiceClient()
    scope = f"projects/{project_id}"
    try:
        response = client.search_all_resources(request={"scope": scope}, timeout=60)
        return sum(1 for _ in response)
    except Exception:
        return 0

def get_project_costs(project_id):
    client = bigquery.Client()
    months = ["202601", "202512", "202511"]
    costs = {m: 0.0 for m in months}
    query = f"""
        SELECT 
            invoice.month as month, 
            ROUND(SUM(cost + (SELECT IFNULL(SUM(c.amount), 0) FROM UNNEST(credits) c)), 2) as total_cost
        FROM `{BILLING_TABLE}`
        WHERE project.id = '{project_id}'
        AND invoice.month IN ({','.join([f"'{m}'" for m in months])})
        GROUP BY 1
    """
    try:
        query_job = client.query(query)
        for row in query_job:
            costs[row.month] = row.total_cost
    except Exception:
        pass
    return costs

def generate_billing_report():
    raw_data = load_projects()
    if not raw_data: return

    projects_list = list(raw_data)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    
    # --- RUTA SOLICITADA ---
    output_dir = "./Reports/Billing"
    os.makedirs(output_dir, exist_ok=True) # Crea la carpeta si no existe
    filename = f"{output_dir}/reporte_multicuenta_{timestamp}.csv"

    print(f"🚀 Generando reporte consolidado en {filename}...")

    try:
        with open(filename, mode='w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            # Nueva columna a la izquierda: BILLING_ACCOUNT_NAME
            writer.writerow([
                "BILLING_ACCOUNT_NAME",
                "BILLING_ACCOUNT_ID",
                "PROJECT_NAME", 
                "PROJECT_ID",
                "CREATED_AT",
                "TOTAL_RESOURCES", 
                "COST_JAN_2026", 
                "COST_DEC_2025", 
                "COST_NOV_2025"
            ])

            for p_name, p_id in projects_list:
                print(f"📊 Procesando: {p_name}...")
                
                b_name, b_id = get_billing_details(p_id)
                creation_date = get_project_details(p_id)
                total_res = get_total_resources(p_id)
                costs = get_project_costs(p_id)
                
                writer.writerow([
                    b_name,
                    b_id,
                    p_name, 
                    p_id,
                    creation_date, 
                    total_res, 
                    costs.get("202601", 0), 
                    costs.get("202512", 0), 
                    costs.get("202511", 0)
                ])

        print(f"✅ Reporte finalizado exitosamente.")
    except Exception as e:
        print(f"❌ Error crítico: {e}")

if __name__ == "__main__":
    generate_billing_report()