import reflex as rx
from .colors import Color, TextColor


style = {
    "font_family": "Inter, sans-serif",
    #"background-image": "linear-gradient(rgba(255, 255, 255, 0.5) 1px, transparent 1px)", # Rayas horizontales
    #"background-size": "100% 20px",
    "background_color": Color.DARK.value,
    "background_image": "url('/bg_dark_pattern.png')",
    "background_repeat": "repeat",
    "background_attachment": "fixed",
    "height": "100vh",
    "overflow": "hidden",

    "min_height": "100vh",  # Ensure the gradient covers the full height of the viewport
    rx.avatar: {
        "border": "4px solid white",
        "box_shadow": "lg",
        "margin_top": "0.25em",
    },
    rx.button: {
        "width": "100%",
        "height": "3em",
        "padding": "0.5em 1em",
        "border_radius": "full",
        "color": "white",
        "background_color": "rgba(0, 0, 0, 0.3)",  # Semi-transparent black
        "backdrop_filter": "blur(10px)",
        "white_space": "nowrap",
        "box_shadow": "0 4px 6px rgba(0, 0, 0, 0.1)",
        "transition": "all 0.3s ease",
        "_hover": {
            "transform": "translateY(-2px)",
            "box_shadow": "0 6px 8px rgba(0, 0, 0, 0.15)",
            "background_color": "rgba(0, 0, 0, 0.7)",  # Darker on hover
        },
    },
    rx.link: {
        "text_decoration": "none",
        "_hover": {
            "text_decoration": "none",
        },
    },
    rx.vstack: {
        "background_color": Color.DARK.value,
        "background_image": "url('/bg_dark_pattern.png')",
        "background_repeat": "repeat",
        "background_attachment": "fixed",
        #"background": "rgba(255, 255, 255, 0.7)",
        "backdrop_filter": "blur(20px)",
        "border_radius": "3px",
        "padding": "1em",  
        "box_shadow": "0 4px 16px rgba(0, 0, 0, 0.1)",  
        "color": "black",
        "align_items": "center",
        "text_align": "center",
       
    },
    rx.hstack: {
        "spacing": "2",
        "width": "100%",
        #"background": "rgba(255, 255, 255, 0.9)",
        "background_color": Color.DARK.value,
        "background_image": "url('/bg_dark_pattern.png')",
        "background_repeat": "repeat",
        "background_attachment": "fixed",
        "backdrop_filter": "blur(20px)",
        "border_radius": "15px",
        "color": "white",
        "align_items": "center",
        "align": "center",
        "text_align": "center",
        "padding": "0.5em",
        "padding_top":"0.5em",
        "padding_bottom":"0.5em",
        "justify_content":"space-between",
    },
    rx.heading: {
        "color": "black",
        "margin_bottom": "0.25em", 
    },
    rx.text: {
        "color": "black",
        "margin_bottom": "0.5em",
    },
    rx.badge: {
        "baackground": "white",
        "color": "black",
        "margin_bottom": "0.25em",
        "align_items": "center",
        "text_align": "center",
    }
}
