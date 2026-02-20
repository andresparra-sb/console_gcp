import csv
import os
import re
import sys
import argparse
from collections import defaultdict
from pathlib import Path
from typing import List, Dict, Tuple


# Configuración por defecto
DEFAULT_INPUT_FOLDER = "Files_report"
BASE_PROJECT_PATH = "/Users/YeisonAndresParraVargas/Documents/github/console_gcp"
OUTPUT_FOLDER = "Reports/Billing"

# Umbrales para evitar porcentajes/proyecciones irreales por bases muy pequeñas
MIN_PREV_SUBTOTAL_FOR_PCT = 10.0  # USD
MIN_SUBTOTAL_FOR_FORECAST = 10.0  # USD


def parse_billing_filename(filename: str) -> Tuple[str, str, bool]:
    """
    Parsea el nombre de archivo de billing para extraer:
    - Nombre de la cuenta de facturación
    - Mes en formato YYYY-MM
    - Si tiene sufijo (1), (2), etc. (para diferenciar cuentas duplicadas)
    
    Ejemplos:
    - "Billing Account for segurosbolivar.com_Reports, 2026-01-01 — 2026-01-31.csv"
      -> ("Billing Account for segurosbolivar.com", "2026-01", False)
    - "Mi cuenta de facturación_Reports, 2026-01-01 — 2026-01-31 (1).csv"
      -> ("Mi cuenta de facturación", "2026-01", True)
    """
    # Extraer mes (YYYY-MM)
    month_match = re.search(r"(\d{4})-(\d{2})-\d{2}", filename)
    if not month_match:
        return None, None, False
    year, month = month_match.group(1), month_match.group(2)
    month_key = f"{year}-{month}"
    
    # Detectar sufijo (1), (2), etc.
    suffix_match = re.search(r"\((\d+)\)\.csv$", filename)
    has_suffix = suffix_match is not None
    suffix_num = int(suffix_match.group(1)) if suffix_match else None
    
    # Extraer nombre de cuenta (todo antes de "_Reports")
    # Si tiene sufijo, removerlo primero
    base_name = filename
    if has_suffix:
        base_name = re.sub(r"\s*\(\d+\)\.csv$", ".csv", base_name)
    
    account_match = re.match(r"^(.+?)_Reports,", base_name)
    if not account_match:
        return None, None, False
    
    account_name = account_match.group(1)
    
    return account_name, month_key, has_suffix


def generate_account_id(account_name: str, has_suffix: bool, suffix_num: int = None) -> str:
    """
    Genera un ID único para la cuenta de facturación.
    Si hay sufijo, lo incluye en el nombre y ID.
    """
    # Normalizar nombre para ID: minúsculas, espacios a guiones, caracteres especiales removidos
    base_id = re.sub(r"[^a-zA-Z0-9\s-]", "", account_name.lower())
    base_id = re.sub(r"\s+", "-", base_id.strip())
    
    if has_suffix and suffix_num:
        display_name = f"{account_name} {suffix_num}"
        account_id = f"BA-{base_id}-{suffix_num}"
    else:
        display_name = account_name
        account_id = f"BA-{base_id}"
    
    return display_name, account_id


def scan_billing_files(folder_path: str) -> List[Dict]:
    """
    Escanea la carpeta especificada y encuentra todos los archivos CSV de billing.
    Retorna una lista de diccionarios con la información de cada archivo.
    """
    input_files = []
    folder = Path(folder_path)
    
    if not folder.exists():
        raise ValueError(f"La carpeta no existe: {folder_path}")
    
    # Buscar todos los archivos CSV que contengan "_Reports," en el nombre
    csv_files = list(folder.glob("*_Reports,*.csv"))
    
    if not csv_files:
        print(f"ADVERTENCIA: No se encontraron archivos CSV de billing en: {folder_path}")
        return []
    
    # Agrupar archivos por cuenta de facturación para manejar duplicados
    account_groups = defaultdict(list)
    
    for csv_file in csv_files:
        account_name, month_key, has_suffix = parse_billing_filename(csv_file.name)
        
        if account_name is None:
            print(f"ADVERTENCIA: No se pudo parsear el archivo: {csv_file.name}")
            continue
        
        # Detectar sufijo numérico si existe
        suffix_match = re.search(r"\((\d+)\)\.csv$", csv_file.name)
        suffix_num = int(suffix_match.group(1)) if suffix_match else None
        
        # Crear clave única para agrupar: nombre + sufijo
        if has_suffix and suffix_num:
            group_key = (account_name, suffix_num)
        else:
            group_key = (account_name, None)
        
        account_groups[group_key].append({
            "path": str(csv_file),
            "account_name": account_name,
            "month_key": month_key,
            "has_suffix": has_suffix,
            "suffix_num": suffix_num,
        })
    
    # Generar IDs y nombres de cuenta finales
    input_files = []
    for (account_name, suffix_num), files in account_groups.items():
        display_name, account_id = generate_account_id(
            account_name, 
            has_suffix=(suffix_num is not None),
            suffix_num=suffix_num
        )
        
        for file_info in files:
            input_files.append({
                "path": file_info["path"],
                "account_name": display_name,
                "account_id": account_id,
            })
    
    print(f"Encontrados {len(input_files)} archivos de billing de {len(account_groups)} cuentas")
    return input_files


