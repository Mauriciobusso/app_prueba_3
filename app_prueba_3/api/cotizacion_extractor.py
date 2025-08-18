import io
import re
from typing import List, Union, Dict, Optional, Tuple
import pdfplumber
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from google.oauth2 import service_account
from ..utils import Cot, completar_con_ceros

SERVICE_ACCOUNT_FILE = 'app_prueba_3/serviceAccountKey.json'
SCOPES = ['https://www.googleapis.com/auth/drive.readonly']

def get_drive_service():
    creds = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    return build('drive', 'v3', credentials=creds)

def download_pdf_from_drive(file_id: str) -> bytes:
    """Descarga un archivo PDF de Google Drive por su ID (soporta unidades compartidas) y retorna los bytes."""
    service = get_drive_service()
    request = service.files().get_media(fileId=file_id, supportsAllDrives=True)
    fh = io.BytesIO()
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while not done:
        status, done = downloader.next_chunk()
    fh.seek(0)
    return fh.read()

def extract_tables_from_pdf(pdf_bytes: bytes) -> List[Dict]:
    """Extrae tablas de un PDF (bytes) y retorna una lista de filas como diccionarios."""
    tables = []
    descripcion_col = 'DESCRIPCIÓN DE PRODUCTOS'
    descripcion_trabajos_col = 'DESCRIPCIÓN DE TRABAJOS'
    descripcion_extraida = False
    
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for page in pdf.pages:
            for table in page.extract_tables():
                # Detectar si es la tabla de productos
                is_productos = False
                is_trabajos = False
                
                for row in table[:2]:
                    if any((h or '').strip().upper() == descripcion_col for h in row):
                        is_productos = True
                        break
                    if any((h or '').strip().upper() == descripcion_trabajos_col for h in row):
                        is_trabajos = True
                        break
                
                if is_productos:
                    # --- Lógica especial para tabla de productos ---
                    header_row_idx = 0
                    for idx, row in enumerate(table):
                        if any((h or '').strip().upper() == descripcion_col for h in row):
                            header_row_idx = idx
                            break
                    raw_headers = [(h or "").strip() for h in table[header_row_idx]]
                    valid_indices = [i for i, h in enumerate(raw_headers) if h]
                    headers = [raw_headers[i] for i in valid_indices]
                    num_cols = len(headers)
                    cantidad_idx = None
                    cantidad_valor = None
                    for idx, row in enumerate(table[header_row_idx+1:], start=header_row_idx+1):
                        for cell in row:
                            if cell and 'CANTIDAD DE FAMILIAS' in cell.upper():
                                cantidad_idx = idx
                                m = re.search(r'CANTIDAD DE FAMILIAS\s*:?\s*(\d+)', cell, re.IGNORECASE)
                                if m:
                                    cantidad_valor = m.group(1)
                                else:
                                    cantidad_valor = cell.strip()
                                break
                        if cantidad_idx is not None:
                            break
                    if cantidad_idx and cantidad_idx > header_row_idx+1:
                        for row in table[header_row_idx+1:cantidad_idx]:
                            if len(row) == 1:
                                descripcion = row[0].strip()
                            else:
                                try:
                                    desc_idx = [h.upper() for h in headers].index(descripcion_col)
                                    descripcion = (row[desc_idx] or '').strip() if desc_idx < len(row) else ''
                                except ValueError:
                                    descripcion = ''
                            if descripcion:
                                tables.append({descripcion_col: descripcion})
                                descripcion_extraida = True
                    if cantidad_valor:
                        tables.append({'CANTIDAD DE FAMILIAS': cantidad_valor})
                        
                elif is_trabajos:
                    # --- Lógica especial para tabla de trabajos ---
                    header_row_idx = 0
                    for idx, row in enumerate(table):
                        if any((h or '').strip().upper() == descripcion_trabajos_col for h in row):
                            header_row_idx = idx
                            break
                    
                    raw_headers = [(h or "").strip() for h in table[header_row_idx]]
                    valid_indices = [i for i, h in enumerate(raw_headers) if h]
                    headers = [raw_headers[i] for i in valid_indices]
                    
                    # Procesar todas las filas después del header
                    for row in table[header_row_idx+1:]:
                        if isinstance(row, list) and len(row) > 0:
                            # Crear un dict con las columnas disponibles
                            clean_row = [(row[i].strip() if row[i] else "") if i < len(row) else "" for i in valid_indices]
                            if any(cell for cell in clean_row):
                                row_dict = dict(zip(headers, clean_row))
                                # Solo agregar si tiene contenido útil en la descripción
                                desc_value = row_dict.get(descripcion_trabajos_col, "").strip()
                                if desc_value and desc_value.lower() != "sin trabajos disponibles":
                                    tables.append(row_dict)
                    
                else:
                    # --- Lógica general para cualquier otra tabla ---
                    # Buscar la primera fila con más de una celda como header
                    header_row_idx = 0
                    for idx, row in enumerate(table):
                        if len(row) > 1:
                            header_row_idx = idx
                            break
                    raw_headers = [(h or "").strip() for h in table[header_row_idx]]
                    valid_indices = [i for i, h in enumerate(raw_headers) if h]
                    headers = [raw_headers[i] for i in valid_indices]
                    num_cols = len(headers)
                    for row in table[header_row_idx+1:]:
                        clean_row = [(row[i].strip() if row[i] else "") if i < len(row) else "" for i in valid_indices]
                        if any(cell for cell in clean_row):
                            tables.append(dict(zip(headers, clean_row)))
                            
        # Si no hay filas intermedias en productos, fallback a texto plano
        if not descripcion_extraida:
            for page in pdf.pages:
                text = page.extract_text() or ""
                lines = [l.strip() for l in text.splitlines()]
                for i, line in enumerate(lines):
                    if descripcion_col in line.upper():
                        for next_line in lines[i+1:]:
                            if next_line and 'CANTIDAD DE FAMILIAS' not in next_line.upper():
                                tables.append({descripcion_col: next_line})
                                break
                        break
    return tables


