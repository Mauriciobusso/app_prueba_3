import reflex as rx
from ..backend.app_state import AppState
from reflex_calendar import calendar
from ..styles import colors
from ..styles.style import search_container_style

def format_date_component(date_var):
    """
    Componente para formatear fechas de YYYY-mm-dd a dd/mm/YYYY
    """
    return rx.cond(
        date_var.contains("-") & (date_var.length() == 10),
        date_var.split("-")[2] + "/" + date_var.split("-")[1] + "/" + date_var.split("-")[0],
        date_var
    )

def search_bar_component(height="auto") -> rx.Component:
    """
    Componente reutilizable para la barra de búsqueda - Estilo Bureau Veritas
    """
    return rx.hstack(
        rx.input(
            placeholder="Buscar...",
            value=AppState.search_text,
            on_change=AppState.set_search_text,
            width="100%",
            height=height if height != "auto" else "44px",
            on_key_down=lambda key: AppState.handle_search_key(key),
        ),
        rx.button(
            "🔍 Buscar",
            on_click=AppState.execute_search,
            size="3",
            variant="solid",
            style={
                "white_space": "nowrap",
                "min_width": "120px",
            }
        ),
        width="50%",
        style=search_container_style,
        spacing="3",
        align_items="center",
    )

def select_rol()->rx.Component:
    """Select component for choosing a role."""
    return rx.cond(
        AppState.user_data.current_rol_name,
        rx.select(
            items=AppState.user_data.roles_names,
            value= AppState.user_data.current_rol_name,
            on_change=AppState.set_current_rol,
            name= "select_rol",
            required=True,
            align="center",
            width="150px",
        ),
        rx.spinner(
            size="2",
            color="blue.500",
            empty_color="gray.200",
            thickness="4px",
            speed="0.65s",
        ),
    )


def select_area()->rx.Component:
    """Select component for choosing an area."""
    return rx.cond(
        AppState.user_data.current_area_name,
        rx.select(
            items=AppState.user_data.areas_names,
            value= AppState.user_data.current_area_name,
            on_change=AppState.set_current_area,
            name= "select_area",
            required=True,
            align="center",
            width="150px",
        ),
        rx.spinner(
            size="2",
            color="blue.500",
            empty_color="gray.200",
            thickness="4px",
            speed="0.65s"
        )
    )

def table_certificados()->rx.Component:
    return rx.vstack(
        search_bar_component(),
        rx.table.root(
            rx.table.header(
                rx.table.row(
                    rx.table.column_header_cell("Certificado", width="14.3%"),
                    rx.table.column_header_cell("Revisión", width="14.3%"),
                    rx.table.column_header_cell("Fecha de Asignación", width="14.3%"),
                    rx.table.column_header_cell("Fecha de Emisión", width="14.3%"),
                    rx.table.column_header_cell("Vencimiento", width="14.3%"),
                    rx.table.column_header_cell("Estado", width="14.3%"),
                    rx.table.column_header_cell("Id Familia", width="14.2%"),
                ),
            ),
            rx.table.body(
                rx.cond(
                    AppState.certs_show.length() > 0,
                    rx.foreach(AppState.certs_show, lambda cert: rx.table.row(
                    rx.table.cell(f"{cert.num}-{cert.year}"),
                    rx.cond(cert.rev!="00",
                        rx.table.cell(f"Rev.{cert.rev}"),
                        rx.table.cell(".", content_editable=True)
                    ),
                    rx.table.cell(cert.assigmentdate, 
                                    style={"white-space": "nowrap"}),
                    rx.table.cell(format_date_component(cert.issuedate),
                                    style={"white-space": "nowrap"}),
                    rx.table.cell(format_date_component(cert.vencimiento),
                                    style={"white-space": "nowrap"}),
                    rx.table.cell(cert.status),
                    rx.table.cell(rx.link(
                        cert.family_id,
                        href=f"https://panel.bvarg.com.ar/app/familias/{cert.family_id}",
                        is_external=True,
                        )
                    ),
                    style={
                        "_hover": {"bg": colors.Color.LIGHT_BLUE.value},
                        "height": "48px",
                        "border_bottom": f"1px solid {colors.Color.LIGHT_GREY.value}",
                    },
                    align="center",
                )),
                    # Mostrar mensaje cuando no hay resultados
                    rx.table.row(
                        rx.table.cell(
                            rx.text("Ningún resultado encontrado", 
                                   style={"font_style": "italic", "color": colors.TextColor.MUTED.value}),
                            col_span=7,
                            text_align="center",
                            padding="40px"
                        )
                    )
                )
            ),
            variant="surface",
            size="3",
            width="100%",
            style={
                "border": f"1px solid {colors.Color.LIGHT_GREY.value}",
                "border_radius": "8px",
                "overflow": "hidden",
            }
        ),
        spacing="4",
        width="100%",
    )

