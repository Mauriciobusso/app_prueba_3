import reflex as rx
from app_prueba_3.styles.style import *
from app_prueba_3.styles.colors import Color
from app_prueba_3.backend.app_state import AppState
from ..utils import format_date_reflex

def loading_spinner(text: str = "Cargando..."):
    """Componente spinner de carga reutilizable"""
    return rx.hstack(
        rx.spinner(
            size="3",
            color="blue",
        ),
        rx.text(text, size="2", color="gray"),
        spacing="3",
        align="center",
        justify="center",
        width="100%",
        padding="4"
    )

def loading_overlay(text: str = "Cargando...", show: bool = True):
    """Overlay de carga que cubre toda la pantalla"""
    return rx.cond(
        show,
        rx.box(
            rx.center(
                rx.vstack(
                    rx.spinner(size="3", color="blue"),
                    rx.text(text, size="3", weight="medium"),
                    spacing="4",
                    align="center"
                ),
                width="100%",
                height="100vh"
            ),
            position="fixed",
            top="0",
            left="0",
            width="100vw",
            height="100vh",
            background_color="rgba(255, 255, 255, 0.9)",
            z_index="1000"
        ),
        rx.fragment()
    )

def session_keepalive():
    """Componente invisible que mantiene la sesión activa"""
    return rx.fragment(
        # Componente invisible que actualiza la actividad cada 5 minutos
        rx.script(f"""
            setInterval(() => {{
                // Solo hacer ping si hay sesión activa
                if (localStorage.getItem('session_internal') === 'true') {{
                    // Trigger keepalive usando el evento de Reflex
                    const event = new CustomEvent('keepalive_trigger');
                    document.dispatchEvent(event);
                }}
            }}, 300000); // 5 minutos
            
            // Listener para el evento personalizado
            document.addEventListener('keepalive_trigger', function() {{
                // Llamar al método de keepalive del estado
                const trigger = document.querySelector('[data-keepalive-trigger]');
                if (trigger) {{
                    trigger.click();
                }}
            }});
        """),
        # Botón invisible que se activa desde JavaScript
        rx.button(
            "keepalive",
            on_click=AppState.keepalive_ping,
            style={
                "display": "none",
                "visibility": "hidden",
                "position": "absolute",
                "left": "-9999px"
            },
            **{"data-keepalive-trigger": "true"}
        )
    )

def session_status_indicator():
    """Indicador visual del estado de la sesión"""
    return rx.cond(
        AppState.session_internal,
        rx.hstack(
            rx.icon("check_circle", size=16, color="green"),
            rx.text(
                "Sesión activa", 
                font_size="0.8rem", 
                color=Color.GRAY_600.value
            ),
            spacing="1",
            align="center"
        ),
        rx.hstack(
            rx.icon("x_circle", size=16, color="red"),
            rx.text(
                "Sin sesión", 
                font_size="0.8rem", 
                color=Color.GRAY_600.value
            ),
            spacing="1",
            align="center"
        )
    )

def table_cell(content, compact_mode=True):
    """Componente reutilizable para celdas de tabla con modo compacto"""
    if compact_mode:
        return rx.table.cell(
            content,
            padding="0px 3px",
            font_size="0.7rem",
            line_height="1",
            height="18px",
            border_bottom=f"1px solid {Color.GRAY_200.value}",
            white_space="nowrap",
            overflow="hidden",
            text_overflow="ellipsis",
            max_width="200px",
        )
    else:
        return rx.table.cell(
            content,
            padding="8px 12px",
            font_size="0.9rem",
            border_bottom=f"1px solid {Color.GRAY_200.value}",
            white_space="nowrap",
        )

def table_header_cell(content):
    """Componente reutilizable para headers de tabla"""
    return rx.table.column_header_cell(
        content,
        padding="0px 3px",
        font_size="0.6rem",
        font_weight="600",
        color=Color.GRAY_700.value,
        background=Color.GRAY_50.value,
        height="18px",
        line_height="1",
        border_bottom=f"1px solid {Color.GRAY_300.value}",
        white_space="nowrap",
    )

