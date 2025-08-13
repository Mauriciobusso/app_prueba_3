import reflex as rx
from ..views.navbar import navbar
from ..components.components import table_certificados, table_familias, table_cotizaciones, session_keepalive, loading_spinner, loading_overlay
from ..backend.app_state import AppState
from ..styles.colors import Color
from ..styles.style import container_style
from ..utils import Cot


def certificados_view() -> rx.Component:
    """Vista de certificados - Estilo Bureau Veritas"""
    return rx.box(
        # Overlay de carga para inicialización del usuario
        loading_overlay(
            rx.cond(
                AppState.is_loading_user_initialization,
                "Inicializando usuario...",
                rx.cond(
                    AppState.is_loading_areas,
                    "Cargando áreas...",
                    rx.cond(
                        AppState.is_loading_roles,
                        "Cargando roles...",
                        rx.cond(
                            AppState.is_loading_data,
                            "Cargando certificados...",
                            "Cargando..."
                        )
                    )
                )
            ),
            AppState.is_loading_user_initialization | AppState.is_loading_areas | AppState.is_loading_roles | AppState.is_loading_data
        ),
        session_keepalive(),  # Mantener sesión activa
        navbar(title="Certificados"),
        rx.box(
            rx.vstack(
                rx.cond(
                    (AppState.certs.length() == 0) & (AppState.values["search_value"] == "") & ~AppState.is_loading_data,
                    rx.center(
                        rx.spinner(
                            size="3", 
                            color=Color.SECONDARY_BLUE.value,
                        ),
                        padding="60px",
                    ),
                    table_certificados(),
                ),
                spacing="6",
                width="100%",
            ),
            style=container_style,
            padding_top="84px",  # Account for fixed navbar (64px + padding)
        ),
        overflow_y="auto",
        width="100%",
        height="100vh",
        background_color="var(--color-background)",
        on_scroll=lambda: AppState.on_scroll_throttled(),
        on_mount=AppState.on_mount_certificados,
    )


def familias_view() -> rx.Component:
    """Vista de familias - Estilo Bureau Veritas"""
    return rx.box(
        # Overlay de carga para inicialización del usuario
        loading_overlay(
            rx.cond(
                AppState.is_loading_user_initialization,
                "Inicializando usuario...",
                rx.cond(
                    AppState.is_loading_areas,
                    "Cargando áreas...",
                    rx.cond(
                        AppState.is_loading_roles,
                        "Cargando roles...",
                        rx.cond(
                            AppState.is_loading_data,
                            "Cargando familias...",
                            "Cargando..."
                        )
                    )
                )
            ),
            AppState.is_loading_user_initialization | AppState.is_loading_areas | AppState.is_loading_roles | AppState.is_loading_data
        ),
        session_keepalive(),  # Mantener sesión activa
        navbar(title="Familias"),
        rx.box(
            rx.vstack(
                rx.cond(
                    (AppState.fams.length() == 0) & (AppState.values["search_value"] == "") & ~AppState.is_loading_data,
                    rx.center(
                        rx.spinner(
                            size="3", 
                            color=Color.SECONDARY_BLUE.value,
                        ),
                        padding="60px",
                    ),
                    table_familias(),
                ),
                spacing="6",
                width="100%",
            ),
            style=container_style,
            padding_top="84px",
        ),
        overflow_y="auto",
        width="100%",
        height="100vh",
        background_color="var(--color-background)",
        on_scroll=lambda: AppState.on_scroll_throttled(),
        on_mount=AppState.on_mount_familias,
    )


def cotizaciones_view() -> rx.Component:
    """Vista de cotizaciones - Estilo Bureau Veritas"""
    return rx.box(
        # Overlay de carga para inicialización del usuario
        loading_overlay(
            rx.cond(
                AppState.is_loading_user_initialization,
                "Inicializando usuario...",
                rx.cond(
                    AppState.is_loading_areas,
                    "Cargando áreas...",
                    rx.cond(
                        AppState.is_loading_roles,
                        "Cargando roles...",
                        rx.cond(
                            AppState.is_loading_data,
                            "Cargando cotizaciones...",
                            "Cargando..."
                        )
                    )
                )
            ),
            AppState.is_loading_user_initialization | AppState.is_loading_areas | AppState.is_loading_roles | AppState.is_loading_data
        ),
        session_keepalive(),  # Mantener sesión activa
        navbar(title="Cotizaciones"),
        rx.box(
            rx.vstack(
                rx.cond(
                    (AppState.cots.length() == 0) & (AppState.values["search_value"] == "") & ~AppState.is_loading_data,
                    rx.center(
                        rx.spinner(
                            size="3", 
                            color=Color.SECONDARY_BLUE.value,
                        ),
                        padding="60px",
                    ),
                    table_cotizaciones(),
                ),
                spacing="6",
                width="100%",
            ),
            style=container_style,
            padding_top="84px",
        ),
        overflow_y="auto",
        width="100%",
        height="100vh",
        background_color="var(--color-background)",
        on_scroll=lambda: AppState.on_scroll_throttled(),
        on_mount=AppState.on_mount_cotizaciones,
    )


