import reflex as rx
from ..views.navbar import navbar
from ..components.components import table_certificados, table_familias, table_cotizaciones, session_keepalive
from ..backend.app_state import AppState
from ..styles.colors import Color
from ..styles.style import container_style
from ..utils import Cot


def certificados_view() -> rx.Component:
    """Vista de certificados - Estilo Bureau Veritas"""
    return rx.box(
        session_keepalive(),  # Mantener sesión activa
        navbar(title="Certificados"),
        rx.box(
            rx.vstack(
                rx.cond(
                    (AppState.certs.length() == 0) & (AppState.values["search_value"] == ""),
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
        navbar(title="Familias"),
        rx.box(
            rx.vstack(
                rx.cond(
                    (AppState.fams.length() == 0) & (AppState.values["search_value"] == ""),
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
        navbar(title="Cotizaciones"),
        rx.box(
            rx.vstack(
                rx.cond(
                    (AppState.cots.length() == 0) & (AppState.values["search_value"] == ""),
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
                                
                                # Fecha de Envío
                                rx.vstack(
                                    rx.text("Fecha de Envío:", weight="bold", style={"color": "var(--accent-11)"}),
                                    rx.cond(
                                        AppState.cotizacion_detalle.enviada_fecha != "",
                                        rx.text(AppState.cotizacion_detalle.enviada_fecha),
                                        rx.text("No enviada")
                                    ),
                                    align="start",
                                    spacing="1"
                                ),
                                
                                # Fecha de Paso a Facturar
                                rx.vstack(
                                    rx.text("Fecha de Paso a Facturar:", weight="bold", style={"color": "var(--accent-11)"}),
                                    rx.cond(
                                        AppState.cotizacion_detalle.facturada_fecha != "",
                                        rx.text(AppState.cotizacion_detalle.facturada_fecha),
                                        rx.text("No facturada")
                                    ),
                                    align="start",
                                    spacing="1"
                                ),
                                
                                # Nombre
                                rx.vstack(
                                    rx.text("Nombre:", weight="bold", style={"color": "var(--accent-11)"}),
                                    rx.cond(
                                        AppState.cotizacion_detalle.nombre != "",
                                        rx.text(AppState.cotizacion_detalle.nombre),
                                        rx.text("No especificado")
                                    ),
                                    align="start",
                                    spacing="1"
                                ),
                                
                                # Email
                                rx.vstack(
                                    rx.text("Email:", weight="bold", style={"color": "var(--accent-11)"}),
                                    rx.cond(
                                        AppState.cotizacion_detalle.email != "",
                                        rx.text(AppState.cotizacion_detalle.email),
                                        rx.text("No especificado")
                                    ),
                                    align="start",
                                    spacing="1"
                                ),
                                
                                columns="2",
                                spacing="4",
                                width="100%"
                            ),
                            
                            # Sección de familias
                            rx.vstack(
                                rx.text("Familias:", weight="bold", style={"color": "var(--accent-11)", "margin_top": "20px"}),
                                rx.cond(
                                    AppState.cotizacion_detalle.familys.length() > 0,
                                    rx.vstack(
                                        rx.foreach(
                                            AppState.cotizacion_detalle.familys,
                                            lambda fam: rx.box(
                                                rx.text(f"• {fam.family} - {fam.product}", style={"margin": "5px 0"}),
                                                width="100%"
                                            )
                                        ),
                                        align="start",
                                        width="100%"
                                    ),
                                    rx.text("No hay familias asociadas", style={"font_style": "italic", "color": "gray"})
                                ),
                                align="start",
                                width="100%",
                                spacing="2"
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
                                
                                rx.link(
                                    rx.button(
                                        rx.icon("external-link", size=18),
                                        "Abrir en Panel",
                                        variant="outline",
                                        size="3",
                                        style={
                                            "border": f"1px solid {Color.SECONDARY_BLUE.value}",
                                            "color": Color.SECONDARY_BLUE.value,
                                            "_hover": {
                                                "background_color": Color.LIGHT_GREY.value,
                                            }
                                        }
                                    ),
                                    href=f"https://panel.bvarg.com.ar/app/cotizaciones/{AppState.cotizacion_detalle.id}",
                                    is_external=True
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
                
                spacing="6",
                width="100%",
                align="center"
            ),
            style=container_style,
            padding_top="84px",
        ),
        overflow_y="auto",
        width="100%",
        height="100vh",
        background_color="var(--color-background)",
    )