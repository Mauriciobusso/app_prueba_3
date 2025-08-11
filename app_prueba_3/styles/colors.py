from enum import Enum

class Color(Enum):
    # Bureau Veritas Brand Colors
    PRIMARY_BLUE = "#003366"        # Bureau Veritas Navy Blue (primary)
    SECONDARY_BLUE = "#0066CC"      # Lighter blue for accents
    LIGHT_BLUE = "#E6F2FF"         # Very light blue for backgrounds
    
    # Supporting Colors
    WHITE = "#FFFFFF"               # Clean white
    LIGHT_GREY = "#F8F9FA"         # Light background
    MEDIUM_GREY = "#6C757D"        # Text secondary
    DARK_GREY = "#343A40"          # Text primary
    
    # Accent Colors
    SUCCESS_GREEN = "#28A745"      # Success states
    WARNING_ORANGE = "#FD7E14"     # Warning states
    ERROR_RED = "#DC3545"          # Error states
    
    # Legacy (for backward compatibility)
    LIGHT = "#F8F9FA"
    DARK = "#003366"               # Now using Bureau Veritas blue
    PRIMARY = "#0066CC"
    PURPLE = "#7D00FE"
    YELLOW = "#FFA61E"
    ORANGE = "#FF5500"
    GREY = "rgba(0, 51, 102, 0.1)"  # Light Bureau Veritas blue with transparency


class TextColor(Enum):
    # Bureau Veritas Text Colors
    PRIMARY = "#003366"            # Bureau Veritas Navy for headings
    SECONDARY = "#6C757D"          # Medium grey for secondary text
    LIGHT = "#FFFFFF"              # White text on dark backgrounds
    DARK = "#343A40"               # Dark grey for body text
    MUTED = "#6C757D"              # Muted text