def table_familias()->rx.Component:
    return rx.vstack(
        search_bar_component(),
        rx.table.root(
            rx.table.header(
                rx.table.row(
                    rx.table.column_header_cell("Rubro", width="8%"),
                    rx.table.column_header_cell("Sub Rubro", width="10%"),
                    rx.table.column_header_cell("Matricula", width="10%"),
                    rx.table.column_header_cell("Familia", width="12%"),
                    rx.table.column_header_cell("Razon Social", width="25%"),
                    rx.table.column_header_cell("Origen", width="8%"),
                    rx.table.column_header_cell("Vencimiento", width="12%"),
                    rx.table.column_header_cell("Estado", width="8%"),
                    rx.table.column_header_cell("Id Familia", width="7%"),
                ),
            ),
            rx.table.body(
                rx.cond(
                    AppState.fams_show.length() > 0,
                    rx.foreach(AppState.fams_show, lambda fam: rx.table.row(
                    rx.table.cell(fam.rubro, style={"overflow": "hidden", "text-overflow": "ellipsis", "white-space": "nowrap"}),
                    rx.table.cell(fam.subrubro, style={"overflow": "hidden", "text-overflow": "ellipsis", "white-space": "nowrap"}),
                    rx.table.cell(fam.client, style={"overflow": "hidden", "text-overflow": "ellipsis", "white-space": "nowrap"}),
                    rx.table.cell(fam.family, style={"overflow": "hidden", "text-overflow": "ellipsis", "white-space": "nowrap"}),
                    rx.table.cell(fam.client, style={"overflow": "hidden", "text-overflow": "ellipsis", "white-space": "nowrap"}),
                    rx.table.cell(fam.origen, style={"overflow": "hidden", "text-overflow": "ellipsis", "white-space": "nowrap"}),
                    rx.table.cell(format_date_component(fam.expirationdate), 
                                    style={"white-space": "nowrap", "overflow": "hidden", "text-overflow": "ellipsis"}),
                    rx.table.cell(fam.status, style={"overflow": "hidden", "text-overflow": "ellipsis", "white-space": "nowrap"}),
                    rx.table.cell(rx.link(
                        fam.id,
                        href=f"https://panel.bvarg.com.ar/app/familias/{fam.id}",
                        is_external=True,
                        ), style={"overflow": "hidden", "text-overflow": "ellipsis", "white-space": "nowrap"}
                    ),
                    style={
                        "_hover": {"bg": rx.color("gray", 3)},
                        "height": "40px",
                        "max-height": "40px",
                        "overflow": "hidden"
                    },
                    align="center",
                )),
                    # Mostrar mensaje cuando no hay resultados
                    rx.table.row(
                        rx.table.cell(
                            rx.text("Ningún resultado encontrado", 
                                   style={"font-style": "italic", "color": "gray"}),
                            col_span=9,
                            text_align="center",
                            padding="20px"
                        )
                    )
                )
            ),
            variant="surface",
            size="1",
        ),
        width="100%",
    )
   
def table_cotizaciones()->rx.Component:
    return rx.vstack(
        search_bar_component(height="40px"),
        rx.cond(
            # Mostrar spinner mientras se cargan los datos (cuando cots_show está vacío pero se está cargando)
            (AppState.cots_show.length() == 0) & (AppState.values["search_value"] == ""),
            rx.vstack(
                rx.spinner(
                    size="3",
                    color="blue.500",
                    empty_color="gray.200",
                    thickness="4px",
                    speed="0.65s"
                ),
                rx.text("Cargando cotizaciones...", 
                       style={"color": colors.TextColor.MUTED.value, "font_style": "italic"}),
                spacing="3",
                align="center",
                padding="40px",
                width="100%"
            ),
            # Mostrar tabla cuando hay datos o cuando hay búsqueda activa
            rx.table.root(
                rx.table.header(
                    rx.table.row(
                        rx.table.column_header_cell("Número", width="15%"), #1
                        rx.table.column_header_cell("Fecha", width="15%"), #2
                        rx.table.column_header_cell("Razon Social", width="35%"), #3
                        rx.table.column_header_cell("Estado", width="20%"), #4
                        rx.table.column_header_cell("Id Cotización", width="15%"), #5
                    ),
                ),
                rx.table.body(
                    rx.cond(
                        AppState.cots_show.length() > 0,
                        rx.foreach(AppState.cots_show, lambda cot: rx.table.row(
                        rx.table.cell(cot.num + '-' + cot.year, style={"overflow": "hidden", "text-overflow": "ellipsis", "white-space": "nowrap"}), #1
                        rx.table.cell(format_date_component(cot.issuedate),
                                        style={"white-space": "nowrap", "overflow": "hidden", "text-overflow": "ellipsis"}), #2
                        rx.table.cell(cot.client, style={"overflow": "hidden", "text-overflow": "ellipsis", "white-space": "nowrap"}), #3
                        #rx.table.cell(cot.familys),
                        rx.table.cell(cot.status, style={"overflow": "hidden", "text-overflow": "ellipsis", "white-space": "nowrap"}), #4
                        rx.table.cell(rx.link(
                            cot.id,
                            href=f"https://panel.bvarg.com.ar/app/cotizaciones/{cot.id}",
                            is_external=True,
                            ), style={"overflow": "hidden", "text-overflow": "ellipsis", "white-space": "nowrap"} #5
                        ),
                        style={
                            "_hover": {"bg": rx.color("gray", 3)},
                            "height": "40px",
                            "max-height": "40px",
                            "overflow": "hidden"
                        },
                        align="center",
                    )),
                        # Mostrar mensaje cuando no hay resultados
                        rx.table.row(
                            rx.table.cell(
                                rx.text("Ningún resultado encontrado", 
                                       style={"font-style": "italic", "color": "gray"}),
                                col_span=5,
                                text_align="center",
                                padding="20px"
                            )
                        )
                    )
                ),
                variant="surface",
                size="1",
                width="100%",
            )
        ),
        width="100%",
    )

def calendar_component() -> rx.Component:         
    return rx.vstack(
            rx.heading("Calendario", size="4"),
            calendar(
                on_change=AppState.on_click_day_calendar,
    
            ),
            rx.spacer(),
            rx.link("Volver al inicio", 
                    href="/"
            ),
            rx.text(AppState.get_date),        
            background= "rgba(255, 255, 255, 0.9)",
            width="25%",
        )