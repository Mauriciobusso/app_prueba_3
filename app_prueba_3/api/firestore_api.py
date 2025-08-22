import os
from typing import Dict, Callable, Union, List, Tuple, Any
from dotenv import load_dotenv
import firebase_admin
from firebase_admin import credentials, firestore
from google.cloud.firestore_v1 import FieldFilter
import asyncio
from threading import Thread, Lock
from ..utils import User, Fam, Cot, Certs, Model, Client, completar_con_ceros
from .algolia_api import algolia_api

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

    # Métodos para manejar cotizaciones detalle (información extraída)
    def save_cotizacion_detalle(
        self,
        cotizacion_id: str,
        client_data: dict,
        familias: list,
        trabajos: list,
        productos: list = None,
        metadata: dict = None,
        tables: list = None,
        condiciones: Union[str, None] = None
    ) -> bool:
        """
        Guarda la información extraída de una cotización en Firestore.
        
        Args:
            cotizacion_id (str): ID de la cotización
            client_data (dict): Información del cliente
            familias (list): Lista de familias extraídas
            trabajos (list): Lista de trabajos extraídos
            productos (list): Lista de productos extraídos (opcional)
            metadata (dict): Metadatos adicionales (fecha de procesamiento, etc.)
        
        Returns:
            bool: True si se guardó exitosamente, False en caso contrario
        """
        if not self.firebase_initialized:
            print("⚠️  Firebase no inicializado. No se puede guardar cotización detalle.")
            return False
        
        try:
            # Preparar los datos para guardar
            # Sanitizar 'tables' para evitar arrays anidados (Firestore no permite arrays dentro de arrays)
            sanitized_tables = tables
            if isinstance(tables, list) and any(isinstance(el, list) for el in tables):
                # Convertir cada fila (lista) en un objeto para evitar arrays anidados
                sanitized_tables = [{"row": el} for el in tables]

            detalle_data = {
                "cotizacion_id": cotizacion_id,
                "client": client_data,
                "familias": familias or [],
                "trabajos": trabajos or [],
                "productos": productos or [],
                # Campos adicionales solicitados
                "metadata": metadata or {},
                "tables": sanitized_tables or [],
                "condiciones": condiciones or "",
                "fecha_procesamiento": firestore.SERVER_TIMESTAMP,
                "version": "1.0"
            }

            # Guardar dentro del documento existente de la colección 'cotizaciones'
            try:
                cot_ref = self.db.collection("cotizaciones").document(cotizacion_id)
                # Guardar el detalle como subcampo para no romper el schema principal
                cot_ref.set({"detalle": detalle_data}, merge=True)
                # Además, asegurar que los campos principales solicitados estén en el doc de cotización
                try:
                    top_update = {}
                    # Fecha
                    fecha = detalle_data.get('metadata', {}).get('fecha') or detalle_data.get('metadata', {}).get('issuedate')
                    if fecha:
                        top_update['issuedate'] = fecha
                    # Empresa / Razón social
                    empresa = detalle_data.get('client', {}).get('razonsocial') or detalle_data.get('client', {}).get('name')
                    if empresa:
                        top_update['razonsocial'] = empresa
                    # At (nombre)
                    at = detalle_data.get('metadata', {}).get('dirigido_a') or detalle_data.get('metadata', {}).get('at')
                    if at:
                        top_update['nombre'] = at
                    # Consultora
                    consultora = detalle_data.get('metadata', {}).get('consultora') or detalle_data.get('client', {}).get('consultora')
                    if consultora:
                        top_update['consultora'] = consultora
                    # Facturar a
                    facturar = detalle_data.get('metadata', {}).get('facturar') or detalle_data.get('client', {}).get('facturar')
                    if facturar:
                        top_update['facturar'] = facturar
                    # Mail receptor
                    mail_receptor = detalle_data.get('metadata', {}).get('mail_receptor') or detalle_data.get('client', {}).get('email_cotizacion') or detalle_data.get('condiciones', '')
                    if mail_receptor:
                        top_update['mail'] = mail_receptor
                    # Familias y trabajos (guardar versiones simplificadas)
                    familias_top = []
                    for f in detalle_data.get('familias', []) or []:
                        if isinstance(f, dict):
                            familias_top.append({
                                'id': f.get('id', ''),
                                'family': f.get('family', ''),
                                'product': f.get('product', '')
                            })
                        else:
                            familias_top.append({'value': str(f)})
                    if familias_top:
                        top_update['familias'] = familias_top

                    trabajos_top = []
                    for t in detalle_data.get('trabajos', []) or []:
                        if isinstance(t, dict):
                            trabajos_top.append({
                                'descripcion': t.get('descripcion') or t.get('Descripcion') or t.get('desc', ''),
                                'cantidad': t.get('cantidad', 0),
                                'descuento': t.get('descuento', 0),
                                'precio': t.get('precio', 0)
                            })
                        else:
                            trabajos_top.append({'descripcion': str(t)})
                    if trabajos_top:
                        top_update['trabajos'] = trabajos_top

                    if top_update:
                        cot_ref.set(top_update, merge=True)
                except Exception as e_top:
                    print(f"⚠️ Error actualizando campos principales de cotización: {e_top}")
                print(f"✅ Cotización detalle guardada dentro de cotizaciones/{cotizacion_id}")
                # Indexar en Algolia para búsquedas rápidas (si está configurado)
                try:
                    if algolia_api and getattr(algolia_api, 'enabled', False):
                        # Construir registro mínimo para Algolia combinando cot info + detalle
                        cot_doc = cot_ref.get()
                        cot_top = cot_doc.to_dict() if cot_doc.exists else {}
                        # Priorizar campos del doc top-level, si existen
                        fecha = (cot_top.get('issuedate') or detalle_data.get('metadata', {}).get('issuedate') or detalle_data.get('metadata', {}).get('fecha') or '')
                        numero = (str(cot_top.get('number') or detalle_data.get('metadata', {}).get('numero_cotizacion') or detalle_data.get('metadata', {}).get('number', '')))
                        empresa = (cot_top.get('razonsocial') or detalle_data.get('client', {}).get('razonsocial') or detalle_data.get('client', {}).get('name') or '')
                        at = detalle_data.get('metadata', {}).get('at', detalle_data.get('metadata', {}).get('nombre', ''))
                        consultora = cot_top.get('consultora') or detalle_data.get('client', {}).get('consultora') or detalle_data.get('metadata', {}).get('consultora', '')
                        facturar = cot_top.get('facturar') or detalle_data.get('metadata', {}).get('facturar', '')
                        mail_receptor = cot_top.get('mail') or detalle_data.get('metadata', {}).get('mail_receptor') or detalle_data.get('client', {}).get('email_cotizacion', '')

                        familias_list = []
                        try:
                            for f in detalle_data.get('familias', []):
                                if isinstance(f, dict):
                                    familias_list.append(f.get('family') or f.get('product') or f.get('razonsocial') or f.get('id') or str(f))
                                else:
                                    familias_list.append(str(f))
                        except Exception:
                            familias_list = []

                        trabajos_list = []
                        try:
                            for t in detalle_data.get('trabajos', []):
                                if isinstance(t, dict):
                                    trabajos_list.append({
                                        'descripcion': t.get('descripcion') or t.get('Descripcion') or t.get('desc') or t.get('description',''),
                                        'cantidad': t.get('cantidad') or t.get('qty') or t.get('cantidad', 0),
                                        'descuento': t.get('descuento') or t.get('discount') or 0,
                                        'precio': t.get('precio') or t.get('price') or t.get('unit_price') or 0
                                    })
                                else:
                                    trabajos_list.append({'descripcion': str(t)})
                        except Exception:
                            trabajos_list = []

                        algolia_record = {
                            'objectID': f"cot_{cotizacion_id}",
                            'id': cotizacion_id,
                            'num': numero,
                            'fecha': fecha,
                            'empresa': empresa,
                            'at': at,
                            'consultora': consultora,
                            'facturar': facturar,
                            'mail_receptor': mail_receptor,
                            'familias': familias_list,
                            'trabajos': trabajos_list,
                            'type': 'cotizacion'
                        }
                        algolia_api.index_data('cotizaciones', [algolia_record])
                except Exception as e:
                    print(f"⚠️ Error indexando cotización en Algolia: {e}")
                return True
            except Exception:
                # Fallback: si por alguna razón no existe la colección/doc o hay permisos, crear colección separada
                doc_ref = self.db.collection("cotizaciones_detalle").document(cotizacion_id)
                doc_ref.set(detalle_data, merge=True)
                print(f"⚠️  Fallback: Cotización detalle guardada en cotizaciones_detalle/{cotizacion_id}")
                # Intentar indexar también en Algolia con la información disponible
                try:
                    if algolia_api and getattr(algolia_api, 'enabled', False):
                        algolia_record = {
                            'objectID': f"cot_{cotizacion_id}",
                            'id': cotizacion_id,
                            'num': detalle_data.get('metadata', {}).get('numero_cotizacion', ''),
                            'fecha': detalle_data.get('metadata', {}).get('issuedate', ''),
                            'empresa': detalle_data.get('client', {}).get('razonsocial', ''),
                            'at': detalle_data.get('metadata', {}).get('at', ''),
                            'consultora': detalle_data.get('client', {}).get('consultora', ''),
                            'facturar': detalle_data.get('metadata', {}).get('facturar', ''),
                            'mail_receptor': detalle_data.get('metadata', {}).get('mail_receptor', ''),
                            'familias': [f.get('family', '') if isinstance(f, dict) else str(f) for f in detalle_data.get('familias', [])],
                            'trabajos': [{
                                'descripcion': t.get('descripcion') or t.get('Descripcion', ''),
                                'cantidad': t.get('cantidad', 0),
                                'descuento': t.get('descuento', 0),
                                'precio': t.get('precio', 0),
                            } if isinstance(t, dict) else {'descripcion': str(t)} for t in detalle_data.get('trabajos', [])],
                            'type': 'cotizacion'
                        }
                        algolia_api.index_data('cotizaciones', [algolia_record])
                except Exception as e:
                    print(f"⚠️ Error indexando cotización (fallback) en Algolia: {e}")
                return True
            
        except Exception as e:
            print(f"❌ Error al guardar cotización detalle: {e}")
            return False
    
    def get_cotizacion_detalle(self, cotizacion_id: str) -> dict:
        """
        Obtiene la información extraída de una cotización desde Firestore.
        
        Args:
            cotizacion_id (str): ID de la cotización
        
        Returns:
            dict: Información de la cotización detalle o None si no existe
        """
        if not self.firebase_initialized:
            print("⚠️  Firebase no inicializado. Retornando None.")
            return None
        
        try:
            # Primero intentar leer el detalle dentro del documento de 'cotizaciones'
            cot_ref = self.db.collection("cotizaciones").document(cotizacion_id)
            cot_doc = cot_ref.get()
            if cot_doc.exists:
                cot_data = cot_doc.to_dict()
                if "detalle" in cot_data:
                    print(f"✅ Cotización detalle encontrada dentro de cotizaciones/{cotizacion_id}")
                    return cot_data.get("detalle")

            # Fallback: leer de la colección legacy 'cotizaciones_detalle'
            doc_ref = self.db.collection("cotizaciones_detalle").document(cotizacion_id)
            doc = doc_ref.get()
            if doc.exists:
                data = doc.to_dict()
                print(f"✅ Cotización detalle encontrada en cotizaciones_detalle/{cotizacion_id}")
                return data
            else:
                print(f"📋 No existe cotización detalle para: {cotizacion_id}")
                return None
                
        except Exception as e:
            print(f"❌ Error al obtener cotización detalle: {e}")
            return None
    
    def cotizacion_detalle_exists(self, cotizacion_id: str) -> bool:
        """
        Verifica si ya existe información extraída para una cotización.
        
        Args:
            cotizacion_id (str): ID de la cotización
        
        Returns:
            bool: True si existe, False en caso contrario
        """
        if not self.firebase_initialized:
            return False
        
        try:
            # Verificar primero en la colección principal 'cotizaciones' (campo 'detalle')
            cot_ref = self.db.collection("cotizaciones").document(cotizacion_id)
            cot_doc = cot_ref.get()
            if cot_doc.exists and "detalle" in cot_doc.to_dict():
                return True

            # Fallback: verificar en la colección legacy
            doc_ref = self.db.collection("cotizaciones_detalle").document(cotizacion_id)
            doc = doc_ref.get()
            return doc.exists
        except Exception as e:
            print(f"❌ Error al verificar cotización detalle: {e}")
            return False
    
    def delete_cotizacion_detalle(self, cotizacion_id: str) -> bool:
        """
        Elimina la información extraída de una cotización.
        
        Args:
            cotizacion_id (str): ID de la cotización
        
        Returns:
            bool: True si se eliminó exitosamente, False en caso contrario
        """
        if not self.firebase_initialized:
            print("⚠️  Firebase no inicializado. No se puede eliminar.")
            return False
        
        try:
            # Intentar eliminar el campo 'detalle' dentro del documento de 'cotizaciones'
            cot_ref = self.db.collection("cotizaciones").document(cotizacion_id)
            try:
                # Usar update con DELETE_FIELD para eliminar solo el subcampo
                cot_ref.update({"detalle": firestore.DELETE_FIELD})
                print(f"✅ Campo 'detalle' eliminado de cotizaciones/{cotizacion_id}")
                return True
            except Exception:
                # Fallback: eliminar documento en la colección legacy
                doc_ref = self.db.collection("cotizaciones_detalle").document(cotizacion_id)
                doc_ref.delete()
                print(f"⚠️  Fallback: Documento eliminado en cotizaciones_detalle/{cotizacion_id}")
                return True
        except Exception as e:
            print(f"❌ Error al eliminar cotización detalle: {e}")
            return False

    # Métodos para plantillas de trabajos y precarga
    def save_trabajo_template(
        self,
        client_id: str,
        area: str,
        trabajo_data: dict,
        template_name: str = "default"
    ) -> bool:
        """
        Guarda una plantilla de trabajo para un cliente específico.
        
        Args:
            client_id (str): ID del cliente
            area (str): Área del trabajo
            trabajo_data (dict): Datos del trabajo (descripción, precio, etc.)
            template_name (str): Nombre de la plantilla
        
        Returns:
            bool: True si se guardó exitosamente
        """
        if not self.firebase_initialized:
            print("⚠️  Firebase no inicializado. No se puede guardar plantilla.")
            return False
        
        try:
            template_data = {
                "client_id": client_id,
                "area": area,
                "template_name": template_name,
                "trabajo": trabajo_data,
                "fecha_creacion": firestore.SERVER_TIMESTAMP,
                "fecha_actualizacion": firestore.SERVER_TIMESTAMP,
                "activo": True
            }
            
            # Usar combinación de client_id, area y template_name como ID
            doc_id = f"{client_id}_{area}_{template_name}"
            doc_ref = self.db.collection("trabajos_templates").document(doc_id)
            doc_ref.set(template_data, merge=True)
            
            print(f"✅ Plantilla de trabajo guardada: {doc_id}")
            return True
            
        except Exception as e:
            print(f"❌ Error al guardar plantilla de trabajo: {e}")
            return False
    
    def get_trabajos_templates(self, client_id: str, area: str = None) -> list:
        """
        Obtiene las plantillas de trabajo para un cliente.
        
        Args:
            client_id (str): ID del cliente
            area (str): Área específica (opcional)
        
        Returns:
            list: Lista de plantillas de trabajo
        """
        if not self.firebase_initialized:
            print("⚠️  Firebase no inicializado. Retornando lista vacía.")
            return []
        
        try:
            query = self.db.collection("trabajos_templates").where("client_id", "==", client_id)
            
            if area:
                query = query.where("area", "==", area)
            
            query = query.where("activo", "==", True)
            
            docs = query.get()
            templates = []
            
            for doc in docs:
                data = doc.to_dict()
                data["id"] = doc.id
                templates.append(data)
            
            print(f"✅ {len(templates)} plantillas encontradas para cliente: {client_id}")
            return templates
            
        except Exception as e:
            print(f"❌ Error al obtener plantillas de trabajo: {e}")
            return []
    
    def get_trabajos(self) -> list:
        """
        Obtiene los trabajos desde la colección 'Trabajo'.
        
        Args:
            limit (int): Límite de resultados
        
        Returns:
            list: Lista de trabajos con campos 'titulo' y 'descripcion'
        """
        if not self.firebase_initialized:
            print("⚠️  Firebase no inicializado. Retornando lista vacía.")
            return []
        
        try:
            # Crear query base - simplificada para evitar el índice por ahora
            query = self.db.collection("Trabajo")
            
            # Por ahora omitir el filtro por área hasta crear el índice
            # if area:
            #     query = query.where("area", "==", area)
            
            # Ordenar por título y limitar resultados
            query = query.order_by("Titulo")
            
            docs = query.get()
            trabajos = []
            
            for doc in docs:
                data = doc.to_dict()
                data["id"] = doc.id
                trabajos.append(data)
            
            print(f"✅ {len(trabajos)} trabajos encontrados")
            return trabajos
            
        except Exception as e:
            print(f"❌ Error al obtener trabajos: {e}")
            return []
    
    def get_next_cotizacion_number(self, area: str, year: str = None) -> dict:
        """
        Obtiene el siguiente número de cotización para un área específica.
        
        Args:
            area (str): ID del área
            year (str): Año (formato YY), si no se especifica usa el año actual
        
        Returns:
            dict: {"number": str, "year": str, "formatted": "NNNN/YY"}
        """
        if not self.firebase_initialized:
            print("⚠️  Firebase no inicializado. Retornando número por defecto.")
            return {"number": "0001", "year": "25", "formatted": "0001/25"}
        
        try:
            from datetime import datetime
            
            # Usar año actual si no se especifica
            if not year:
                current_year = datetime.now().year
                year = str(current_year)[-2:]  # Últimos 2 dígitos del año
            
            # Obtener la última cotización del área y año
            query = (self.db.collection("cotizaciones")
                    .where("area", "==", area)
                    .where("year", "==", year)
                    .order_by("number", direction=firestore.Query.DESCENDING)
                    .limit(1))
            
            docs = list(query.get())
            
            if docs:
                last_doc = docs[0].to_dict()
                last_number = int(last_doc.get("number", 0))
                next_number = last_number + 1
            else:
                next_number = 1
            
            # Formatear con ceros a la izquierda
            formatted_number = str(next_number).zfill(4)
            formatted_full = f"{formatted_number}/{year}"
            
            print(f"✅ Siguiente número de cotización: {formatted_full}")
            
            return {
                "number": formatted_number,
                "year": year,
                "formatted": formatted_full
            }
            
        except Exception as e:
            print(f"❌ Error al obtener siguiente número de cotización: {e}")
            # Retornar número por defecto en caso de error
            return {"number": "0001", "year": year or "25", "formatted": f"0001/{year or '25'}"}
    
    def create_cotizacion_from_template(
        self,
        client_id: str,
        area: str,
        trabajos_templates: list,
        metadata: dict = None
    ) -> str:
        """
        Crea una nueva cotización usando plantillas de trabajo.
        
        Args:
            client_id (str): ID del cliente
            area (str): Área de la cotización
            trabajos_templates (list): Lista de IDs de plantillas de trabajo a incluir
            metadata (dict): Metadatos adicionales
        
        Returns:
            str: ID de la cotización creada o None si falló
        """
        if not self.firebase_initialized:
            print("⚠️  Firebase no inicializado. No se puede crear cotización.")
            return None
        
        try:
            # Obtener siguiente número
            next_info = self.get_next_cotizacion_number(area)
            
            # Obtener datos del cliente
            client_doc = self.db.collection("clientes").document(client_id).get()
            if not client_doc.exists:
                print(f"❌ Cliente no encontrado: {client_id}")
                return None
            
            client_data = client_doc.to_dict()
            
            # Preparar datos de la cotización
            from datetime import datetime
            now = datetime.now()
            
            cotizacion_data = {
                "number": next_info["number"],
                "year": next_info["year"],
                "area": area,
                "client": client_id,
                "razonsocial": client_data.get("razonsocial", ""),
                "estado": "BORRADOR",
                "issuedate": now.strftime("%Y-%m-%d"),
                "issuedate_timestamp": now.timestamp(),
                "fecha_creacion": firestore.SERVER_TIMESTAMP,
                "creado_desde_template": True,
                "templates_usados": trabajos_templates,
                # Campos solicitados por el usuario
                "metadata": metadata or {},
                "empresa": client_data.get("razonsocial", ""),
                "at": client_data.get("contacto", ""),
                "consultora": client_data.get("consultora", ""),
                "facturar": client_data.get("facturar", ""),
                "mail_receptor": client_data.get("email_cotizacion", ""),
                "familias": [],
                "trabajos": []
            }
            
            # Crear la cotización
            doc_ref = self.db.collection("cotizaciones").add(cotizacion_data)
            cotizacion_id = doc_ref[1].id
            
            print(f"✅ Cotización creada desde template: {next_info['formatted']} (ID: {cotizacion_id})")
            # Indexar en Algolia el registro básico de la cotización
            try:
                if algolia_api and getattr(algolia_api, 'enabled', False):
                    algolia_record = {
                        'objectID': f"cot_{cotizacion_id}",
                        'id': cotizacion_id,
                        'num': next_info['number'],
                        'fecha': cotizacion_data.get('issuedate', ''),
                        'empresa': cotizacion_data.get('empresa', ''),
                        'at': cotizacion_data.get('at', ''),
                        'consultora': cotizacion_data.get('consultora', ''),
                        'facturar': cotizacion_data.get('facturar', ''),
                        'mail_receptor': cotizacion_data.get('mail_receptor', ''),
                        'familias': [],
                        'trabajos': [],
                        'type': 'cotizacion'
                    }
                    algolia_api.index_data('cotizaciones', [algolia_record])
            except Exception as e:
                print(f"⚠️ Error indexando cotización recién creada en Algolia: {e}")
            return cotizacion_id
            
        except Exception as e:
            print(f"❌ Error al crear cotización desde template: {e}")
            return None
        
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
            
            # Intentar consulta con filtros completos
            try:
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
                
            except Exception as index_error:
                if "index" in str(index_error).lower():
                    print(f"⚠️  Consulta requiere índice. Ejecutando consulta simplificada.")
                    print(f"🔗 Para crear el índice: {str(index_error)}")
                    
                    # Fallback: consulta simplificada sin área si hay filtros adicionales
                    if isinstance(filter, list) and filter and area:
                        print("🔄 Fallback: Buscando sin filtro de área debido a índice faltante")
                        query = clients_ref
                        
                        # Solo aplicar filtros adicionales
                        for field, op, value in filter:
                            print(f"Aplicando filtro cliente (sin área): {field} {op} {value}")
                            query = query.where(filter=FieldFilter(field, op, value))
                        
                        # Limitar resultados
                        if limit > 0:
                            query = query.limit(limit)
                        
                        docs = query.stream()
                    else:
                        # Si no hay filtros adicionales, solo filtrar por área
                        if area:
                            query = clients_ref.where(filter=FieldFilter("area", "==", area))
                        else:
                            query = clients_ref
                        
                        if limit > 0:
                            query = query.limit(limit)
                            
                        docs = query.stream()
                else:
                    raise index_error
            
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

            # Si se hizo fallback sin filtro de área, filtrar manualmente por área
            if area and isinstance(filter, list) and filter:
                area_filtered_clients = [c for c in clients if c.id and area == area]  # Aquí necesitaríamos el campo área del cliente
                print(f"⚠️  Nota: Filtrado de área aplicado en memoria debido a índice faltante")
            
            print(f"✅ {len(clients)} clientes obtenidos correctamente" + (f" (con filtro por área: {area})" if area else ""))
            return clients

        except Exception as e:
            print(f"❌ Error al obtener clientes: {e}")
            import traceback
            traceback.print_exc()
            return []

    def normalize_company_name(self, name: str) -> str:
        """
        Normaliza nombres de empresas eliminando puntuación y terminaciones de tipo de sociedad.
        
        Args:
            name (str): Nombre de la empresa a normalizar
            
        Returns:
            str: Nombre normalizado
        """
        if not name:
            return ""
            
        import re
        
        # Convertir a mayúsculas y quitar espacios extra
        normalized = name.upper().strip()
        
        # Eliminar puntuación común
        normalized = re.sub(r'[.,;:\-_()[\]{}"]', ' ', normalized)
        
        # Reemplazar múltiples espacios con uno solo
        normalized = re.sub(r'\s+', ' ', normalized).strip()
        
        # Lista de terminaciones de tipos de sociedad a eliminar
        society_endings = [
            # Formatos con puntos y sin puntos
            'SOCIEDAD ANONIMA',
            'S\\.?A\\.?$',  # SA, S.A., S.A
            'S\\s+A$',  # S A
            
            'SOCIEDAD DE RESPONSABILIDAD LIMITADA', 
            'S\\.?R\\.?L\\.?$',  # SRL, S.R.L., S.R.L
            'S\\s+R\\s+L$',  # S R L
            
            'CENTRO INTEGRAL DE COMERCIALIZACION SOCIEDAD ANONIMA',
            'CICSA',
            
            'S\\.?H\\.?$',  # SH, S.H.
            'S\\s+H$',  # S H
            
            'S\\.?A\\.?S\\.?$',  # SAS, S.A.S.
            
            'LTD',
            
            'S\\.?A\\.?I\\.?C\\.?A\\.?I\\.?$',  # SAICAI, S.A.I.C.A.I.
            'S\\.?A\\.?I\\.?C\\s+Y\\s+F\\.?$',  # SAICYF, S.A.I.C Y F., S.A.I.C.YF.
            'SAICYF$',
            'S\\.?A\\.?I\\.?C\\.?YF\\.?$'
        ]
        
        # Eliminar cada tipo de terminación
        for ending in society_endings:
            # Usar regex para eliminar la terminación al final de la cadena
            pattern = f'\\s*{ending}\\s*$'
            normalized = re.sub(pattern, '', normalized, flags=re.IGNORECASE)
            normalized = normalized.strip()
        
        return normalized

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
            # Obtener todos los clientes (sin límite para búsqueda)
            print(f"🔍 DEBUG: Obteniendo clientes para similitud con área: {area}")
            all_clients = self.get_clients(area=area, limit=1000)  # Límite alto para búsqueda
            print(f"🔍 DEBUG: Obtenidos {len(all_clients)} clientes para comparar")
            
            if not all_clients:
                print(f"⚠️  No hay clientes disponibles para comparar")
                return []
            
            import difflib
            
            # Normalizar el término de búsqueda
            razonsocial_normalized = self.normalize_company_name(razonsocial)
            print(f"🔍 DEBUG: Nombre normalizado para búsqueda: '{razonsocial}' → '{razonsocial_normalized}'")
            
            similar_clients = []
            
            print(f"🔍 DEBUG: Buscando similitud para '{razonsocial_normalized}' (umbral: {similarity_threshold})")
            
            for client in all_clients:
                if not client.razonsocial:
                    continue
                
                # Normalizar nombre del cliente
                client_name_normalized = self.normalize_company_name(client.razonsocial)
                
                if not client_name_normalized:
                    continue
                
                # Calcular similitud usando SequenceMatcher con nombres normalizados
                similarity = difflib.SequenceMatcher(None, razonsocial_normalized, client_name_normalized).ratio()
                
                # También buscar palabras clave con nombres normalizados
                search_words = set(razonsocial_normalized.split())
                client_words = set(client_name_normalized.split())
                word_overlap = len(search_words.intersection(client_words))
                word_similarity = word_overlap / max(len(search_words), len(client_words)) if search_words or client_words else 0
                
                # Combinar similitudes
                final_similarity = max(similarity, word_similarity)
                
                # Debug para mostrar comparaciones prometedoras
                if final_similarity > 0.3:  # Mostrar comparaciones prometedoras
                    print(f"🔍 DEBUG: '{client.razonsocial}' → '{client_name_normalized}' -> similitud: {similarity:.3f}, palabras: {word_similarity:.3f}, final: {final_similarity:.3f}")
                
                if final_similarity >= similarity_threshold:
                    similar_clients.append((client, final_similarity))
            
            # Ordenar por similitud (más similar primero)
            similar_clients.sort(key=lambda x: x[1], reverse=True)
            
            result = [client for client, similarity in similar_clients]
            print(f"🔍 Encontrados {len(result)} clientes similares a '{razonsocial}' con umbral {similarity_threshold}")
            
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