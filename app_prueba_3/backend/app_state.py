import reflex as rx
from google.oauth2.id_token import verify_oauth2_token
from google.auth.transport import requests
import os, json
from dotenv import load_dotenv
from ..api.firestore_api import firestore_api
from ..api.algolia_api import algolia_api
from ..api.algolia_utils import algolia_to_cot, algolia_to_certs, algolia_to_fam
from ..utils import User, Fam, Certs, Cot, buscar_fams, buscar_cots
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

    certs: list[Certs] = []         # Lista para almacenar los certificados
    certs_show: list[Certs] = []    # Lista para mostrar los certificados

    fams: list[Fam] = []            # Lista para almacenar las familias
    fams_show: list[Fam] = []       # Lista para mostrar las familias

    cots: list[Cot] = []            # Lista para almacenar las cotizaciones
    cots_show: list[Cot] = []       # Lista para mostrar las cotizaciones
    
    # Cotización de detalle para la vista individual
    cotizacion_detalle: Cot = Cot()

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
        self.current_page = page
        print(f"📄 Página establecida: {page}")
        
        # Cargar datos según la página
        if self.is_authenticated:
            print(f"🔐 Usuario autenticado, cargando datos para: {page}")
            if page == "certificaciones":
                yield AppState.get_certs()
            elif page == "familias":
                yield AppState.get_fams()
            elif page == "cotizaciones":
                yield AppState.get_cots()
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
                
                # Cargar roles en paralelo
                print("👥 Cargando roles...")
                self.roles = firestore_api.get_roles()
                self.user_data.roles_names = sorted([role['name'] for role in self.roles if role['id'] in user_data.get('roles', [])])
                self.user_data.current_rol = user_data.get("currentRole", "")
                self.user_data.current_rol_name = firestore_api.get_rol_name(self.user_data.current_rol)
                
                # Cargar áreas de forma optimizada
                print("🌍 Cargando áreas...")
                self.areas = firestore_api.get_areas()
                
                # Procesar áreas inmediatamente después de obtenerlas
                user_area_ids = user_data.get('areas', [])
                if user_area_ids:
                    area_names = sorted([area['name'] for area in self.areas if area['id'] in user_area_ids])
                    self.user_data.areas_names = area_names
                    self.user_data.current_area = user_data.get("currentArea", "")
                    self.user_data.current_area_name = firestore_api.get_area_name(self.user_data.current_area) if self.user_data.current_area else "TODAS"
                    
                    print(f"✅ Áreas cargadas: {len(area_names)} áreas disponibles")
                else:
                    # Usuario sin áreas asignadas
                    self.user_data.areas_names = []
                    self.user_data.current_area = ""
                    self.user_data.current_area_name = ""
                    print("⚠️  Usuario sin áreas asignadas")
                
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
                    except Exception as e:
                        print(f"Error al colocar datos en la cola: {e}")

                firestore_api.setup_listener(email, firestore_callback)
            else:
                print("✅ Listener ya configurado.")
                
            print(f"✅ Usuario inicializado correctamente: {email}")
                
        except Exception as e:
            print(f"❌ Error al inicializar usuario: {e}")
            await self.clear_session()

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