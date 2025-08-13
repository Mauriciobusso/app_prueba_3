# Sistema de Gestión de Sesiones - Documentación

## Descripción General

El sistema implementa una **sesión interna persistente** que no depende de la validez del token de Google OAuth, manteniendo al usuario autenticado hasta que:

1. **Cierre sesión manualmente**
2. **No tenga áreas asignadas** (validación de negocio)

## Componentes Principales

### 1. Variables de Estado (`app_state.py`)

```python
session_internal: bool = rx.LocalStorage(False)  # Sesión interna independiente
last_activity: float = rx.LocalStorage(0.0)      # Timestamp de última actividad
```

### 2. Lógica de Autenticación Modificada

**`is_authenticated()` - Nueva implementación:**

- ✅ **Prioridad a sesión interna**: Si existe `session_internal = True`, mantener autenticado
- ✅ **Validación de áreas**: Verifica que el usuario tenga áreas asignadas
- ✅ **Fallback a Google**: Solo usa token de Google para crear sesión interna inicial
- ✅ **Actualización de actividad**: Cada verificación actualiza `last_activity`

### 3. Ciclo de Vida de la Sesión

#### **Inicio de Sesión:**
1. Usuario se autentica con Google OAuth
2. `on_success()` crea `session_internal = True`
3. `initialize_user()` verifica áreas asignadas
4. Si sin áreas → `clear_session()` automático

#### **Mantenimiento de Sesión:**
1. **Keepalive automático**: Script JS hace ping cada 5 minutos
2. **Actualización por actividad**: Búsquedas, cambio de área, etc.
3. **Validación continua**: Cada `is_authenticated()` verifica áreas

#### **Fin de Sesión:**
1. **Manual**: Usuario hace clic en "Cerrar sesión"
2. **Automático**: Usuario pierde áreas asignadas
3. **Limpieza completa**: `session_internal = False`

## Funciones Clave

### `update_activity()`
```python
async def update_activity(self):
    if self.session_internal:
        self.last_activity = time.time()
```
- Se llama automáticamente en acciones del usuario
- Mantiene registro de actividad

### `check_user_areas()`
```python
async def check_user_areas(self):
    if not self.user_data.areas_names:
        await self.logout()
        return False
```
- Valida áreas asignadas
- Cierra sesión si no tiene áreas

### Endpoint Keepalive
```python
@rx.api(route="/api/keepalive", methods=["POST"])
async def keepalive_endpoint():
    return {"status": "ok", "timestamp": time.time()}
```
- Recibe pings periódicos del frontend
- Mantiene evidencia de actividad

## Componentes de UI

### `session_keepalive()`
```javascript
setInterval(() => {
    if (localStorage.getItem('session_internal') === 'true') {
        fetch('/api/keepalive', {method: 'POST'});
    }
}, 300000); // 5 minutos
```

### `session_status_indicator()`
- Muestra estado visual de la sesión
- ✅ "Sesión activa" o ❌ "Sin sesión"

## Beneficios del Sistema

✅ **Sesión persistente**: No se pierde por tokens expirados
✅ **Validación de negocio**: Control granular por áreas
✅ **Experiencia fluida**: Usuario no necesita re-autenticarse
✅ **Seguridad**: Validaciones automáticas continuas
✅ **Observabilidad**: Logs detallados de estado de sesión

## Casos de Uso Cubiertos

1. **Token de Google expira** → Sesión interna mantiene acceso
2. **Usuario pierde áreas** → Cierre automático inmediato
3. **Sesión larga** → Keepalive mantiene actividad
4. **Cierre manual** → Limpieza completa de sesión
5. **Recarga de página** → Restauración desde LocalStorage

## Monitoreo

Los logs incluyen:
- `✅ Sesión interna válida para: {email}`
- `⏰ Token de Google expirado - manteniendo sesión interna`
- `❌ Usuario sin áreas asignadas - cerrando sesión`
- `🔄 Keepalive ping recibido`

## Configuración

El sistema está **habilitado por defecto** y no requiere configuración adicional. Los intervalos se pueden ajustar:

- **Keepalive**: 5 minutos (300000ms)
- **Verificación de áreas**: En cada acción del usuario
