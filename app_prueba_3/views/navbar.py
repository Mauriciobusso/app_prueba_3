import reflex as rx
from ..backend.app_state import AppState
from ..components.components import select_rol, select_area
from ..styles.colors import Color, TextColor
from ..styles.style import nav_style


def navbar(title: str = "Seguimiento") -> rx.Component:
    return rx.hstack(
        # User info
        rx.text(
            AppState.user_data.data.get("email",""),
            style={
                "color": Color.WHITE.value,
                "font_size": "14px",
                "font_weight": "400",
            }
        ),
        rx.spacer(),
        
        # Title
        rx.heading(
            title, 
            size="6",
            style={
                "color": Color.WHITE.value,
                "font_weight": "600",
                "margin": "0",
            }
        ),
        rx.spacer(),
        
        # Controls
        rx.hstack(
            select_rol(),
            select_area(),
            rx.button(
                "Cerrar sesión", 
                on_click=AppState.logout, 
                size="3",
                variant="outline",
                style={
                    "color": Color.WHITE.value,
                    "border_color": Color.WHITE.value,
                    "background_color": "transparent",
                    "_hover": {
                        "background_color": Color.WHITE.value,
                        "color": Color.PRIMARY_BLUE.value,
                    }
                }
            ),
            spacing="3",
            align="center",
        ),
        
        style=nav_style,
        align="center",
        width="100%",
        z_index="9999",
        position="fixed",
        top="0",
        height="64px",  # Standard header height
    )
