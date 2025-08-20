import reflex as rx
from dotenv import load_dotenv
import os
import asyncio

from .styles.style import *
from .components.react_oauth_google import GoogleOAuthProvider, GoogleLogin
from .views.authenticated import certificados_view, familias_view, cotizaciones_view, cotizacion_detalle_view
from .views.authenticated import cotizacion_new_view
from .backend.app_state import AppState

from .components.components import table_certificados, table_familias

from .utils import completar_con_ceros

# Cargar variables de entorno
load_dotenv()
CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")

# Cola para almacenar los cambios detectados en Firestore
firestore_queue = asyncio.Queue()

def theme_wrapper(children: list) -> rx.Component:
    """Wrapper component - Dark mode disabled for now."""
    return rx.box(
        *children,
        # class_name=rx.cond(AppState.dark_mode, "dark", ""),  # DISABLED FOR NOW
        class_name="",  # Always light mode for now
        style={
            "min_height": "100vh",
            "background_color": "var(--color-background)",
            "color": "var(--color-text)",
        }
    )

def index() -> rx.Component:
    """Página de inicio"""
    return theme_wrapper([
        rx.center(
            rx.vstack(
                rx.heading("Bienvenido", size="7"),
                rx.link("Ir a Cotizaciones", href="/cotizaciones"),
                spacing="4",
                align="center"
            ),
            height="100vh"
        )
    ])


def login_view() -> rx.Component:
    """Vista de login con Google OAuth"""
    return rx.center(
        rx.cond(
            AppState.is_loading_user_initialization,
            rx.vstack(
                rx.heading("Bienvenido", size="7"), ##Agregar mail
                rx.text(AppState.user_email),
                rx.spinner(size="3", color="blue"),
                spacing="4",
                align="center"
            ),
            rx.vstack(
                rx.heading("Iniciar Sesión", size="7"),
                GoogleLogin.create(
                    on_success=AppState.on_success,
                    on_error=lambda: rx.window_alert("Error en la autenticación")
                ),
                spacing="4",
                align="center"
            )
        ),
        height="100vh"
    )


def certificados() -> rx.Component:
    """Página de certificados"""
    return theme_wrapper([
        GoogleOAuthProvider.create(
            rx.cond(
                AppState.is_authenticated,
                certificados_view(),
                login_view()
            ),
            client_id=CLIENT_ID
        )
    ])

def familias() -> rx.Component:
    """Página de familias"""
    return theme_wrapper([
        GoogleOAuthProvider.create(
            rx.cond(
                AppState.is_authenticated,
                familias_view(),
                login_view()
            ),
            client_id=CLIENT_ID
        )
    ])

def cotizaciones() -> rx.Component:
    """Página de cotizaciones"""
    return theme_wrapper([
        GoogleOAuthProvider.create(
            rx.cond(
                AppState.is_authenticated,
                cotizaciones_view(),
                login_view()
            ),
            client_id=CLIENT_ID
        )
    ])


def cotizacion_detalle() -> rx.Component:
    """Página de detalle de cotización"""
    return theme_wrapper([
        GoogleOAuthProvider.create(
            rx.cond(
                AppState.is_authenticated,
                cotizacion_detalle_view(),
                login_view()
            ),
            client_id=CLIENT_ID
        )
    ])


# Configuración de la aplicación
app = rx.App(
    style=style,
    theme=rx.theme(
        appearance="inherit",  # Use system theme initially
        has_background=True,
        radius="medium",
        scaling="100%",
    ),
)
app.add_page(index, route="/")
app.add_page(login_view, route="/login")
app.add_page(certificados, route="/certificados", on_load=AppState.on_mount_certificados)
app.add_page(familias, route="/familias", on_load=AppState.on_mount_familias)
app.add_page(cotizaciones, route="/cotizaciones", on_load=AppState.on_mount_cotizaciones)
app.add_page(cotizacion_detalle, route="/cotizaciones/[cot_id]", on_load=AppState.cargar_cotizacion_detalle)
app.add_page(cotizacion_new_view, route="/cotizaciones/new", on_load=AppState.on_mount_cotizaciones)