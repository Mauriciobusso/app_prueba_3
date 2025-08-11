import reflex as rx
from .colors import Color, TextColor

# Bureau Veritas Design System
style = {
    # Global Typography and Base Styles
    "font_family": "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', sans-serif",
    "background_color": Color.LIGHT_GREY.value,
    "color": TextColor.DARK.value,
    "line_height": "1.6",
    "font_size": "14px",
    
    # Global Layout
    "min_height": "100vh",
    "margin": "0",
    "padding": "0",
    
    # Avatar Styling
    rx.avatar: {
        "border": f"3px solid {Color.PRIMARY_BLUE.value}",
        "box_shadow": f"0 4px 12px {Color.GREY.value}",
        "margin_top": "0.5em",
    },
    
    # Button Styling - Bureau Veritas Style
    rx.button: {
        "font_family": "'Inter', sans-serif",
        "font_weight": "500",
        "font_size": "14px",
        "padding": "12px 24px",
        "border_radius": "6px",
        "border": "none",
        "cursor": "pointer",
        "transition": "all 0.2s ease",
        "text_decoration": "none",
        "display": "inline-flex",
        "align_items": "center",
        "justify_content": "center",
        "white_space": "nowrap",
        
        # Primary button style (Bureau Veritas blue)
        "background_color": f"{Color.PRIMARY_BLUE.value}",
        "color": f"{Color.WHITE.value}",
        "box_shadow": f"0 2px 4px {Color.GREY.value}",
        
        "_hover": {
            "background_color": f"{Color.SECONDARY_BLUE.value}",
            "transform": "translateY(-1px)",
            "box_shadow": f"0 4px 8px {Color.GREY.value}",
        },
        
        "_active": {
            "transform": "translateY(0)",
            "box_shadow": f"0 2px 4px {Color.GREY.value}",
        },
        
        "_focus": {
            "outline": f"2px solid {Color.SECONDARY_BLUE.value}",
            "outline_offset": "2px",
        },
    },
    
    # Link Styling
    rx.link: {
        "color": f"{Color.SECONDARY_BLUE.value}",
        "text_decoration": "none",
        "transition": "color 0.2s ease",
        "_hover": {
            "color": f"{Color.PRIMARY_BLUE.value}",
            "text_decoration": "underline",
        },
    },
    
    # Heading Styling
    rx.heading: {
        "color": f"{TextColor.PRIMARY.value}",
        "font_weight": "600",
        "margin_bottom": "0.5em",
        "line_height": "1.3",
    },
    
    # Text Styling
    rx.text: {
        "color": f"{TextColor.DARK.value}",
        "line_height": "1.6",
        "margin_bottom": "0.75em",
    },
    
    # Badge/Label Styling
    rx.badge: {
        "background_color": f"{Color.LIGHT_BLUE.value}",
        "color": f"{Color.PRIMARY_BLUE.value}",
        "padding": "4px 8px",
        "border_radius": "4px",
        "font_size": "12px",
        "font_weight": "500",
        "text_align": "center",
    },
    
    # Table Styling
    rx.table.body: {
        "width": "100%",
        "border_collapse": "collapse",
        "background_color": f"{Color.WHITE.value}",
        "border_radius": "8px",
        "overflow": "hidden",
        "box_shadow": f"0 2px 8px {Color.GREY.value}",
    },
    
    # Input Styling
    rx.input: {
        "padding": "12px 16px",
        "border": f"1px solid {Color.MEDIUM_GREY.value}",
        "border_radius": "6px",
        "font_size": "14px",
        "font_family": "'Inter', sans-serif",
        "background_color": f"{Color.WHITE.value}",
        "transition": "border-color 0.2s ease, box-shadow 0.2s ease",
        
        "_focus": {
            "border_color": f"{Color.SECONDARY_BLUE.value}",
            "box_shadow": f"0 0 0 3px {Color.LIGHT_BLUE.value}",
            "outline": "none",
        },
        
        "_placeholder": {
            "color": f"{TextColor.MUTED.value}",
        },
    },
    
    # Select Styling
    rx.select: {
        "padding": "12px 16px",
        "border": f"1px solid {Color.MEDIUM_GREY.value}",
        "border_radius": "6px",
        "font_size": "14px",
        "font_family": "'Inter', sans-serif",
        "background_color": f"{Color.WHITE.value}",
        "cursor": "pointer",
        
        "_focus": {
            "border_color": f"{Color.SECONDARY_BLUE.value}",
            "box_shadow": f"0 0 0 3px {Color.LIGHT_BLUE.value}",
            "outline": "none",
        },
    },
    
    # Spinner Styling
    rx.spinner: {
        "color": f"{Color.SECONDARY_BLUE.value}",
    },
}

# Card styles for containers
card_style = {
    "background_color": f"{Color.WHITE.value}",
    "border_radius": "8px",
    "padding": "24px",
    "box_shadow": f"0 2px 8px {Color.GREY.value}",
    "border": f"1px solid {Color.LIGHT_GREY.value}",
}

# Navigation styles
nav_style = {
    "background_color": f"{Color.PRIMARY_BLUE.value}",
    "color": f"{Color.WHITE.value}",
    "padding": "16px 24px",
    "box_shadow": f"0 2px 4px {Color.GREY.value}",
}

# Container styles for main content
container_style = {
    "max_width": "1200px",
    "margin": "0 auto",
    "padding": "24px",
}

# Search bar specific styles
search_container_style = {
    "background_color": f"{Color.WHITE.value}",
    "padding": "16px",
    "border_radius": "8px",
    "box_shadow": f"0 2px 4px {Color.GREY.value}",
    "margin_bottom": "24px",
    "border": f"1px solid {Color.LIGHT_GREY.value}",
}