# =============================
# Familias: parsing y validación
# =============================

FAMILIA_DESC_KEY = 'DESCRIPCIÓN DE PRODUCTOS'


def _normalize_family_code(code: str) -> str:
    """Normaliza el código de familia: trim, mayúsculas, compactar espacios.
    No aplica padding ni cambia el contenido alfanumérico.
    """
    if not code:
        return ""
    code = re.sub(r"\s+", " ", str(code)).strip().upper()
    # Quitar prefijos como FLIA o FAMILIA si quedaron mezclados
    code = re.sub(r"^(FLIA|FAMILIA)\s*[:\-]?\s*", "", code, flags=re.IGNORECASE)
    return code


def _parse_family_line(line: str) -> List[Dict]:
    """Intenta extraer (code, description) desde una línea de descripción de productos.
    Casos contemplados:
      - "FLIA 01 - Pinturas"
      - "FAMILIA A02: Sistemas de ..."
      - "03 Equipos eléctricos"
      - "B5 - Válvulas"
      - "Componentes (FLIA 4)"
      - "Familia 8 - Accesorios"
      - "Flia A24 - Equipos"
      - "Equipos Eléctricos (34)"
    Devuelve lista de dict {code, description, raw} o lista vacía si no matchea ninguno.
    """
    if not line:
        return []
        
    results = []
    # Primero dividir el texto por líneas
    lines = [l.strip() for l in line.split('\n')]
    
    # Procesar cada línea individualmente
    for single_line in lines:
        if not single_line.strip():
            continue
            
        raw = single_line
        clean_line = re.sub(r"\s+", " ", single_line).strip()

        # Patrones ordenados de más específicos a más generales
        patterns: List[Tuple[re.Pattern, Tuple[int, int]]] = [
            # FLIA/FAMILIA + código + separador + descripción
            (re.compile(r"^(?:FLIA|FAMILIA)\s*[:\-]?\s*([A-Za-z]?\d+[A-Za-z]?)\s*[\-–:]{1}\s*(.+)$", re.IGNORECASE), (1, 2)),
            # Código + separador + descripción
            (re.compile(r"^([A-Za-z]?\d+[A-Za-z]?)\s*[\-–:]{1}\s*(.+)$", re.IGNORECASE), (1, 2)),
            # FLIA/FAMILIA + código + espacio + descripción
            (re.compile(r"^(?:FLIA|FAMILIA)\s*[:\-]?\s*([A-Za-z]?\d+[A-Za-z]?)\s+(.+)$", re.IGNORECASE), (1, 2)),
            # Código + espacio + descripción
            (re.compile(r"^([A-Za-z]?\d+[A-Za-z]?)\s+(.+)$", re.IGNORECASE), (1, 2)),
            # Descripción + (FLIA/FAMILIA + código)
            (re.compile(r"^(.+)\s*\(\s*(?:FLIA|FAMILIA)\s*[:\-]?\s*([A-Za-z]?\d+[A-Za-z]?)\s*\)$", re.IGNORECASE), (2, 1)),
            # Descripción + (código)
            (re.compile(r"^(.+)\s*\(\s*([A-Za-z]?\d+[A-Za-z]?)\s*\)$", re.IGNORECASE), (2, 1)),
            # Solo código (sin descripción)
            (re.compile(r"^(?:FLIA|FAMILIA)\s*[:\-]?\s*([A-Za-z]?\d+[A-Za-z]?)$", re.IGNORECASE), (1, -1)),
            (re.compile(r"^([A-Za-z]?\d+[A-Za-z]?)$", re.IGNORECASE), (1, -1)),
        ]

        for pat, (gcode, gdesc) in patterns:
            m = pat.match(clean_line)
            if m:
                code = _normalize_family_code(m.group(gcode))
                desc = (m.group(gdesc).strip() if gdesc != -1 else "") if m.lastindex and gdesc != -1 else ""
                results.append({"code": code, "description": desc, "raw": raw})
                break  # Found a match for this line, move to next line

    return results



