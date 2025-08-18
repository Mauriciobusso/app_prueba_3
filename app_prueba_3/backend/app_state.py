import reflex as rx
from google.oauth2.id_token import verify_oauth2_token
from google.auth.transport import requests
import os, json
from dotenv import load_dotenv
from ..api.firestore_api import firestore_api
from ..api.algolia_api import algolia_api
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
        self.cotizacion_detalle_pdf_metadata = ""
        self.cotizacion_detalle_pdf_tablas = ""
        self.cotizacion_detalle_pdf_condiciones = ""
        self.cotizacion_detalle_pdf_error = ""
        self.cotizacion_detalle_pdf_familias = ""
        self.cotizacion_detalle_pdf_familias_validacion = ""
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

                # 1. BUSCAR CLIENTE EN FIRESTORE O CREAR DESDE COTIZACIÓN
                try:
                    area_filter = self.user_data.current_area if self.user_data.current_area else None
                    print(f"🔍 DEBUG: Buscando cliente '{client_name}' en área: {area_filter}")
                    
                    client_found = None
                    
                    # Primero buscar con filtro exacto en el área
                    if client_name:
                        clients_exact = firestore_api.get_clients(
                            area=area_filter,
                            filter=[("razonsocial", "==", client_name)]
                        )
                        if clients_exact:
                            client_found = clients_exact[0]
                            print(f"✅ DEBUG: Cliente encontrado exacto en área: {client_found.razonsocial}")
                    
                    # Si no se encuentra exacto, buscar sin filtro de área
                    if not client_found and client_name:
                        clients_exact_no_area = firestore_api.get_clients(
                            area=None,
                            filter=[("razonsocial", "==", client_name)]
                        )
                        if clients_exact_no_area:
                            client_found = clients_exact_no_area[0]
                            print(f"✅ DEBUG: Cliente encontrado exacto sin área: {client_found.razonsocial}")
                    
                    # Si aún no se encuentra, buscar por similitud
                    if not client_found and client_name:
                        clients_similar = firestore_api.search_clients_by_similarity(
                            razonsocial=client_name,
                            area=area_filter,
                            similarity_threshold=0.7
                        )
                        if clients_similar:
                            client_found = clients_similar[0]
                            print(f"✅ DEBUG: Cliente encontrado por similitud: {client_found.razonsocial}")
                    
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
            except Exception as e:
                self.cotizacion_detalle_pdf_error = str(e)
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
    
    # Datos extraídos del PDF de la cotización seleccionada
    cotizacion_detalle_pdf_metadata: str = ""
    cotizacion_detalle_pdf_tablas: str = ""
    cotizacion_detalle_pdf_condiciones: str = ""
    cotizacion_detalle_pdf_error: str = ""

    # Campo de texto de búsqueda temporal (no ejecuta búsqueda automáticamente)
    search_text: str = ""
    
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
            # Obtener el parámetro cot_id de la URL actual usando la nueva API
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
            
        except Exception as e:
            print(f"❌ Error al cargar cotización detalle: {e}")
            self.cotizacion_detalle = Cot()
    
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
                    
                    # Buscar tabla con columnas DESCRIPCIÓN, CANTIDAD, PRECIO (formato estándar)
                    if (any("DESCRIPCIÓN DE TRABAJOS" not in str(h).upper() for h in headers) and 
                        any("CANTIDAD" in str(h).upper() for h in headers) and
                        any("PRECIO" in str(h).upper() for h in headers)):
                        
                        print(f"✅ DEBUG: Tabla de trabajos estándar encontrada")
                        # Encontrar índices de columnas
                        desc_idx = next((i for i, h in enumerate(headers) if "DESCRIPCIÓN DE TRABAJOS" not in str(h).upper()), 0)
                        cant_idx = next((i for i, h in enumerate(headers) if "CANTIDAD" in str(h).upper()), -1)
                        precio_idx = next((i for i, h in enumerate(headers) if "PRECIO" in str(h).upper()), -1)
                        
                        # Procesar filas
                        for fila in tabla[1:]:  # Skip header
                            if isinstance(fila, list) and len(fila) > desc_idx:
                                descripcion = str(fila[desc_idx]).strip() if len(fila) > desc_idx else ""
                                cantidad = str(fila[cant_idx]).strip() if cant_idx >= 0 and len(fila) > cant_idx else ""
                                precio = str(fila[precio_idx]).strip() if precio_idx >= 0 and len(fila) > precio_idx else ""
                                
                                if descripcion and not descripcion.upper().startswith(("TOTAL", "SUBTOTAL")):
                                    trabajos.append({
                                        "descripcion": descripcion,
                                        "cantidad": cantidad,
                                        "precio": precio
                                    })
                                    print(f"✅ DEBUG: Trabajo estándar agregado: {descripcion} | {cantidad} | {precio}")
                    
                    # Buscar tabla con "DESCRIPCIÓN DE TRABAJOS" (formato específico)
                    elif any("DESCRIPCIÓN DE TRABAJOS" in str(h).upper() for h in headers):
                        print(f"✅ DEBUG: Tabla de trabajos con 'DESCRIPCIÓN DE TRABAJOS' encontrada")
                        
                        # Encontrar índices de columnas
                        desc_idx = next((i for i, h in enumerate(headers) if "DESCRIPCIÓN DE TRABAJOS" in str(h).upper()), 0)
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
                        
                        if "DESCRIPCIÓN DE TRABAJOS" in key_upper or "DESCRIPCIÓN" in key_upper:
                            descripcion = value_str
                        elif "CANTIDAD" in key_upper:
                            cantidad = value_str
                        elif "PRECIO" in key_upper:
                            precio = value_str
                    
                    # Solo agregar si tiene descripción válida
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
    async def get_cots(self):
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
                    self.cots_show = self.cots[:30]  # Mostrar solo las primeras 30 cotizaciones
                    print(f"✅ {len(self.cots)} cotizaciones obtenidas correctamente y ordenadas por número, mostrando {len(self.cots_show)}")
                else:
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