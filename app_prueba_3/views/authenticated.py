import reflex as rx
from ..views.navbar import navbar
from ..components.components import table_certificados, table_familias, table_cotizaciones, session_keepalive, loading_spinner, loading_overlay, pagination_controls
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
    on_scroll=AppState.update_activity,
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
    on_scroll=AppState.update_activity,
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
                    rx.vstack(
                        table_cotizaciones(),
                        # Controles de paginación - Solo mostrar si hay cotizaciones
                        rx.cond(
                            AppState.cots.length() > 0,
                            pagination_controls(),
                            rx.fragment()
                        ),
                        spacing="4",
                        width="100%",
                    ),
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
    on_scroll=AppState.update_activity,
        on_mount=AppState.on_mount_cotizaciones,
    )


def cotizacion_detalle_view() -> rx.Component:
    """Vista de detalle de una cotización específica - Estilo Bureau Veritas"""
    return rx.box(
        # Overlay de carga para cotización detalle
        loading_overlay(
            "Cargando cotización...",
            AppState.is_loading_cotizacion_detalle
        ),
        # Overlay de procesamiento para cotización detalle
        loading_overlay(
            "Procesando datos del PDF...",
            AppState.cotizacion_detalle_processing
        ),
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
                
                # Tarjeta con detalles de la cotización - Solo mostrar cuando NO esté cargando Y NO esté procesando Y tenga datos
                rx.cond(
                    (AppState.cotizacion_detalle.id != "") & (~AppState.is_loading_cotizacion_detalle) & (~AppState.cotizacion_detalle_processing),
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
                                    on_click=AppState.reprocesar_cotizacion_detalle,
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
                                    # Fallback: usar familias mapeadas - Solo mostrar cuando NO esté cargando
                                    rx.cond(
                                        (AppState.cotizacion_detalle_familys_count > 0) & (~AppState.is_loading_cotizacion_detalle) & (~AppState.cotizacion_detalle_processing),
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
                            # Tabla de trabajos extraídos del PDF - Solo mostrar cuando NO esté cargando
                            rx.vstack(
                                rx.cond(
                                    (AppState.cotizacion_detalle_trabajos_count > 0) & (~AppState.is_loading_cotizacion_detalle) & (~AppState.cotizacion_detalle_processing),
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
        background_color="var(--color-background)",
        on_mount=AppState.on_mount_cotizacion_detalle
    )                  


def nueva_cotizacion_view() -> rx.Component:
    """Vista para crear una nueva cotización desde un formulario profesional."""
    from ..backend.app_state import AppState
    from ..styles.colors import Color
    import json

    return rx.box(
        navbar(title="Nueva Cotización"),
        rx.box(
            rx.vstack(
                # Header con título estilo profesional
                rx.card(
                    rx.hstack(
                        rx.vstack(
                            rx.heading(
                                "NUEVA COTIZACIÓN", 
                                size="8",
                                style={"color": Color.PRIMARY_BLUE.value, "font_weight": "700", "letter_spacing": "0.5px"},
                                align="center",
                            ),
                            rx.text(
                                "Complete la información para generar una nueva cotización", 
                                style={"color": "var(--gray-11)", "font_size": "16px"}
                            ),
                            align="start",
                            spacing="2"
                        ),
                        width="100%",
                        align="center"
                    ),
                    style={
                        "padding": "32px",
                        "border_radius": "12px",
                        "border": "1px solid var(--gray-6)",
                        "background": "linear-gradient(135deg, var(--color-background) 0%, var(--gray-1) 100%)"
                    }, 
                    width="100%",
                    align="center",
                ),
                rx.box(
                    # Header superior derecha: Fecha y N° Cotización
                    rx.vstack(
                        rx.hstack(
                            rx.text(
                                "Fecha: ",
                                size="2",
                                weight="medium",
                            ),
                            rx.input(
                                value=AppState.new_cot_issuedate,
                                on_change=AppState.set_new_cot_fecha,
                                placeholder="dd/MM/YYYY",
                                style={
                                    "width": "150px",
                                    "text_align": "right",
                                    "border": "1px solid var(--gray-6)",
                                    "padding": "4px 8px",
                                    "border_radius": "4px"
                                }
                            ),
                            align="end",
                        ),
                        rx.hstack(
                            rx.text(
                                "N° Cotización: BVE N°",
                                size="2",
                                weight="medium",
                            ),
                            rx.input(
                                value=AppState.new_cot_num,
                                on_change=AppState.set_new_cot_num,
                                placeholder="Número",
                                style={
                                    "width": "80px",
                                    "text_align": "right",
                                    "border": "1px solid var(--gray-6)",
                                    "padding": "4px 8px",
                                    "border_radius": "4px"
                                }
                            ),
                            rx.text("/"),
                            rx.input(
                                value=AppState.new_cot_year,
                                on_change=AppState.set_new_cot_year,
                                placeholder="Año",
                                style={
                                    "width": "60px",
                                    "text_align": "right",
                                    "border": "1px solid var(--gray-6)",
                                    "padding": "4px 8px",
                                    "border_radius": "4px"
                                }
                            ),
                            align="center",
                        ),
                        align="end",
                        width="100%",
                        spacing="2",
                    ),
                    rx.box(height="1px", width="100%", background_color="var(--gray-6)", margin_y="10px"),

                    # Bloque de datos de cabecera
                    rx.vstack(
                        rx.hstack(
                            rx.text("Empresa:", weight="bold", width="150px"),
                            rx.input(
                                on_change=AppState.set_new_cot_empresa,
                                placeholder="Buscar empresa...",
                                style={
                                    "width": "300px",
                                    "border": "1px solid var(--gray-6)",
                                    "padding": "4px 8px",
                                    "border_radius": "4px"
                                }
                            ),
                            rx.icon_button(
                                rx.icon("plus", size=18),
                                on_click=AppState.add_empresa_temporal
                            ),
                            spacing="2",
                        ),
                        rx.hstack(
                            rx.text("At Sr./Sra.:", weight="bold", width="150px"),
                            rx.input(
                                on_change=AppState.set_new_cot_nombre,
                                placeholder="Dirigido a:",
                                style={
                                    "width": "300px",
                                    "border": "1px solid var(--gray-6)",
                                    "padding": "4px 8px",
                                    "border_radius": "4px"
                                }
                            ),
                            spacing="2",
                        ),
                        rx.hstack(
                            rx.text("Consultora:", weight="bold", width="150px"),
                            rx.input(
                                on_change=AppState.set_new_cot_consultora,
                                placeholder="Buscar consultora...",
                                style={
                                    "width": "300px",
                                    "border": "1px solid var(--gray-6)",
                                    "padding": "4px 8px",
                                    "border_radius": "4px"
                                }
                            ),
                            spacing="2",
                        ),
                        rx.hstack(
                            rx.text("Facturar a:", weight="bold", width="150px"),
                            rx.input(
                                value=AppState.new_cot_facturar,
                                on_change=AppState.set_new_cot_facturar,
                                placeholder="Facturar a:",
                                style={
                                    "width": "300px",
                                    "border": "1px solid var(--gray-6)",
                                    "padding": "4px 8px",
                                    "border_radius": "4px"
                                }
                            ),
                            spacing="2",
                        ),
                        rx.hstack(
                            rx.text("Mail Receptor:", weight="bold", width="150px"),
                            rx.input(
                                value=AppState.new_cot_mail,
                                on_change=AppState.set_new_cot_mail,
                                placeholder="Email del receptor:",
                                style={
                                    "width": "600px",
                                    "border": "1px solid var(--gray-6)",
                                    "padding": "4px 8px",
                                    "border_radius": "4px"
                                },
                                type="email",
                            ),
                            spacing="2",
                        ),
                        spacing="1",
                        margin_top="6px",
                    ),

                    rx.box(height="1px", width="100%", background_color="var(--gray-6)", margin_y="12px"),

                    # Título central
                    rx.center(
                        rx.text(
                            f"CERTIFICACIÓN DE PRODUCTO SEGÚN RESOLUCIÓN {AppState.new_cot_resolucion}",
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
                                f"CANTIDAD DE FAMILIAS: {AppState.new_cot_familias.length()}",
                                weight="bold",
                            ),
                            align="center",
                            width="100%",
                            padding_y="8px",
                            style={"border": "1px solid var(--gray-7)", "background": "var(--gray-3)", "padding_left": "10px", "padding_right": "10px"}
                        ),
                        # Contenido de la tabla
                        rx.foreach(
                            AppState.new_cot_familias,
                            lambda fam, idx: rx.grid(
                                rx.box(
                                    rx.hstack(
                                        # Campos de entrada para familia y producto
                                        rx.text("FLIA ", weight="bold", style={"width": "80px"}),
                                        rx.input(
                                            value=fam.family, 
                                            placeholder="Ej: PROYECTOR LED (FLIA G74)",
                                            on_change=lambda v, i=idx: AppState.set_new_cot_family(i, v),
                                            style={
                                                "width": "50px",
                                                "border": "none",
                                                "background": "transparent",
                                                "padding": "8px",
                                                "font_size": "14px",
                                                "_focus": {"outline": "none"}
                                            }
                                        ), 
                                        rx.text(" - ", weight="bold", style={"width": "10px"}),
                                        rx.input(
                                            value=fam.product, 
                                            placeholder="Ej: PROYECTOR LED",
                                            on_change=lambda v, i=idx: AppState.set_new_cot_product(i, v),
                                            style={
                                                "width": "100%",
                                                "border": "none",
                                                "background": "transparent",
                                                "padding": "8px",
                                                "font_size": "14px",
                                                "_focus": {"outline": "none"}
                                            }
                                        ),  
                                        rx.button(
                                            rx.icon("trash-2", size=20),
                                            on_click=lambda *_, i=idx: AppState.remove_new_cot_family(i),
                                            variant="ghost",
                                            color_scheme="red",
                                            size="1",
                                            style={"padding": "4px", "min_width": "24px"}
                                        ),
                                        justify="between",
                                        align="center",
                                        width="100%"
                                    ),
                                    justify="between",
                                    align="center",
                                    width="100%",
                                    style={
                                        "background": "var(--color-background)",
                                        "padding": "8px",
                                        "border": "1px solid var(--gray-6)",
                                        "border_right": "none",
                                        "border_top": "none"
                                    }
                                ),
                            )
                        ),
                        
                        # Botón para agregar familia
                        rx.button(
                            rx.icon("plus", size=16),
                            "Agregar Familia de Producto",
                            on_click=AppState.add_new_cot_family,
                            variant="outline",
                            size="3",
                            style={
                                "width": "100%",
                                "margin_top": "16px",
                                "border": "2px dashed var(--gray-6)",
                                "color": Color.SECONDARY_BLUE.value,
                                "border_radius": "8px",
                                "padding": "16px"
                            }
                        ),
                        
                        width="100%",
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
                        # Contenido de trabajos
                        rx.foreach(
                            AppState.new_cot_trabajos,
                            lambda trabajo, idx: rx.grid(
                                # Descripción con selector
                                rx.box(
                                    rx.vstack(
                                        # Info sobre trabajos disponibles
                                        rx.cond(
                                            AppState.trabajos_disponibles.length() > 0,
                                            rx.text(
                                                f"💡 Hay {AppState.trabajos_disponibles.length()} trabajos disponibles. Haga clic en 'Cargar Trabajos' para verlos.",
                                                style={"font_size": "12px", "color": "var(--blue-9)", "margin_bottom": "8px"}
                                            ),
                                            rx.fragment()
                                        ),
                                        # Campo de descripción manual
                                        rx.text_area(
                                            value=trabajo.get('descripcion',''), 
                                            placeholder="Descripción detallada del trabajo/servicio (ej: Certificación para una Familia de Productos según descripción proveniente de una Fábrica ya Inspeccionada...)",
                                            on_change=lambda v, i=idx: AppState.set_new_cot_trabajo_field(i, 'descripcion', v),
                                            style={
                                                "width": "100%",
                                                "min_height": "100px",
                                                "border": "none",
                                                "background": "transparent",
                                                "padding": "8px",
                                                "font_size": "13px",
                                                "resize": "vertical",
                                                "_focus": {"outline": "none"}
                                            }
                                        ),
                                        # Botón eliminar (solo visible al hacer hover)
                                        rx.button(
                                            rx.icon("trash-2", size=20),
                                            on_click=lambda: AppState.remove_new_cot_trabajo(trabajo),
                                            variant="ghost",
                                            color_scheme="red",
                                            size="1",
                                            style={
                                                "position": "absolute",
                                                "top": "8px",
                                                "right": "8px",
                                                "opacity": "0.7",
                                                "padding": "4px"
                                            }
                                        ),
                                        align="start",
                                        spacing="2",
                                        style={"position": "relative"}
                                    ),
                                    style={
                                        "background": "var(--color-background)",
                                        "padding": "12px",
                                        "border": "1px solid var(--gray-6)",
                                        "border_top": "none",
                                        "min_height": "120px"
                                    }
                                ),
                                # Cantidad
                                rx.box(
                                    rx.input(
                                        value=trabajo.get('cantidad','1'), 
                                        placeholder='1',
                                        on_change=lambda v, i=idx: AppState.set_new_cot_trabajo_field(i, 'cantidad', v),
                                        style={
                                            "width": "100%",
                                            "border": "none",
                                            "background": "transparent",
                                            "padding": "8px",
                                            "font_size": "14px",
                                            "text_align": "center",
                                            "_focus": {"outline": "none"}
                                        }
                                    ),
                                    style={
                                        "background": "var(--color-background)",
                                        "padding": "8px",
                                        "border": "1px solid var(--gray-6)",
                                        "border_left": "none",
                                        "border_top": "none",
                                        "display": "flex",
                                        "align_items": "center"
                                    }
                                ),
                                # Precio
                                rx.box(
                                    rx.input(
                                        value=trabajo.get('precio',''), 
                                        placeholder='$ 548.600,00',
                                        on_change=lambda v, i=idx: AppState.set_new_cot_trabajo_field(i, 'precio', v),
                                        style={
                                            "width": "100%",
                                            "border": "none",
                                            "background": "transparent",
                                            "padding": "8px",
                                            "font_size": "14px",
                                            "text_align": "center",
                                            "_focus": {"outline": "none"}
                                        }
                                    ),
                                    style={
                                        "background": "var(--color-background)",
                                        "padding": "8px",
                                        "border": "1px solid var(--gray-6)",
                                        "border_left": "none",
                                        "border_top": "none",
                                        "display": "flex",
                                        "align_items": "center"
                                    }
                                ),
                                columns="3fr 1fr 1fr",
                                width="100%"
                            )
                        ),
                        # Botón para agregar trabajo
                        rx.button(
                            rx.icon("plus", size=16),
                            "Agregar Trabajo",
                            on_click=AppState.add_new_cot_trabajo,
                            variant="outline",
                            size="3",
                            style={
                                "width": "100%",
                                "margin_top": "16px",
                                "border": "2px dashed var(--gray-6)",
                                "color": Color.SECONDARY_BLUE.value,
                                "border_radius": "8px",
                                "padding": "16px"
                            }
                        ),
                        margin_top="10px",
                    ),

                    # Condiciones
                    rx.box(
                        rx.text("Condiciones:", weight="bold", margin_top="12px"),
                        rx.text(AppState.new_cot_pdf_condiciones, size="2", style={"white_space": "pre-wrap"}),
                        margin_top="10px",
                    ),

                    # Footer con revisión
                    rx.hstack(
                        rx.text("Néstor Luis Quintela – Gerente Certificación de Productos", size="1", color="var(--gray-10)"),
                        rx.spacer(),
                        rx.text(f"Rev.: {AppState.new_cot_rev}", size="1", color="var(--gray-10)"),
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
                    }, 
                    align="center",
                ),
                rx.fragment(),

                style={
                    "padding": "32px",
                    "border_radius": "12px",
                    "border": "1px solid var(--gray-6)",
                    "background": "var(--color-background)"
                }
            ),

                # Mensajes de estado
                rx.cond(
                    AppState.new_cot_status == 'error',
                    rx.card(
                        rx.hstack(
                            rx.icon("triangle_alert", size=20, color=Color.ERROR.value),
                            rx.text(AppState.new_cot_error_message, color=Color.ERROR.value, weight="medium"),
                            spacing="3",
                            align="center"
                        ),
                        style={
                            "padding": "20px",
                            "border_radius": "8px",
                            "border": f"1px solid {Color.ERROR.value}",
                            "background": "var(--red-2)"
                        }
                    ),
                    rx.cond(
                        AppState.new_cot_status == 'success',
                        rx.card(
                            rx.hstack(
                                rx.icon("message_circle_more", size=20, color=Color.SUCCESS.value),
                                rx.text('✅ Cotización creada exitosamente', color=Color.SUCCESS.value, weight="medium"),
                                spacing="3",
                                align="center"
                            ),
                            style={
                                "padding": "20px",
                                "border_radius": "8px",
                                "border": f"1px solid {Color.SUCCESS.value}",
                                "background": "var(--green-2)"
                            }
                        ),
                        rx.fragment()
                    )
                ),

                # Botones de acción (estilo profesional)
                rx.card(
                    rx.hstack(
                        rx.link(
                            rx.button(
                                rx.icon("arrow-left", size=18),
                                "Volver a Cotizaciones",
                                variant="outline",
                                size="4",
                                style={
                                    "padding": "16px 32px",
                                    "border_radius": "8px",
                                    "border": "2px solid var(--gray-6)",
                                    "font_weight": "500",
                                    "color": "var(--gray-11)"
                                }
                            ),
                            href="/cotizaciones"
                        ),
                        rx.spacer(),
                        rx.button(
                            rx.icon("file-plus", size=18),
                            "Crear Cotización",
                            on_click=AppState.submit_new_cot,
                            variant="solid",
                            size="4",
                            style={
                                "background": f"linear-gradient(135deg, {Color.PRIMARY_BLUE.value} 0%, {Color.SECONDARY_BLUE.value} 100%)",
                                "color": Color.WHITE.value,
                                "padding": "16px 32px",
                                "border_radius": "8px",
                                "font_weight": "600",
                                "box_shadow": f"0 4px 12px {Color.PRIMARY_BLUE.value}30"
                            }
                        ),
                        width="100%",
                        align="center"
                    ),
                    style={
                        "padding": "24px",
                        "border_radius": "12px",
                        "border": "1px solid var(--gray-6)",
                        "background": "var(--color-background)"
                    }
                ),
                style=container_style,
                spacing="8",
                width="100%",
                max_width="1400px",
                # Cargar trabajos disponibles al montar la vista
                on_mount=AppState.load_new_cot
            ),
            
            padding_top="84px",
            overflow_y="auto",
        )