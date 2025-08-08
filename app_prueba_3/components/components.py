import reflex as rx
from ..backend.app_state import AppState
from reflex_calendar import calendar
from ..styles import colors

def format_date_component(date_var):
    """
    Componente para formatear fechas de YYYY-mm-dd a dd/mm/YYYY
    """
    return rx.cond(
        date_var.contains("-") & (date_var.length() == 10),
        date_var.split("-")[2] + "/" + date_var.split("-")[1] + "/" + date_var.split("-")[0],
        date_var
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
        rx.hstack(
            rx.input(
                placeholder="Search here...",
                value=AppState.search_text,
                on_change=AppState.set_search_text,
                width="80%",
            ),
            rx.button(
                "🔍 Buscar",
                on_click=AppState.execute_search,
                width="20%",
                background_color="blue",
                color="white",
            ),
            width="100%",
            spacing="2",
        ),
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
                        "_hover": {"bg": rx.color("gray", 3)},
                        "height": "40px",
                        "max-height": "40px",
                        "overflow": "hidden"
                    },
                    align="center",
                )),
            ),
            variant="surface",
            size="3",
            width="100%",
        ),
        # Botón para cargar más resultados
        rx.cond(
            AppState.values["search_value"] != "",
            rx.vstack(
                rx.cond(
                    AppState.is_loading_more,
                    rx.spinner(size="2"),
                    rx.button(
                        "📄 Cargar más certificados",
                        on_click=AppState.load_more_certs,
                        variant="outline",
                        size="2",
                        width="200px",
                    )
                ),
                rx.text(
                    f"Mostrando {AppState.certs_show.length()} de {AppState.total_certs} certificados",
                    size="2",
                    color="gray"
                ),
                spacing="2",
                align="center",
                padding="20px"
            )
        ),
        width="100%",
    )

def table_familias()->rx.Component:
    return rx.vstack(
        rx.hstack(
            rx.input(
                placeholder="Search here...",
                value=AppState.search_text,
                on_change=AppState.set_search_text,
                width="80%",
            ),
            rx.button(
                "🔍 Buscar",
                on_click=AppState.execute_search,
                width="20%",
                background_color="blue",
                color="white",
            ),
            width="100%",
            spacing="2",
        ),
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
            ),
            variant="surface",
            size="1",
        ),
        # Botón para cargar más resultados
        rx.cond(
            AppState.values["search_value"] != "",
            rx.vstack(
                rx.cond(
                    AppState.is_loading_more,
                    rx.spinner(size="2"),
                    rx.button(
                        "📄 Cargar más familias",
                        on_click=AppState.load_more_fams,
                        variant="outline",
                        size="2",
                        width="200px",
                    )
                ),
                rx.text(
                    f"Mostrando {AppState.fams_show.length()} de {AppState.total_fams} familias",
                    size="2",
                    color="gray"
                ),
                spacing="2",
                align="center",
                padding="20px"
            )
        ),
        width="100%",
    )
   
def table_cotizaciones()->rx.Component:
    return rx.vstack(
        rx.hstack(
            rx.input(
                placeholder="Search here...",
                value=AppState.search_text,
                on_change=AppState.set_search_text,
                width="80%",
                height="40px",
            ),
            rx.button(
                "🔍 Buscar",
                on_click=AppState.execute_search,
                width="20%",
                background_color=colors.Color.GREY.value,
                color="white",
                height="40px",
            ),
            width="100%",
            spacing="2",
        ),
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
            ),
            variant="surface",
            size="1",
            width="100%",
        ),
        # Botón para cargar más resultados
        rx.cond(
            AppState.values["search_value"] != "",
            rx.vstack(
                rx.cond(
                    AppState.is_loading_more,
                    rx.spinner(size="2"),
                    rx.button(
                        "💼 Cargar más cotizaciones",
                        on_click=AppState.load_more_cots,
                        variant="outline",
                        size="2",
                        width="200px",
                    )
                ),
                rx.text(
                    f"Mostrando {AppState.cots_show.length()} de {AppState.total_cots} cotizaciones",
                    size="2",
                    color="gray"
                ),
                spacing="2",
                align="center",
                padding="20px"
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