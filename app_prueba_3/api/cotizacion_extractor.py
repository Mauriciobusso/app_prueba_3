import io
import re
from typing import List, Union, Dict
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
    descripcion_extraida = False
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for page in pdf.pages:
            for table in page.extract_tables():
                # Detectar si es la tabla de productos
                is_productos = False
                for row in table[:2]:
                    if any((h or '').strip().upper() == descripcion_col for h in row):
                        is_productos = True
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
            m = re.search(r'(?:Dirigido a|Sr\.?/Sra\.?|Sra\.?|Sr\.?|Atenci[oó]n)\s*[:\-]?\s*(.+)', full_text)
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
    return {'tablas': tablas, 'metadata': metadata, 'condiciones': condiciones}

# Ejemplo de uso:
# data = get_cotizacion_full_data_from_drive('ID_DE_DRIVE')
# print(data['metadata'])
# print(data['tablas'])
