import reflex as rx
from ..views.navbar import navbar
from ..components.components import table_certificados, table_familias, table_cotizaciones
from ..backend.app_state import AppState
from ..styles.colors import Color
from ..styles.style import container_style


def certificados_view() -> rx.Component:
    """Vista de certificados - Estilo Bureau Veritas"""
    return rx.box(
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
        background_color=Color.LIGHT_GREY.value,
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
        background_color=Color.LIGHT_GREY.value,
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
        background_color=Color.LIGHT_GREY.value,
        on_scroll=lambda: AppState.on_scroll_throttled(),
        on_mount=AppState.on_mount_cotizaciones,
    )