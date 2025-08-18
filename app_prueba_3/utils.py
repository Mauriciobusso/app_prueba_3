import reflex as rx

class User(rx.Base):
    """Values for Users"""
    email: str = ""
    data: dict = {}
    roles_names: list = []
    current_rol_name: str = ""
    current_rol: str = ""
    areas_names: list = []
    current_area: str = ""
    current_area_name: str = ""

class Model(rx.Base):
    """Values for Models"""
    id: str = ""
    brands: list = []
    model: str = ""
    specs: dict = {}

class Client(rx.Base):
    """Values for Clients"""
    id: str = ""
    razonsocial: str = ""
    cuit: str = ""
    direccion: str = ""
    phone: str = ""
    email_cotizacion: str = ""
    active_fams: int = 0
    condiciones: str = ""
    consultora: str = ""

class Fam(rx.Base):
    """Values for Fams"""
    id: str = ""
    area: str = ""
    family: str = ""
    product: str = ""
    origen: str = ""
    expirationdate: str = ""
    vigencia: str = ""
    client: str = ""
    client_id: str = ""
    system: str = ""        #TIPO / MARCA / LOTE
    status: str = ""
    models: list[Model] = []
    rubro: str = ""
    subrubro: str = ""

class Cot(rx.Base):
    """Values for Cotizaciones"""
    id: str = ""
    num: str = ""
    year: str = ""
    client: str = ""
    client_id: str = ""
    area: str = ""
    familys_ids: list[str] = []
    familys: list[Fam] = []
    familys_codigos: list[str] = []
    familys_productos: list[str] = []
    issuedate: str = ""
    issuedate_timestamp: float = 0.0  # Timestamp para ordenamiento eficiente
    status: str = ""    
    aprueba: str = ""
    drive_file_id: str = ""
    drive_file_id_name: str = ""
    drive_aprobacion_id: str = ""
    drive_aceptacion_id: str = ""
    enviada_fecha: str = ""
    facturada_fecha: str = ""
    facturar: str = ""
    nombre: str = ""
    consultora: str = ""
    email: str = ""
    ot: str = ""
    rev: str = ""
    resolucion: str = ""
    cuenta: str = ""
    # Datos extraídos del PDF (persistidos en la COT para revisión/uso posterior)
    pdf_metadata: dict = {}
    pdf_tablas: list = []
    pdf_condiciones: str = ""
    pdf_familias: list[dict] = []
    pdf_familias_validacion: dict = {}

class Certs(rx.Base):
    """Values for Certs"""
    id: str = ""
    num: str = ""
    year: str = ""
    rev: str = ""
    assigmentdate: str = ""
    issuedate: str = ""
    vencimiento: str = ""
    area: str = ""
    client: str = ""
    client_id: str = ""
    status: str = ""    
    family_id: str = ""
    family: Fam = Fam()
    ensayos: list = []
    drive_file_id: str = ""
    drive_file_id_signed: str = ""

def completar_con_ceros(cadena, longitud):
    return str(cadena).zfill(longitud)


def buscar_fams(fams, query: str):
    query = query.lower()
    return [
        f for f in fams
        if any(query in getattr(f, campo, "").lower() for campo in ["client", "product", "family", "origen"])
    ]

def buscar_cots(cots, query: str):
    query_lower = query.lower()
    return [
        cotizacion for cotizacion in cots
        if any(query_lower in str(getattr(cotizacion, field, '')).lower() 
               for field in ["client", "num", "year", "status", "id", "ot", "nombre", "email"])
    ]

def format_date(date_str: str) -> str:
    """
    Convierte fecha de formato YYYY-mm-dd a dd/mm/YYYY
    """
    if not date_str:
        return ""
    
    # Si ya está en formato dd/mm/YYYY, devolverla tal como está
    if "/" in date_str and len(date_str.split("/")[2]) == 4:
        return date_str
    
    # Convertir de YYYY-mm-dd (formato ISO) a dd/mm/YYYY
    if "-" in date_str and len(date_str) == 10:
        try:
            year, month, day = date_str.split("-")
            return f"{day}/{month}/{year}"
        except ValueError:
            return date_str
    
    return date_str

def format_date_reflex(date_str):
    """Formato de fecha compatible con Reflex usando rx.cond"""
    return rx.cond(
        date_str.contains("-"),
        # Si contiene guiones (formato YYYY-mm-dd), reformatear a dd/mm/YYYY
        rx.cond(
            date_str.length() == 10,
            date_str.split("-")[2] + "/" + date_str.split("-")[1] + "/" + date_str.split("-")[0],
            date_str
        ),
        # Si no contiene guiones, devolver tal como está
        date_str
    )