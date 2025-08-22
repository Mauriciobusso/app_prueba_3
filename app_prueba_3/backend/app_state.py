import reflex as rx
from google.oauth2.id_token import verify_oauth2_token
from google.auth.transport import requests
import os, json
from dotenv import load_dotenv
from ..api.firestore_api import firestore_api
from ..api.algolia_api import algolia_api
from ..api import cotizacion_extractor
from ..api.algolia_utils import algolia_to_cot, algolia_to_certs, algolia_to_fam
from ..utils import User, Fam, Certs, Cot, Client, buscar_fams, buscar_cots
from datetime import datetime
import time
import asyncio
import traceback

# Cargar variables de entorno
load_dotenv()
CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")

# Cola para almacenar los cambios detectados en Firestore
firestore_queue = asyncio.Queue()


class AppState(rx.State):
    def add_empresa_temporal(self):
        # Aquí puedes agregar la lógica para crear una empresa temporal o simplemente dejarlo como placeholder
        print("Empresa temporal agregada (placeholder)")
    def set_new_cot_empresa(self, value: str):
        self.new_cot_razonsocial = value
    @rx.event
    async def update_activity(self):
        """Actualiza el timestamp de última actividad para mantener la sesión activa."""
        import time
        if self.session_internal:
            self.set_last_activity(time.time())
    # Datos extraídos del PDF de la cotización seleccionada
    cotizacion_detalle_pdf_metadata: str = ""
    cotizacion_detalle_pdf_tablas: str = ""
    cotizacion_detalle_pdf_condiciones: str = ""
    cotizacion_detalle_pdf_error: str = ""
    cotizacion_detalle_pdf_familias: str = ""
    cotizacion_detalle_pdf_familias_validacion: str = ""
    @rx.event
    async def extraer_pdf_cotizacion_detalle(self):
        """Extrae los datos del PDF de la cotización seleccionada y los guarda en el estado como string."""
        from app_prueba_3.api.cotizacion_extractor import get_cotizacion_full_data_from_drive
        import json, re
        
        # Marcar como procesando - NO mostrar datos hasta completar
        self.cotizacion_detalle_processing = True
        
        # Limpiar datos previos
        self.cotizacion_detalle_pdf_metadata = ""
        self.cotizacion_detalle_pdf_tablas = ""
        self.cotizacion_detalle_pdf_condiciones = ""
        self.cotizacion_detalle_pdf_error = ""
        self.cotizacion_detalle_pdf_familias = ""
        self.cotizacion_detalle_pdf_familias_validacion = ""
        
        # 1. VERIFICAR SI YA EXISTEN DATOS PROCESADOS EN FIRESTORE (solo si no es reprocesamiento forzado)
        if self.cotizacion_detalle.id and not self.force_pdf_reprocess:
            try:
                print(f"🔍 Verificando si existen datos procesados para cotización {self.cotizacion_detalle.id}...")
                existing_data = firestore_api.get_cotizacion_detalle(self.cotizacion_detalle.id)
                
                if existing_data and isinstance(existing_data, dict):
                    print(f"✅ Datos ya procesados encontrados en Firestore. Cargando desde base de datos...")
                    
                    # Cargar datos desde Firestore en lugar de procesar PDF
                    await self._load_from_firestore_detalle(existing_data)
                    
                    # Marcar procesamiento como completo
                    self.cotizacion_detalle_processing = False
                    print("✅ Datos cargados desde Firestore sin procesar PDF")
                    return
                else:
                    print(f"🔄 No existen datos procesados. Procediendo a procesar PDF...")
                    
            except Exception as e_check:
                print(f"⚠️  Error verificando datos existentes: {e_check}")
                print(f"🔄 Continuando con procesamiento de PDF...")
        elif self.force_pdf_reprocess:
            print("🔥 REPROCESAMIENTO FORZADO: Saltando verificación de cache y reprocesando PDF...")
            # Resetear el flag después de usarlo
            self.force_pdf_reprocess = False
        
        file_id = self.cotizacion_detalle.drive_file_id
        if file_id:
            try:
                data = get_cotizacion_full_data_from_drive(file_id)
                self.cotizacion_detalle_pdf_metadata = json.dumps(data.get("metadata", {}), ensure_ascii=False, indent=2)
                self.cotizacion_detalle_pdf_tablas = json.dumps(data.get("tablas", []), ensure_ascii=False, indent=2)
                self.cotizacion_detalle_pdf_condiciones = str(data.get("condiciones", ""))
                self.cotizacion_detalle_pdf_familias = json.dumps(data.get("familias", []), ensure_ascii=False, indent=2)
                self.cotizacion_detalle_pdf_familias_validacion = json.dumps(data.get("familias_validacion", {}), ensure_ascii=False, indent=2)
                
                # Mapear metadata y familias al objeto Cot en memoria
                meta = data.get("metadata", {}) or {}
                numero_cot = str(meta.get("numero_cotizacion", ""))
                digits = re.findall(r"\d+", numero_cot)
                if digits:
                    joined = "".join(digits)
                    self.cotizacion_detalle.num = (joined[:4] if len(joined) >= 4 else joined).zfill(4)
                    self.cotizacion_detalle.year = joined[-2:] if len(joined) >= 2 else self.cotizacion_detalle.year
                
                # client y otros campos directos
                client_name = (meta.get("empresa") or "").strip()
                if client_name:
                    self.cotizacion_detalle.client = client_name
                if meta.get("fecha"):
                    self.cotizacion_detalle.issuedate = meta.get("fecha")
                if meta.get("dirigido_a"):
                    self.cotizacion_detalle.nombre = meta.get("dirigido_a").strip()
                if meta.get("consultora"):
                    self.cotizacion_detalle.consultora = meta.get("consultora").strip()
                if meta.get("mail_receptor"):
                    self.cotizacion_detalle.email = meta.get("mail_receptor").strip()
                if meta.get("revision"):
                    self.cotizacion_detalle.rev = str(meta.get("revision")).strip()

                # 1. BUSCAR CLIENTE CON BÚSQUEDA INTELIGENTE
                try:
                    client_found = None
                    
                    if client_name:
                        print(f"🔍 DEBUG: Iniciando búsqueda inteligente de cliente: '{client_name}'")
                        client_found = await self._search_client_intelligent(client_name)
                    
                    # Si se encuentra cliente, usar sus datos
                    if client_found:
                        self.cotizacion_detalle_client = client_found
                        self.cotizacion_detalle.client_id = client_found.id
                        # Actualizar datos de cotización con datos del cliente
                        self.cotizacion_detalle.client = client_found.razonsocial
                        if client_found.consultora and not self.cotizacion_detalle.consultora:
                            self.cotizacion_detalle.consultora = client_found.consultora
                        print(f"✅ DEBUG: Cliente configurado: {client_found.razonsocial} (ID: {client_found.id})")
                    else:
                        # Si no se encuentra, crear cliente temporal con datos de la cotización
                        print(f"⚠️  DEBUG: Cliente no encontrado, creando temporal para '{client_name}'")
                        self.cotizacion_detalle_client = Client(
                            id="",  # Sin ID porque no está en Firestore
                            razonsocial=client_name,
                            consultora=meta.get("consultora", ""),
                            email_cotizacion=meta.get("mail_receptor", ""),
                        )
                        print(f"✅ DEBUG: Cliente temporal creado: {client_name}")
                
                except Exception as e_client:
                    print(f"⚠️  Error al buscar cliente: {e_client}")
                    import traceback
                    traceback.print_exc()

                # 2. BUSCAR Y MAPEAR FAMILIAS
                try:
                    familias_pdf = data.get("familias", []) or []
                    print(f"🔍 DEBUG: Familias extraídas del PDF: {len(familias_pdf)} encontradas")
                    print(f"🔍 DEBUG: Primeras 3 familias: {familias_pdf[:3] if familias_pdf else 'Ninguna'}")
                    
                    # Guardar códigos/productos extraídos
                    self.cotizacion_detalle.familys_codigos = [
                        (itm.get("code") or "").strip().upper() for itm in familias_pdf
                    ]
                    self.cotizacion_detalle.familys_productos = [
                        (itm.get("description") or "").strip() for itm in familias_pdf
                    ]
                    
                    print(f"🔍 DEBUG: Códigos extraídos: {self.cotizacion_detalle.familys_codigos}")
                    print(f"🔍 DEBUG: Productos extraídos: {self.cotizacion_detalle.familys_productos}")

                    # Si se encontró cliente, obtener sus familias para mapear
                    fams_cliente = []
                    if client_found:
                        try:
                            area_filter = self.user_data.current_area if self.user_data.current_area else None
                            fams_cliente = firestore_api.get_fams(
                                area=area_filter,
                                order_by="razonsocial",
                                limit=500,
                                filter=[("client_id", "==", client_found.id)]
                            )
                            print(f"🔍 DEBUG: Familias del cliente encontradas: {len(fams_cliente)}")
                        except Exception as e_fam:
                            print(f"⚠️  Error al obtener familias del cliente: {e_fam}")
                    
                    # Mapear familias del PDF con familias del cliente
                    matched_fams, matched_ids = [], []
                    
                    if fams_cliente:
                        # Indexar familias por código y producto
                        fams_by_code = {}
                        fams_by_product = []
                        
                        for fam in fams_cliente:
                            code_norm = (fam.family or "").strip().upper()
                            if code_norm:
                                fams_by_code[code_norm] = fam
                            if fam.product:
                                fams_by_product.append(fam)
                        
                        print(f"🔍 DEBUG: Familias indexadas por código: {list(fams_by_code.keys())}")
                        print(f"🔍 DEBUG: Familias con productos: {len(fams_by_product)}")

                        # Procesar cada familia del PDF
                        for item in familias_pdf:
                            code = (item.get("code") or "").strip().upper()
                            desc = (item.get("description") or "").strip().lower()
                            fam_match = None
                            
                            print(f"🔍 DEBUG: Procesando item - Código: '{code}', Descripción: '{desc}'")
                            
                            # Buscar por código exacto
                            if code and code in fams_by_code:
                                fam_match = fams_by_code[code]
                                print(f"✅ DEBUG: Match por código: {code}")
                            else:
                                # Buscar por descripción/producto
                                for fam in fams_by_product:
                                    prod = (fam.product or "").strip().lower()
                                    if not prod:
                                        continue
                                    if desc and (desc in prod or prod in desc):
                                        fam_match = fam
                                        print(f"✅ DEBUG: Match por descripción: '{desc}' <-> '{prod}'")
                                        break
                            
                            if fam_match and fam_match.id not in matched_ids:
                                matched_fams.append(fam_match)
                                matched_ids.append(fam_match.id)
                                print(f"✅ DEBUG: Familia agregada: {fam_match.family} - {fam_match.product}")

                    # Si no se encontraron familias mapeadas, crear familias temporales del PDF
                    if not matched_fams and familias_pdf:
                        print(f"⚠️  DEBUG: No hay familias del cliente, creando familias temporales del PDF")
                        area_filter = self.user_data.current_area if self.user_data.current_area else ""
                        for item in familias_pdf:
                            temp_fam = Fam(
                                id="",  # Sin ID porque no está en Firestore
                                family=(item.get("code") or "").strip(),
                                product=(item.get("description") or "").strip(),
                                client=client_name,
                                client_id=client_found.id if client_found else "",
                                area=area_filter or "",
                                status="TEMPORAL"  # Marcar como temporal
                            )
                            matched_fams.append(temp_fam)
                            print(f"✅ DEBUG: Familia temporal creada: {temp_fam.family} - {temp_fam.product}")

                    self.cotizacion_detalle.familys = matched_fams
                    self.cotizacion_detalle.familys_ids = matched_ids
                    print(f"🔍 DEBUG: RESULTADO FINAL - Familias mapeadas: {len(matched_fams)}")
                    
                except Exception as e_map:
                    print(f"⚠️  No se pudo mapear familias: {e_map}")
                    import traceback
                    print(f"🔍 DEBUG: Traceback completo:")
                    traceback.print_exc()
                    
                # 4. GUARDAR DATOS PROCESADOS EN FIRESTORE
                try:
                    await self._save_cotizacion_detalle_to_firestore(data, client_found)
                except Exception as e_save:
                    print(f"⚠️  Error al guardar datos en Firestore: {e_save}")
                    
            except Exception as e:
                self.cotizacion_detalle_pdf_error = str(e)
            finally:
                # Marcar procesamiento como completo - AHORA mostrar datos
                self.cotizacion_detalle_processing = False
                self.is_loading_cotizacion_detalle = False  # También finalizar estado de carga
                print("✅ Procesamiento de cotización detalle completado")

    @rx.event
    async def extraer_pdf_forzado(self):
        """Fuerza una nueva extracción del PDF ignorando el caché."""
        print("🔄 Forzando extracción de PDF ignorando caché...")
        
        # Activar flag para saltarse verificación de cache
        self.force_pdf_reprocess = True
        
        # Marcar que no está cargado desde cache para forzar procesamiento completo
        if hasattr(self.cotizacion_detalle, 'loaded_from_cache'):
            self.cotizacion_detalle.loaded_from_cache = False
        
        # Llamar al método principal de extracción
        yield AppState.extraer_pdf_cotizacion_detalle()

    @rx.event
    async def reprocesar_cotizacion_detalle(self):
        """Alias para reprocesar la cotización detalle (usado por el botón en UI)."""
        yield AppState.extraer_pdf_forzado()

    @rx.event
    def limpiar_cotizacion_detalle_cache(self):
        """Limpia el caché de la cotización detalle cuando se sale de la página."""
        print("🧹 Limpiando cache de cotización detalle...")
        
        # Limpiar campos de estado
        self.cotizacion_detalle_pdf_metadata = ""
        self.cotizacion_detalle_pdf_tablas = ""
        self.cotizacion_detalle_pdf_condiciones = ""
        self.cotizacion_detalle_pdf_error = ""
        self.cotizacion_detalle_pdf_familias = ""
        self.cotizacion_detalle_pdf_familias_validacion = ""
        
        # Resetear cotización detalle
        self.cotizacion_detalle = Cot()
        self.cotizacion_detalle_client = Client()
        self.cotizacion_detalle_current_id = ""
        
        # Desactivar loading state
        self.is_loading_cotizacion_detalle = False
        
        print("✅ Cache de cotización detalle limpiado")

    @rx.event
    def on_mount_cotizacion_detalle(self):
        """Método llamado cuando se monta la página de cotización detalle."""
        print("📋 Montando página de cotización detalle")
        
        # Activar estado de loading
        self.is_loading_cotizacion_detalle = True
        
        print("✅ Página de cotización detalle lista")
        
        # Desactivar loading state
        self.is_loading_cotizacion_detalle = False

    id_token: str = rx.LocalStorage()
    user_email: str = rx.LocalStorage()     # Nuevo: persistir email del usuario
    session_valid: bool = False             # Nuevo: estado de sesión (no persistente por limitación de Reflex)
    _session_internal_raw: str = rx.LocalStorage("false")  # Almacenar como string en LocalStorage
    _last_activity_raw: str = rx.LocalStorage("0.0")       # Almacenar como string en LocalStorage
    _last_auth_log: float = 0.0            # Para throttling de logs de autenticación
    _last_no_auth_log: float = 0.0         # Para throttling de logs sin autenticación
    user_data: User = User()
    roles: list = []
    areas: list = []
    date: str = ""
    current_page: str = ""                 # Nuevo: para rastrear la página actual

    # Estados de carga para mostrar spinners
    is_loading_user_initialization: bool = False
    is_loading_areas: bool = False
    is_loading_roles: bool = False
    is_loading_data: bool = False
    is_loading_cotizacion_detalle: bool = False
    cotizacion_detalle_processing: bool = False  # Nuevo: indica si está procesando datos del PDF
    
    # Flags para evitar re-inicializaciones innecesarias
    user_initialized: bool = False
    areas_loaded: bool = False
    roles_loaded: bool = False

    certs: list[Certs] = []         # Lista para almacenar los certificados
    certs_show: list[Certs] = []    # Lista para mostrar los certificados

    fams: list[Fam] = []            # Lista para almacenar las familias
    fams_show: list[Fam] = []       # Lista para mostrar las familias

    cots: list[Cot] = []            # Lista para almacenar las cotizaciones
    cots_show: list[Cot] = []       # Lista para mostrar las cotizaciones
    
    # Cotización de detalle para la vista individual
    cotizacion_detalle: Cot = Cot()
    cotizacion_detalle_client: Client = Client()  # Cliente encontrado o creado desde la cotización
    cotizacion_detalle_current_id: str = ""  # ID de la cotización actualmente cargada
    
    # Estado de procesamiento y progreso
    upload_progress: int = 0
    error_message: str = ""
    success_message: str = ""
    force_pdf_reprocess: bool = False  # Flag para forzar reprocesamiento ignorando cache

    # Datos extraídos del PDF de la cotización seleccionada
    cotizacion_detalle_pdf_metadata: str = ""
    cotizacion_detalle_pdf_tablas: str = ""
    cotizacion_detalle_pdf_condiciones: str = ""
    cotizacion_detalle_pdf_error: str = ""
    cotizacion_detalle_pdf_familias: str = ""
    cotizacion_detalle_pdf_familias_validacion: str = ""
    
    # Datos procesados adicionales para la cotización
    cotizacion_detalle_trabajos: list = []
    cotizacion_detalle_productos: list = []

    # Campo de texto de búsqueda temporal (no ejecuta búsqueda automáticamente)
    search_text: str = ""
    
    # --- Campos temporales para crear nueva cotización (UI form) ---
    new_cot_num: str = ""
    new_cot_year: str = ""

    def set_new_cot_num(self, value: str):
        self.new_cot_num = value

    def set_new_cot_year(self, value: str):
        self.new_cot_year = value
    
    def set_new_cot_fecha(self, value: str):
        self.new_cot_issuedate = value

    def set_new_cot_nombre(self, value: str):
        self.new_cot_nombre = value

    def set_new_cot_consultora(self, value: str):
        self.new_cot_consultora = value

    def set_new_cot_facturar(self, value: str):
        self.new_cot_facturar = value

    def set_new_cot_mail(self, value: str):
        self.new_cot_mail = value

    new_cot_issuedate: str = ""
    new_cot_razonsocial: str = ""
    new_cot_nombre: str = ""
    new_cot_consultora: str = "BV"
    new_cot_facturar: str = ""
    new_cot_mail: str = ""
    new_cot_resolucion: str = ""
    new_cot_pdf_condiciones: str = ""
    new_cot_rev: str = ""
    new_cot_mail: str = ""
    new_cot_familias: list[Fam] = []
    new_cot_trabajos: list[dict] = []
    new_cot_status: str = ""  # '', 'success', 'error'
    new_cot_error_message: str = ""
    
    # Lista de trabajos disponibles para seleccionar
    trabajos_disponibles: list = []
    is_loading_trabajos: bool = False
    # Estado de Carga de Datos Iniciales Nueva Cotización
    is_loading_new_cot: bool = False

    # New cotization form methods
    def add_new_cot_family(self):
        """Add new family to the new cotization form."""
        self.new_cot_familias.append(Fam())

    def set_new_cot_family(self, index: int, value: str):
        """Set family value at specific index."""
        if 0 <= index < len(self.new_cot_familias):
            self.new_cot_familias[index].family = value

    def set_new_cot_product(self, index: int, value: str):
        """Set product value at specific index."""
        if 0 <= index < len(self.new_cot_familias):
            self.new_cot_familias[index].product = value

    def remove_new_cot_family(self, family_to_remove):
        """Remove family from the list."""
        # Si es un diccionario (evento), ignoramos
        if isinstance(family_to_remove, dict):
            print("Intento de eliminar familia inválido (dict)")
            return
        
        # Si es un objeto Fam, lo buscamos y removemos
        if isinstance(family_to_remove, Fam):
            try:
                self.new_cot_familias.remove(family_to_remove)
                print(f"✅ Familia eliminada: {family_to_remove}")
            except ValueError:
                pass  # El elemento no está en la lista
        # Si es un índice (int), lo usamos directamente
        elif isinstance(family_to_remove, int) and 0 <= family_to_remove < len(self.new_cot_familias):
            self.new_cot_familias.pop(family_to_remove)

    def add_new_cot_trabajo(self):
        """Add new trabajo to the new cotization form."""
        self.new_cot_trabajos.append({
            'titulo': '',
            'descripcion': '',
            'cantidad': '1',
            'precio': ''
        })

    def set_new_cot_trabajo_field(self, index: int, field: str, value: str):
        """Set trabajo field value at specific index."""
        if 0 <= index < len(self.new_cot_trabajos):
            self.new_cot_trabajos[index][field] = value

    def set_new_cot_trabajo_from_template(self, index: int, trabajo_id: str):
        """Set trabajo from template/available trabajo."""
        if 0 <= index < len(self.new_cot_trabajos):
            # Find the trabajo by id
            trabajo_found = None
            for trabajo in self.trabajos_disponibles:
                if trabajo.get('id') == trabajo_id:
                    trabajo_found = trabajo
                    break
            
            if trabajo_found:
                self.new_cot_trabajos[index]['titulo'] = trabajo_found.get('titulo', '')
                self.new_cot_trabajos[index]['descripcion'] = trabajo_found.get('descripcion', '')
                # Keep existing cantidad and precio
                if not self.new_cot_trabajos[index].get('cantidad'):
                    self.new_cot_trabajos[index]['cantidad'] = '1'

    def remove_new_cot_trabajo(self, trabajo_to_remove):
        """Remove trabajo from the list."""
        # Si es un diccionario (evento), ignoramos
        if isinstance(trabajo_to_remove, dict) and 'type' in trabajo_to_remove:
            return
        
        # Si es un diccionario de trabajo, lo buscamos y removemos
        if isinstance(trabajo_to_remove, dict):
            try:
                self.new_cot_trabajos.remove(trabajo_to_remove)
            except ValueError:
                pass  # El elemento no está en la lista
        # Si es un índice (int), lo usamos directamente
        elif isinstance(trabajo_to_remove, int) and 0 <= trabajo_to_remove < len(self.new_cot_trabajos):
            self.new_cot_trabajos.pop(trabajo_to_remove)

    @rx.event(background=True)
    async def load_new_cot(self):
        """Load available trabajos from Firestore."""
        async with self:
            self.is_loading_new_cot = True
            self.is_loading_trabajos = True
            
        try:
            async with self:
                await self.reset_new_cot_form()
                self.is_loading_trabajos = False
                
        except Exception as e:
            print(f"❌ Error al cargar trabajos disponibles: {e}")
            async with self:
                self.is_loading_trabajos = False

    def submit_new_cot(self):
        """Submit new cotization form."""
        # Reset status
        self.new_cot_status = ""
        self.new_cot_error_message = ""
        
        # Basic validation
        if not self.new_cot_razonsocial.strip():
            self.new_cot_status = "error"
            self.new_cot_error_message = "La razón social es obligatoria"
            return
            
        if not self.new_cot_nombre.strip():
            self.new_cot_status = "error"
            self.new_cot_error_message = "El nombre de contacto es obligatorio"
            return
        
        try:
            # Here would go the actual creation logic
            # For now, just show success
            self.new_cot_status = "success"
            
            # Reset form after successful submission
            yield AppState.reset_new_cot_form
            
        except Exception as e:
            self.new_cot_status = "error"
            self.new_cot_error_message = f"Error al crear cotización: {str(e)}"

    async def reset_new_cot_form(self):
        """Reset the new cotization form."""
        # Get proximo numero de cotizacion (función sincrónica)
        try:
            next_num = cotizacion_extractor.get_next_cotizacion_number(datetime.now().year, self.cots)
        except Exception:
            # Fallback en caso de error
            next_num = "0001"
        year_str = str(datetime.now().year)[-2:]


        # Get trabajos from current user area (función sincrónica)
        try:
            trabajos = firestore_api.get_trabajos()
        except Exception:
            trabajos = []

        self.new_cot_issuedate = datetime.now().strftime('%d/%m/%Y')  # Fecha de hoy con formato dd/MM/YYYY
        self.new_cot_num = next_num
        self.new_cot_year = year_str
        self.trabajos_disponibles = trabajos
        self.new_cot_razonsocial = ""
        self.new_cot_nombre = ""
        self.new_cot_consultora = ""
        self.new_cot_facturar = ""
        self.new_cot_mail = ""
        self.new_cot_familias = []
        self.new_cot_trabajos = []
        self.new_cot_status = ""
        self.new_cot_error_message = ""
    
    # Tema (modo oscuro/claro) - DISABLED FOR NOW, KEEP FOR FUTURE USE
    # dark_mode: bool = rx.LocalStorage(False)  # Persistir preferencia del tema

    # Paginación
    cots_page: int = 0
    certs_page: int = 0
    fams_page: int = 0
    total_cots: int = 0
    total_certs: int = 0
    total_fams: int = 0
    is_loading_more: bool = False
    scroll_threshold: float = 0.8  # Disparar carga cuando llegue al 80% del scroll

    @rx.var
    def cots_page_info(self) -> str:
        """Información de paginación para cotizaciones."""
        total_pages = (len(self.cots) + 29) // 30 if self.cots else 0  # 30 items per page
        current_page = self.cots_page + 1
        return f"Página {current_page} de {total_pages}"
    
    @rx.var  
    def cots_has_prev_page(self) -> bool:
        """Si hay página anterior de cotizaciones."""
        return self.cots_page > 0
    
    @rx.var
    def cots_has_next_page(self) -> bool:
        """Si hay página siguiente de cotizaciones."""
        total_pages = (len(self.cots) + 29) // 30 if self.cots else 0
        return (self.cots_page + 1) < total_pages

    @rx.var
    def cots_current_page_display(self) -> int:
        """Página actual de cotizaciones para mostrar (1-indexed)."""
        return self.cots_page + 1

    @rx.var
    def cots_total_pages(self) -> int:
        """Total de páginas de cotizaciones."""
        return (len(self.cots) + 29) // 30 if self.cots else 0

    values: dict = {
        "collection": "",
        "search_value":"", 
        "sorted_value": "",
        "client": "", 
        "order_by": [],
        "direction": "DESCENDING",
        "limit": 100,
        "filters": [],
    }

    @rx.var
    def session_internal(self) -> bool:
        """Devuelve el estado de sesión interna como booleano."""
        try:
            if self._session_internal_raw.lower() in ('true', '1', 'yes'):
                return True
            return False
        except:
            return False
    
    @rx.var  
    def last_activity(self) -> float:
        """Devuelve el timestamp de última actividad como float."""
        try:
            return float(self._last_activity_raw)
        except:
            return 0.0

    def set_session_internal(self, value: bool):
        """Establece el estado de sesión interna."""
        self._session_internal_raw = "true" if value else "false"
    
    def set_last_activity(self, value: float):
        """Establece el timestamp de última actividad."""
        self._last_activity_raw = str(value)

    @rx.event
    async def on_click_day_calendar(self, date: str):
        """Callback para el evento de clic en un día del calendario."""
        self.date = date
    
    @rx.var
    def get_date(self) -> str:
        return self.date    
    
    # Métodos de paginación para cotizaciones
    @rx.event
    def next_cots_page(self):
        """Ir a la siguiente página de cotizaciones."""
        total_pages = (len(self.cots) + 29) // 30 if self.cots else 0
        if (self.cots_page + 1) < total_pages:
            self.cots_page += 1
            start_idx = self.cots_page * 30
            end_idx = min(start_idx + 30, len(self.cots))
            self.cots_show = self.cots[start_idx:end_idx]
            print(f"📄 Página siguiente: {self.cots_page + 1}/{total_pages}")
    
    @rx.event
    def prev_cots_page(self):
        """Ir a la página anterior de cotizaciones."""
        if self.cots_page > 0:
            self.cots_page -= 1
            start_idx = self.cots_page * 30
            end_idx = min(start_idx + 30, len(self.cots))
            self.cots_show = self.cots[start_idx:end_idx]
            total_pages = (len(self.cots) + 29) // 30 if self.cots else 0
            print(f"📄 Página anterior: {self.cots_page + 1}/{total_pages}")
    
    @rx.event
    def first_cots_page(self):
        """Ir a la primera página de cotizaciones."""
        self.cots_page = 0
        if self.cots:
            self.cots_show = self.cots[:30]
            total_pages = (len(self.cots) + 29) // 30
            print(f"📄 Primera página: 1/{total_pages}")
    
    @rx.event
    def last_cots_page(self):
        """Ir a la última página de cotizaciones."""
        if self.cots:
            total_pages = (len(self.cots) + 29) // 30
            self.cots_page = max(0, total_pages - 1)
            start_idx = self.cots_page * 30
            self.cots_show = self.cots[start_idx:]
            print(f"📄 Última página: {total_pages}/{total_pages}")

    @rx.event
    async def set_current_page(self, page: str):
        """Establece la página actual para cargar los datos apropiados."""
        # Verificar si los datos específicos ya están cargados
        data_already_loaded = False
        if page == "certificaciones" and len(self.certs) > 0:
            data_already_loaded = True
        elif page == "familias" and len(self.fams) > 0:
            data_already_loaded = True
        elif page == "cotizaciones" and len(self.cots) > 0:
            data_already_loaded = True
            
        # Si ya estamos en la misma página y los datos ya están cargados, no hacer nada
        if self.current_page == page and data_already_loaded:
            print(f"📄 Ya en la página {page} con datos cargados, omitiendo recarga")
            return
            
        self.current_page = page
        print(f"📄 Página establecida: {page}")
        
        # Cargar datos según la página
        if self.is_authenticated:
            print(f"🔐 Usuario autenticado, cargando datos para: {page}")
            self.is_loading_data = True
            try:
                if page == "certificaciones":
                    yield AppState.get_certs()
                elif page == "familias":
                    yield AppState.get_fams()
                elif page == "cotizaciones":
                    yield AppState.get_cots()
            finally:
                self.is_loading_data = False
        else:
            print("❌ Usuario no autenticado, no se pueden cargar datos")
    
    @rx.event
    async def on_mount_certificados(self):
        """Inicialización específica para la página de certificados."""
        yield AppState.on_mount()
        yield AppState.set_current_page("certificaciones")

    @rx.event
    async def on_mount_familias(self):
        """Inicialización específica para la página de familias."""
        yield AppState.on_mount()
        yield AppState.set_current_page("familias")

    @rx.event
    async def on_mount_cotizaciones(self):
        """Inicialización específica para la página de cotizaciones."""
        yield AppState.on_mount()
        yield AppState.set_current_page("cotizaciones")
    
    @rx.event
    async def on_mount(self):
        """Inicialización al cargar la página protegida."""
        print("🔄 Inicializando página...")
        
        # Si el usuario ya está inicializado y autenticado, evitar re-inicialización
        if self.user_initialized and self.is_authenticated:
            print("✅ Usuario ya inicializado, omitiendo re-inicialización")
            # Solo iniciar la tarea para procesar la cola de Firestore si no está ya iniciada
            yield AppState.process_firestore_changes()
            return
        
        # Verificar si hay un email persistente (sesión anterior)
        if self.user_email and not self.id_token:
            print(f"📧 Email persistente encontrado: {self.user_email}")
            print("⚠️  Pero no hay token activo, requiere nueva autenticación")
            
        # Si hay token, verificar autenticación
        if self.id_token:
            print("🔑 Token encontrado, verificando autenticación...")
            try:
                if self.is_authenticated:
                    print("🚀 Iniciando carga rápida de datos del usuario...")
                    await self.initialize_user()
                    print("✅ Usuario inicializado, esperando carga específica de página")
                else:
                    print("❌ Token inválido o expirado")
            except Exception as e:
                print(f"❌ Error en verificación: {e}")
        else:
            print("❓ No hay token activo")
        
        # Iniciar la tarea para procesar la cola de Firestore
        yield AppState.process_firestore_changes()

    @rx.var
    def is_authenticated(self) -> bool:
        """Verifica si el usuario está autenticado con sesión interna persistente."""
        import time
        current_time = time.time()
        
        # Si hay sesión interna válida, actualizar actividad y continuar
        if self.session_internal and self.user_email:
            # Solo verificar áreas si ya están cargadas para evitar bloqueos
            if hasattr(self.user_data, 'areas_names') and self.user_data.areas_names is not None:
                if not self.user_data.areas_names:
                    return False
            
            # Actualizar timestamp de actividad cada vez que se verifica autenticación
            self.set_last_activity(current_time)
            # Solo mostrar log cada 30 segundos para reducir spam
            if current_time - self._last_auth_log > 30:
                self._last_auth_log = current_time
            return True
        
        # Si no hay sesión interna pero hay token de Google, intentar validar con Google una vez
        if self.id_token and not self.session_internal:
            try:
                token_data = json.loads(self.id_token)
                decoded_token = verify_oauth2_token(
                    token_data["credential"],
                    requests.Request(),
                    CLIENT_ID,
                )
                
                # Si el token es válido, crear sesión interna
                email = decoded_token.get("email", "")
                if email:
                    self.set_session_internal(True)
                    self.set_last_activity(current_time)
                    self.user_email = email
                    return True
                    
            except json.JSONDecodeError as e:
                pass
            except Exception as e:
                if "expired" in str(e).lower() or "invalid" in str(e).lower():
                    # Si hay una sesión interna previa y email, mantenerla
                    if self.user_email and self.session_internal:
                        self.set_last_activity(current_time)
                        return True
        
        # Si llegamos aquí, no hay autenticación válida
        if current_time - self._last_no_auth_log > 10:
            self._last_no_auth_log = current_time
        return False

    @rx.event
    async def on_success(self, id_token: dict):
        """Callback de autenticación exitosa."""
        try:
            import time
            current_time = time.time()
            
            self.id_token = json.dumps(id_token)
            
            # Extraer información del token para persistencia
            token_data = json.loads(self.id_token)
            decoded_token = verify_oauth2_token(
                token_data["credential"],
                requests.Request(),
                CLIENT_ID,
            )
            
            # Guardar email para identificación persistente y crear sesión interna
            email = decoded_token.get("email", "")
            self.user_email = email
            self.set_session_internal(True)  # Crear sesión interna persistente
            self.set_last_activity(current_time)
            
            print(f"✅ Autenticación exitosa y sesión interna creada para: {email}")
            
            # Inicializar usuario después de autenticación exitosa (skip auth check since we just authenticated)
            yield AppState.initialize_user(skip_auth_check=True)
        except Exception as e:
            print(f"❌ Error en callback de autenticación: {e}")
            # Limpiar sesión si hay error
            self.set_session_internal(False)

    @rx.event
    async def clear_session(self):
        """Limpia toda la información de sesión."""
        print("🧹 Limpiando sesión...")
        self.id_token = ""
        self.set_session_internal(False)  # Limpiar sesión interna
        self.set_last_activity(0.0)
        
        # Resetear flags de inicialización
        self.user_initialized = False
        self.areas_loaded = False
        self.roles_loaded = False
        self.is_loading_user_initialization = False
        self.is_loading_areas = False
        self.is_loading_roles = False
        self.is_loading_data = False
        
        # Limpiar datos de listas para permitir recarga
        self.certs = []
        self.certs_show = []
        self.fams = []
        self.fams_show = []
        self.cots = []
        self.cots_show = []
        
        # Resetear página actual para forzar recarga
        self.current_page = ""
        
        # Mantener el email para mostrar al usuario que se puede reconectar
        # self.user_email = ""  # No limpiar para mostrar último usuario
        self.user_data = User()

    @rx.event
    async def logout(self):
        """Cierra la sesión del usuario."""
        print("👋 Cerrando sesión...")
        firestore_api.cleanup()
        
        # Limpiar toda la información de sesión
        self.id_token = ""
        self.user_email = ""
        self.set_session_internal(False)  # Limpiar sesión interna
        self.set_last_activity(0.0)
        self.roles = []
        self.areas = []
        self.user_data = User()
        
        print("✅ Sesión cerrada correctamente")
        return rx.redirect("/")

    @rx.var
    def display_rol(self) -> str:
        """Variable reactiva que muestra el rol actual del usuario."""
        return f"{self.user_data.current_rol_name}"

    @rx.event(background=True)
    async def process_firestore_changes(self):
        """Procesa los cambios en Firestore desde la cola."""
        while True:
            # Obtener datos de la cola
            new_data = await firestore_queue.get()

            # Actualizar el estado dentro del contexto Reflex
            async with self:
                self.user_data.data = new_data

                self.roles = firestore_api.get_roles()
                self.user_data.roles_names = sorted([role['name'] for role in self.roles if role['id'] in new_data['roles']])
                self.user_data.current_rol = new_data.get("currentRole", "")
                self.user_data.current_rol_name = firestore_api.get_rol_name(self.user_data.current_rol)
                
                self.areas = firestore_api.get_areas()
                area_names = sorted([area['name'] for area in self.areas if area['id'] in new_data.get('areas', [])])
                # Agregar "TODAS" como primera opción
                self.user_data.areas_names = area_names
                self.user_data.current_area = new_data.get("currentArea", "")
                self.user_data.current_area_name = firestore_api.get_area_name(self.user_data.current_area) if self.user_data.current_area else "TODAS"

            # Marcar como procesado
            firestore_queue.task_done()

    async def initialize_user(self, skip_auth_check: bool = False):
        """Inicializa los datos del usuario desde Firestore."""
        if not skip_auth_check and not self.is_authenticated:
            print("No se pudo autenticar.")
            return

        # Si el usuario ya está inicializado, evitar re-inicialización
        if self.user_initialized and self.user_data.email:
            print(f"✅ Usuario ya inicializado: {self.user_data.email}, omitiendo re-inicialización")
            return

        self.is_loading_user_initialization = True
        try:
            token = json.loads(self.id_token)
            user_info = verify_oauth2_token(
                token["credential"],
                requests.Request(),
                CLIENT_ID
            )
            email = user_info["email"]
            
            # Guardar información de sesión persistente
            self.user_email = email
            self.user_data.email = email

            if email:
                print(f"🔄 Inicializando usuario: {email}")
                
                # Obtener datos iniciales del usuario - Primera carga rápida
                print("📋 Obteniendo datos del usuario...")
                user_data = firestore_api.get_user(email)
                self.user_data.data = user_data
                
                # Cargar roles solo si no están ya cargados
                if not self.roles_loaded:
                    self.is_loading_roles = True
                    print("👥 Cargando roles...")
                    self.roles = firestore_api.get_roles()
                    self.roles_loaded = True
                    print("Roles ya obtenidos." if self.roles else "✅ Roles cargados.")
                else:
                    print("Roles ya obtenidos.")
                    
                self.user_data.roles_names = sorted([role['name'] for role in self.roles if role['id'] in user_data.get('roles', [])])
                self.user_data.current_rol = user_data.get("currentRole", "")
                self.user_data.current_rol_name = firestore_api.get_rol_name(self.user_data.current_rol)
                self.is_loading_roles = False
                
                # Cargar áreas solo si no están ya cargadas
                if not self.areas_loaded:
                    self.is_loading_areas = True
                    print("🌍 Cargando áreas...")
                    self.areas = firestore_api.get_areas()
                    self.areas_loaded = True
                    print(f"✅ Áreas cargadas: {len(self.areas)} áreas disponibles" if self.areas else "⚠️ No se cargaron áreas")
                else:
                    print("Areas ya obtenidas.")
                
                # Procesar áreas inmediatamente después de obtenerlas
                user_area_ids = user_data.get('areas', [])
                if user_area_ids:
                    area_names = sorted([area['name'] for area in self.areas if area['id'] in user_area_ids])
                    self.user_data.areas_names = area_names
                    self.user_data.current_area = user_data.get("currentArea", "")
                    self.user_data.current_area_name = firestore_api.get_area_name(self.user_data.current_area) if self.user_data.current_area else "TODAS"
                    
                    print(f"✅ Áreas del usuario procesadas: {len(area_names)} áreas disponibles")
                else:
                    # Usuario sin áreas asignadas
                    self.user_data.areas_names = []
                    self.user_data.current_area = ""
                    self.user_data.current_area_name = ""
                    print("⚠️  Usuario sin áreas asignadas")
                
                self.is_loading_areas = False
                
                # Verificar que el usuario tenga áreas asignadas
                if not self.user_data.areas_names:
                    print(f"❌ Usuario {email} sin áreas asignadas")
                    await self.clear_session()
                    return
                

            # Configurar listener para cambios en Firestore
            if not firestore_api.listener:
                async def firestore_callback(data):
                    try:
                        await firestore_queue.put(data)
                        print("Cambios detectados en Firestore.")
                    except Exception as e:
                        print(f"Error al colocar datos en la cola: {e}")

                firestore_api.setup_listener(email, firestore_callback)
                print("Listener configurado.")
            else:
                print("✅ Listener ya configurado.")
            
            # Marcar usuario como inicializado
            self.user_initialized = True
            print(f"✅ Usuario inicializado correctamente: {email}")
            
        except Exception as e:
            print(f"❌ Error al inicializar usuario: {e}")
        finally:
            self.is_loading_user_initialization = False

    @rx.event
    async def update_activity(self):
        """Actualiza el timestamp de última actividad para mantener la sesión activa."""
        import time
        if self.session_internal:
            self.set_last_activity(time.time())
    
    @rx.event
    async def check_user_areas(self):
        """Verifica si el usuario tiene áreas asignadas y cierra sesión si no las tiene."""
        if self.session_internal and self.user_email:
            # Verificar que el usuario tenga áreas asignadas
            if hasattr(self.user_data, 'areas_names') and not self.user_data.areas_names:
                print(f"❌ Usuario {self.user_email} sin áreas asignadas - cerrando sesión automáticamente")
                await self.logout()
                return False
            return True
        return False

    @rx.event
    async def keepalive_ping(self):
        """Mantiene la sesión activa actualizando la actividad."""
        if self.session_internal:
            await self.update_activity()
            print(f"🔄 Keepalive ping - sesión mantenida para: {self.user_email}")
    
    @rx.event
    async def set_current_rol(self, rol_name: str):
        """Establece el rol actual del usuario."""
        try:
            email = self.user_data.data.get("email", "")
            self.user_data.current_rol_name = rol_name
            self.user_data.current_rol = self._find_rol_id_by_title(rol_name)
            firestore_api.update_current_user(email, "currentRole", self.user_data.current_rol) if self.user_data.current_rol else None
        except Exception as e:
            print(f"Error al establecer el rol: {e}")
    
    @rx.event
    async def set_current_area(self, area_name: str):
        """Establece el área actual del usuario y actualiza las tablas."""
        # Actualizar actividad del usuario
        await self.update_activity()
        
        try:
            email = self.user_data.data.get("email", "")
            self.user_data.current_area_name = area_name
            
            # Si el área es "TODAS", establecer current_area como None para no filtrar
            if area_name == "TODAS":
                self.user_data.current_area = None
                print("📍 Area establecida a TODAS - Sin filtro por área")
            else:
                area_id = self._find_area_id_by_name(area_name)
                self.user_data.current_area = area_id
                print(f"📍 Area establecida: {area_name} (ID: {area_id})")
            
            # Actualizar en Firestore (guardar string vacío si es TODAS)
            area_to_save = self.user_data.current_area if area_name != "TODAS" else ""
            firestore_api.update_current_user(email, "currentArea", area_to_save)
            
            # Limpiar datos existentes para forzar recarga con el nuevo filtro
            print("🧹 Limpiando datos para recarga...")
            self.certs = []
            self.certs_show = []
            self.fams = []
            self.fams_show = []
            self.cots = []
            self.cots_show = []
            
            # Limpiar también los valores de búsqueda para evitar conflictos
            self.values["search_value"] = ""
            
            # Recargar datos según la página actual
            try:
                current_page = self.router.url.path
                print(f"🔄 Recargando datos para página: {current_page}")
                
                if "/certificados" in current_page:
                    print("🔄 Iniciando carga de certificados...")
                    yield AppState.get_certs()
                elif "/familias" in current_page:
                    print("🔄 Iniciando carga de familias...")
                    yield AppState.get_fams()
                elif "/cotizaciones" in current_page:
                    print("🔄 Iniciando carga de cotizaciones...")
                    yield AppState.get_cots()
                else:
                    print(f"⚠️  Página no reconocida: {current_page}")
                    
            except Exception as router_error:
                print(f"❌ Error con router: {router_error}")
                # Fallback: recargar según current_page almacenado
                if self.current_page == "certificaciones":
                    yield AppState.get_certs()
                elif self.current_page == "familias":  
                    yield AppState.get_fams()
                elif self.current_page == "cotizaciones":
                    yield AppState.get_cots()
                
        except Exception as e:
            print(f"❌ Error al establecer el area: {e}")
            import traceback
            traceback.print_exc()
    
    # Función para buscar el rol_id a partir del título
    def _find_rol_id_by_title(self, title):
        if self.user_data and self.roles:
            roles = self.roles
            for rol_info in roles:
                if rol_info.get("name") == title:
                    return rol_info.get("id")
        return None  # Retorna None si no se encuentra el título

    # Función para buscar el rol_id a partir del título
    def _find_area_id_by_name(self, name):
        # Si el nombre es "TODOS", retornar None directamente
        if name == "TODOS":
            return None
            
        if self.user_data.data and self.areas:
            areas = self.areas
            for area_info in areas:
                if area_info.get("name") == name:
                    return area_info.get("id")
        return None  # Retorna None si no se encuentra el título
    
    
    @rx.event
    async def cargar_cotizacion_detalle(self):
        """Carga los detalles de una cotización específica usando el parámetro de ruta."""
        try:
            # 1. LIMPIAR CACHE ANTERIOR INMEDIATAMENTE para evitar mostrar datos erróneos
            print("🧹 Limpiando datos anteriores antes de cargar nueva cotización...")
            self._limpiar_cache_cotizacion_detalle()
            
            # 2. FORZAR ACTUALIZACIÓN DE ESTADO para limpiar UI inmediatamente
            yield  # Forzar actualización del estado antes de continuar
            
            # 3. Obtener el parámetro cot_id de la URL actual usando la nueva API
            cot_id = ""
            try:
                # Usar la nueva API de router
                url_path = self.router.url.path if hasattr(self.router.url, 'path') else str(self.router.url)
                # Extraer el ID de la URL /cotizaciones/[cot_id]
                if "/cotizaciones/" in url_path:
                    parts = url_path.split("/")
                    if len(parts) >= 3:
                        cot_id = parts[-1]  # Último segmento de la URL
                        
                # Fallback: intentar con params si está disponible
                if not cot_id and hasattr(self.router, 'page') and hasattr(self.router.page, 'params'):
                    cot_id = self.router.page.params.get("cot_id", "")
            except Exception as e:
                print(f"⚠️ Error extrayendo parámetro de URL: {e}")
                cot_id = ""
                    
            print(f"🔍 Cargando cotización detalle: {cot_id}")
            
            if not cot_id or cot_id == "undefined":
                print("❌ No se encontró parámetro cot_id válido en la URL")
                self.cotizacion_detalle = Cot()
                return
            
            # Buscar primero en la lista actual
            cotizacion_encontrada = None
            for cot in self.cots:
                if cot.id == cot_id:
                    cotizacion_encontrada = cot
                    break
            
            # Si no se encontró en la lista actual, buscar en la lista mostrada
            if not cotizacion_encontrada:
                for cot in self.cots_show:
                    if cot.id == cot_id:
                        cotizacion_encontrada = cot
                        break
            
            # Si aún no se encontró, buscar en Firestore
            if not cotizacion_encontrada:
                print(f"⚡ Cotización no encontrada en listas actuales, buscando en Firestore...")
                # Aquí podrías implementar una búsqueda específica en Firestore
                # Por ahora, usaremos una cotización vacía con el ID
                cotizacion_encontrada = Cot(id=cot_id)
            
            self.cotizacion_detalle = cotizacion_encontrada
            print(f"✅ Cotización detalle cargada: {cotizacion_encontrada.num}-{cotizacion_encontrada.year} (ID: {cot_id})")
            
            # Extraer PDF si hay archivo asociado
            await self.extraer_pdf_cotizacion_detalle()
            
            # ASEGURAR que loading esté desactivado al final (por si no se procesó PDF o falló)
            if self.is_loading_cotizacion_detalle:
                self.is_loading_cotizacion_detalle = False
                print("✅ Estado de carga finalizado")
            
        except Exception as e:
            print(f"❌ Error al cargar cotización detalle: {e}")
            self.cotizacion_detalle = Cot()
            # Asegurar que loading esté desactivado en caso de error
            self.is_loading_cotizacion_detalle = False
    
    @rx.var
    def cotizacion_detalle_fecha_formateada(self) -> str:
        """Formatea la fecha de la cotización de detalle para mostrar."""
        date_str = self.cotizacion_detalle.issuedate
        if not date_str:
            return "No especificada"
        
        # Si ya está en formato dd/mm/yyyy
        if "/" in date_str and len(date_str.split("/")) == 3:
            return date_str
        
        # Si está en formato yyyy-mm-dd, convertir
        if "-" in date_str and len(date_str) == 10:
            try:
                year, month, day = date_str.split("-")
                return f"{day}/{month}/{year}"
            except ValueError:
                return date_str
        
        return date_str
    
    @rx.var
    def cotizacion_detalle_descripcion_productos(self) -> list[dict]:
        """Extrae las descripciones de productos desde las tablas del PDF."""
        try:
            if not self.cotizacion_detalle_pdf_tablas:
                return []
            
            import json
            tablas = json.loads(self.cotizacion_detalle_pdf_tablas)
            productos = []
            
            for tabla in tablas:
                if isinstance(tabla, list) and len(tabla) > 0:
                    # Buscar tabla que contenga "DESCRIPCIÓN" en el header
                    headers = tabla[0] if tabla else []
                    if any("DESCRIPCIÓN" in str(header).upper() for header in headers):
                        # Procesar filas de productos
                        for i, fila in enumerate(tabla[1:], 1):  # Skip header
                            if isinstance(fila, list) and len(fila) > 0:
                                descripcion = str(fila[0]).strip() if fila[0] else ""
                                if descripcion and not descripcion.upper().startswith(("TOTAL", "SUBTOTAL")):
                                    productos.append({
                                        "descripcion": descripcion,
                                        "fila_completa": fila
                                    })
            
            return productos[:10]  # Limitar a 10 productos
            
        except Exception as e:
            print(f"Error al parsear productos: {e}")
            return []
    
    @rx.var 
    def cotizacion_detalle_descripcion_trabajos(self) -> list[dict]:
        """Extrae la descripción de trabajos desde las tablas del PDF."""
        try:
            if not self.cotizacion_detalle_pdf_tablas:
                return []
            
            import json
            tablas = json.loads(self.cotizacion_detalle_pdf_tablas)
            trabajos = []
            
            print(f"🔍 DEBUG: Buscando trabajos en {len(tablas)} tablas/items")
            
            for idx, tabla in enumerate(tablas):
                print(f"🔍 DEBUG: Procesando tabla {idx}: {type(tabla)}")
                
                # Caso 1: Tabla estándar (lista de listas)
                if isinstance(tabla, list) and len(tabla) > 0:
                    headers = tabla[0] if tabla else []
                    print(f"🔍 DEBUG: Headers encontrados: {headers}")
                    
                    # Buscar SOLO tabla con "DESCRIPCIÓN DE TRABAJOS" en el header
                    if any("DESCRIPCIÓN DE TRABAJOS" in str(h).upper() for h in headers):
                        print(f"✅ DEBUG: Tabla de trabajos con 'DESCRIPCIÓN DE TRABAJOS' encontrada")
                        
                        # Encontrar índices de columnas
                        desc_idx = next((i for i, h in enumerate(headers) if "DESCRIPCIÓN DE TRABAJOS" in str(h).upper()), 0)
                        # Buscar CANT o CANTIDAD
                        cant_idx = next((i for i, h in enumerate(headers) if "CANT" in str(h).upper() and "CANTIDAD" not in str(h).upper()), -1)
                        if cant_idx == -1:  # Si no encuentra CANT, buscar CANTIDAD
                            cant_idx = next((i for i, h in enumerate(headers) if "CANTIDAD" in str(h).upper()), -1)
                        precio_idx = next((i for i, h in enumerate(headers) if "PRECIO" in str(h).upper()), -1)
                        
                        print(f"🔍 DEBUG: Índices - Descripción: {desc_idx}, Cantidad: {cant_idx}, Precio: {precio_idx}")
                        
                        # Procesar filas
                        for row_idx, fila in enumerate(tabla[1:], 1):  # Skip header
                            if isinstance(fila, list):
                                print(f"🔍 DEBUG: Procesando fila {row_idx}: {fila}")
                                
                                descripcion = str(fila[desc_idx]).strip() if len(fila) > desc_idx else ""
                                cantidad = str(fila[cant_idx]).strip() if cant_idx >= 0 and len(fila) > cant_idx else ""
                                precio = str(fila[precio_idx]).strip() if precio_idx >= 0 and len(fila) > precio_idx else ""
                                
                                print(f"🔍 DEBUG: Extraído - Desc: '{descripcion}', Cant: '{cantidad}', Precio: '{precio}'")
                                
                                # Filtrar filas vacías o con texto de placeholder
                                if (descripcion and 
                                    descripcion.lower() != "sin trabajos disponibles" and 
                                    not descripcion.upper().startswith(("TOTAL", "SUBTOTAL"))):
                                    
                                    trabajos.append({
                                        "descripcion": descripcion,
                                        "cantidad": cantidad if cantidad else "N/A",
                                        "precio": precio if precio else "N/A"
                                    })
                                    print(f"✅ DEBUG: Trabajo agregado: {descripcion} | {cantidad} | {precio}")
                                elif descripcion:
                                    print(f"⚠️  DEBUG: Trabajo filtrado: '{descripcion}' (placeholder o total)")
                
                # Caso 2: Dict individual (formato de extracción de pdfplumber)
                elif isinstance(tabla, dict):
                    print(f"🔍 DEBUG: Procesando dict: {tabla.keys()}")
                    
                    # Buscar claves relacionadas con trabajos
                    descripcion, cantidad, precio = "", "", ""
                    
                    for key, value in tabla.items():
                        key_upper = str(key).upper()
                        value_str = str(value).strip()
                        
                        if "DESCRIPCIÓN DE TRABAJOS" in key_upper:
                            descripcion = value_str
                        elif "CANT" in key_upper and "CANTIDAD" not in key_upper:  # Priorizar CANT sobre CANTIDAD
                            cantidad = value_str
                        elif "CANTIDAD" in key_upper and not cantidad:  # Solo si no se encontró CANT
                            cantidad = value_str
                        elif "PRECIO" in key_upper:
                            precio = value_str
                    
                    # Solo agregar si tiene descripción válida y viene de trabajos
                    if (descripcion and 
                        descripcion.lower() != "sin trabajos disponibles" and
                        not descripcion.upper().startswith(("TOTAL", "SUBTOTAL"))):
                        
                        trabajos.append({
                            "descripcion": descripcion,
                            "cantidad": cantidad if cantidad else "N/A",
                            "precio": precio if precio else "N/A"
                        })
                        print(f"✅ DEBUG: Trabajo de dict agregado: {descripcion} | {cantidad} | {precio}")
            
            print(f"🔍 DEBUG: Total trabajos encontrados: {len(trabajos)}")
            for i, trabajo in enumerate(trabajos):
                print(f"🔍 DEBUG: Trabajo {i+1}: {trabajo}")
            
            return trabajos[:15]  # Limitar a 15 trabajos
            
        except Exception as e:
            print(f"Error al parsear trabajos: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    @rx.var
    def cotizacion_detalle_familys_count(self) -> int:
        """Devuelve el número de familias en la cotización de detalle."""
        count = len(self.cotizacion_detalle.familys)
        print(f"🔍 DEBUG: cotizacion_detalle_familys_count = {count}")
        return count
    
    @rx.var
    def cotizacion_detalle_productos_count(self) -> int:
        """Devuelve el número de productos extraídos del PDF."""
        count = len(self.cotizacion_detalle_descripcion_productos)
        print(f"🔍 DEBUG: cotizacion_detalle_productos_count = {count}")
        return count
    
    @rx.var
    def cotizacion_detalle_trabajos_count(self) -> int:
        """Devuelve el número de trabajos extraídos del PDF."""
        count = len(self.cotizacion_detalle_descripcion_trabajos)
        print(f"🔍 DEBUG: cotizacion_detalle_trabajos_count = {count}")
        return count
    
    def format_date_display(self, date_str: str) -> str:
        """Formatea fechas para mostrar en la interfaz."""
        if not date_str:
            return "No especificada"
        
        # Si ya está en formato dd/mm/yyyy
        if "/" in date_str and len(date_str.split("/")) == 3:
            return date_str
        
        # Si está en formato yyyy-mm-dd, convertir
        if "-" in date_str and len(date_str) == 10:
            try:
                year, month, day = date_str.split("-")
                return f"{day}/{month}/{year}"
            except ValueError:
                return date_str
        
        return date_str
    
    # DARK MODE FUNCTIONALITY - DISABLED FOR NOW, KEEP FOR FUTURE USE
    # @rx.event
    # def toggle_dark_mode(self):
    #     """Cambia entre modo oscuro y claro."""
    #     self.dark_mode = not self.dark_mode
    #     print(f"🎨 Cambiando a modo {'oscuro' if self.dark_mode else 'claro'}")
    
    # @rx.var
    # def theme_appearance(self) -> str:
    #     """Devuelve el tema actual para la aplicación."""
    #     return "dark" if self.dark_mode else "light"
    
    @rx.event(background=True)
    async def get_certs(self):
        """Obtiene los certificados del usuario."""
        try:
            async with self:
                print("🔄 Cargando certificados...")
                filter = "" #Completar con el filtro
                
                # Si current_area es None (TODOS), no aplicar filtro por área
                area_filter = self.user_data.current_area if self.user_data.current_area else None
                
                if area_filter is None:
                    print("📋 Cargando TODOS los certificados (sin filtro por área)")
                else:
                    print(f"📋 Cargando certificados para área: {area_filter}")
                
                certs_data = firestore_api.get_certs(area=area_filter, order_by="issuedate", limit=100, filter=filter)
                self.certs = certs_data
                self.certs_show = self.certs
                
                if self.certs:
                    print(f"✅ {len(certs_data)} certificados obtenidos correctamente")
                else:
                    print("⚠️  No se encontraron certificados")
                    
        except Exception as e:
            print(f"❌ Error al obtener los certificados: {e}")
            import traceback
            traceback.print_exc()
    
    @rx.event
    async def update_certs_show(self):
        """Actualiza certificados a mostrar."""
        try:
            # Determinar si necesitamos cargar más datos para búsqueda
            search_limit = 0 if self.values.get("search_value", "") else 100  # 0 = sin límite para búsqueda
            has_search = bool(self.values.get("search_value", ""))
            
            # Si hay búsqueda, intentar usar Algolia primero
            if has_search:
                print(f"� Buscando certificados con Algolia: '{self.values['search_value']}'")
                
                # Preparar filtros para Algolia
                filters = {}
                if self.values.get("client", ""):
                    filters["client"] = self.values["client"]
                
                # Buscar con Algolia
                algolia_results = await algolia_api.search_certs(
                    self.values["search_value"], 
                    area=self.user_data.current_area,  # None si es TODOS
                    filters=filters
                )
                
                if algolia_results:
                    # Convertir resultados de Algolia a objetos Certs
                    self.certs = [algolia_to_certs(dict(hit)) for hit in algolia_results["hits"]]
                    print(f"✅ Algolia encontró {len(self.certs)} certificados")
                else:
                    # Fallback a búsqueda en Firestore si Algolia falla o no encuentra resultados
                    print("⚠️  Algolia no disponible o sin resultados, usando Firestore...")
                    if self.values.get("client", "") != "": 
                        filter_conditions = [("client", "==", self.values["client"])]
                    else:
                        filter_conditions = ""
                    
                    self.certs = firestore_api.get_certs(
                        area=self.user_data.current_area,  # None si es TODOS
                        order_by="issuedate", 
                        limit=search_limit,
                        filter=filter_conditions
                    )
                    
                    # Filtrar localmente como fallback
                    if self.values.get("search_value", ""):
                        self.certs = [c for c in self.certs
                                     if any(self.values["search_value"].lower() in str(getattr(c, field, "")).lower() 
                                           for field in ["client", "num", "year", "status"])]
                        
            elif not self.certs:
                # Cargar datos iniciales desde Firestore
                print(f"🔄 Cargando certificados iniciales (límite: {search_limit})...")
                if self.values.get("client", "") != "": 
                    filter_conditions = [("client", "==", self.values["client"])]
                else:
                    filter_conditions = ""
                
                self.certs = firestore_api.get_certs(
                    area=self.user_data.current_area,  # None si es TODOS
                    order_by="issuedate", 
                    limit=search_limit,
                    filter=filter_conditions
                )
            else:
                # Si no hay búsqueda y ya tenemos datos, usar existentes pero actualizarlos si es necesario
                if self.values.get("client", "") != "": 
                    filter_conditions = [("client", "==", self.values["client"])]
                    # Recargar datos con filtro de cliente
                    certs_data = firestore_api.get_certs(
                        area = self.user_data.current_area, 
                        order_by = "issuedate", 
                        limit = self.values.get("limit", 100) if self.values.get("limit", 100) > 0 else search_limit,
                        filter = filter_conditions
                    )
                    self.certs = certs_data
                
            # Ordenar por fecha si se especifica
            if self.values.get("order_by", "") == "fecha":
                self.certs_show = sorted(self.certs, key=lambda c: c.issuedate)
            elif self.values.get("order_by", "") == "cliente":
                self.certs_show = sorted(self.certs, key=lambda c: c.client)
            else:
                self.certs_show = self.certs
            
            # Si no usamos Algolia para la búsqueda, aplicar filtro local
            if not has_search or not algolia_api.enabled:
                if self.values.get("search_value", "") != "" and not algolia_results:
                    print(f"🔍 Filtrando {len(self.certs)} certificados localmente por: '{self.values['search_value']}'")
                    self.certs_show = [c for c in self.certs_show 
                                     if any(self.values["search_value"].lower() in str(getattr(c, field, "")).lower() 
                                           for field in ["client", "num", "year", "status"])]
                    print(f"✅ Se encontraron {len(self.certs_show)} certificados que coinciden")
            
            # Limitar resultados mostrados (pero después del filtro)
            display_limit = 50
            if len(self.certs_show) > display_limit:
                print(f"📄 Limitando resultados a {display_limit} de {len(self.certs_show)} encontrados")
                self.certs_show = self.certs_show[:display_limit]
                
        except Exception as e:
            print(f"❌ Error al actualizar certificados: {e}")
            import traceback
            traceback.print_exc()
    
    @rx.event(background=True)
    async def get_fams(self):
        """Obtiene las familias."""
        try:
            async with self:
                print("🔄 Cargando familias...")
                
                # Si current_area es None (TODOS), no aplicar filtro por área
                area_filter = self.user_data.current_area if self.user_data.current_area else None
                
                if area_filter is None:
                    print("📋 Cargando TODAS las familias (sin filtro por área)")
                else:
                    print(f"📋 Cargando familias para área: {area_filter}")

                self.fams = firestore_api.get_fams(
                    area=area_filter, 
                    order_by="razonsocial",
                    limit=100,
                    filter=""
                )  
                
                if self.fams:
                    self.fams_show = self.fams[:30]  # Mostrar solo las primeras 30 familias
                    print(f"✅ {len(self.fams)} familias obtenidas correctamente, mostrando {len(self.fams_show)}")
                else:
                    self.fams_show = []
                    print("⚠️  No se encontraron familias")

        except Exception as e:
            print(f"❌ Error al obtener las familias: {e}")
            import traceback
            traceback.print_exc()

    def set_search_text(self, value: str):
        """Actualiza el texto de búsqueda sin ejecutar la búsqueda."""
        self.search_text = value

    @rx.event
    async def handle_search_key(self, key: str):
        """Maneja las teclas presionadas en el campo de búsqueda."""
        if key == "Enter":
            await self.execute_search()

    @rx.event
    async def execute_search(self):
        """Ejecuta la búsqueda usando el texto almacenado en search_text."""
        # Actualizar actividad del usuario
        await self.update_activity()
        
        try:
            # Si el texto de búsqueda está vacío o es solo espacios, limpiar búsqueda
            search_value = self.search_text.strip() if self.search_text else ""
            if not search_value:
                print("🧹 Limpiando búsqueda - texto vacío")
                await self.clear_search()
            else:
                await self.filter_values(search_value)
        except Exception as e:
            print(f"❌ Error en búsqueda: {e}")

    @rx.event
    async def clear_search(self):
        """Limpia la búsqueda y restaura todos los datos."""
        try:
            print("🧹 Limpiando búsqueda y restaurando datos completos")
            
            # Limpiar el texto de búsqueda
            self.search_text = ""
            self.values["search_value"] = ""
            
            # Recargar datos completos según la página actual
            if self.current_page == "certificaciones":
                await self.update_certs_show()
            elif self.current_page == "familias":
                await self.update_fams_show()
            elif self.current_page == "cotizaciones":
                await self.update_cots_show()
            else:
                print(f"⚠️  Página no reconocida para limpieza: {self.current_page}")
                
        except Exception as e:
            print(f"❌ Error al limpiar búsqueda: {e}")

    @rx.event
    async def filter_values(self, search_value: str):
        """Filtra valores según la página actual."""
        try:
            # Si el valor de búsqueda está vacío o es solo espacios, limpiar búsqueda
            clean_search_value = search_value.strip() if search_value else ""
            if not clean_search_value:
                print("🧹 Valor de búsqueda vacío - limpiando búsqueda")
                await self.clear_search()
                return
            
            self.values["search_value"] = clean_search_value
            print(f"🔍 Filtrando '{clean_search_value}' en página: {self.current_page}")
            
            # Aplicar filtro según la página actual
            if self.current_page == "certificaciones":
                await self.update_certs_show()
            elif self.current_page == "familias":
                await self.update_fams_show()
            elif self.current_page == "cotizaciones":
                await self.update_cots_show()
            else:
                print(f"⚠️  Página no reconocida para filtrado: {self.current_page}")
                # Aun así mantener el valor de búsqueda para cuando se establezca la página
                
        except Exception as e:
            print(f"❌ Error en filter_values: {e}")
            # Mantener el valor de búsqueda incluso si hay error
            self.values["search_value"] = search_value

    @rx.event
    async def update_fams_show(self):
        """Actualiza familias a mostrar."""
        try:
            # Determinar si necesitamos cargar más datos para búsqueda
            search_limit = 0 if self.values.get("search_value", "") else 100  # 0 = sin límite para búsqueda
            has_search = bool(self.values.get("search_value", ""))
            
            # Si hay búsqueda, intentar usar Algolia primero
            if has_search:
                print(f"🔍 Buscando familias con Algolia: '{self.values['search_value']}'")
                
                # Preparar filtros para Algolia
                filters = {}
                if self.values.get("client", ""):
                    filters["client"] = self.values["client"]
                
                # Buscar con Algolia
                algolia_results = await algolia_api.search_fams(
                    self.values["search_value"], 
                    area=self.user_data.current_area,
                    filters=filters
                )
                
                if algolia_results:
                    # Convertir resultados de Algolia a objetos Fam
                    self.fams = [algolia_to_fam(dict(hit)) for hit in algolia_results["hits"]]
                    print(f"✅ Algolia encontró {len(self.fams)} familias")
                else:
                    # Fallback a búsqueda en Firestore si Algolia falla o no encuentra resultados
                    print("⚠️  Algolia no disponible o sin resultados, usando Firestore...")
                    if self.values.get("client", "") != "": 
                        self.fams = firestore_api.get_fams(
                            area=self.user_data.current_area,  # None si es TODOS
                            order_by="razonsocial", 
                            limit=search_limit,
                            filter=[("razonsocial", "==", self.values["client"])]
                        )
                    else:
                        self.fams = firestore_api.get_fams(
                            area=self.user_data.current_area,  # None si es TODOS
                            order_by="razonsocial", 
                            limit=search_limit,
                            filter=""
                        )
                    
                    # Filtrar localmente como fallback
                    if self.values.get("search_value", ""):
                        self.fams = buscar_fams(self.fams, self.values["search_value"])
                        
            elif not self.fams:
                # Cargar datos iniciales desde Firestore
                print(f"🔄 Cargando familias iniciales (límite: {search_limit})...")
                if self.values.get("client", "") != "": 
                    self.fams = firestore_api.get_fams(
                        area=self.user_data.current_area,  # None si es TODOS
                        order_by="razonsocial", 
                        limit=search_limit,
                        filter=[("razonsocial", "==", self.values["client"])]
                    )
                else:
                    self.fams = firestore_api.get_fams(
                        area=self.user_data.current_area,  # None si es TODOS
                        order_by="razonsocial", 
                        limit=search_limit,
                        filter=""
                    )
            else:
                # Si no hay búsqueda y ya tenemos datos, usar existentes pero actualizarlos si es necesario
                #Filtrar por cliente
                if self.values.get("client", "") != "": 
                    self.fams = firestore_api.get_fams(
                        area = self.user_data.current_area, 
                        order_by = "razonsocial", 
                        limit = self.values["limit"] if self.values["limit"]>0 else 0,
                        filter = [("razonsocial", "==", self.values["client"])]
                    )
                else:
                    # Usar datos existentes si no hay filtros específicos
                    pass
            
            # Ordenar las familias por fecha de vencimiento
            if self.values["sorted_value"] == "expirationdate":
                self.fams_show = sorted(
                    self.fams,
                    key=lambda f: datetime.strptime(f.expirationdate, "%Y-%m-%d") if f.expirationdate else datetime.max
                )
            elif self.values["sorted_value"] == "family":
                self.fams_show = sorted(self.fams, key=lambda f: f.family)
            else: 
                self.fams_show = self.fams

            # Si no usamos Algolia para la búsqueda, aplicar filtro local
            if not has_search or not algolia_api.enabled:
                if self.values.get("search_value", "") != "" and not algolia_results:
                    print(f"🔍 Filtrando {len(self.fams)} familias localmente por: '{self.values['search_value']}'")
                    self.fams_show = buscar_fams(self.fams_show, self.values["search_value"])
                    print(f"✅ Se encontraron {len(self.fams_show)} familias que coinciden")

            # Limitar resultados mostrados (pero después del filtro)
            display_limit = 50
            if len(self.fams_show) > display_limit:
                print(f"📄 Limitando resultados a {display_limit} de {len(self.fams_show)} encontrados")
                self.fams_show = self.fams_show[:display_limit]
                
        except Exception as e:
            print(f"❌ Error al actualizar la familia: {e}")
            import traceback
            traceback.print_exc()

    @rx.event(background=True)
    async def get_cots(self, append_mode: bool = False):
        """Obtiene las cotizaciones."""
        try:
            async with self:
                print("🔄 Cargando cotizaciones...")
                
                # Si current_area es None (TODOS), no aplicar filtro por área
                area_filter = self.user_data.current_area if self.user_data.current_area else None
                
                if area_filter is None:
                    print("📋 Cargando TODAS las cotizaciones (sin filtro por área)")
                else:
                    print(f"📋 Cargando cotizaciones para área: {area_filter}")
                
                self.cots = firestore_api.get_cots(
                    area=area_filter, 
                    order_by="issuedate_timestamp",  # Usar timestamp para mejor ordenamiento
                    limit=100,
                    filter=""
                )  
                
                if self.cots:
                    # Ordenar por número de cotización (año descendente, número descendente)
                    self.cots = sorted(self.cots, key=lambda cot: (int(cot.year) if cot.year.isdigit() else 0, int(cot.num) if cot.num.isdigit() else 0), reverse=True)
                    
                    if append_mode:
                        # Modo scroll infinito: agregar a los existentes
                        print(f"📄 Modo scroll infinito: agregando {len(self.cots)} cotizaciones")
                        self.cots_show.extend(self.cots)
                    else:
                        # Modo paginación: reiniciar y mostrar primera página
                        self.cots_page = 0
                        self.cots_show = self.cots[:30]  # Mostrar solo las primeras 30 cotizaciones
                        print(f"✅ {len(self.cots)} cotizaciones obtenidas correctamente y ordenadas por número, mostrando {len(self.cots_show)}")
                else:
                    if not append_mode:
                        self.cots_show = []
                    print("⚠️  No se encontraron cotizaciones")

        except Exception as e:
            print(f"❌ Error al obtener las cotizaciones: {e}")
            import traceback
            traceback.print_exc()

    @rx.event
    async def update_cots_show(self):
        """Actualiza cotizaciones a mostrar."""
        try:
            # Determinar si necesitamos cargar más datos para búsqueda
            search_limit = 0 if self.values.get("search_value", "") else 100  # 0 = sin límite para búsqueda
            has_search = bool(self.values.get("search_value", ""))
            
            # Si hay búsqueda, intentar usar Algolia primero
            if has_search:
                print(f"🔍 Buscando cotizaciones con Algolia: '{self.values['search_value']}'")
                
                # Preparar filtros para Algolia
                filters = {}
                if self.values.get("client", ""):
                    filters["client"] = self.values["client"]
                
                # Buscar con Algolia
                algolia_results = await algolia_api.search_cots(
                    self.values["search_value"], 
                    area=self.user_data.current_area,
                    filters=filters
                )
                
                if algolia_results:
                    # Convertir resultados de Algolia a objetos Cot
                    self.cots = [algolia_to_cot(dict(hit)) for hit in algolia_results["hits"]]
                    print(f"✅ Algolia encontró {len(self.cots)} cotizaciones")
                else:
                    # Fallback a búsqueda en Firestore si Algolia falla o no encuentra resultados
                    print("⚠️  Algolia no disponible o sin resultados, usando Firestore...")
                    algolia_results = []  # Definir variable para evitar error
                    if self.values.get("client", "") != "": 
                        self.cots = firestore_api.get_cots(
                            area=self.user_data.current_area,  # None si es TODOS
                            order_by="issuedate_timestamp",
                            limit=search_limit,
                            filter=[("client", "==", self.values["client"])]
                        )
                    else:
                        self.cots = firestore_api.get_cots(
                            area=self.user_data.current_area,  # None si es TODOS
                            order_by="issuedate_timestamp",
                            limit=search_limit,
                            filter=""
                        )
                    
                    # Filtrar localmente como fallback
                    if self.values.get("search_value", ""):
                        self.cots = buscar_cots(self.cots, self.values["search_value"])
                        
            elif not self.cots:
                # Cargar datos iniciales desde Firestore
                print(f"🔄 Cargando cotizaciones iniciales (límite: {search_limit})...")
                
                if self.values.get("client", "") != "": 
                    self.cots = firestore_api.get_cots(
                        area=self.user_data.current_area,  # None si es TODOS
                        order_by="issuedate_timestamp",
                        limit=search_limit,
                        filter=[("client", "==", self.values["client"])]
                    )
                else:
                    self.cots = firestore_api.get_cots(
                        area=self.user_data.current_area,  # None si es TODOS
                        order_by="issuedate_timestamp",
                        limit=search_limit,
                        filter=""
                    )
            else:
                # Si no hay búsqueda y ya tenemos datos, usar existentes pero actualizarlos si es necesario
                #Filtrar por cliente
                if self.values.get("client", "") != "": 
                    self.cots = firestore_api.get_cots(
                        area=self.user_data.current_area,  # None si es TODOS
                        order_by="issuedate_timestamp",  # Usar timestamp
                        limit=self.values["limit"] if self.values["limit"]>0 else 0,
                        filter=[("client", "==", self.values["client"])]
                    )
                else:
                    # Usar datos existentes si no hay filtros específicos
                    pass
            
            # Ordenar las cotizaciones por número (año descendente, número descendente)
            if self.values["sorted_value"] == "issuedate":
                self.cots_show = sorted(
                    self.cots,
                    key=lambda f: f.issuedate_timestamp if f.issuedate_timestamp > 0 else 0,
                    reverse=True  # Más recientes primero
                )
            elif self.values["sorted_value"] == "client":
                self.cots_show = sorted(self.cots, key=lambda f: f.client)
            else:
                # Ordenamiento por defecto: número de cotización (año descendente, número descendente)
                self.cots_show = sorted(self.cots, key=lambda cot: (int(cot.year) if cot.year.isdigit() else 0, int(cot.num) if cot.num.isdigit() else 0), reverse=True)

            # Si no usamos Algolia para la búsqueda, aplicar filtro local
            if not has_search or not algolia_api.enabled:
                if self.values.get("search_value", "") != "" and not algolia_results:
                    print(f"🔍 Filtrando {len(self.cots)} cotizaciones localmente por: '{self.values['search_value']}'")
                    self.cots_show = buscar_cots(self.cots_show, self.values["search_value"])
                    print(f"✅ Se encontraron {len(self.cots_show)} cotizaciones que coinciden")
            
            # Limitar resultados mostrados (pero después del filtro)
            display_limit = 50
            if len(self.cots_show) > display_limit:
                print(f"📄 Limitando resultados a {display_limit} de {len(self.cots_show)} encontrados")
                self.cots_show = self.cots_show[:display_limit]

        except Exception as e:
            print(f"❌ Error al actualizar la cotización: {e}")
            import traceback
            traceback.print_exc()

    @rx.event
    async def load_more_certs(self):
        """Carga más certificados para scroll infinito"""
        if self.is_loading_more:
            print("⏳ Ya se están cargando más certificados...")
            return
            
        try:
            self.is_loading_more = True
            print(f"📄 Cargando más certificados (página {self.certs_page + 1})")
            
            # Verificar si hay una búsqueda activa
            has_search = bool(self.values.get("search_value", ""))
            
            if has_search:
                # Preparar filtros para Algolia
                filters = {}
                if self.values.get("client", ""):
                    filters["client"] = self.values["client"]
                
                # Buscar siguiente página con Algolia
                algolia_results = await algolia_api.search_certs(
                    self.values["search_value"],
                    page=self.certs_page + 1,
                    hits_per_page=20,
                    area=self.user_data.current_area,
                    filters=filters
                )
                
                if algolia_results and algolia_results.get('hits'):
                    # Convertir y agregar nuevos resultados
                    new_certs = [algolia_to_certs(dict(hit)) for hit in algolia_results['hits']]
                    self.certs_show.extend(new_certs)
                    self.certs_page += 1
                    self.total_certs = algolia_results.get('nbHits', 0)
                    print(f"✅ Se cargaron {len(new_certs)} certificados más (total: {len(self.certs_show)})")
                else:
                    print("📄 No hay más certificados para cargar")
            else:
                print("⚠️  Carga de más datos sin búsqueda no implementada aún")
                
        except Exception as e:
            print(f"❌ Error al cargar más certificados: {e}")
        finally:
            self.is_loading_more = False

    @rx.event
    async def load_more_fams(self):
        """Carga más familias para scroll infinito"""
        if self.is_loading_more:
            print("⏳ Ya se están cargando más familias...")
            return
            
        try:
            self.is_loading_more = True
            print(f"📄 Cargando más familias (página {self.fams_page + 1})")
            
            # Verificar si hay una búsqueda activa
            has_search = bool(self.values.get("search_value", ""))
            
            if has_search:
                # Preparar filtros para Algolia
                filters = {}
                if self.values.get("client", ""):
                    filters["client"] = self.values["client"]
                
                # Buscar siguiente página con Algolia
                algolia_results = await algolia_api.search_fams(
                    self.values["search_value"],
                    page=self.fams_page + 1,
                    hits_per_page=20,
                    area=self.user_data.current_area,
                    filters=filters
                )
                
                if algolia_results and algolia_results.get('hits'):
                    # Convertir y agregar nuevos resultados
                    new_fams = [algolia_to_fam(dict(hit)) for hit in algolia_results['hits']]
                    self.fams_show.extend(new_fams)
                    self.fams_page += 1
                    self.total_fams = algolia_results.get('nbHits', 0)
                    print(f"✅ Se cargaron {len(new_fams)} familias más (total: {len(self.fams_show)})")
                else:
                    print("📄 No hay más familias para cargar")
            else:
                print("⚠️  Carga de más datos sin búsqueda no implementada aún")
                
        except Exception as e:
            print(f"❌ Error al cargar más familias: {e}")
        finally:
            self.is_loading_more = False

    @rx.event
    async def load_more_cots(self):
        """Carga más cotizaciones para scroll infinito"""
        if self.is_loading_more:
            print("⏳ Ya se están cargando más cotizaciones...")
            return
            
        try:
            self.is_loading_more = True
            print(f"📄 Cargando más cotizaciones (página {self.cots_page + 1})")
            
            # Verificar si hay una búsqueda activa
            has_search = bool(self.values.get("search_value", ""))
            
            if has_search:
                # Preparar filtros para Algolia
                filters = {}
                if self.values.get("client", ""):
                    filters["client"] = self.values["client"]
                
                # Buscar siguiente página con Algolia
                algolia_results = await algolia_api.search_cots(
                    self.values["search_value"],
                    page=self.cots_page + 1,
                    hits_per_page=20,
                    area=self.user_data.current_area,
                    filters=filters
                )
                
                if algolia_results and algolia_results.get('hits'):
                    # Convertir y agregar nuevos resultados
                    new_cots = [algolia_to_cot(dict(hit)) for hit in algolia_results['hits']]
                    self.cots_show.extend(new_cots)
                    self.cots_page += 1
                    self.total_cots = algolia_results.get('nbHits', 0)
                    print(f"✅ Se cargaron {len(new_cots)} cotizaciones más (total: {len(self.cots_show)})")
                else:
                    print("📄 No hay más cotizaciones para cargar")
            else:
                print("⚠️  Carga de más datos sin búsqueda no implementada aún")
                
        except Exception as e:
            print(f"❌ Error al cargar más cotizaciones: {e}")
        finally:
            self.is_loading_more = False

    @rx.event
    async def on_scroll_end(self):
        """Detecta cuando el usuario hace scroll hasta el final y carga más datos"""
        if self.is_loading_more:
            return
            
        # Solo cargar más si hay una búsqueda activa
        if not self.values.get("search_value", ""):
            return
            
        # Determinar qué tipo de datos cargar según la página actual
        if self.current_page == "certificaciones":
            await self.load_more_certs()
        elif self.current_page == "familias":
            await self.load_more_fams()
        elif self.current_page == "cotizaciones":
            await self.load_more_cots()

    # Variable para controlar throttling de scroll
    last_scroll_time: float = 0
    scroll_position: int = 0
    
    @rx.event 
    async def on_scroll_throttled(self, scroll_info: dict = None):
        """Evento de scroll con throttling y detección de final"""
        import time
        current_time = time.time()
        
        # Solo procesar si han pasado al menos 1 segundo desde el último scroll
        if current_time - self.last_scroll_time < 1.0:
            return
            
        self.last_scroll_time = current_time
        
        # Solo cargar más si hay una búsqueda activa
        if not self.values.get("search_value", ""):
            return
        
        if self.is_loading_more:
            return
            
        # Simular que estamos cerca del final después de un scroll
        # En una implementación real, usarías scroll_info para determinar la posición
        print("🔄 Scroll detectado, cargando más datos...")
        
        # Determinar qué tipo de datos cargar según la página actual
        if self.current_page == "certificaciones":
            await self.load_more_certs()
        elif self.current_page == "familias":
            await self.load_more_fams()
        elif self.current_page == "cotizaciones":
            await self.load_more_cots()

    def logout(self):
        """Cierra sesión del usuario"""
        print("👋 Cerrando sesión...")
        
        firestore_api.cleanup()
        
        # Limpiar toda la información de sesión persistente
        self.id_token = ""
        self.user_email = ""
        self.set_session_internal(False)  # Limpiar sesión interna
        self.set_last_activity(0.0)
        self.session_valid = False
        self.roles = []
        self.areas = []
        self.user_data = User(
            data = {}, 
            roles_names = [],
            current_rol_name = "",
            current_rol = "",
            areas_names = [],
            current_area = "",
            current_area_name = "",
            email = ""
        )
        
        print("✅ Sesión cerrada correctamente")
        return rx.redirect("/")

    async def on_firestore_change(self, data):
        """Callback para cambios en Firestore (usado en restore_session)."""
        try:
            await firestore_queue.put(data)
        except Exception as e:
            print(f"Error al colocar datos en la cola: {e}")

    def _normalize_company_name(self, name: str) -> str:
        """
        Normaliza nombres de empresa eliminando tipos de sociedad y caracteres especiales
        """
        if not name:
            return ""
        
        # Convertir a mayúsculas y quitar acentos
        normalized = name.upper().strip()
        # Normalizar acentos
        import unicodedata
        normalized = unicodedata.normalize('NFD', normalized)
        normalized = ''.join(char for char in normalized if unicodedata.category(char) != 'Mn')
        
        # Lista de tipos de sociedad comunes a eliminar
        company_types = [
            "S.A.", "SA", "S.A", "SOCIEDAD ANONIMA", "SOCIEDAD ANÓNIMA", "SOCIEDAD ANÓNIMA",
            "S.R.L.", "SRL", "S.R.L", "SOCIEDAD RESPONSABILIDAD LIMITADA", "SOCIEDAD DE RESPONSABILIDAD LIMITADA",
            "S.L.", "SL", "SOCIEDAD LIMITADA",
            "S.C.", "SC", "SOCIEDAD COLECTIVA", 
            "LTDA", "LTDA.", "LIMITADA",
            "CIA", "CIA.", "COMPAÑIA", "COMPAÑÍA", "COMPANIA",
            "INC", "INC.", "INCORPORATED",
            "LLC", "LLC.", "LIMITED LIABILITY COMPANY",
            "LTD", "LTD.", "LIMITED",
            "CORP", "CORP.", "CORPORATION",
            "CO.", "COMPANY",  # Solo CO. con punto, no CO solo
        ]
        
        # Eliminar tipos de sociedad (al final o precedidos por espacio)
        for company_type in company_types:
            # Al final de la cadena
            if normalized.endswith(" " + company_type):
                normalized = normalized[:-len(" " + company_type)]
            elif normalized.endswith(company_type) and company_type != "CO":  # Evitar eliminar CO solo
                normalized = normalized[:-len(company_type)]
            
            # En medio o al principio (precedido por espacio)
            normalized = normalized.replace(" " + company_type + " ", " ")
            if normalized.startswith(company_type + " ") and company_type != "CO":
                normalized = normalized[len(company_type + " "):]
        
        # Eliminar puntos, comas y otros caracteres especiales
        import re
        normalized = re.sub(r'[.,;:\-_()[\]{}]', ' ', normalized)
        
        # Eliminar espacios múltiples y strip
        normalized = ' '.join(normalized.split())
        
        return normalized.strip()

    async def _search_client_intelligent(self, client_name: str):
        """
        Búsqueda inteligente de cliente:
        1. Busca en Algolia (sin filtro de área)
        2. Si falla, busca en Firestore (sin filtro de área)
        3. Normaliza nombres para ignorar tipos de sociedad
        """
        if not client_name:
            return None
            
        try:
            # Normalizar el nombre de búsqueda
            normalized_search = self._normalize_company_name(client_name)
            print(f"🔍 DEBUG: Búsqueda normalizada: '{client_name}' → '{normalized_search}'")
            
            # 1. INTENTAR BÚSQUEDA EN ALGOLIA PRIMERO
            try:
                print(f"🔍 DEBUG: Buscando en Algolia sin filtro de área...")
                algolia_results = await algolia_api.search_clients(
                    query=normalized_search,
                    page=0,
                    hits_per_page=10,
                    area="",  # Sin filtro de área
                    filters=None
                )
                
                if algolia_results and algolia_results.get("hits"):
                    # Buscar coincidencia exacta o muy similar en resultados de Algolia
                    for hit in algolia_results["hits"]:
                        # Convertir hit a diccionario si es necesario
                        hit_dict = hit.to_dict() if hasattr(hit, 'to_dict') else hit
                        hit_name = hit_dict.get("razonsocial", "")
                        hit_normalized = self._normalize_company_name(hit_name)
                        
                        # Verificar coincidencia exacta normalizada
                        if hit_normalized == normalized_search:
                            print(f"✅ DEBUG: Cliente encontrado exacto en Algolia: '{hit_name}' (normalizado: '{hit_normalized}')")
                            # Convertir hit de Algolia a objeto Client
                            from ..utils import Client
                            return Client(
                                id=hit_dict.get("objectID", ""),
                                razonsocial=hit_name,
                                consultora=hit_dict.get("consultora", ""),
                                email_cotizacion=hit_dict.get("email_cotizacion", ""),
                                area=hit_dict.get("area", "")
                            )
                    
                    # Si no hay coincidencia exacta, buscar similitud alta
                    import difflib
                    best_match = None
                    best_similarity = 0.0
                    
                    for hit in algolia_results["hits"]:
                        # Convertir hit a diccionario si es necesario
                        hit_dict = hit.to_dict() if hasattr(hit, 'to_dict') else hit
                        hit_name = hit_dict.get("razonsocial", "")
                        hit_normalized = self._normalize_company_name(hit_name)
                        
                        if not hit_normalized:
                            continue
                            
                        similarity = difflib.SequenceMatcher(None, normalized_search, hit_normalized).ratio()
                        
                        if similarity > best_similarity and similarity >= 0.8:  # Alta similitud
                            best_similarity = similarity
                            best_match = hit_dict
                            print(f"🔍 DEBUG: Candidato Algolia: '{hit_name}' → similitud: {similarity:.3f}")
                    
                    if best_match:
                        print(f"✅ DEBUG: Cliente encontrado por similitud en Algolia: '{best_match.get('razonsocial')}' (similitud: {best_similarity:.3f})")
                        from ..utils import Client
                        return Client(
                            id=best_match.get("objectID", ""),
                            razonsocial=best_match.get("razonsocial", ""),
                            consultora=best_match.get("consultora", ""),
                            email_cotizacion=best_match.get("email_cotizacion", ""),
                            area=best_match.get("area", "")
                        )
                
                print(f"⚠️  DEBUG: No se encontró cliente en Algolia para '{normalized_search}'")
                    
            except Exception as e_algolia:
                print(f"⚠️  Error en búsqueda Algolia: {e_algolia}")
            
            # 2. FALLBACK A FIRESTORE SIN FILTRO DE ÁREA
            try:
                print(f"🔍 DEBUG: Buscando en Firestore sin filtro de área...")
                
                # Búsqueda exacta normalizada en Firestore
                all_clients = firestore_api.get_clients(area=None, limit=500)  # Sin filtro de área
                print(f"🔍 DEBUG: Obtenidos {len(all_clients)} clientes de Firestore para comparar")
                
                if all_clients:
                    # Buscar coincidencia exacta normalizada
                    for client in all_clients:
                        if not client.razonsocial:
                            continue
                            
                        client_normalized = self._normalize_company_name(client.razonsocial)
                        if client_normalized == normalized_search:
                            print(f"✅ DEBUG: Cliente encontrado exacto en Firestore: '{client.razonsocial}' (normalizado: '{client_normalized}')")
                            return client
                    
                    # Si no hay coincidencia exacta, buscar por similitud alta
                    import difflib
                    best_client = None
                    best_similarity = 0.0
                    
                    for client in all_clients:
                        if not client.razonsocial:
                            continue
                            
                        client_normalized = self._normalize_company_name(client.razonsocial)
                        if not client_normalized:
                            continue
                            
                        similarity = difflib.SequenceMatcher(None, normalized_search, client_normalized).ratio()
                        
                        if similarity > best_similarity and similarity >= 0.8:  # Alta similitud
                            best_similarity = similarity
                            best_client = client
                            print(f"🔍 DEBUG: Candidato Firestore: '{client.razonsocial}' → similitud: {similarity:.3f}")
                    
                    if best_client:
                        print(f"✅ DEBUG: Cliente encontrado por similitud en Firestore: '{best_client.razonsocial}' (similitud: {best_similarity:.3f})")
                        return best_client
                
                print(f"⚠️  DEBUG: No se encontró cliente en Firestore para '{normalized_search}'")
                    
            except Exception as e_firestore:
                print(f"⚠️  Error en búsqueda Firestore: {e_firestore}")
            
            # Si no se encuentra en ningún lado
            print(f"⚠️  DEBUG: Cliente '{client_name}' no encontrado ni en Algolia ni en Firestore")
            return None
            
        except Exception as e:
            print(f"❌ Error en búsqueda inteligente de cliente: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    async def _save_cotizacion_detalle_to_firestore(self, extracted_data: dict, client_found):
        """
        Guarda los datos procesados de la cotización en Firestore usando save_cotizacion_detalle
        """
        if not self.cotizacion_detalle.id:
            print("⚠️  No se puede guardar: ID de cotización no disponible")
            return
            
        try:
            print(f"💾 Guardando datos procesados de cotización {self.cotizacion_detalle.id}...")
            
            # Preparar datos del cliente
            client_data = {}
            if client_found:
                client_data = {
                    "id": client_found.id,
                    "razonsocial": client_found.razonsocial,
                    "consultora": getattr(client_found, 'consultora', ''),
                    "email_cotizacion": getattr(client_found, 'email_cotizacion', ''),
                    "area": getattr(client_found, 'area', '')
                }
            else:
                # Cliente temporal creado desde PDF
                if hasattr(self, 'cotizacion_detalle_client') and self.cotizacion_detalle_client:
                    client_data = {
                        "id": "",
                        "razonsocial": self.cotizacion_detalle_client.razonsocial,
                        "consultora": getattr(self.cotizacion_detalle_client, 'consultora', ''),
                        "email_cotizacion": getattr(self.cotizacion_detalle_client, 'email_cotizacion', ''),
                        "area": ""
                    }
            
            # Preparar lista de familias
            familias_data = []
            if hasattr(self.cotizacion_detalle, 'familys') and self.cotizacion_detalle.familys:
                for fam in self.cotizacion_detalle.familys:
                    if hasattr(fam, '__dict__'):
                        familias_data.append({
                            "id": getattr(fam, 'id', ''),
                            "family": getattr(fam, 'family', ''),
                            "product": getattr(fam, 'product', ''),
                            "client": getattr(fam, 'client', ''),
                            "client_id": getattr(fam, 'client_id', ''),
                            "area": getattr(fam, 'area', ''),
                            "status": getattr(fam, 'status', '')
                        })
            
            # Preparar lista de trabajos
            trabajos_data = []
            if hasattr(self, 'cotizacion_detalle_trabajos') and self.cotizacion_detalle_trabajos:
                trabajos_data = self.cotizacion_detalle_trabajos
            
            # Preparar lista de productos (si existe)
            productos_data = []
            if hasattr(self, 'cotizacion_detalle_productos') and self.cotizacion_detalle_productos:
                productos_data = self.cotizacion_detalle_productos
            
            # Preparar metadata
            metadata = extracted_data.get("metadata", {})
            
            # Preparar tablas
            tablas = extracted_data.get("tablas", [])
            
            # Preparar condiciones
            condiciones = extracted_data.get("condiciones", "")
            
            # Llamar a la función de firestore_api para guardar
            success = firestore_api.save_cotizacion_detalle(
                cotizacion_id=self.cotizacion_detalle.id,
                client_data=client_data,
                familias=familias_data,
                trabajos=trabajos_data,
                productos=productos_data,
                metadata=metadata,
                tables=tablas,
                condiciones=condiciones
            )
            
            if success:
                print(f"✅ Datos procesados guardados exitosamente en cotizaciones/{self.cotizacion_detalle.id}/detalle")
            else:
                print(f"❌ Error al guardar datos procesados")
                
        except Exception as e:
            print(f"❌ Error en _save_cotizacion_detalle_to_firestore: {e}")
            import traceback
            traceback.print_exc()
    
    def _limpiar_cache_cotizacion_detalle(self):
        """Limpia el cache de cotización detalle para evitar mostrar datos erróneos."""
        print("🧹 Limpiando cache de cotización detalle...")
        
        # MARCAR COMO CARGANDO INMEDIATAMENTE para ocultar datos antiguos
        self.is_loading_cotizacion_detalle = True
        
        # Limpiar la cotización actual
        self.cotizacion_detalle = Cot()
        
        # Limpiar cliente relacionado
        self.cotizacion_detalle_client = Client()
        self.cotizacion_detalle_current_id = ""
        
        # Resetear estados relacionados
        self.cotizacion_detalle_processing = False
        self.upload_progress = 0
        self.error_message = ""
        self.success_message = ""
        self.force_pdf_reprocess = False
            
        # Limpiar metadata y tablas procesadas
        self.cotizacion_detalle_pdf_metadata = ""
        self.cotizacion_detalle_pdf_tablas = ""
        self.cotizacion_detalle_pdf_condiciones = ""
        self.cotizacion_detalle_pdf_error = ""
        self.cotizacion_detalle_pdf_familias = ""
        self.cotizacion_detalle_pdf_familias_validacion = ""
        
        # Limpiar datos procesados adicionales
        self.cotizacion_detalle_trabajos = []
        self.cotizacion_detalle_productos = []
        
        print("✅ Cache de cotización detalle limpiado correctamente")
    
    def _firestore_to_json_safe(self, obj):
        """
        Convierte objetos de Firestore a formato JSON serializable
        """
        import datetime
        
        def json_serializer(obj):
            """Serializador personalizado para objetos de Firestore"""
            # Verificar diferentes tipos de objetos datetime de Firestore
            if hasattr(obj, 'isoformat') and hasattr(obj, '__class__'):
                class_name = obj.__class__.__name__
                # Manejar DatetimeWithNanoseconds y otros objetos datetime de Firestore
                if 'Datetime' in class_name or isinstance(obj, datetime.datetime):
                    return obj.isoformat()
            elif isinstance(obj, dict):
                # Recursivamente procesar diccionarios
                return {k: json_serializer(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                # Recursivamente procesar listas
                return [json_serializer(item) for item in obj]
            # Para otros tipos, intentar serializar directamente
            try:
                import json
                json.dumps(obj)  # Test if it's already serializable
                return obj
            except (TypeError, ValueError):
                # Si no es serializable, convertir a string
                return str(obj)
        
        # Procesar el objeto y convertir a JSON
        try:
            processed_obj = json_serializer(obj)
            return json.dumps(processed_obj, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"⚠️ Error en serialización JSON: {e}")
            # Fallback: convertir todo el objeto a string
            return json.dumps(str(obj), ensure_ascii=False, indent=2)
    
    async def _load_from_firestore_detalle(self, firestore_data: dict):
        """
        Carga datos procesados desde Firestore en lugar de procesar PDF
        """
        try:
            print(f"📥 Cargando datos procesados desde Firestore...")
            
            # Cargar metadata usando el serializador seguro
            metadata = firestore_data.get("metadata", {})
            self.cotizacion_detalle_pdf_metadata = self._firestore_to_json_safe(metadata)
            
            # Cargar tablas usando el serializador seguro
            tables = firestore_data.get("tables", [])
            self.cotizacion_detalle_pdf_tablas = self._firestore_to_json_safe(tables)
            
            # Cargar condiciones
            condiciones = firestore_data.get("condiciones", "")
            self.cotizacion_detalle_pdf_condiciones = str(condiciones)
            
            # Cargar familias usando el serializador seguro
            familias_data = firestore_data.get("familias", [])
            self.cotizacion_detalle_pdf_familias = self._firestore_to_json_safe(familias_data)
            
            # Procesar cliente desde datos guardados
            client_data = firestore_data.get("client", {})
            if client_data:
                client_name = client_data.get("razonsocial", "")
                if client_name:
                    self.cotizacion_detalle.client = client_name
                    
                    # Crear objeto cliente desde datos guardados
                    from ..utils import Client
                    self.cotizacion_detalle_client = Client(
                        id=client_data.get("id", ""),
                        razonsocial=client_data.get("razonsocial", ""),
                        consultora=client_data.get("consultora", ""),
                        email_cotizacion=client_data.get("email_cotizacion", ""),
                        area=client_data.get("area", "")
                    )
                    self.cotizacion_detalle.client_id = client_data.get("id", "")
            
            # Cargar familias procesadas
            familias_list = []
            for fam_data in familias_data:
                if isinstance(fam_data, dict):
                    from ..utils import Fam
                    fam_obj = Fam(
                        id=fam_data.get("id", ""),
                        family=fam_data.get("family", ""),
                        product=fam_data.get("product", ""),
                        client=fam_data.get("client", ""),
                        client_id=fam_data.get("client_id", ""),
                        area=fam_data.get("area", ""),
                        status=fam_data.get("status", "")
                    )
                    familias_list.append(fam_obj)
            
            self.cotizacion_detalle.familys = familias_list
            self.cotizacion_detalle.familys_ids = [fam.id for fam in familias_list if fam.id]
            
            # Cargar trabajos
            trabajos_data = firestore_data.get("trabajos", [])
            self.cotizacion_detalle_trabajos = trabajos_data
            
            # Cargar productos
            productos_data = firestore_data.get("productos", [])
            self.cotizacion_detalle_productos = productos_data
            
            # Actualizar metadata en cotización
            if metadata:
                numero_cot = str(metadata.get("numero_cotizacion", ""))
                import re
                digits = re.findall(r"\d+", numero_cot)
                if digits:
                    joined = "".join(digits)
                    self.cotizacion_detalle.num = (joined[:4] if len(joined) >= 4 else joined).zfill(4)
                    self.cotizacion_detalle.year = joined[-2:] if len(joined) >= 2 else self.cotizacion_detalle.year
                
                if metadata.get("fecha"):
                    self.cotizacion_detalle.issuedate = metadata.get("fecha")
                if metadata.get("dirigido_a"):
                    self.cotizacion_detalle.nombre = metadata.get("dirigido_a").strip()
                if metadata.get("consultora"):
                    self.cotizacion_detalle.consultora = metadata.get("consultora").strip()
                if metadata.get("mail_receptor"):
                    self.cotizacion_detalle.email = metadata.get("mail_receptor").strip()
                if metadata.get("revision"):
                    self.cotizacion_detalle.rev = str(metadata.get("revision")).strip()
            
            print(f"✅ Datos cargados desde Firestore: {len(familias_list)} familias, {len(trabajos_data)} trabajos")
            
            # MARCAR CARGA COMO COMPLETADA
            self.is_loading_cotizacion_detalle = False
            
        except Exception as e:
            print(f"❌ Error cargando datos desde Firestore: {e}")
            import traceback
            traceback.print_exc()
            # También marcar como completado en caso de error
            self.is_loading_cotizacion_detalle = False