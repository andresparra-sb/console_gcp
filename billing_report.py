def generate_billing_report():
    # 1. Cargamos la lista completa de proyectos
    raw_data = load_projects()
    if not raw_data:
        print("❌ No se encontraron proyectos en projects.txt")
        return

    projects_list = list(raw_data)
    
    # Nombre del archivo único con fecha y hora
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    filename = f"reporte_consolidado_costos_{timestamp}.csv"

    print(f"🚀 Generando reporte único para {len(projects_list)} proyectos...")

    # 2. ABRIMOS EL ARCHIVO FUERA DEL BUCLE
    try:
        with open(filename, mode='w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            # Escribimos el encabezado una sola vez
            writer.writerow([
                "PROJECT_NAME", 
                "TOTAL_RESOURCES", 
                "COST_JAN_2026", 
                "COST_DEC_2025", 
                "COST_NOV_2025"
            ])

            # 3. AHORA RECORREMOS TODOS LOS PROYECTOS
            for p_name, p_id in projects_list:
                print(f"📊 Procesando: {p_name} ({p_id})...")
                
                # Paso A: Conteo de recursos
                total_res = get_total_resources(p_id)
                
                # Paso B: Consulta de costos en BigQuery
                costs = get_project_costs(p_id)
                
                # Paso C: Escribimos la fila en el archivo abierto
                writer.writerow([
                    p_name, 
                    total_res, 
                    costs.get("202601", 0), 
                    costs.get("202512", 0), 
                    costs.get("202511", 0)
                ])

        print(f"✅ Proceso terminado. Archivo consolidado: {filename}")
        
    except Exception as e:
        print(f"❌ Error al escribir el archivo consolidado: {e}")

if __name__ == "__main__":
    generate_billing_report()