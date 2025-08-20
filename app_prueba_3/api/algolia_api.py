"""
API de Algolia para búsquedas optimizadas
"""
import os
from typing import List, Dict, Any
from dotenv import load_dotenv

from algoliasearch.search.client import SearchClient

# Cargar variables de entorno desde .env
load_dotenv()
from dotenv import load_dotenv
import json

# Cargar variables de entorno
load_dotenv()

class AlgoliaAPI:
    def __init__(self):
        self.app_id = os.getenv("ALGOLIA_APP_ID")
        self.api_key = os.getenv("ALGOLIA_API_KEY")
        self.search_api_key = os.getenv("ALGOLIA_SEARCH_API_KEY")  # Solo para búsquedas (más seguro)
        
        if not self.app_id or not self.api_key:
            print("⚠️  Credenciales de Algolia no configuradas")
            self.client = None
            self.enabled = False
            return
            
        try:
            # Usar la clave de búsqueda para operaciones de búsqueda (más segura)
            self.search_key = self.search_api_key if self.search_api_key else self.api_key
            self.client = SearchClient(self.app_id, self.search_key)
            
            self.enabled = True
            print("✅ Algolia inicializado correctamente")
        except Exception as e:
            print(f"❌ Error al inicializar Algolia: {e}")
            self.client = None
            self.enabled = False

    async def search_cots(self, query: str, page: int = 0, hits_per_page: int = 20, area: str = "", filters: Dict = None) -> Dict:
        """Buscar cotizaciones en Algolia con paginación"""
        if not self.enabled:
            print("⚠️  Algolia no está habilitado")
            return {}
        
        try:
            print(f"🔍 Iniciando búsqueda en Algolia: '{query}', página: {page}")
            if area:
                print(f"🔍 Filtrando por área: {area}")
            if filters:
                print(f"🔍 Filtros adicionales: {filters}")
            
            from algoliasearch.search.client import SearchClientSync
            sync_client = SearchClientSync(self.app_id, self.search_key)
            
            # Agregar filtros si se proporcionan
            algolia_filters = []
            if area:
                algolia_filters.append(f"area:{area}")
            if filters:
                for key, value in filters.items():
                    algolia_filters.append(f"{key}:{value}")
            
            if algolia_filters:
                print(f"🔍 Filtros aplicados: {' AND '.join(algolia_filters)}")
            
            results = sync_client.search_single_index(
                index_name="cotizaciones", 
                search_params={
                    "query": query,
                    "page": page,
                    "hitsPerPage": hits_per_page,
                    **({} if not algolia_filters else {"filters": " AND ".join(algolia_filters)})
                }
            )
            
            print(f"🔍 Algolia encontró {results.nb_hits} cotizaciones para '{query}'")
            return {"hits": results.hits, "nbHits": results.nb_hits, "page": results.page, "nbPages": results.nb_pages, "hitsPerPage": results.hits_per_page}
                
        except Exception as e:
            print(f"❌ Error en búsqueda de Algolia (cotizaciones): {e}")
            return {}

    async def search_certs(self, query: str, page: int = 0, hits_per_page: int = 20, area: str = "", filters: Dict = None) -> Dict:
        """
        Busca certificados en Algolia con paginación
        """
        if not self.enabled:
            print("⚠️  Algolia no está habilitado, usando búsqueda local")
            return {}
            
        try:
            print(f"🔍 Iniciando búsqueda de certificados en Algolia: '{query}', página: {page}")
            if area:
                print(f"🔍 Filtrando por área: {area}")
            if filters:
                print(f"🔍 Filtros adicionales: {filters}")
            
            from algoliasearch.search.client import SearchClientSync
            sync_client = SearchClientSync(self.app_id, self.search_key)
            
            # Agregar filtros si se proporcionan
            algolia_filters = []
            if area:
                algolia_filters.append(f"area:{area}")
            if filters:
                for key, value in filters.items():
                    algolia_filters.append(f"{key}:{value}")
            
            if algolia_filters:
                print(f"🔍 Filtros aplicados: {' AND '.join(algolia_filters)}")
            
            results = sync_client.search_single_index(
                index_name="certificados", 
                search_params={
                    "query": query,
                    "page": page,
                    "hitsPerPage": hits_per_page,
                    **({} if not algolia_filters else {"filters": " AND ".join(algolia_filters)})
                }
            )
            
            print(f"🔍 Algolia encontró {results.nb_hits} certificados para '{query}'")
            return {"hits": results.hits, "nbHits": results.nb_hits, "page": results.page, "nbPages": results.nb_pages, "hitsPerPage": results.hits_per_page}
            
        except Exception as e:
            print(f"❌ Error en búsqueda de Algolia (certificados): {e}")
            return {}
    
    async def search_fams(self, query: str, page: int = 0, hits_per_page: int = 20, area: str = "", filters: Dict = None) -> Dict:
        """
        Busca familias en Algolia con paginación
        """
        if not self.enabled:
            print("⚠️  Algolia no está habilitado, usando búsqueda local")
            return {}
            
        try:
            print(f"🔍 Iniciando búsqueda de familias en Algolia: '{query}', página: {page}")
            if area:
                print(f"🔍 Filtrando por área: {area}")
            if filters:
                print(f"🔍 Filtros adicionales: {filters}")
            
            from algoliasearch.search.client import SearchClientSync
            sync_client = SearchClientSync(self.app_id, self.search_key)
            
            # Agregar filtros si se proporcionan
            algolia_filters = []
            if area:
                algolia_filters.append(f"area:{area}")
            if filters:
                for key, value in filters.items():
                    algolia_filters.append(f"{key}:{value}")
            
            if algolia_filters:
                print(f"🔍 Filtros aplicados: {' AND '.join(algolia_filters)}")
            
            results = sync_client.search_single_index(
                index_name="familias", 
                search_params={
                    "query": query,
                    "page": page,
                    "hitsPerPage": hits_per_page,
                    **({} if not algolia_filters else {"filters": " AND ".join(algolia_filters)})
                }
            )
            
            print(f"🔍 Algolia encontró {results.nb_hits} familias para '{query}'")
            return {"hits": results.hits, "nbHits": results.nb_hits, "page": results.page, "nbPages": results.nb_pages, "hitsPerPage": results.hits_per_page}
            
        except Exception as e:
            print(f"❌ Error en búsqueda de Algolia (familias): {e}")
            return {}
    
    async def search_clients(self, query: str, page: int = 0, hits_per_page: int = 20, area: str = "", filters: Dict = None) -> Dict:
        """
        Busca clientes en Algolia con paginación
        """
        if not self.enabled:
            print("⚠️  Algolia no está habilitado, usando búsqueda local")
            return {}
            
        try:
            print(f"🔍 Iniciando búsqueda de clientes en Algolia: '{query}', página: {page}")
            if area:
                print(f"🔍 Filtrando por área: {area}")
            if filters:
                print(f"🔍 Filtros adicionales: {filters}")
            
            from algoliasearch.search.client import SearchClientSync
            sync_client = SearchClientSync(self.app_id, self.search_key)
            
            # Agregar filtros si se proporcionan
            algolia_filters = []
            if area:
                algolia_filters.append(f"area:{area}")
            if filters:
                for key, value in filters.items():
                    algolia_filters.append(f"{key}:{value}")
            
            if algolia_filters:
                print(f"🔍 Filtros aplicados: {' AND '.join(algolia_filters)}")
            
            results = sync_client.search_single_index(
                index_name="clientes", 
                search_params={
                    "query": query,
                    "page": page,
                    "hitsPerPage": hits_per_page,
                    **({} if not algolia_filters else {"filters": " AND ".join(algolia_filters)})
                }
            )
            
            print(f"🔍 Algolia encontró {results.nb_hits} clientes para '{query}'")
            return {"hits": results.hits, "nbHits": results.nb_hits, "page": results.page, "nbPages": results.nb_pages, "hitsPerPage": results.hits_per_page}
            
        except Exception as e:
            print(f"❌ Error en búsqueda de Algolia (clientes): {e}")
            return {}
    
    def index_data(self, index_name: str, records: List[Dict]) -> bool:
        """
        Indexa datos en Algolia usando el cliente administrativo.
        """
        if not self.enabled:
            print("⚠️ Algolia deshabilitado - no se indexarán datos")
            return False
            
        if not records:
            print("⚠️ No hay registros para indexar")
            return False
            
        try:
            # Para indexar necesitamos la API key con permisos de escritura
            admin_client = SearchClient(self.app_id, self.api_key)
            
            # Indexar en lotes usando save_objects directamente
            batch_size = 1000
            for i in range(0, len(records), batch_size):
                batch = records[i:i + batch_size]
                # Usar save_objects directamente en el cliente, pasando el índice como parámetro
                # Nota: Algunas versiones de algoliasearch pueden devolver un coroutine
                # Si save_objects devuelve coroutine, necesitamos await en contexto async
                result = admin_client.save_objects(index_name, batch, {'autoGenerateObjectIDIfNotExist': True})
                # Si es un coroutine, imprimir warning y continuar
                if hasattr(result, '__await__'):
                    print("⚠️ save_objects devolvió coroutine - versión de Algolia requiere await")
                
            print(f"✅ {len(records)} registros indexados en '{index_name}'")
            return True
            
        except Exception as e:
            print(f"❌ Error al indexar datos en Algolia: {e}")
            return False

    async def list_index(self, index_name: str, page: int = 0, hits_per_page: int = 100) -> Dict:
        """
        Lista registros de un índice de Algolia (útil para obtener áreas/roles u otros índices pequeños).
        """
        if not self.enabled:
            return {}

        try:
            from algoliasearch.search.client import SearchClientSync
            sync_client = SearchClientSync(self.app_id, self.search_key)

            results = sync_client.search_single_index(
                index_name=index_name,
                search_params={
                    "query": "",
                    "page": page,
                    "hitsPerPage": hits_per_page,
                }
            )

            return {"hits": results.hits, "nbHits": results.nb_hits, "page": results.page, "nbPages": results.nb_pages, "hitsPerPage": results.hits_per_page}
        except Exception as e:
            print(f"❌ Error listando índice {index_name} en Algolia: {e}")
            return {}

# Instancia global
algolia_api = AlgoliaAPI()
