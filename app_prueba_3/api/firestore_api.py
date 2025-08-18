import os
from typing import Dict, Callable, Union, List, Tuple, Any
from dotenv import load_dotenv
import firebase_admin
from firebase_admin import credentials, firestore
from google.cloud.firestore_v1 import FieldFilter
import asyncio
from threading import Thread, Lock
from ..utils import User, Fam, Cot, Certs, Model, Client, completar_con_ceros

class FirestoreAPI:
    def __init__(self):
        load_dotenv()
        
        # Verificar que todas las variables de entorno estén presentes
        required_env_vars = [
            "FIREBASE_PROJECT_ID",
            "FIREBASE_PRIVATE_KEY_ID", 
            "FIREBASE_PRIVATE_KEY",
            "FIREBASE_CLIENT_EMAIL",
            "FIREBASE_CLIENT_ID",
            "FIREBASE_CLIENT_X509_CERT_URL"
        ]
        
        missing_vars = [var for var in required_env_vars if not os.getenv(var)]
        
        if missing_vars:
            print(f"⚠️  Variables de entorno faltantes: {', '.join(missing_vars)}")
            print("🔧 Por favor, crea un archivo .env con las credenciales de Firebase.")
            print("📋 Puedes usar .env.example como referencia.")
            
            # Inicializar sin Firebase para modo desarrollo
            self.db = None
            self.firebase_initialized = False
        else:
            try:
                private_key = os.getenv("FIREBASE_PRIVATE_KEY")
                if private_key:
                    private_key = private_key.replace("\\n", "\n")
                
                cred = credentials.Certificate({
                    "type": "service_account",
                    "project_id": os.getenv("FIREBASE_PROJECT_ID"),
                    "private_key_id": os.getenv("FIREBASE_PRIVATE_KEY_ID"),
                    "private_key": private_key,
                    "client_email": os.getenv("FIREBASE_CLIENT_EMAIL"),
                    "client_id": os.getenv("FIREBASE_CLIENT_ID"),
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                    "client_x509_cert_url": os.getenv("FIREBASE_CLIENT_X509_CERT_URL")
                })
                firebase_admin.initialize_app(cred)
                self.db = firestore.client()
                self.firebase_initialized = True
                print("✅ Firebase inicializado correctamente")
            except Exception as e:
                print(f"❌ Error al inicializar Firebase: {e}")
                self.db = None
                self.firebase_initialized = False
        self.listener = None
        self.callback_loop = None  # Event loop para ejecutar callbacks
        self.callback_thread = None
        self.lock = Lock()  # Para asegurar el manejo del loop en hilos
        self.roles: list = []
        self.areas: list = []

    def start_callback_loop(self):
        """Inicia un thread con un event loop para ejecutar coroutines."""
        with self.lock:
            if not self.callback_loop:
                self.callback_loop = asyncio.new_event_loop()
                self.callback_thread = Thread(target=self._run_loop, daemon=True)
                self.callback_thread.start()

    def _run_loop(self):
        """Ejecuta el event loop en un hilo separado."""
        asyncio.set_event_loop(self.callback_loop)
        try:
            self.callback_loop.run_forever()
        except Exception as e:
            print(f"Error en el event loop: {e}")
        finally:
            self.callback_loop.close()

    def stop_callback_loop(self):
        """Detiene el event loop y el hilo del callback."""
        with self.lock:
            if self.callback_loop:
                self.callback_loop.call_soon_threadsafe(self.callback_loop.stop)
                self.callback_thread.join()
                self.callback_loop = None
                self.callback_thread = None
                print("Event loop detenido")  

    def setup_listener(self, email: str, callback: Callable[[Dict], None]):
        """Configura un listener para cambios en Firestore"""
        self.start_callback_loop()

        if self.listener:
            print("Listener ya configurado.")
            return

        query = self.db.collection("users").where(filter=FieldFilter("email", "==", email))
        
        def on_snapshot(snapshot, changes, read_time):
            print("Cambios detectados en Firestore.")
            for change in changes:
                if change.type.name in ["ADDED", "MODIFIED"]:
                    try:
                        with self.lock:
                            if self.callback_loop:
                                asyncio.run_coroutine_threadsafe(
                                    callback(change.document.to_dict()), self.callback_loop
                                )
                            else:
                                print("Event loop no disponible")
                    except Exception as e:
                        print(f"Error en callback: {e}")

        self.listener = query.on_snapshot(on_snapshot)
        print("Listener configurado.")

    def cleanup(self):
        """Limpia el listener activo y el event loop del callback"""
        if self.listener:
            self.listener.unsubscribe()
            self.listener = None
            print("Listener eliminado.")
        self.stop_callback_loop()


    def get_user(self, email: str) -> Dict:
        """Obtiene datos del usuario desde Firestore"""
        if not self.firebase_initialized:
            print("⚠️  Firebase no inicializado. Retornando datos de ejemplo.")
            return {}
        
        try:
            query = self.db.collection("users").where(filter=FieldFilter("email", "==", email))
            docs = query.stream()
            return next((doc.to_dict() for doc in docs), {})
        except Exception as e:
            print(f"Error al obtener usuario: {e}")
            return {}

    def get_roles(self) -> dict:
        """Obtiene el nombre del rol desde Firestore"""
        if not self.firebase_initialized:
            print("⚠️  Firebase no inicializado. Retornando roles de ejemplo.")
            return [{"id": "role1", "name": "Admin"}, {"id": "role2", "name": "User"}]
            
        if not self.roles:
            try:
                query = self.db.collection("roles")
                docs = query.stream()
                roles = {doc.id: doc.to_dict() for doc in docs}
                resultados = [{"id": role_id, "name": role_data.get("title", "")} for role_id, role_data in roles.items()]
                self.roles = resultados
                return resultados
            except Exception as e:
                print(f"Error al obtener roles: {e}")
                return [] 
        else:   
            print("Roles ya obtenidos.")
            return self.roles
        
    def get_rol_name(self, rol_id: str) -> str:
        """Obtiene el nombre del rol desde Firestore"""
        try:
            doc = self.db.collection("roles").document(rol_id).get()
            return doc.to_dict().get("title", "") if doc.exists else ""
        except Exception as e:
            print(f"Error al obtener nombre del rol: {e}")
            return "" 
    
    def get_certs(self, area: str = "HGGSLLi2VCJaBtK0w794", order_by: str = "issuedate", limit: int = 50, filter: str = "") -> list:
        """Obtiene los certificados del usuario desde Firestore"""
        if not self.firebase_initialized:
            print("⚠️  Firebase no inicializado. Retornando lista vacía.")
            return []
            
        try:
            # Si area es None, obtener todos los certificados sin filtro por área
            if area is None:
                print("📋 Obteniendo TODOS los certificados (sin filtro por área)")
                # Obtener todos los certificados sin filtrar por área
                certs_collection = self.db.collection("certificados")
                
                # Aplicar filtros adicionales si los hay
                query = certs_collection
                if filter:
                    if isinstance(filter, list):
                        for f in filter:
                            field, op, value = f
                            query = query.where(field, op, value)
                
                # Aplicar ordenamiento
                if order_by:
                    query = query.order_by(order_by, direction=firestore.Query.ASCENDING)
                
                # Aplicar límite
                if limit > 0:
                    query = query.limit(limit)
                
                docs_snapshot = query.get()
                docs = []
                for doc in docs_snapshot:
                    data = doc.to_dict()
                    data["id"] = doc.id
                    docs.append(data)
                    
            elif area:  # Si hay un área específica
                docs = self.get_collection_data(
                    collection="certificados",
                    area=area,
                    order_by=order_by,
                    direction=firestore.Query.ASCENDING,
                    limit=limit
                )
            else:
                # Caso donde area es string vacío pero no None
                print("📋 Área vacía, retornando lista vacía")
                return []
            
            # Verificar si docs es None o vacío
            if not docs:
                if area is None:
                    print("📋 No se encontraron certificados en toda la base de datos")
                else:
                    print(f"📋 No se encontraron certificados para el área: {area}")
                return []
            
            resultados = [Certs(
                id=cert_data.get("id", ""),
                num=completar_con_ceros(cert_data.get("number", ""),4),
                year=completar_con_ceros(cert_data.get("year", ""),2),
                rev=completar_con_ceros(cert_data.get("revisionnumber", ""),2),
                assigmentdate=cert_data.get("assigmentdate", ""),
                issuedate=cert_data.get("issuedate", ""),
                vencimiento=cert_data.get("vencimiento", ""),
                area=cert_data.get("area", ""),
                client=cert_data.get("client", ""),
                client_id=cert_data.get("client_id", ""),
                status=cert_data.get("status", ""),
                family_id=cert_data.get("family", ""),
                family= Fam(),
                ensayos=cert_data.get("ensayos", []),
                drive_file_id=cert_data.get("drive_file_id", ""),
                drive_file_id_signed=cert_data.get("drive_file_id_signed", ""),
                ) for cert_data in docs]
            
            if area is None:
                print(f"✅ {len(resultados)} certificados obtenidos correctamente (TODAS las áreas)")
            else:
                print(f"✅ {len(resultados)} certificados obtenidos correctamente para área: {area}")
            return resultados
        except Exception as e:
            print(f"❌ Error al obtener certificados: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def get_fams(
            self, 
            area: str = "HGGSLLi2VCJaBtK0w794", 
            order_by: str = "razonsocial", 
            limit: int = 50, 
            filter: str = ""
        ) -> list:
        """Obtiene las familias del usuario desde Firestore"""
        if not self.firebase_initialized:
            print("⚠️  Firebase no inicializado. Retornando lista vacía.")
            return []
            
        try:
            # Si area es None, obtener todas las familias sin filtro por área
            if area is None:
                print("📋 Obteniendo TODAS las familias (sin filtro por área)")
                # Obtener todas las familias sin filtrar por área
                fams_collection = self.db.collection("familias")
                
                # Aplicar filtros adicionales si los hay
                query = fams_collection
                if filter:
                    if isinstance(filter, list):
                        for f in filter:
                            field, op, value = f
                            query = query.where(field, op, value)
                
                # Aplicar ordenamiento
                if order_by:
                    query = query.order_by(order_by, direction=firestore.Query.ASCENDING)
                
                # Aplicar límite
                if limit > 0:
                    query = query.limit(limit)
                
                docs = query.get()
                fams = []
                for doc in docs:
                    data = doc.to_dict()
                    data["id"] = doc.id
                    fams.append(data)
                    
            elif area:  # Si hay un área específica
                fams = self.get_collection_data(
                    collection="familias",
                    area=area,
                    filters=filter,
                    order_by=order_by,
                    direction=firestore.Query.ASCENDING,
                    limit=limit
                )
            else:
                # Caso donde area es string vacío pero no None
                print("📋 Área vacía, retornando lista vacía")
                return []

            # Verificar si fams es None o vacío
            if not fams:
                if area is None:
                    print("📋 No se encontraron familias en toda la base de datos")
                else:
                    print(f"📋 No se encontraron familias para el área: {area}")
                return []

            resultados = [Fam(
                id=fam.get("id", ""),
                area=fam.get("area", ""),
                family=fam.get("family", ""),
                product=fam.get("product", ""),
                origen=fam.get("origen", ""),
                expirationdate=fam.get("expirationdate", ""),
                vigencia=fam.get("vigencia", ""),
                client=fam.get("razonsocial", ""),
                client_id=fam["client"] if "client" in fam and fam["client"] is not None and isinstance(fam["client"], str) else "",
                system=fam.get("system", "") if fam.get("system") is not None else "",
                status=fam.get("status", "") if fam.get("status") is not None else "",
                models=[Model()],
                rubro=fam["rubro"] if "rubro" in fam and fam["rubro"] is not None else "",
                subrubro=fam["subrubro"] if "subrubro" in fam and fam["subrubro"] is not None else ""
            ) for fam in fams]

            if area is None:
                print(f"✅ {len(resultados)} familias obtenidas correctamente (TODAS las áreas)")
            else:
                print(f"✅ {len(resultados)} familias obtenidas correctamente para área: {area}")
            return resultados
            
        except Exception as e:
            print(f"❌ Error al obtener familias: {e}")
            import traceback
            traceback.print_exc()
            return []

    def get_cots(
            self, 
            area: str = "HGGSLLi2VCJaBtK0w794", 
            order_by: str = "issuedate", 
            limit: int = 50, 
            filter: str = ""
        ) -> list:
        """Obtiene las cotizaciones del usuario desde Firestore"""
        if not self.firebase_initialized:
            print("⚠️  Firebase no inicializado. Retornando lista vacía.")
            return []
            
        try:
            # Si area es None, obtener todas las cotizaciones sin filtro por área
            if area is None:
                print("📋 Obteniendo TODAS las cotizaciones (sin filtro por área)")
                # Obtener todas las cotizaciones sin filtrar por área
                cots_collection = self.db.collection("cotizaciones")
                
                # Aplicar filtros adicionales si los hay
                query = cots_collection
                if filter:
                    if isinstance(filter, list):
                        for f in filter:
                            field, op, value = f
                            query = query.where(field, op, value)
                    else:
                        # Manejo de filtros string (si es necesario)
                        pass
                
                # Aplicar ordenamiento
                if order_by:
                    query = query.order_by(order_by, direction=firestore.Query.DESCENDING)
                
                # Aplicar límite
                if limit > 0:
                    query = query.limit(limit)
                
                docs = query.get()
                cots = []
                for doc in docs:
                    data = doc.to_dict()
                    data["id"] = doc.id
                    cots.append(data)
                    
            elif area:  # Si hay un área específica
                cots = self.get_collection_data(
                    collection="cotizaciones",
                    area=area,
                    filters=filter,
                    order_by=order_by,
                    direction=firestore.Query.DESCENDING,  # Más recientes primero
                    limit=limit
                )
            else:
                # Caso donde area es string vacío pero no None
                print("📋 Área vacía, retornando lista vacía")
                return []

            # Verificar si cots es None o vacío
            if not cots:
                if area is None:
                    print("📋 No se encontraron cotizaciones en toda la base de datos")
                else:
                    print(f"📋 No se encontraron cotizaciones para el área: {area}")
                return []

            resultados = [Cot(
                id=cot.get("id", ""),
                area=cot.get("area", ""),
                #family=cot.get("family", ""),
                #product=cot.get("product", ""),
                num=completar_con_ceros(cot.get("number", ""), 4),
                year=completar_con_ceros(cot.get("year", ""), 2),
                client=cot.get("razonsocial", ""),
                client_id=cot["client"] if "client" in cot and cot["client"] is not None and isinstance(cot["client"], str) else "",
                issuedate=cot.get("issuedate", ""),
                issuedate_timestamp=cot.get("issuedate_timestamp", 0.0),  # Timestamp para ordenamiento
                vigencia=cot.get("vigencia", ""),
                status=cot.get("estado", "") if cot.get("estado") is not None else "",
                aprueba=cot.get("aprueba", "") if cot.get("aprueba") is not None else "",
                drive_file_id=cot.get("drive_file_id", "") if cot.get("drive_file_id") is not None else "",
                drive_file_id_name=cot.get("drive_file_id_name", "") if cot.get("drive_file_id_name") is not None else "",
                drive_aprobacion_id=cot.get("drive_aprobacion_id", "") if cot.get("drive_aprobacion_id") is not None else "",
                drive_aceptacion_id=cot.get("drive_aceptacion_id", "") if cot.get("drive_aceptacion_id") is not None else "",
                enviada_fecha=cot.get("enviada_fecha", "") if cot.get("enviada_fecha") is not None else "",
                facturada_fecha=cot.get("facturada_fecha", "") if cot.get("facturada_fecha") is not None else "",
                facturar=cot.get("facturar", "") if cot.get("facturar") is not None else "",
                nombre=cot.get("nombre", "") if cot.get("nombre") is not None else "",
                email=cot.get("mail", "") if cot.get("mail") is not None else "",
                ot=cot.get("op", "") if cot.get("op") is not None else "",
                rev=cot.get("rev", "") if cot.get("rev") is not None else "",
                resolucion=cot.get("resolucion", "") if cot.get("resolucion") is not None else "",
                cuenta=cot.get("cuenta", "") if cot.get("cuenta") is not None else "",
            ) for cot in cots]

            if area is None:
                print(f"✅ {len(resultados)} cotizaciones obtenidas correctamente (TODAS las áreas)")
            else:
                print(f"✅ {len(resultados)} cotizaciones obtenidas correctamente para área: {area}")
            return resultados
            
        except Exception as e:
            print(f"❌ Error al obtener cotizaciones: {e}")
            import traceback
            traceback.print_exc()
            return []
        
    def get_collection_data(
        self,
        collection: str = "",
        area: str = "HGGSLLi2VCJaBtK0w794",
        order_by: str = "",
        direction=firestore.Query.DESCENDING,
        limit: int = 50,
        filters: List[Tuple[str, str, Any]] = None
    ) -> Union[list, None]:
        """
        Obtiene los datos desde Firestore con múltiples filtros opcionales.

        Args:
            collection (str): Nombre de la colección de Firestore.
            area (str): Valor del campo 'area' para filtrar.
            order_by (str): Campo por el cual ordenar.
            direction: Dirección de orden (ASCENDING o DESCENDING).
            limit (int): Número máximo de resultados.
            filters (list): Lista de tuplas (campo, operador, valor), ej: [("status", "==", "aprobado")]

        Returns:
            list: Lista de documentos con sus IDs, o lista vacía en caso de error.
        """
        if not self.firebase_initialized:
            print("⚠️  Firebase no inicializado. Retornando lista vacía.")
            return []
            
        try:
            if not collection:
                raise ValueError("El nombre de la colección no puede estar vacío.")
            
            cert_ref = self.db.collection(collection)
            query = cert_ref.where(filter=FieldFilter("area", "==", area))

            if filters:
                for field, op, value in filters:
                    print(f"Aplicando filtro: {field} {op} {value}")
                    query = query.where(filter=FieldFilter(field, op, value))

            # Si la consulta requiere un índice compuesto, intentar sin order_by primero
            try:
                if order_by:
                    query = query.order_by(order_by, direction=direction)
                
                if limit > 0:
                    query = query.limit(limit)

                docs = query.stream()
                return [{"id": doc.id, **doc.to_dict()} for doc in docs]
                
            except Exception as index_error:
                if "index" in str(index_error).lower():
                    print(f"⚠️  Consulta requiere índice. Ejecutando consulta simplificada sin ordenar.")
                    print(f"🔗 Para crear el índice: {str(index_error)}")
                    
                    # Consulta simplificada sin order_by
                    simple_query = cert_ref.where(filter=FieldFilter("area", "==", area))
                    if limit > 0:
                        simple_query = simple_query.limit(limit)
                    
                    docs = simple_query.stream()
                    return [{"id": doc.id, **doc.to_dict()} for doc in docs]
                else:
                    raise index_error
        
        except Exception as e:
            print(f"Error al obtener datos de la colección: {e}")
            return []

    def get_areas(self) -> dict:
        """Obtiene el nombre del rol desde Firestore"""
        if not self.areas:
            try:
                query = self.db.collection("areas")
                docs = query.stream()
                areas = {doc.id: doc.to_dict() for doc in docs}
                resultados = [{"id": area_id, "name": area_data.get("name", "")} for area_id, area_data in areas.items()]
                self.areas = resultados
                return resultados
            except Exception as e:
                print(f"Error al obtener areas: {e}")
                return "" 
        else:   
            print("Areas ya obtenidas.")
            return self.areas

    def get_area_name(self, area_id: str) -> str:
        """Obtiene el nombre del area desde Firestore"""
        try:
            doc = self.db.collection("areas").document(area_id).get()
            return doc.to_dict().get("name", "") if doc.exists else ""
        except Exception as e:
            print(f"Error al obtener nombre del area: {e}")
            return "" 

    def get_clients(
        self,
        area: str = None,
        order_by: str = "razonsocial",
        limit: int = 100,
        filter: Union[str, list] = ""
    ) -> list[Client]:
        """
        Obtiene los clientes desde Firestore.

        Args:
            area (str): Filtrar por área específica. Si es None, obtiene de todas las áreas.
            order_by (str): Campo por el cual ordenar (por defecto: razonsocial).
            limit (int): Número máximo de resultados.
            filter: Filtros adicionales. Puede ser una lista de tuplas o cadena vacía.

        Returns:
            list[Client]: Lista de clientes.
        """
        if not self.firebase_initialized:
            print("⚠️  Firebase no inicializado. Retornando lista vacía.")
            return []

        try:
            clients_ref = self.db.collection('clientes')
            query = clients_ref
            
            # Aplicar filtro por área si se especifica
            if area:
                query = query.where(filter=FieldFilter("area", "==", area))

            # Aplicar filtros adicionales
            if isinstance(filter, list) and filter:
                for field, op, value in filter:
                    print(f"Aplicando filtro cliente: {field} {op} {value}")
                    query = query.where(filter=FieldFilter(field, op, value))

            # Ordenar
            if order_by:
                query = query.order_by(order_by, direction=firestore.Query.ASCENDING)

            # Limitar resultados
            if limit > 0:
                query = query.limit(limit)

            docs = query.stream()
            clients = []
            
            for doc in docs:
                data = doc.to_dict()
                client = Client(
                    id=doc.id,
                    razonsocial=data.get('razonsocial', ''),
                    cuit=data.get('cuit', ''),
                    direccion=data.get('direccion', ''),
                    phone=data.get('phone', ''),
                    email_cotizacion=data.get('email_cotizacion', ''),
                    active_fams=data.get('active_fams', 0),
                    condiciones=data.get('condiciones', ''),
                    consultora=data.get('consultora', ''),
                )
                clients.append(client)

            print(f"✅ {len(clients)} clientes obtenidos correctamente" + (f" para área: {area}" if area else ""))
            return clients

        except Exception as e:
            print(f"❌ Error al obtener clientes: {e}")
            import traceback
            traceback.print_exc()
            return []

    def search_clients_by_similarity(
        self,
        razonsocial: str,
        area: str = None,
        similarity_threshold: float = 0.6
    ) -> list[Client]:
        """
        Busca clientes por similitud de razón social.
        
        Args:
            razonsocial (str): Razón social a buscar.
            area (str): Filtrar por área específica.
            similarity_threshold (float): Umbral de similitud (0.0-1.0).
        
        Returns:
            list[Client]: Lista de clientes similares ordenados por similitud.
        """
        if not razonsocial:
            return []
        
        try:
            # Obtener todos los clientes
            all_clients = self.get_clients(area=area, limit=0)  # Sin límite para búsqueda
            
            import difflib
            razonsocial_clean = razonsocial.upper().strip()
            similar_clients = []
            
            for client in all_clients:
                client_name_clean = (client.razonsocial or "").upper().strip()
                
                if not client_name_clean:
                    continue
                
                # Calcular similitud usando SequenceMatcher
                similarity = difflib.SequenceMatcher(None, razonsocial_clean, client_name_clean).ratio()
                
                # También buscar palabras clave
                razonsocial_words = set(razonsocial_clean.split())
                client_words = set(client_name_clean.split())
                word_overlap = len(razonsocial_words.intersection(client_words))
                word_similarity = word_overlap / max(len(razonsocial_words), len(client_words)) if razonsocial_words or client_words else 0
                
                # Combinar similitudes
                final_similarity = max(similarity, word_similarity)
                
                if final_similarity >= similarity_threshold:
                    similar_clients.append((client, final_similarity))
            
            # Ordenar por similitud (más similar primero)
            similar_clients.sort(key=lambda x: x[1], reverse=True)
            
            result = [client for client, similarity in similar_clients]
            print(f"🔍 Encontrados {len(result)} clientes similares a '{razonsocial}'")
            
            return result
            
        except Exception as e:
            print(f"❌ Error en búsqueda por similitud: {e}")
            return [] 
    
    def update_current_user(self, email, campo: str, value: str):
        """Actualiza el rol actual del usuario en Firestore"""
        try:
            user_ref = self.db.collection("users").where(filter=FieldFilter("email", "==", email))
            docs = user_ref.stream()
            for doc in docs:
                # Obtener los datos del documento
                doc_data = doc.to_dict()
                if campo in doc_data:
                    doc.reference.update({campo: value})
                else:
                    print(f"Campo '{campo}' no encontrado en el documento.")
        except Exception as e:
            print(f"Error al actualizar usuario: {e}")

# Instancia global del API
firestore_api = FirestoreAPI()