import reflex as rx
from ..views.navbar import navbar
from ..components.components import table_certificados, table_familias, table_cotizaciones

from ..backend.app_state import AppState


def certificados_view() -> rx.Component:
    """Vista de usuario autenticado"""
    return rx.box(
        navbar(title="02 Certificados"),
        rx.hstack(
            rx.vstack(
                rx.cond(
                    AppState.certs.length() == 0,
                    rx.spinner(size = "2", 
                            loading = True,
                            color="white",   
                    ),
                    table_certificados(),  # Siempre mostrar la tabla cuando hay datos cargados
                ),
                width="100%",
            ),

            padding_top="4em",
            spacing="4",
            padding="2rem",
            align_items="start",
            align="end",
            justify_content="end",
            justify="end",
            height="100%",
        ),
        overflow_y="auto",
        width="100%",
        height="100vh",  # Ocupa toda la altura de la pantalla
        padding_top="0.5em",
        display="flex",  # Habilita flexbox
        flex_direction="column",
        on_scroll=lambda: AppState.on_scroll_throttled(),  # Scroll infinito con throttling
    )

def familias_view() -> rx.Component:
    """Vista de usuario autenticado"""
    return rx.box(
        navbar(title="Familias"),
        rx.hstack(
            rx.vstack(
                rx.cond(
                    AppState.fams.length() == 0,
                    rx.spinner(size = "2", 
                            loading = True,
                            color_scheme="white",   
                    ),
                    table_familias(),  # Siempre mostrar la tabla cuando hay datos cargados
                ),
                width="100%",
            ),

            padding_top="4em",
            spacing="4",
            padding="2rem",
            align_items="start",
            align="end",
            justify_content="end",
            justify="end",
            height="100%",
        ),
        overflow_y="auto",
        width="100%",
        height="100vh",  # Ocupa toda la altura de la pantalla
        padding_top="0.5em",
        display="flex",  # Habilita flexbox
        flex_direction="column",
        on_scroll=lambda: AppState.on_scroll_throttled(),  # Scroll infinito con throttling
    )

def cotizaciones_view() -> rx.Component:
    """Vista de usuario autenticado"""
    return rx.box(
        navbar(title="Cotizaciones"),
        rx.hstack(
            rx.vstack(
                rx.cond(
                    AppState.cots.length() == 0,
                    rx.spinner(size = "2", 
                            loading = True,
                            color_scheme="white",   
                    ),
                    table_cotizaciones(),  # Siempre mostrar la tabla cuando hay datos cargados
                ),
                width="100%",
            ),

            padding_top="4em",
            spacing="4",
            padding="2rem",
            align_items="start",
            align="end",
            justify_content="end",
            justify="end",
            height="100%",
        ),
        overflow_y="auto",
        width="100%",
        height="100vh",  # Ocupa toda la altura de la pantalla
        padding_top="0.5em",
        display="flex",  # Habilita flexbox
        flex_direction="column",
        on_scroll=lambda: AppState.on_scroll_throttled(),  # Scroll infinito con throttling
    )