def extract_month_key(path: str) -> str:
    """
    Extrae una clave de mes en formato YYYY-MM desde el nombre del archivo.
    Ejemplo: '..., 2026-01-01 — 2026-01-31.csv' -> '2026-01'
    """
    filename = os.path.basename(path)
    _, month_key, _ = parse_billing_filename(filename)
    if month_key is None:
        raise ValueError(f"No se encontró fecha en el nombre de archivo: {path}")
    return month_key


def to_float(value: str) -> float:
    if value is None:
        return 0.0
    value = value.strip()
    if not value:
        return 0.0
    # El CSV viene con punto decimal (ej: 4663.72)
    try:
        return float(value)
    except ValueError:
        # Por si acaso hay comas como separador decimal
        value = value.replace(",", ".")
        return float(value)


def main(input_folder: str = None, output_folder: str = None, base_path: str = None) -> None:
    # Usar argumentos si se proporcionan, sino usar valores por defecto
    folder = input_folder if input_folder else DEFAULT_INPUT_FOLDER
    base_project = base_path if base_path else BASE_PROJECT_PATH
    out_folder = output_folder if output_folder else OUTPUT_FOLDER
    
    # Construir ruta completa de salida: base_project/Reports/Billing
    full_output_path = os.path.join(base_project, out_folder)
    
    # Escanear archivos automáticamente
    input_files = scan_billing_files(folder)
    
    if not input_files:
        print("No se encontraron archivos de billing para procesar.")
        return
    
    # totals[(account_name, account_id, project_name, project_id, project_number)][month_key] = subtotal
    totals: dict = defaultdict(lambda: defaultdict(float))
    months_found = set()

    for entry in input_files:
        path = entry["path"]
        account_name = entry["account_name"]
        account_id = entry["account_id"]

        if not os.path.exists(path):
            print(f"ADVERTENCIA: no existe el archivo: {path}")
            continue

        month_key = extract_month_key(path)
        months_found.add(month_key)

        with open(path, newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                project_name = row.get("Project name", "").strip()
                project_id = row.get("Project ID", "").strip()
                project_number = row.get("Project number", "").strip()

                # Saltar filas de subtotal/impuestos (no tienen nombre de proyecto)
                if not project_name:
                    continue

                subtotal_str = row.get("Subtotal ($)", "") or row.get("Unrounded subtotal ($)", "")
                subtotal = to_float(subtotal_str)

                key = (account_name, account_id, project_name, project_id, project_number)
                totals[key][month_key] += subtotal

    if not totals:
        print("No se encontraron datos de proyectos en los CSV indicados.")
        return

    # Orden cronológico de los meses detectados
    months_sorted = sorted(months_found)
    
    # Generar nombre del archivo basado en el último mes procesado
    if months_sorted:
        last_month = months_sorted[-1]  # Formato: YYYY-MM
        output_filename = f"Billing_{last_month}.csv"
    else:
        output_filename = "Billing_unknown.csv"
    
    # Crear carpeta de salida si no existe
    output_dir = Path(full_output_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Ruta completa del archivo de salida
    output = str(output_dir / output_filename)

    header_month_cols = [f"Subtotal {m}" for m in months_sorted]

    # Identificar meses relevantes para las métricas
    # Nombres de columnas más cortos y claros
    percent_change_col_name = "MoM Change %"
    projected_col_name = "Next Month Forecast"
    projected_growth_pct_col_name = "Next Month Growth %"

    with open(output, "w", newline="", encoding="utf-8") as out_f:
        writer = csv.writer(out_f)
        header = [
            "Billing Account Name",
            "Billing Account ID",
            "Project Name",
            "Project ID",
            "Project Number",
        ] + header_month_cols + [
            percent_change_col_name,
            projected_col_name,
            projected_growth_pct_col_name,
        ]
        writer.writerow(header)

        for (account_name, account_id, project_name, project_id, project_number), monthly in sorted(
            totals.items(), key=lambda x: (x[0][0], x[0][2])
        ):
            # Valores por mes en el orden de months_sorted
            monthly_values = [monthly.get(m, 0.0) for m in months_sorted]

            # Cambio porcentual entre el último y el penúltimo mes
            percent_change_str = ""
            if len(months_sorted) >= 2:
                last = months_sorted[-1]
                prev = months_sorted[-2]
                last_val = monthly.get(last, 0.0)
                prev_val = monthly.get(prev, 0.0)
                # Calcular si hay un valor previo > 0 (evitar división por cero)
                # Solo evitar si el valor previo es exactamente 0 o muy pequeño (< $0.01)
                if prev_val > 0.01:
                    pct_change = (last_val - prev_val) / prev_val * 100.0
                    percent_change_str = f"{pct_change:.2f}%"
                elif prev_val == 0.0 and last_val > 0:
                    # Si pasó de 0 a un valor positivo, indicar crecimiento infinito o "N/A"
                    percent_change_str = "N/A"

            # Proyección del próximo mes (Feb) usando los últimos 3 meses (Nov, Dec, Jan)
            projected_val_str = ""
            projected_growth_pct_str = ""
            if len(months_sorted) >= 2:
                # Tomamos como máximo los últimos 3 meses
                recent_months = months_sorted[-3:] if len(months_sorted) >= 3 else months_sorted
                recent_vals = [monthly.get(m, 0.0) for m in recent_months]

                # Preferimos una tasa mensual compuesta (CMGR) basada en el primer y último mes
                # para evitar sesgos por picos en un solo mes.
                # CMGR = (last/first)^(1/(n-1)) - 1  ;  Feb = last * (1 + CMGR)
                n = len(recent_vals)
                first_val = recent_vals[0] if n >= 1 else 0.0
                last_val = recent_vals[-1] if n >= 1 else 0.0

                if (
                    n >= 3
                    and first_val >= MIN_SUBTOTAL_FOR_FORECAST
                    and last_val >= MIN_SUBTOTAL_FOR_FORECAST
                ):
                    cmgr = (last_val / first_val) ** (1.0 / (n - 1)) - 1.0
                    projected_val = last_val * (1.0 + cmgr)
                    projected_val_str = f"{projected_val:.2f}"
                    projected_growth_pct_str = f"{cmgr * 100.0:.2f}%"
                else:
                    # Fallback realista: tendencia lineal en USD usando los últimos 2 meses
                    if n >= 2:
                        prev_val = recent_vals[-2]
                        
                        # Si ambos meses son >= $10, usar tendencia lineal
                        if prev_val >= MIN_SUBTOTAL_FOR_FORECAST and last_val >= MIN_SUBTOTAL_FOR_FORECAST:
                            delta = last_val - prev_val
                            projected_val = max(0.0, last_val + delta)
                            projected_val_str = f"{projected_val:.2f}"
                            if last_val > 0:
                                projected_growth_pct_str = f"{(delta / last_val) * 100.0:.2f}%"
                        # Si el último mes es >= $10 pero el anterior es pequeño, usar proyección conservadora
                        elif last_val >= MIN_SUBTOTAL_FOR_FORECAST:
                            if prev_val > 0:
                                # Hay algún valor previo, proyectamos un crecimiento conservador del 5%
                                projected_val = last_val * 1.05
                                projected_val_str = f"{projected_val:.2f}"
                                projected_growth_pct_str = "5.00%"
                            else:
                                # No hay valor previo significativo, mantenemos el valor actual
                                projected_val = last_val
                                projected_val_str = f"{projected_val:.2f}"
                                projected_growth_pct_str = "0.00%"
                        # Si ambos meses son pequeños pero hay tendencia (último mes > 0), calcular igual
                        elif last_val > 0 and prev_val > 0:
                            # Usar tendencia lineal incluso para valores pequeños
                            delta = last_val - prev_val
                            projected_val = max(0.0, last_val + delta)
                            projected_val_str = f"{projected_val:.2f}"
                            if last_val > 0:
                                projected_growth_pct_str = f"{(delta / last_val) * 100.0:.2f}%"
                        # Si solo el último mes tiene valor (prev_val = 0 o muy pequeño)
                        elif last_val > 0:
                            # Mantener el valor actual si no hay tendencia previa
                            projected_val = last_val
                            projected_val_str = f"{projected_val:.2f}"
                            projected_growth_pct_str = "0.00%"

            row = [
                account_name,
                account_id,
                project_name,
                project_id,
                project_number,
            ] + [f"{v:.2f}" for v in monthly_values] + [
                percent_change_str,
                projected_val_str,
                projected_growth_pct_str,
            ]

            writer.writerow(row)

    print(f"Archivo combinado generado: {os.path.abspath(output)}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Combina archivos CSV de billing de GCP en un solo archivo consolidado"
    )
    parser.add_argument(
        "--folder",
        "-f",
        type=str,
        required=True,
        help="Carpeta donde buscar archivos CSV de billing (requerido)",
    )
    parser.add_argument(
        "--output-folder",
        type=str,
        default=OUTPUT_FOLDER,
        help=f"Carpeta relativa donde guardar el archivo de salida dentro del proyecto (default: {OUTPUT_FOLDER})",
    )
    parser.add_argument(
        "--base-path",
        type=str,
        default=BASE_PROJECT_PATH,
        help=f"Ruta base del proyecto donde se guardará el archivo (default: {BASE_PROJECT_PATH})",
    )
    
    args = parser.parse_args()
    
    # Llamar a main con los argumentos
    main(input_folder=args.folder, output_folder=args.output_folder, base_path=args.base_path)