def extract_familias_from_tablas(tablas: List[Dict]) -> Tuple[List[Dict], Optional[int]]:
    """A partir de las tablas extraídas, obtiene las líneas bajo 'DESCRIPCIÓN DE PRODUCTOS'
    y parsea familias. También intenta leer 'CANTIDAD DE FAMILIAS'.
    Devuelve (familias, cantidad_esperada)
    """
    descripciones: List[str] = []
    expected_count: Optional[int] = None
    for row in tablas:
        if not isinstance(row, dict):
            continue
        # Capturar cantidad de familias, si existe
        if 'CANTIDAD DE FAMILIAS' in row:
            try:
                expected_count = int(re.search(r"(\d+)", str(row.get('CANTIDAD DE FAMILIAS', ""))).group(1))
            except Exception:
                expected_count = None
        # Capturar descripciones
        if FAMILIA_DESC_KEY in row and row.get(FAMILIA_DESC_KEY):
            descripciones.append(str(row[FAMILIA_DESC_KEY]).strip())

    familias: List[Dict] = []
    for line in descripciones:
        # Algunos PDFs pueden concatenar varias familias en una misma celda con separadores extraños.
        # Intento simple: no dividir agresivamente para no romper descripciones con '-'.
        parsed = _parse_family_line(line)
        if parsed:
            familias.extend(parsed)  # Use extend to flatten the list of dictionaries
    return familias, expected_count


