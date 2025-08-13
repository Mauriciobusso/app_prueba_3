import reflex as rx
from .colors import Color, TextColor

# Bureau Veritas Modern Design System - Inspired by bureauveritas.com
style = {
    # Global Typography and Base Styles - Modern Bureau Veritas
    "font_family": "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Helvetica Neue', Arial, sans-serif",
    "background_color": Color.GRAY_50.value,
    "color": TextColor.PRIMARY.value,
    "line_height": "1.6",
    "font_size": "16px",
    "font_weight": "400",
    
    # Global Layout
    "min_height": "100vh",
    "margin": "0",
    "padding": "0",
    
    # Modern CSS Custom Properties - Bureau Veritas Design System
    ":root": {
        # Background colors
        "--color-background": Color.GRAY_50.value,
        "--color-surface": Color.WHITE.value,
        "--color-surface-alt": Color.GRAY_100.value,
        
        # Text colors
        "--color-text-primary": TextColor.PRIMARY.value,
        "--color-text-secondary": TextColor.SECONDARY.value,
        "--color-text-tertiary": TextColor.TERTIARY.value,
        "--color-text-muted": TextColor.MUTED.value,
        "--color-text-inverse": TextColor.INVERSE.value,
        "--color-text-brand": TextColor.BRAND.value,
        
        # Brand colors
        "--color-primary": Color.PRIMARY_BLUE.value,
        "--color-secondary": Color.SECONDARY_BLUE.value,
        "--color-accent": Color.ACCENT_BLUE.value,
        "--color-navy": Color.NAVY.value,
        
        # Semantic colors
        "--color-success": Color.SUCCESS.value,
        "--color-warning": Color.WARNING.value,
        "--color-error": Color.ERROR.value,
        "--color-info": Color.INFO.value,
        
        # Border and divider colors
        "--color-border": Color.GRAY_200.value,
        "--color-border-light": Color.GRAY_100.value,
        "--color-border-strong": Color.GRAY_300.value,
        
        # Shadow colors
        "--shadow-sm": "0 1px 2px 0 rgba(0, 0, 0, 0.05)",
        "--shadow": "0 1px 3px 0 rgba(0, 0, 0, 0.1), 0 1px 2px 0 rgba(0, 0, 0, 0.06)",
        "--shadow-md": "0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)",
        "--shadow-lg": "0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05)",
        "--shadow-xl": "0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04)",
        
        # Radii
        "--radius-sm": "0.25rem",
        "--radius": "0.375rem",
        "--radius-md": "0.5rem",
        "--radius-lg": "0.75rem",
        "--radius-xl": "1rem",
    },
    
    # Dark mode theme - Modern and elegant
    ".dark": {
        # Background colors
        "--color-background": Color.GRAY_900.value,
        "--color-surface": Color.GRAY_800.value,
        "--color-surface-alt": Color.GRAY_700.value,
        
        # Text colors (inverted and optimized for dark mode)
        "--color-text-primary": Color.GRAY_100.value,
        "--color-text-secondary": Color.GRAY_300.value,
        "--color-text-tertiary": Color.GRAY_400.value,
        "--color-text-muted": Color.GRAY_500.value,
        "--color-text-inverse": Color.GRAY_900.value,
        "--color-text-brand": Color.ACCENT_BLUE.value,
        
        # Brand colors (adjusted for dark mode)
        "--color-primary": Color.SECONDARY_BLUE.value,
        "--color-secondary": Color.ACCENT_BLUE.value,
        "--color-accent": "#93C5FD",  # Even lighter blue for dark mode
        "--color-navy": Color.GRAY_800.value,
        
        # Semantic colors (adjusted for dark mode)
        "--color-success": "#34D399",
        "--color-warning": "#FBBF24",
        "--color-error": "#F87171",
        "--color-info": Color.ACCENT_BLUE.value,
        
        # Border colors (adjusted for dark mode)
        "--color-border": Color.GRAY_700.value,
        "--color-border-light": Color.GRAY_800.value,
        "--color-border-strong": Color.GRAY_600.value,
        
        # Darker shadows for dark mode
        "--shadow-sm": "0 1px 2px 0 rgba(0, 0, 0, 0.3)",
        "--shadow": "0 1px 3px 0 rgba(0, 0, 0, 0.4), 0 1px 2px 0 rgba(0, 0, 0, 0.3)",
        "--shadow-md": "0 4px 6px -1px rgba(0, 0, 0, 0.4), 0 2px 4px -1px rgba(0, 0, 0, 0.3)",
        "--shadow-lg": "0 10px 15px -3px rgba(0, 0, 0, 0.4), 0 4px 6px -2px rgba(0, 0, 0, 0.3)",
        "--shadow-xl": "0 20px 25px -5px rgba(0, 0, 0, 0.4), 0 10px 10px -5px rgba(0, 0, 0, 0.3)",
    },
    
    # Avatar Styling - Modern Bureau Veritas
    rx.avatar: {
        "border": f"2px solid {Color.PRIMARY_BLUE.value}",
        "box_shadow": "var(--shadow-md)",
        "margin_top": "0.5em",
    },

    
    # Typography styles - Modern text hierarchy
    # Headings - Bureau Veritas inspired
    ".heading-1": {
        "font_size": "2.25rem",  # 36px
        "font_weight": "700",
        "line_height": "1.2",
        "color": "var(--color-text-primary)",
        "margin": "0 0 1rem 0",
        "letter_spacing": "-0.025em",
    },
    
    ".heading-2": {
        "font_size": "1.875rem",  # 30px
        "font_weight": "600",
        "line_height": "1.3",
        "color": "var(--color-text-primary)",
        "margin": "0 0 0.75rem 0",
        "letter_spacing": "-0.025em",
    },
    
    ".heading-3": {
        "font_size": "1.5rem",  # 24px
        "font_weight": "600",
        "line_height": "1.4",
        "color": "var(--color-text-primary)",
        "margin": "0 0 0.5rem 0",
    },
    
    ".heading-4": {
        "font_size": "1.25rem",  # 20px
        "font_weight": "600",
        "line_height": "1.5",
        "color": "var(--color-text-primary)",
        "margin": "0 0 0.5rem 0",
    },
    
    # Body text variants
    ".body-large": {
        "font_size": "1.125rem",  # 18px
        "line_height": "1.7",
        "color": "var(--color-text-primary)",
        "margin": "0 0 1rem 0",
    },
    
    ".body": {
        "font_size": "1rem",  # 16px
        "line_height": "1.6",
        "color": "var(--color-text-primary)",
        "margin": "0 0 1rem 0",
    },
    
    ".body-small": {
        "font_size": "0.875rem",  # 14px
        "line_height": "1.5",
        "color": "var(--color-text-secondary)",
        "margin": "0 0 0.75rem 0",
    },
    
    # Utility text styles
    ".text-muted": {
        "color": "var(--color-text-muted)",
    },
    
    ".text-primary": {
        "color": "var(--color-primary)",
        "font_weight": "600",
    },
    
    ".text-success": {
        "color": Color.SUCCESS.value,
        "font_weight": "600",
    },
    
    ".text-warning": {
        "color": Color.WARNING.value,
        "font_weight": "600",
    },
    
    ".text-error": {
        "color": Color.ERROR.value,
        "font_weight": "600",
    },
    
    # Professional quote styling
    ".blockquote": {
        "border_left": f"4px solid {Color.PRIMARY_BLUE.value}",
        "padding": "1rem 1.5rem",
        "margin": "1.5rem 0",
        "background_color": f"{Color.GRAY_50.value}",
        "font_style": "italic",
        "font_size": "1.125rem",
        "line_height": "1.7",
        "color": "var(--color-text-secondary)",
    },

    # Button styles
    rx.button: {
        "font_family": "'Inter', sans-serif",
        "font_weight": "500",
        "font_size": "14px",
        "line_height": "1.25",
        "padding": "0.75rem 1.5rem",
        "border_radius": "var(--radius-md)",
        "border": "1px solid transparent",
        "cursor": "pointer",
        "transition": "all 0.2s cubic-bezier(0.4, 0, 0.2, 1)",
        "text_decoration": "none",
        "display": "inline-flex",
        "align_items": "center",
        "justify_content": "center",
        "white_space": "nowrap",
        "position": "relative",
        "overflow": "hidden",
        
        # Primary button style - Bureau Veritas blue
        "background_color": "var(--color-primary)",
        "color": "var(--color-text-inverse)",
        "box_shadow": "var(--shadow-sm)",
        
        "_hover": {
            "background_color": Color.NAVY.value,
            "box_shadow": "var(--shadow-md)",
            "transform": "translateY(-1px)",
        },
        
        "_active": {
            "transform": "translateY(0)",
            "box_shadow": "var(--shadow-sm)",
        },
        
        "_focus": {
            "outline": "2px solid var(--color-secondary)",
            "outline_offset": "2px",
        },
        
        "_disabled": {
            "opacity": "0.5",
            "cursor": "not-allowed",
            "transform": "none",
        },
    },
    
    # Link Styling - Modern and accessible
    rx.link: {
        "color": "var(--color-text-brand)",
        "text_decoration": "none",
        "font_weight": "500",
        "transition": "all 0.2s ease",
        "position": "relative",
        
        "_hover": {
            "color": "var(--color-primary)",
            "text_decoration": "underline",
            "text_decoration_thickness": "2px",
            "text_underline_offset": "2px",
        },
        
        "_focus": {
            "outline": "2px solid var(--color-secondary)",
            "outline_offset": "2px",
            "border_radius": "var(--radius-sm)",
        },
    },
    
    # Heading Styling - Modern typography hierarchy
    rx.heading: {
        "color": "var(--color-text-primary)",
        "font_weight": "600",
        "line_height": "1.2",
        "margin_bottom": "0.5em",
        "letter_spacing": "-0.025em",
    },
    
    # Text Styling - Optimized readability
    rx.text: {
        "color": "var(--color-text-primary)",
        "line_height": "1.6",
        "margin_bottom": "1em",
    },
    
    # Badge/Label Styling - Modern pills
    rx.badge: {
        "background_color": Color.GRAY_100.value,
        "color": "var(--color-text-secondary)",
        "padding": "0.25rem 0.75rem",
        "border_radius": "9999px",
        "font_size": "0.75rem",
        "font_weight": "600",
        "text_align": "center",
        "text_transform": "uppercase",
        "letter_spacing": "0.05em",
        "border": f"1px solid {Color.GRAY_200.value}",
    },
    
    # Table Styling - Modern and clean
    rx.table.root: {
        "background_color": "var(--color-surface)",
        "border_radius": "var(--radius-lg)",
        "overflow": "hidden",
        "box_shadow": "var(--shadow)",
        "border": "1px solid var(--color-border)",
    },
    
    rx.table.header: {
        "background_color": Color.GRAY_50.value,
        "border_bottom": f"1px solid {Color.GRAY_200.value}",
    },
    
    rx.table.column_header_cell: {
        "padding": "0.75rem 1rem",
        "font_weight": "600",
        "font_size": "0.875rem",
        "color": "var(--color-text-secondary)",
        "text_transform": "uppercase",
        "letter_spacing": "0.05em",
    },
    
    rx.table.cell: {
        "padding": "1rem",
        "border_bottom": f"1px solid {Color.GRAY_100.value}",
        "font_size": "0.875rem",
        "color": "var(--color-text-primary)",
    },
    
    rx.table.row: {
        "transition": "background-color 0.2s ease",
        "_hover": {
            "background_color": Color.GRAY_50.value,
        },
    },
    
    # Input Styling - Modern forms with excellent UX
    rx.input: {
        "padding": "0.75rem 1rem",
        "border": "1px solid var(--color-border)",
        "border_radius": "var(--radius-md)",
        "font_size": "0.875rem",
        "font_family": "'Inter', sans-serif",
        "background_color": "var(--color-surface)",
        "color": "var(--color-text-primary)",
        "transition": "all 0.2s cubic-bezier(0.4, 0, 0.2, 1)",
        "outline": "none",
        
        "_focus": {
            "border_color": "var(--color-primary)",
            "box_shadow": f"0 0 0 3px {Color.PRIMARY_BLUE.value}20",  # 20% opacity
            "background_color": "var(--color-surface)",
        },
        
        "_hover": {
            "border_color": "var(--color-border-strong)",
        },
        
        "_placeholder": {
            "color": "var(--color-text-muted)",
            "opacity": "1",
        },
        
        "_disabled": {
            "background_color": Color.GRAY_100.value,
            "color": "var(--color-text-muted)",
            "cursor": "not-allowed",
        },
    },
    
    # Select Styling - Consistent with inputs
    rx.select: {
        "padding": "0.75rem 1rem",
        "border": "1px solid var(--color-border)",
        "border_radius": "var(--radius-md)",
        "font_size": "0.875rem",
        "font_family": "'Inter', sans-serif",
        "background_color": "var(--color-surface)",
        "color": "var(--color-text-primary)",
        "cursor": "pointer",
        "transition": "all 0.2s cubic-bezier(0.4, 0, 0.2, 1)",
        "outline": "none",
        
        "_focus": {
            "border_color": "var(--color-primary)",
            "box_shadow": f"0 0 0 3px {Color.PRIMARY_BLUE.value}20",
        },
        
        "_hover": {
            "border_color": "var(--color-border-strong)",
        },
    },
    
    # Spinner Styling - Modern and smooth
    rx.spinner: {
        "color": "var(--color-primary)",
        "animation": "spin 1s linear infinite",
    },
    
    # Card component styling
    ".card": {
        "background_color": "var(--color-surface)",
        "border": "1px solid var(--color-border)",
        "border_radius": "var(--radius-lg)",
        "box_shadow": "var(--shadow)",
        "padding": "1.5rem",
        "transition": "all 0.2s cubic-bezier(0.4, 0, 0.2, 1)",
        
        "_hover": {
            "box_shadow": "var(--shadow-md)",
            "transform": "translateY(-1px)",
        },
    },
    
    # Navigation bar styling
    ".navbar": {
        "background_color": "var(--color-primary)",
        "color": "var(--color-text-inverse)",
        "border_bottom": "1px solid var(--color-border)",
        "box_shadow": "var(--shadow)",
        "backdrop_filter": "blur(8px)",
        "position": "sticky",
        "top": "0",
        "z_index": "50",
    },
    
    # Status indicators
    ".status-success": {
        "background_color": Color.SUCCESS.value,
        "color": TextColor.INVERSE.value,
        "padding": "0.25rem 0.75rem",
        "border_radius": "9999px",
        "font_size": "0.75rem",
        "font_weight": "600",
    },
    
    ".status-warning": {
        "background_color": Color.WARNING.value,
        "color": TextColor.PRIMARY.value,
        "padding": "0.25rem 0.75rem",
        "border_radius": "9999px",
        "font_size": "0.75rem",
        "font_weight": "600",
    },
    
    ".status-error": {
        "background_color": Color.ERROR.value,
        "color": TextColor.INVERSE.value,
        "padding": "0.25rem 0.75rem",
        "border_radius": "9999px",
        "font_size": "0.75rem",
        "font_weight": "600",
    },
    
    # Modern utility classes
    ".glass-effect": {
        "background": f"rgba(255, 255, 255, 0.9)",
        "backdrop_filter": "blur(10px)",
        "border": f"1px solid rgba(255, 255, 255, 0.2)",
    },
    
    ".gradient-primary": {
        "background": f"linear-gradient(135deg, {Color.PRIMARY_BLUE.value} 0%, {Color.SECONDARY_BLUE.value} 100%)",
    },
    
    ".text-gradient": {
        "background": f"linear-gradient(135deg, {Color.PRIMARY_BLUE.value} 0%, {Color.ACCENT_BLUE.value} 100%)",
        "background_clip": "text",
        "color": "transparent",
    },

}
