# App Prueba 3 - Sistema de Gestión con Reflex

Una aplicación web desarrollada con [Reflex](https://reflex.dev/) para la gestión de certificaciones, familias y cotizaciones, integrada con Firebase Firestore y búsquedas optimizadas con Algolia.

## 🚀 Características

- **Autenticación Google OAuth**: Sistema de login seguro con Google
- **Gestión de datos**: Manejo de certificaciones, familias y cotizaciones
- **Búsqueda avanzada**: Integración con Algolia para búsquedas rápidas y eficientes
- **Filtrado dinámico**: Filtros por área, cliente y otros criterios
- **Interfaz responsive**: Diseño adaptable con componentes Reflex
- **Scroll infinito**: Carga progresiva de resultados (en desarrollo)
- **Base de datos**: Firebase Firestore como backend

## 🛠️ Tecnologías

- **Backend**: Python 3.11+ con Reflex Framework
- **Frontend**: Reflex (React + Python)
- **Base de datos**: Firebase Firestore
- **Búsqueda**: Algolia Search
- **Autenticación**: Google OAuth 2.0
- **Estilos**: CSS-in-Python con Reflex

## 📦 Instalación

### Prerrequisitos

- Python 3.11 o superior
- Node.js (para dependencias de frontend)
- Cuenta de Firebase
- Cuenta de Algolia (opcional, para búsquedas avanzadas)

### Configuración del entorno

1. **Clonar el repositorio**:
```bash
git clone <URL_DEL_REPOSITORIO>
cd app_prueba_3
```

2. **Crear y activar entorno virtual**:
```bash
python -m venv .venv
source .venv/bin/activate  # En Windows: .venv\Scripts\activate
```

3. **Instalar dependencias**:
```bash
pip install -r requirements.txt
```

4. **Configurar variables de entorno**:
Crear un archivo `.env` en la raíz del proyecto:
```env
# Firebase
FIREBASE_PROJECT_ID=tu-proyecto-firebase
GOOGLE_CLIENT_ID=tu-client-id-google

# Algolia (opcional)
ALGOLIA_APP_ID=tu-algolia-app-id
ALGOLIA_API_KEY=tu-algolia-api-key
ALGOLIA_SEARCH_API_KEY=tu-algolia-search-key
```

5. **Configurar Firebase**:
- Colocar el archivo `serviceAccountKey.json` en la carpeta `app_prueba_3/`
- Configurar las reglas de Firestore según tu estructura de datos

## 🚀 Uso

### Desarrollo

```bash
reflex run
```

La aplicación estará disponible en:
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000

### Producción

```bash
reflex run --env prod
```

## 📁 Estructura del proyecto

```
app_prueba_3/
├── app_prueba_3/
│   ├── __init__.py
│   ├── app_prueba_3.py          # Aplicación principal
│   ├── utils.py                 # Utilidades y modelos de datos
│   ├── api/
│   │   ├── firestore_api.py     # API de Firebase Firestore
│   │   ├── algolia_api.py       # API de Algolia Search
│   │   └── algolia_utils.py     # Utilidades de Algolia
│   ├── backend/
│   │   └── app_state.py         # Estado global de la aplicación
│   ├── components/
│   │   └── components.py        # Componentes de UI reutilizables
│   ├── styles/
│   │   ├── colors.py           # Paleta de colores
│   │   └── style.py            # Estilos CSS
│   └── views/
│       ├── authenticated.py    # Vistas para usuarios autenticados
│       └── navbar.py           # Barra de navegación
├── assets/                     # Recursos estáticos
├── .env                        # Variables de entorno (no incluido en Git)
├── requirements.txt            # Dependencias Python
├── rxconfig.py                 # Configuración de Reflex
└── README.md
```

## 🔧 Configuración

### Firebase Firestore

La aplicación utiliza las siguientes colecciones:
- `users`: Información de usuarios y permisos
- `certificados`: Datos de certificaciones
- `familias`: Información de familias/empresas
- `cotizaciones`: Datos de cotizaciones
- `roles`: Roles de usuario
- `areas`: Áreas de trabajo

### Algolia Search

Índices configurados:
- `certificados`: Búsqueda en certificaciones
- `familias`: Búsqueda en familias
- `cotizaciones`: Búsqueda en cotizaciones

## 📋 Funcionalidades

### Autenticación
- Login con Google OAuth
- Gestión de sesiones persistentes
- Control de acceso por roles y áreas

### Gestión de datos
- **Certificaciones**: Visualización, filtrado y búsqueda de certificados
- **Familias**: Gestión de familias/empresas con filtros avanzados
- **Cotizaciones**: Manejo de cotizaciones con búsqueda optimizada

### Búsqueda y filtrado
- Búsqueda en tiempo real con Algolia
- Filtros por área de trabajo
- Filtros por cliente
- Ordenamiento personalizable

## 🚧 Desarrollo en progreso

- [ ] Implementación completa del scroll infinito
- [ ] Paginación optimizada
- [ ] Carga de más resultados bajo demanda
- [ ] Mejoras en el rendimiento de búsquedas

## 🤝 Contribución

1. Fork del proyecto
2. Crear rama para feature (`git checkout -b feature/nueva-funcionalidad`)
3. Commit de cambios (`git commit -am 'Agregar nueva funcionalidad'`)
4. Push a la rama (`git push origin feature/nueva-funcionalidad`)
5. Crear Pull Request

## 📄 Licencia

Este proyecto está bajo la licencia MIT. Ver `LICENSE` para más detalles.

## 🆘 Soporte

Para soporte y preguntas, por favor abrir un issue en el repositorio de GitHub.

---

**Versión**: 1.0.0  
**Última actualización**: Agosto 2025
