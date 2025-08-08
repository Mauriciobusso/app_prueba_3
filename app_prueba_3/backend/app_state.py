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

    # Campo de texto de búsqueda temporal (no ejecuta búsqueda automáticamente)
    search_text: str = ""

    # Paginación
    cots_page: int = 0
    certs_page: int = 0
    fams_page: int = 0
    total_cots: int = 0
    total_certs: int = 0
    total_fams: int = 0
    is_loading_more: bool = False

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
            print(f"� Email persistente encontrado: {self.user_email}")
            print("⚠️  Pero no hay token activo, requiere nueva autenticación")
            
        # Si hay token, verificar autenticación
        if self.id_token:
            print("🔑 Token encontrado, verificando autenticación...")
            try:
                if self.is_authenticated:
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
        """Verifica si el usuario está autenticado."""
        try:
            if not self.id_token:
                return False
                
            # Verificar el token con Google
            token_data = json.loads(self.id_token)
            verify_oauth2_token(
                token_data["credential"],
                requests.Request(),
                CLIENT_ID,
            )
            return True
        except json.JSONDecodeError as e:
            print(f"❌ Error al decodificar token JSON: {e}")
            return False
        except Exception as e:
            # Si el token expiró, simplemente retornar False sin limpiar aún
            if "expired" in str(e).lower() or "invalid" in str(e).lower():
                print(f"⏰ Token expirado o inválido: {e}")
            else:
                print(f"❌ Error de autenticación: {e}")
            return False

    def on_success(self, id_token: dict):
        """Callback de autenticación exitosa."""
        try:
            self.id_token = json.dumps(id_token)
            
            # Extraer información del token para persistencia
            token_data = json.loads(self.id_token)
            decoded_token = verify_oauth2_token(
                token_data["credential"],
                requests.Request(),
                CLIENT_ID,
            )
            
            # Guardar email para identificación persistente
            self.user_email = decoded_token.get("email", "")
            
            print(f"✅ Autenticación exitosa para: {self.user_email}")
            return AppState.initialize_user
        except Exception as e:
            print(f"❌ Error en callback de autenticación: {e}")
            return None

    @rx.event
    async def clear_session(self):
        """Limpia toda la información de sesión."""
        print("🧹 Limpiando sesión...")
        self.id_token = ""
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
                self.user_data.areas_names= sorted([area['name'] for area in self.areas if area['id'] in new_data['areas']])
                self.user_data.current_area = new_data.get("currentArea", "")
                self.user_data.current_area_name = firestore_api.get_area_name(self.user_data.current_area)

            # Marcar como procesado
            firestore_queue.task_done()

    async def initialize_user(self):
        """Inicializa los datos del usuario desde Firestore."""
        if not self.is_authenticated:
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
                
                # Obtener datos iniciales del usuario
                user_data = firestore_api.get_user(email)
                self.user_data.data = user_data
                
                self.roles = firestore_api.get_roles()
                self.user_data.roles_names = sorted([role['name'] for role in self.roles if role['id'] in user_data.get('roles', [])])
                self.user_data.current_rol = user_data.get("currentRole", "")
                self.user_data.current_rol_name = firestore_api.get_rol_name(self.user_data.current_rol)
                
                self.areas = firestore_api.get_areas()
                self.user_data.areas_names= sorted([area['name'] for area in self.areas if area['id'] in user_data.get('areas', [])])
                self.user_data.current_area = user_data.get("currentArea", "")
                self.user_data.current_area_name = firestore_api.get_area_name(self.user_data.current_area)
                

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
        """Establece el rol actual del usuario."""
        try:
            email = self.user_data.data.get("email", "")
            self.user_data.current_area_name = area_name
            self.user_data.current_area = self._find_area_id_by_name(area_name)
            print(f"Area: {self.user_data.current_area}")
            firestore_api.update_current_user(email, "currentArea", self.user_data.current_area) if self.user_data.current_area else None
        except Exception as e:
            print(f"Error al establecer el area: {e}")
    
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
        if self.user_data.data and self.areas:
            areas = self.areas
            for area_info in areas:
                if area_info.get("name") == name:
                    return area_info.get("id")
        return None  # Retorna None si no se encuentra el título
    
    @rx.event(background=True)
    async def get_certs(self):
        """Obtiene los certificados del usuario."""
        try:
            async with self:
                print("🔄 Cargando certificados...")
                filter = "" #Completar con el filtro
                certs_data = firestore_api.get_certs(area = self.user_data.current_area, order_by = "issuedate" ,limit = 100, filter = filter)
                self.certs = certs_data
                self.certs_show = self.certs
                print(f"✅ {len(certs_data)} certificados obtenidos correctamente")
        except Exception as e:
            print(f"Error al obtener los certificados: {e}")
    
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
                    area=self.user_data.current_area,
                    filters=filters
                )
                
                if algolia_results:
                    # Convertir resultados de Algolia a objetos Certs
                    self.certs = [algolia_to_certs(hit) for hit in algolia_results]
                    print(f"✅ Algolia encontró {len(self.certs)} certificados")
                else:
                    # Fallback a búsqueda en Firestore si Algolia falla o no encuentra resultados
                    print("⚠️  Algolia no disponible o sin resultados, usando Firestore...")
                    if self.values.get("client", "") != "": 
                        filter_conditions = [("client", "==", self.values["client"])]
                    else:
                        filter_conditions = ""
                    
                    self.certs = firestore_api.get_certs(
                        area = self.user_data.current_area, 
                        order_by = "issuedate", 
                        limit = search_limit,
                        filter = filter_conditions
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
                    area = self.user_data.current_area, 
                    order_by = "issuedate", 
                    limit = search_limit,
                    filter = filter_conditions
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
                self.fams = firestore_api.get_fams(
                    area = self.user_data.current_area, 
                    order_by = "razonsocial",
                    limit = 100,
                    filter = ""
                )  
                self.fams_show = self.fams[:30]  # Mostrar solo las primeras 30 familias

        except Exception as e:
            print(f"Error al obtener las familias: {e}")

    def set_search_text(self, value: str):
        """Actualiza el texto de búsqueda sin ejecutar la búsqueda."""
        self.search_text = value

    @rx.event
    async def execute_search(self):
        """Ejecuta la búsqueda usando el texto almacenado en search_text."""
        try:
            await self.filter_values(self.search_text)
        except Exception as e:
            print(f"❌ Error en búsqueda: {e}")

    @rx.event
    async def filter_values(self, search_value: str):
        """Filtra valores según la página actual."""
        try:
            self.values["search_value"] = search_value
            print(f"🔍 Filtrando '{search_value}' en página: {self.current_page}")
            
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
                    self.fams = [algolia_to_fam(hit) for hit in algolia_results]
                    print(f"✅ Algolia encontró {len(self.fams)} familias")
                else:
                    # Fallback a búsqueda en Firestore si Algolia falla o no encuentra resultados
                    print("⚠️  Algolia no disponible o sin resultados, usando Firestore...")
                    if self.values.get("client", "") != "": 
                        self.fams = firestore_api.get_fams(
                            area = self.user_data.current_area, 
                            order_by = "razonsocial", 
                            limit = search_limit,
                            filter = [("razonsocial", "==", self.values["client"])]
                        )
                    else:
                        self.fams = firestore_api.get_fams(
                            area = self.user_data.current_area, 
                            order_by = "razonsocial", 
                            limit = search_limit,
                            filter = ""
                        )
                    
                    # Filtrar localmente como fallback
                    if self.values.get("search_value", ""):
                        self.fams = buscar_fams(self.fams, self.values["search_value"])
                        
            elif not self.fams:
                # Cargar datos iniciales desde Firestore
                print(f"🔄 Cargando familias iniciales (límite: {search_limit})...")
                if self.values.get("client", "") != "": 
                    self.fams = firestore_api.get_fams(
                        area = self.user_data.current_area, 
                        order_by = "razonsocial", 
                        limit = search_limit,
                        filter = [("razonsocial", "==", self.values["client"])]
                    )
                else:
                    self.fams = firestore_api.get_fams(
                        area = self.user_data.current_area, 
                        order_by = "razonsocial", 
                        limit = search_limit,
                        filter = ""
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
                self.cots = firestore_api.get_cots(
                    area = self.user_data.current_area, 
                    order_by = "issuedate_timestamp",  # Usar timestamp para mejor ordenamiento
                    limit = 100,
                    filter = ""
                )  
                self.cots_show = self.cots[:30]  # Mostrar solo las primeras 30 cotizaciones
                print(f"✅ {len(self.cots)} cotizaciones obtenidas correctamente")

        except Exception as e:
            print(f"Error al obtener las cotizaciones: {e}")

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
                    self.cots = [algolia_to_cot(hit) for hit in algolia_results]
                    print(f"✅ Algolia encontró {len(self.cots)} cotizaciones")
                else:
                    # Fallback a búsqueda en Firestore si Algolia falla o no encuentra resultados
                    print("⚠️  Algolia no disponible o sin resultados, usando Firestore...")
                    algolia_results = []  # Definir variable para evitar error
                    if self.values.get("client", "") != "": 
                        self.cots = firestore_api.get_cots(
                            area = self.user_data.current_area, 
                            order_by = "issuedate_timestamp",
                            limit = search_limit,
                            filter = [("client", "==", self.values["client"])]
                        )
                    else:
                        self.cots = firestore_api.get_cots(
                            area = self.user_data.current_area, 
                            order_by = "issuedate_timestamp",
                            limit = search_limit,
                            filter = ""
                        )
                    
                    # Filtrar localmente como fallback
                    if self.values.get("search_value", ""):
                        self.cots = buscar_cots(self.cots, self.values["search_value"])
                        
            elif not self.cots:
                # Cargar datos iniciales desde Firestore
                print(f"🔄 Cargando cotizaciones iniciales (límite: {search_limit})...")
                
                if self.values.get("client", "") != "": 
                    self.cots = firestore_api.get_cots(
                        area = self.user_data.current_area, 
                        order_by = "issuedate_timestamp",
                        limit = search_limit,
                        filter = [("client", "==", self.values["client"])]
                    )
                else:
                    self.cots = firestore_api.get_cots(
                        area = self.user_data.current_area, 
                        order_by = "issuedate_timestamp",
                        limit = search_limit,
                        filter = ""
                    )
            else:
                # Si no hay búsqueda y ya tenemos datos, usar existentes pero actualizarlos si es necesario
                #Filtrar por cliente
                if self.values.get("client", "") != "": 
                    self.cots = firestore_api.get_cots(
                        area = self.user_data.current_area, 
                        order_by = "issuedate_timestamp",  # Usar timestamp
                        limit = self.values["limit"] if self.values["limit"]>0 else 0,
                        filter = [("client", "==", self.values["client"])]
                    )
                else:
                    # Usar datos existentes si no hay filtros específicos
                    pass
            
            # Ordenar las cotizaciones por fecha de emision
            if self.values["sorted_value"] == "issuedate":
                self.cots_show = sorted(
                    self.cots,
                    key=lambda f: f.issuedate_timestamp if f.issuedate_timestamp > 0 else 0,
                    reverse=True  # Más recientes primero
                )
            elif self.values["sorted_value"] == "client":
                self.cots_show = sorted(self.cots, key=lambda f: f.client)
            else:
                self.cots_show = self.cots

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

    def logout(self):
        """Cierra sesión del usuario"""
        print("👋 Cerrando sesión...")
        
        firestore_api.cleanup()
        
        # Limpiar toda la información de sesión persistente
        self.id_token = ""
        self.user_email = ""
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