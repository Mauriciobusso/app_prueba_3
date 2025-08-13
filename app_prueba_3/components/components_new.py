import reflex as rx
from app_prueba_3.styles.style import *
from app_prueba_3.styles.colors import *
from app_prueba_3.backend.app_state import AppState

def table_cell(content, compact_mode=True):
    """Componente reutilizable para celdas de tabla con modo compacto"""
    if compact_mode:
        return rx.table.cell(
            content,
            padding="2px 6px",
            font_size="0.8rem",
            line_height="1.2",
            height="24px",
            border_bottom=f"1px solid {GRAY_200}",
        )
    else:
        return rx.table.cell(
            content,
            padding="8px 12px",
            font_size="0.9rem",
            border_bottom=f"1px solid {GRAY_200}",
        )

def table_header_cell(content):
    """Componente reutilizable para headers de tabla"""
    return rx.table.column_header_cell(
        content,
        padding="4px 6px",
        font_size="0.75rem",
        font_weight="600",
        color=GRAY_700,
        background=GRAY_50,
        height="28px",
        line_height="1.2",
        border_bottom=f"1px solid {GRAY_300}",
    )

def table_link_cell(content, url, compact_mode=True):
    """Componente reutilizable para celdas con enlaces"""
    if compact_mode:
        return rx.table.cell(
            rx.link(
                content,
                href=url,
                target="_blank",
                color=PRIMARY_BLUE,
                text_decoration="none",
                _hover={"text_decoration": "underline"},
                font_size="0.8rem",
            ),
            padding="2px 6px",
            height="24px",
            line_height="1.2",
            border_bottom=f"1px solid {GRAY_200}",
        )
    else:
        return rx.table.cell(
            rx.link(
                content,
                href=url,
                target="_blank",
                color=PRIMARY_BLUE,
                text_decoration="none",
                _hover={"text_decoration": "underline"},
            ),
            padding="8px 12px",
            border_bottom=f"1px solid {GRAY_200}",
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
            border=f"1px solid {GRAY_300}",
            border_radius="4px",
            font_size="0.9rem",
            background="white",
            _focus={
                "border_color": PRIMARY_BLUE,
                "outline": "none",
                "box_shadow": f"0 0 0 2px rgba(0, 122, 255, 0.1)"
            }
        ),
        rx.button(
            "Buscar",
            on_click=on_search,
            background=PRIMARY_BLUE,
            color="white",
            padding="8px 16px",
            border_radius="4px",
            border="none",
            cursor="pointer",
            font_size="0.9rem",
            font_weight="500",
            _hover={
                "background": NAVY
            }
        ),
        spacing="2",
        margin_bottom="20px",
    )

def select_rol():
    """Componente selector de rol"""
    return rx.select(
        AppState.user_data.roles_names,
        placeholder="Seleccionar rol",
        value=AppState.user_data.current_rol_name,
        on_change=lambda value: AppState.set_current_rol(value),
        size="2",
        variant="soft",
        color_scheme="blue",
    )

def select_area():
    """Componente selector de área"""  
    return rx.select(
        [area.get("name", "") for area in AppState.areas],
        placeholder="Seleccionar área",
        value=AppState.user_data.current_area_name,
        on_change=lambda value: AppState.set_current_area(value),
        size="2",
        variant="soft", 
        color_scheme="blue",
    )