def table_link_cell(content, url, compact_mode=True):
    """Componente reutilizable para celdas con enlaces"""
    if compact_mode:
        return rx.table.cell(
            rx.link(
                content,
                href=url,
                target="_blank",
                color=Color.PRIMARY_BLUE.value,
                text_decoration="none",
                _hover={"text_decoration": "underline"},
                font_size="0.8rem",
            ),
            padding="2px 6px",
            height="24px",
            line_height="1.2",
            border_bottom=f"1px solid {Color.GRAY_200.value}",
            white_space="nowrap",
        )
    else:
        return rx.table.cell(
            rx.link(
                content,
                href=url,
                target="_blank",
                color=Color.PRIMARY_BLUE.value,
                text_decoration="none",
                _hover={"text_decoration": "underline"},
            ),
            padding="8px 12px",
            border_bottom=f"1px solid {Color.GRAY_200.value}",
            white_space="nowrap",
        )

def search_bar_component(placeholder, search_term, on_change, on_search):
    """Componente reutilizable para la barra de búsqueda"""
    return rx.hstack(
        rx.input(
            placeholder=placeholder,
            value=search_term,
            on_change=on_change,
            width="300px",
            padding="8px 12px",
            border=f"1px solid {Color.GRAY_300.value}",
            border_radius="4px",
            font_size="0.9rem",
            background="white",
            _focus={
                "border_color": Color.PRIMARY_BLUE.value,
                "outline": "none",
                "box_shadow": f"0 0 0 2px rgba(0, 122, 255, 0.1)"
            }
        ),
        rx.button(
            "Buscar",
            on_click=on_search,
            background=Color.PRIMARY_BLUE.value,
            color="white",
            padding="8px 16px",
            border_radius="4px",
            border="none",
            cursor="pointer",
            font_size="0.9rem",
            font_weight="500",
            _hover={
                "background": Color.NAVY.value
            }
        ),
        widhth="50%",
        spacing="2",
        margin_bottom="20px",
    )

def select_rol():
    """Componente selector de rol"""
    return rx.select(
        AppState.user_data.roles_names,
        placeholder="Seleccionar rol",
        value=AppState.user_data.current_rol_name,
        size="2",
        variant="surface",
        color_scheme="gray",
        background="white",
        color=Color.GRAY_700.value,
        width="160px",
    )

def select_area():
    """Componente selector de área"""  
    return rx.select(
        AppState.user_data.areas_names,
        placeholder="Seleccionar área",
        value=AppState.user_data.current_area_name,
        on_change=lambda value: AppState.set_current_area(value),
        size="2",
        variant="surface", 
        color_scheme="gray",
        background="white",
        color=Color.GRAY_700.value,
        width="160px",
    )

def table_certificados():
    """Tabla de certificados con componentes reutilizables"""
    return rx.vstack(
        search_bar_component(
            placeholder="Buscar certificados...",
            search_term=AppState.search_text,
            on_change=AppState.set_search_text,
            on_search=AppState.execute_search
        ),
        rx.table.root(
            rx.table.header(
                rx.table.row(
                    table_header_cell("N°"),
                    table_header_cell("Cliente"),
                    table_header_cell("Familia"),
                    table_header_cell("Estado"),
                    table_header_cell("Fecha Emisión"),
                    table_header_cell("Vencimiento"),
                )
            ),
            rx.table.body(
                rx.foreach(
                    AppState.certs_show,
                    lambda cert: rx.table.row(
                        table_cell(f"{cert.num}/{cert.year}"),
                        table_cell(cert.client),
                        table_cell(cert.family.family),
                        table_cell(cert.status),
                        table_cell(cert.issuedate),
                        table_cell(cert.vencimiento),
                        cursor="pointer",
                        _hover={"background": Color.GRAY_50.value},
                    )
                )
            ),
            variant="surface",
            size="1",
        ),
        width="100%",
    )

