import reflex as rx
from ..backend.app_state import AppState
from ..components.components import select_rol, select_area


def navbar(title: str = "Seguimiento") -> rx.Component:
    return rx.hstack(
        rx.text(AppState.user_data.data.get("email","")),
        rx.spacer(),
        rx.heading(title, size="6"),
        rx.spacer(),
        select_rol(),
        select_area(),
        rx.button(
            "Cerrar sesión", 
            on_click=AppState.logout, 
            width="10em",
            size="2",
            variant="soft"
        ),
        # rx.hstack(
        #     rx.color_mode.button(
        #         size="2",
        #         icon_spacing="0.5rem",
        #     ),
        #     align="center",
        #     spacing="3",
        # ),
        # spacing="2",
        # variant="surface",
        background= "rgba(255, 255, 255, 0.9)",
        align="center",
        width="100%",
        z_index="9999",
        position="fixed",
        hight="5vh",
    )