def validate_familias(familias: List[Dict], expected_count: Optional[int] = None) -> Dict:
    """Valida las familias detectadas.
    - Verifica códigos duplicados
    - Verifica que cada item tenga code
    - Opcionalmente compara con expected_count
    Retorna {'ok': bool, 'warnings': [...], 'errors': [...], 'unique_familias': [...]}.
    """
    warnings: List[str] = []
    errors: List[str] = []

    # Filtro: debe haber code
    valid = [f for f in familias if f.get('code')]
    missing_code = [f for f in familias if not f.get('code')]
    if missing_code:
        errors.append(f"{len(missing_code)} filas sin código de familia detectable")

    # Duplicados
    seen = set()
    dups = []
    unique_familias: List[Dict] = []
    for f in valid:
        code = f['code']
        if code in seen:
            dups.append(code)
        else:
            seen.add(code)
            unique_familias.append(f)
    if dups:
        warnings.append(f"Códigos de familia duplicados detectados: {sorted(set(dups))}")

    # Conteo esperado
    if expected_count is not None and expected_count != len(unique_familias):
        warnings.append(f"Cantidad de familias detectadas ({len(unique_familias)}) difiere del valor indicado ({expected_count})")

    ok = len(errors) == 0
    return {
        'ok': ok,
        'warnings': warnings,
        'errors': errors,
        'unique_familias': unique_familias,
        'expected_count': expected_count,
        'found_count': len(unique_familias),
    }

def get_cotizacion_data_from_drive(file_id: str) -> List[Dict]:
    """Dado un ID de Drive, descarga el PDF y extrae las tablas de cotización."""
    pdf_bytes = download_pdf_from_drive(file_id)
    return extract_tables_from_pdf(pdf_bytes)

def get_next_cotizacion_number(year: Union[str, int], cots: List[Cot]) -> str:
    """
    Busca el próximo número de cotización para un año dado.
    Args:
        year: Año de la cotización (str o int)
        cots: Lista de objetos Cot existentes
    Returns:
        El próximo número de cotización como string con ceros a la izquierda (4 dígitos)
    """
    year_str = str(year)
    if len(year_str) == 4:
        year_str = year_str[-2:]  # Extract last 2 digits (e.g., 25 from 2025)
    nums = [int(cot.num) for cot in cots if str(cot.year) == year_str and cot.num.isdigit()]
    next_num = max(nums) + 1 if nums else 1
    return completar_con_ceros(next_num, 4)

def extract_cotizacion_metadata_from_pdf(pdf_bytes: bytes) -> dict:
    """
    Extrae metadatos clave de la cotización desde el texto del PDF.
    Devuelve un diccionario con: fecha, numero, empresa, dirigido_a, consultora, mail, template, revision.
    """
    result = {
        'fecha': None,
        'numero_cotizacion': None,
        'empresa': None,
        'dirigido_a': None,
        'consultora': None,
        'mail_receptor': None,
        'template': None,
        'revision': None
    }
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        full_text = "\n".join([page.extract_text() or "" for page in pdf.pages])
        # Fecha (formato dd/mm/yyyy o dd-mm-yyyy)
        m = re.search(r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})', full_text)
        if m:
            result['fecha'] = m.group(1)
        # N° de Cotización (N° o Cotización N°)
        m = re.search(r'(?:Cotizaci[oó]n\s*N[°º:]?\s*|N[°º:]?\s*)?(\d{3,6}[ -/]?\d{2,4})', full_text, re.IGNORECASE)
        if m:
            result['numero_cotizacion'] = m.group(1)
        # Empresa (busca "Empresa:" o "Cliente:")
        m = re.search(r'(?:Empresa|Cliente)\s*[:\-]?\s*(.+)', full_text)
        if m:
            result['empresa'] = m.group(1).split('\n')[0].strip()
        # Dirigido a (busca "A Atte. Sr./Sra.:" o variantes)
        m = re.search(r'A\s*Atte\.?\s*Sr\.?\s*/?\s*Sra\.?\s*[:\-]?\s*(.+)', full_text, re.IGNORECASE)
        if not m:
            m = re.search(r'(?:Atte\.?Sr\.?/?Sra\.?|Dirigido a|Sr\.?/Sra\.?|Sra\.?|Sres\.?|Sr\.?|Atenci[oó]n)\s*[:\-]?\s*(.+)', full_text)
        if m:
            result['dirigido_a'] = m.group(1).split('\n')[0].strip()
        # Consultora (si existe)
        m = re.search(r'Consultora\s*[:\-]?\s*(.+)', full_text)
        if m:
            result['consultora'] = m.group(1).split('\n')[0].strip()
        # Mail receptor
        m = re.search(r'([\w\.-]+@[\w\.-]+)', full_text)
        if m:
            result['mail_receptor'] = m.group(1)
        # Footer: nombre del template y revisión (busca en la última página)
        last_page_text = pdf.pages[-1].extract_text() if pdf.pages else ""
        m = re.search(r'(IT\s*\d+[^\n]*)', last_page_text)
        if m:
            result['template'] = m.group(1).strip()
        # Revisión: busca "Rev. A – Fecha: 26/02/25" o variantes
        m = re.search(r'Rev\.?\s*([A-Za-z0-9.]+)\s*[–-]\s*Fecha\s*:?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})', last_page_text)
        if m:
            result['revision'] = m.group(1).strip()
            result['revision_fecha'] = m.group(2).strip()
        else:
            # fallback: solo "Revisión: X"
            m = re.search(r'Revisi[oó]n\s*[:\-]?\s*([A-Za-z0-9.]+)', last_page_text)
            if m:
                result['revision'] = m.group(1).strip()
    return result