def table_familias():
    """Tabla de familias con componentes reutilizables"""
    return rx.vstack(
        search_bar_component(
            placeholder="Buscar familias...",
            search_term=AppState.search_text,
            on_change=AppState.set_search_text,
            on_search=AppState.execute_search
        ),
        rx.table.root(
            rx.table.header(
                rx.table.row(
                    table_header_cell("Familia"),
                    table_header_cell("Producto"),
                    table_header_cell("Cliente"),
                    table_header_cell("Área"),
                    table_header_cell("Estado"),
                    table_header_cell("Vencimiento"),
                )
            ),
            rx.table.body(
                rx.foreach(
                    AppState.fams_show,
                    lambda fam: rx.table.row(
                        table_cell(fam.family),
                        table_cell(fam.product),
                        table_cell(fam.client),
                        table_cell(fam.area),
                        table_cell(fam.status),
                        table_cell(fam.expirationdate),
                        cursor="pointer",
                        _hover={"background": Color.GRAY_50.value},
                    )
                )
            ),
            variant="surface",
            size="1",
        ),
        width="100%",
    )

def table_cotizaciones():
    """Tabla de cotizaciones con componentes reutilizables"""
    return rx.vstack(
        rx.hstack(
            search_bar_component(
            placeholder="Buscar cotizaciones...",
            search_term=AppState.search_text,
            on_change=AppState.set_search_text,
            on_search=AppState.execute_search
            ),
            rx.link(
                rx.button("Nueva Cotización", background=Color.PRIMARY_BLUE.value, color=Color.WHITE.value),
                href="/cotizaciones/new"
            ),
            spacing="4",
        ),
        rx.table.root(
            rx.table.header(
                rx.table.row(
                    table_header_cell("N°"),
                    table_header_cell("Cliente"),
                    rx.cond(
                        AppState.user_data.current_area_name == "TODAS",
                        table_header_cell("Área"),
                        rx.fragment()
                    ),
                    table_header_cell("Estado"),
                    table_header_cell("Fecha Emisión"),
                    rx.table.column_header_cell(
                        "📁",
                        padding="0px",
                        font_size="0.8rem",
                        font_weight="600",
                        color=Color.GRAY_700.value,
                        background=Color.GRAY_50.value,
                        height="18px",
                        line_height="1",
                        border_bottom=f"1px solid {Color.GRAY_300.value}",
                        white_space="nowrap",
                        text_align="center",
                        width="35px",
                        min_width="35px",
                        max_width="35px",
                    ),
                    rx.table.column_header_cell(
                        "🔗",
                        padding="0px",
                        font_size="0.8rem",
                        font_weight="600",
                        color=Color.GRAY_700.value,
                        background=Color.GRAY_50.value,
                        height="18px",
                        line_height="1",
                        border_bottom=f"1px solid {Color.GRAY_300.value}",
                        white_space="nowrap",
                        text_align="center",
                        width="35px",
                        min_width="35px",
                        max_width="35px",
                    ),
                )
            ),
            rx.table.body(
                rx.foreach(
                    AppState.cots_show,
                    lambda cot: rx.table.row(
                        table_cell(f"{cot.num}/{cot.year}"),
                        table_cell(cot.client),
                        rx.cond(
                            AppState.user_data.current_area_name == "TODAS",
                            table_cell(cot.area),
                            rx.fragment()
                        ),
                        table_cell(cot.status),
                        table_cell(format_date_reflex(cot.issuedate)),
                        rx.table.cell(
                            rx.cond(
                                cot.drive_file_id != "",
                                rx.link(
                                    rx.icon("eye", size=16, display="inline"),
                                    href=f"https://drive.google.com/file/d/{cot.drive_file_id}/view",
                                    target="_blank",
                                    text_decoration="none",
                                    _hover={"opacity": "0.7"},
                                    on_click=rx.stop_propagation,
                                ),
                                rx.text("-", color=Color.GRAY_400.value, font_size="0.7rem")
                            ),
                            padding="1px",
                            height="18px",
                            line_height="1",
                            border_bottom=f"1px solid {Color.GRAY_200.value}",
                            white_space="nowrap",
                            text_align="center",
                            width="35px",
                            min_width="35px",
                            max_width="35px",
                            vertical_align="middle",
                        ),
                        rx.table.cell(
                            rx.link(
                                rx.icon("external_link", size=16, display="inline"),
                                href=f"https://panel.bvarg.com.ar/app/cotizaciones/{cot.id}",
                                target="_blank",
                                text_decoration="none",
                                _hover={"opacity": "0.7"},
                                on_click=rx.stop_propagation,
                            ),
                            padding="1px",
                            height="18px",
                            line_height="1",
                            border_bottom=f"1px solid {Color.GRAY_200.value}",
                            white_space="nowrap",
                            text_align="center",
                            width="35px",
                            min_width="35px",
                            max_width="35px",
                            vertical_align="middle",
                        ),
                        cursor="pointer",
                        _hover={"background": Color.GRAY_50.value},
                        on_click=lambda: rx.redirect(f"/cotizaciones/{cot.id}"),
                    )
                )
            ),
            variant="surface",
            size="1",
            width="100%",
            style={"table_layout": "fixed"},
        ),
        width="100%",
    )