def cotizacion_detalle_view() -> rx.Component:
    """Vista de detalle de una cotización específica - Estilo Bureau Veritas"""
    return rx.box(
        navbar(title="Detalle de Cotización"),
        rx.box(
            rx.vstack(
                # Botón de volver
                rx.link(
                    rx.button(
                        rx.icon("arrow-left", size=18),
                        "Volver a Cotizaciones",
                        variant="outline",
                        size="3",
                        style={
                            "background_color": "var(--color-surface)",
                            "border": "1px solid var(--accent-7)",
                            "color": "var(--accent-11)",
                            "_hover": {
                                "background_color": "var(--accent-3)",
                            },
                            "margin_bottom": "20px"
                        }
                    ),
                    href="/cotizaciones"
                ),
                
                # Tarjeta con detalles de la cotización
                rx.cond(
                    AppState.cotizacion_detalle.id != "",
                    rx.card(
                        rx.vstack(
                            # Título
                            rx.heading(
                                f"Cotización {AppState.cotizacion_detalle.num}-{AppState.cotizacion_detalle.year}",
                                size="6",
                                style={"color": "var(--accent-11)", "margin_bottom": "20px"}
                            ),
                            
                            # Grid con información principal
                            rx.grid(
                                # Número
                                rx.vstack(
                                    rx.text("Número:", weight="bold", style={"color": "var(--accent-11)"}),
                                    rx.text(f"{AppState.cotizacion_detalle.num}-{AppState.cotizacion_detalle.year}"),
                                    align="start",
                                    spacing="1"
                                ),
                                
                                # Cliente
                                rx.vstack(
                                    rx.text("Cliente:", weight="bold", style={"color": "var(--accent-11)"}),
                                    rx.text(AppState.cotizacion_detalle.client),
                                    align="start",
                                    spacing="1"
                                ),
                                
                                # Fecha
                                rx.vstack(
                                    rx.text("Fecha:", weight="bold", style={"color": "var(--accent-11)"}),
                                    rx.text(AppState.cotizacion_detalle_fecha_formateada),
                                    align="start",
                                    spacing="1"
                                ),
                                
                                # Estado
                                rx.vstack(
                                    rx.text("Estado:", weight="bold", style={"color": "var(--accent-11)"}),
                                    rx.text(AppState.cotizacion_detalle.status),
                                    align="start",
                                    spacing="1"
                                ),
                                
                                columns="2",
                                spacing="4",
                                width="100%"
                            ),
                            
                            # Enlaces de acción
                            rx.hstack(
                                rx.cond(
                                    AppState.cotizacion_detalle.drive_file_id != "",
                                    rx.link(
                                        rx.button(
                                            rx.icon("eye", size=18),
                                            "Ver en Drive",
                                            variant="solid",
                                            size="3",
                                            style={
                                                "background_color": Color.SECONDARY_BLUE.value,
                                                "color": Color.WHITE.value,
                                                "_hover": {
                                                    "background_color": Color.PRIMARY_BLUE.value,
                                                }
                                            }
                                        ),
                                        href=f"https://drive.google.com/file/d/{AppState.cotizacion_detalle.drive_file_id}/view?usp=drive_link",
                                        is_external=True
                                    ),
                                    rx.box()  # Elemento vacío si no hay drive_file_id
                                ),
                                spacing="3",
                                justify="start",
                                style={"margin_top": "30px"}
                            ),
                            
                            align="start",
                            spacing="4",
                            width="100%"
                        ),
                        style={
                            "background_color": Color.WHITE.value,
                            "border_radius": "8px",
                            "box_shadow": "0 2px 4px rgba(0,0,0,0.1)",
                            "padding": "30px",
                            "width": "100%",
                            "max_width": "800px"
                        }
                    ),
                    
                    # Mostrar spinner mientras se carga
                    rx.center(
                        rx.spinner(
                            size="3", 
                            color=Color.SECONDARY_BLUE.value,
                        ),
                        padding="60px",
                    )
                ),
                
                # Bloque PDF extraído
                rx.cond(
                    (AppState.cotizacion_detalle.drive_file_id != "") & (AppState.cotizacion_detalle.id != ""),
                    rx.box(
                        rx.heading("Datos extraídos del PDF", size="5", style={"margin_top": "32px", "color": Color.SECONDARY_BLUE.value}),
                        rx.cond(
                            AppState.cotizacion_detalle_pdf_error != "",
                            rx.text(f"Error al extraer PDF: {AppState.cotizacion_detalle_pdf_error}", color="red"),
                            rx.vstack(
                                rx.text("Metadata:", weight="bold", style={"margin_top": "10px", "color": "var(--accent-11)"}),
                                rx.code(AppState.cotizacion_detalle_pdf_metadata, language="json", width="100%", style={"font_size": "0.85rem", "background": Color.LIGHT_GREY.value}),
                                rx.text("Tablas:", weight="bold", style={"margin_top": "10px", "color": "var(--accent-11)"}),
                                rx.code(AppState.cotizacion_detalle_pdf_tablas, language="json", width="100%", style={"font_size": "0.85rem", "background": Color.LIGHT_GREY.value}),
                                rx.text("Condiciones:", weight="bold", style={"margin_top": "10px", "color": "var(--accent-11)"}),
                                rx.code(AppState.cotizacion_detalle_pdf_condiciones, language="text", width="100%", style={"font_size": "0.85rem", "background": Color.LIGHT_GREY.value})
                            )
                        ),
                        style={"background": Color.GRAY_50.value, "border_radius": "8px", "padding": "20px", "margin_top": "20px", "max_width": "800px", "width": "100%"}
                    ),
                    rx.fragment()
                ),
                
                spacing="6",
                width="100%",
                align="center"
            ),
            style=container_style,
            padding_top="84px"
        ),
        overflow_y="auto",
        width="100%",
        height="100vh",
        background_color="var(--color-background)"
    )                  