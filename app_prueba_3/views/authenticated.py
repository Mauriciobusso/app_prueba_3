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
                    AppState.certs_show.length() == 0,
                    rx.vstack(
                        rx.cond(
                            AppState.certs.length() == 0,
                            rx.spinner(size = "2", 
                                    loading = True,
                                    color_scheme="white",   
                            ),
                            rx.button("Cargar Certificados",      
                                on_click = AppState.update_certs_show
                            ),
                        ),
                        spacing="2"
                    ),
                    table_certificados(),
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
    )

def familias_view() -> rx.Component:
    """Vista de usuario autenticado"""
    return rx.box(
        navbar(title="Familias"),
        rx.hstack(
            rx.vstack(
                rx.cond(
                    AppState.fams_show.length() == 0,
                    rx.vstack(
                        rx.cond(
                            AppState.fams.length() == 0,
                            rx.spinner(size = "2", 
                                    loading = True,
                                    color_scheme="white",   
                            ),
                            rx.button("Cargar Familias",      
                                on_click = AppState.update_fams_show
                            ),
                        ),
                        spacing="2"
                    ),
                    table_familias(),
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
    )

def cotizaciones_view() -> rx.Component:
    """Vista de usuario autenticado"""
    return rx.box(
        navbar(title="Cotizaciones"),
        rx.hstack(
            rx.vstack(
                rx.cond(
                    AppState.cots_show.length() == 0,
                    rx.vstack(
                        rx.cond(
                            AppState.cots.length() == 0,
                            rx.spinner(size = "2", 
                                    loading = True,
                                    color_scheme="white",   
                            ),
                            rx.button("Cargar Cotizaciones",      
                                on_click = AppState.update_cots_show,
                                variant="soft"
                            ),
                        ),
                        spacing="2"
                    ),
                    table_cotizaciones(),
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
    )