def extract_condiciones_from_pdf(pdf_bytes: bytes) -> str:
    """
    Extrae el texto que aparece después de la última tabla del PDF (condiciones de la cotización), cortando en 'Atentamente'.
    """
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        last_table_end_y = None
        last_table_page = None
        # Buscar la última tabla y su posición
        for page_num, page in enumerate(pdf.pages):
            tables = page.find_tables()
            if tables:
                last_table = tables[-1]
                last_table_end_y = last_table.bbox[3]  # y2 de la tabla
                last_table_page = page
        if last_table_page and last_table_end_y:
            # Extraer todo el texto de la página después de la última tabla
            words = last_table_page.extract_words()
            condiciones_words = [w for w in words if float(w['top']) > last_table_end_y]
            condiciones = ' '.join(w['text'] for w in condiciones_words)
            # Cortar en 'Atentamente' (case-insensitive, con o sin dos puntos)
            idx = re.search(r'Atentamente\s*:?', condiciones, re.IGNORECASE)
            if idx:
                condiciones = condiciones[:idx.start()].strip()
            return condiciones.strip()
        # Fallback: si no se encuentra tabla, devolver el texto de la última página
        if pdf.pages:
            condiciones = pdf.pages[-1].extract_text() or ""
            idx = re.search(r'Atentamente\s*:?', condiciones, re.IGNORECASE)
            if idx:
                condiciones = condiciones[:idx.start()].strip()
            return condiciones
        return ""

# Modificar get_cotizacion_full_data_from_drive para incluir condiciones:
def get_cotizacion_full_data_from_drive(file_id: str) -> dict:
    pdf_bytes = download_pdf_from_drive(file_id)
    tablas = extract_tables_from_pdf(pdf_bytes)
    metadata = extract_cotizacion_metadata_from_pdf(pdf_bytes)
    condiciones = extract_condiciones_from_pdf(pdf_bytes)

    # Familias: parseo y validación
    familias, expected = extract_familias_from_tablas(tablas)
    familias_check = validate_familias(familias, expected)

    return {
        'tablas': tablas,
        'metadata': metadata,
        'condiciones': condiciones,
        'familias': familias_check.get('unique_familias', familias),
        'familias_validacion': familias_check,
    }

# Ejemplo de uso:
# data = get_cotizacion_full_data_from_drive('ID_DE_DRIVE')
# print(data['metadata'])
# print(data['tablas'])
