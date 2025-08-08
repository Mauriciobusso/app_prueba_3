import reflex as rx
from dotenv import load_dotenv
import os
import asyncio

from .styles.style import *
from .components.react_oauth_google import GoogleOAuthProvider, GoogleLogin
from .views.authenticated import certificados_view, familias_view, cotizaciones_view
from .backend.app_state import AppState

from .components.components import table_certificados, table_familias

from .utils import completar_con_ceros

# Cargar variables de entorno
load_dotenv()
CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")

# Cola para almacenar los cambios detectados en Firestore
firestore_queue = asyncio.Queue()

def index() -> rx.Component:
    """Página de inicio"""
    return rx.center(
        rx.vstack(
            rx.heading("Bienvenido", size="7"),
            rx.link("Ir a página protegida", href="/certificados"),
            spacing="4",
            align="center"
        ),
        height="100vh"
    )


def login_view() -> rx.Component:
    """Página de inicio de sesión"""
    return rx.center(
        GoogleLogin.create(on_success=AppState.on_success),
        height="100vh"
    )


def certificados() -> rx.Component:
    """Página protegida"""
    return GoogleOAuthProvider.create(
        rx.cond(
            AppState.is_authenticated,
            certificados_view(),
            login_view()
        ),
        client_id=CLIENT_ID
    )

def familias() -> rx.Component:
    """Página de familias"""
    return GoogleOAuthProvider.create(
        rx.cond(
            AppState.is_authenticated,
            familias_view(),
            login_view()
        ),
        client_id=CLIENT_ID
    )

def cotizaciones() -> rx.Component:
    """Página de familias"""
    return GoogleOAuthProvider.create(
        rx.cond(
            AppState.is_authenticated,
            cotizaciones_view(),
            login_view()
        ),
        client_id=CLIENT_ID
    )


# Configuración de la aplicación
app = rx.App(
    style=style,
)
app.add_page(index, route="/")
app.add_page(login_view, route="/login")
app.add_page(certificados, route="/certificados", on_load=AppState.on_mount_certificados)
app.add_page(familias, route="/familias", on_load=AppState.on_mount_familias)
app.add_page(cotizaciones, route="/cotizaciones", on_load=AppState.on_mount_cotizaciones)