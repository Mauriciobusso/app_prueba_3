import io
from typing import List, Dict
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from google.oauth2 import service_account
import pdfplumber

# Configuración: ruta a tu service account
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
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for page in pdf.pages:
            for table in page.extract_tables():
                headers = table[0]
                for row in table[1:]:
                    tables.append(dict(zip(headers, row)))
    return tables

def get_cotizacion_data_from_drive(file_id: str) -> List[Dict]:
    """Dado un ID de Drive, descarga el PDF y extrae las tablas de cotización."""
    pdf_bytes = download_pdf_from_drive(file_id)
    return extract_tables_from_pdf(pdf_bytes)

# Ejemplo de uso:
# tablas = get_cotizacion_data_from_drive('ID_DE_DRIVE')
# for fila in tablas:
#     print(fila)
