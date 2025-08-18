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
                                # Botón para reprocesar PDF
                                rx.button(
                                    rx.icon("refresh-cw", size=18),
                                    "Reprocesar PDF",
                                    variant="outline",
                                    size="3",
                                    on_click=AppState.extraer_pdf_cotizacion_detalle,
                                    style={
                                        "border": "1px solid var(--accent-7)",
                                        "color": "var(--accent-11)",
                                        "background_color": "var(--color-surface)",
                                        "_hover": {"background_color": "var(--accent-3)"}
                                    }
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
                
                # Plantilla formateada (similar a la imagen adjunta)
                rx.cond(
                    AppState.cotizacion_detalle.id != "",
                    rx.box(
                        # Header superior derecha: Fecha y N° Cotización
                        rx.vstack(
                            rx.text(
                                f"Fecha: {AppState.cotizacion_detalle_fecha_formateada}",
                                size="2",
                                weight="medium",
                                align="right",
                            ),
                            rx.text(
                                f"N° Cotización: BVE N° {AppState.cotizacion_detalle.num}/{AppState.cotizacion_detalle.year}",
                                size="2",
                                weight="medium",
                                align="right",
                            ),
                            align="end",
                            width="100%",
                        ),
                        rx.box(height="1px", width="100%", background_color="var(--gray-6)", margin_y="10px"),

                        # Bloque de datos de cabecera
                        rx.vstack(
                            rx.hstack(
                                rx.text("Empresa:", weight="bold"),
                                rx.text(AppState.cotizacion_detalle.client),
                                spacing="2",
                            ),
                            rx.hstack(
                                rx.text("At Sr./Sra.:", weight="bold"),
                                rx.text(AppState.cotizacion_detalle.nombre),
                                spacing="2",
                            ),
                            rx.hstack(
                                rx.text("Consultora:", weight="bold"),
                                rx.text(AppState.cotizacion_detalle.consultora),
                                spacing="2",
                            ),
                            rx.hstack(
                                rx.text("Facturar a:", weight="bold"),
                                rx.text(AppState.cotizacion_detalle.facturar),
                                spacing="2",
                            ),
                            rx.hstack(
                                rx.text("Mail Receptor:", weight="bold"),
                                rx.text(AppState.cotizacion_detalle.email),
                                spacing="2",
                            ),
                            spacing="1",
                            margin_top="6px",
                        ),

                        rx.box(height="1px", width="100%", background_color="var(--gray-6)", margin_y="12px"),

                        # Título central
                        rx.center(
                            rx.text(
                                "CERTIFICACIÓN DE PRODUCTO SEGÚN RESOLUCIÓN M.P. S.C. N° 16/25",
                                weight="bold",
                                size="3",
                            ),
                            padding_y="6px",
                        ),

                        # Sección: DESCRIPCIÓN DE PRODUCTOS + Cantidad de Familias
                        rx.box(
                            rx.hstack(
                                rx.text("DESCRIPCIÓN DE PRODUCTOS", weight="bold"),
                                rx.spacer(),
                                rx.text(
                                    f"CANTIDAD DE FAMILIAS: {AppState.cotizacion_detalle_familys_count}",
                                    weight="bold",
                                ),
                                align="center",
                                width="100%",
                                padding_y="8px",
                                style={"border": "1px solid var(--gray-7)", "background": "var(--gray-3)", "padding_left": "10px", "padding_right": "10px"}
                            ),
                            # Lista de productos extraídos del PDF
                            rx.vstack(
                                rx.cond(
                                    AppState.cotizacion_detalle_productos_count > 0,
                                    rx.foreach(
                                        AppState.cotizacion_detalle_descripcion_productos,
                                        lambda p: rx.text(
                                            p["descripcion"],
                                            size="2",
                                            style={"padding": "6px 10px", "border_bottom": "1px solid var(--gray-6)"}
                                        )
                                    ),
                                    # Fallback: usar familias mapeadas
                                    rx.cond(
                                        AppState.cotizacion_detalle_familys_count > 0,
                                        rx.foreach(
                                            AppState.cotizacion_detalle.familys,
                                            lambda f: rx.text(
                                                f"{f.product} (FLIA {f.family})",
                                                size="2",
                                                style={"padding": "6px 10px", "border_bottom": "1px solid var(--gray-6)"}
                                            )
                                        ),
                                        rx.text("Sin productos disponibles", color="var(--gray-10)", style={"padding": "10px"})
                                    )
                                ),
                                width="100%",
                                style={"border_left": "1px solid var(--gray-7)", "border_right": "1px solid var(--gray-7)", "border_bottom": "1px solid var(--gray-7)"}
                            ),
                            margin_top="10px",
                        ),

                        # Sección: DESCRIPCIÓN DE TRABAJOS
                        rx.box(
                            rx.hstack(
                                rx.text("DESCRIPCIÓN DE TRABAJOS", weight="bold"),
                                rx.spacer(),
                                rx.hstack(
                                    rx.text("CANTIDAD", weight="bold"),
                                    rx.text("PRECIO", weight="bold", margin_left="30px"),
                                    spacing="6",
                                ),
                                align="center",
                                width="100%",
                                padding_y="8px",
                                style={"border": "1px solid var(--gray-7)", "background": "var(--gray-3)", "padding_left": "10px", "padding_right": "10px"}
                            ),
                            # Tabla de trabajos extraídos del PDF
                            rx.vstack(
                                rx.cond(
                                    AppState.cotizacion_detalle_trabajos_count > 0,
                                    rx.foreach(
                                        AppState.cotizacion_detalle_descripcion_trabajos,
                                        lambda t: rx.hstack(
                                            rx.text(
                                                t["descripcion"],
                                                size="2",
                                                style={"flex": "1", "padding": "6px"}
                                            ),
                                            rx.text(
                                                t["cantidad"],
                                                size="2",
                                                align="center",
                                                style={"min_width": "80px", "padding": "6px"}
                                            ),
                                            rx.text(
                                                t["precio"],
                                                size="2",
                                                align="right",
                                                style={"min_width": "100px", "padding": "6px"}
                                            ),
                                            width="100%",
                                            align="center",
                                            style={"border_bottom": "1px solid var(--gray-6)"}
                                        )
                                    ),
                                    rx.text("Sin trabajos disponibles", color="var(--gray-9)", style={"padding": "10px"})
                                ),
                                width="100%",
                                style={"border_left": "1px solid var(--gray-7)", "border_right": "1px solid var(--gray-7)", "border_bottom": "1px solid var(--gray-7)"}
                            ),
                            margin_top="10px",
                        ),

                        # Condiciones (texto extraído)
                        rx.box(
                            rx.text("Condiciones:", weight="bold", margin_top="12px"),
                            rx.text(AppState.cotizacion_detalle_pdf_condiciones, size="2", style={"white_space": "pre-wrap"}),
                            margin_top="10px",
                        ),

                        # Footer con revisión
                        rx.hstack(
                            rx.text("Néstor Luis Quintela – Gerente Certificación de Productos", size="1", color="var(--gray-10)"),
                            rx.spacer(),
                            rx.text(f"Rev.: {AppState.cotizacion_detalle.rev}", size="1", color="var(--gray-10)"),
                            width="100%",
                            margin_top="16px",
                        ),

                        style={
                            "background_color": Color.WHITE.value,
                            "border_radius": "8px",
                            "box_shadow": "0 1px 3px rgba(0,0,0,0.1)",
                            "padding": "24px",
                            "width": "100%",
                            "max_width": "900px",
                        }
                    ),
                    rx.fragment()
                ),

                # Bloque PDF extraído
                rx.cond(
                    (AppState.cotizacion_detalle.drive_file_id != "") & (AppState.cotizacion_detalle.id != ""),
                    rx.box(
                        rx.heading("Datos extraídos del PDF", size="5", style={"margin_top": "32px", "color": Color.SECONDARY_BLUE.value}),
                        # Resumen compacto de validación de familias
                        rx.hstack(
                            rx.cond(
                                AppState.cotizacion_detalle_pdf_familias_validacion.contains('"ok": true'),
                                rx.badge("Familias OK", color_scheme="green"),
                                rx.badge("Familias con observaciones", color_scheme="amber")
                            ),
                            rx.text("(ver detalles abajo)", size="1", color="var(--gray-10)"),
                            spacing="2",
                            align="center",
                        ),
                        rx.cond(
                            AppState.cotizacion_detalle_pdf_error != "",
                            rx.text(f"Error al extraer PDF: {AppState.cotizacion_detalle_pdf_error}", color="red"),
                            rx.vstack(
                                rx.text("Metadata:", weight="bold", style={"margin_top": "10px", "color": "var(--accent-11)"}),
                                rx.code(AppState.cotizacion_detalle_pdf_metadata, language="json", width="100%", style={"font_size": "0.85rem", "background": Color.LIGHT_GREY.value}),
                                rx.text("Tablas:", weight="bold", style={"margin_top": "10px", "color": "var(--accent-11)"}),
                                rx.code(AppState.cotizacion_detalle_pdf_tablas, language="json", width="100%", style={"font_size": "0.85rem", "background": Color.LIGHT_GREY.value}),
                                rx.text("Familias detectadas:", weight="bold", style={"margin_top": "10px", "color": "var(--accent-11)"}),
                                rx.code(AppState.cotizacion_detalle_pdf_familias, language="json", width="100%", style={"font_size": "0.85rem", "background": Color.LIGHT_GREY.value}),
                                rx.text("Validación de familias:", weight="bold", style={"margin_top": "10px", "color": "var(--accent-11)"}),
                                rx.code(AppState.cotizacion_detalle_pdf_familias_validacion, language="json", width="100%", style={"font_size": "0.85rem", "background": Color.LIGHT_GREY.value}),
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