def pagination_controls():
    """Controles de paginación para cotizaciones"""
    return rx.vstack(
        # Información de página
        rx.text(
            AppState.cots_page_info,
            size="2",
            color="gray",
            text_align="center",
        ),
        
        # Controles de navegación
        rx.hstack(
            # Botón primera página
            rx.button(
                rx.icon("chevrons-left", size=16),
                size="2",
                variant="outline",
                disabled=~AppState.cots_has_prev_page,
                on_click=AppState.first_cots_page,
                style={
                    "min_width": "40px",
                    "background_color": "var(--color-surface)",
                    "border": "1px solid var(--accent-7)",
                    "color": "var(--accent-11)",
                    "_hover": {
                        "background_color": "var(--accent-3)",
                    },
                    "_disabled": {
                        "opacity": "0.5",
                        "cursor": "not-allowed",
                    }
                }
            ),
            
            # Botón página anterior
            rx.button(
                rx.icon("chevron-left", size=16),
                size="2",
                variant="outline",
                disabled=~AppState.cots_has_prev_page,
                on_click=AppState.prev_cots_page,
                style={
                    "min_width": "40px",
                    "background_color": "var(--color-surface)",
                    "border": "1px solid var(--accent-7)",
                    "color": "var(--accent-11)",
                    "_hover": {
                        "background_color": "var(--accent-3)",
                    },
                    "_disabled": {
                        "opacity": "0.5",
                        "cursor": "not-allowed",
                    }
                }
            ),
            
            # Información de página actual
            rx.box(
                rx.text(
                    f"Página {AppState.cots_current_page_display} de {AppState.cots_total_pages}",
                    size="2",
                    weight="medium",
                    color="var(--accent-11)",
                ),
                padding_x="4",
                padding_y="2",
                border_radius="6px",
                background_color="var(--accent-3)",
                border="1px solid var(--accent-7)",
            ),
            
            # Botón página siguiente
            rx.button(
                rx.icon("chevron-right", size=16),
                size="2",
                variant="outline",
                disabled=~AppState.cots_has_next_page,
                on_click=AppState.next_cots_page,
                style={
                    "min_width": "40px",
                    "background_color": "var(--color-surface)",
                    "border": "1px solid var(--accent-7)",
                    "color": "var(--accent-11)",
                    "_hover": {
                        "background_color": "var(--accent-3)",
                    },
                    "_disabled": {
                        "opacity": "0.5",
                        "cursor": "not-allowed",
                    }
                }
            ),
            
            # Botón última página
            rx.button(
                rx.icon("chevrons-right", size=16),
                size="2",
                variant="outline",
                disabled=~AppState.cots_has_next_page,
                on_click=AppState.last_cots_page,
                style={
                    "min_width": "40px",
                    "background_color": "var(--color-surface)",
                    "border": "1px solid var(--accent-7)",
                    "color": "var(--accent-11)",
                    "_hover": {
                        "background_color": "var(--accent-3)",
                    },
                    "_disabled": {
                        "opacity": "0.5",
                        "cursor": "not-allowed",
                    }
                }
            ),
            
            spacing="2",
            justify="center",
            align="center",
        ),
        
        spacing="3",
        align="center",
        justify="center",
        width="100%",
        padding="4",
        style={
            "background_color": "var(--color-surface)",
            "border_top": "1px solid var(--accent-7)",
            "margin_top": "20px",
        }
    )
