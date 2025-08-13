from enum import Enum

class Color(Enum):
    # Bureau Veritas Modern Brand Colors - Inspired by bureauveritas.com
    PRIMARY_BLUE = "#1E3A8A"          # Deep professional blue (primary brand)
    SECONDARY_BLUE = "#3B82F6"        # Bright blue for interactions
    ACCENT_BLUE = "#60A5FA"           # Light blue for highlights
    NAVY = "#1E293B"                  # Deep navy for headers and dark elements
    
    # Modern Grays - Bureau Veritas style
    WHITE = "#FFFFFF"                 # Pure white
    GRAY_50 = "#F9FAFB"              # Ultra light background
    GRAY_100 = "#F3F4F6"             # Light background
    GRAY_200 = "#E5E7EB"             # Border color
    GRAY_300 = "#D1D5DB"             # Light borders
    GRAY_400 = "#9CA3AF"             # Muted text
    GRAY_500 = "#6B7280"             # Secondary text
    GRAY_600 = "#4B5563"             # Primary text (light mode)
    GRAY_700 = "#374151"             # Dark text
    GRAY_800 = "#1F2937"             # Very dark text
    GRAY_900 = "#111827"             # Darkest text
    
    # Semantic Colors - Modern and professional
    SUCCESS = "#10B981"               # Modern green for success
    WARNING = "#F59E0B"               # Amber for warnings
    ERROR = "#EF4444"                 # Red for errors
    INFO = "#3B82F6"                  # Blue for info
    
    # Accent Colors - Bureau Veritas inspired
    ACCENT_TEAL = "#14B8A6"          # Teal accent
    ACCENT_PURPLE = "#8B5CF6"        # Purple accent
    ACCENT_ORANGE = "#F97316"        # Orange accent
    
    # Legacy (for backward compatibility) - Updated with modern values
    LIGHT_GREY = "#F9FAFB"           # Now using modern gray-50
    MEDIUM_GREY = "#6B7280"          # Now using modern gray-500
    DARK_GREY = "#374151"            # Now using modern gray-700
    LIGHT_BLUE = "#EFF6FF"           # Very light blue background
    LIGHT = "#F9FAFB"
    DARK = "#1E293B"
    PRIMARY = "#1E3A8A"
    PURPLE = "#8B5CF6"
    YELLOW = "#F59E0B"
    ORANGE = "#F97316"
    GREY = "rgba(30, 58, 138, 0.05)"  # Very subtle blue-gray with transparency


class TextColor(Enum):
    # Modern Bureau Veritas Text Colors - Optimized for readability
    PRIMARY = "#111827"               # Darkest gray for primary text
    SECONDARY = "#4B5563"             # Medium gray for secondary text
    TERTIARY = "#6B7280"              # Lighter gray for tertiary text
    MUTED = "#9CA3AF"                 # Muted text
    INVERSE = "#FFFFFF"               # White text for dark backgrounds
    BRAND = "#1E3A8A"                 # Brand blue for brand text
    LIGHT = "#FFFFFF"                 # White text
    DARK = "#111827"                  # Dark text
    
    # Semantic text colors
    SUCCESS = "#065F46"               # Dark green for success text
    WARNING = "#92400E"               # Dark amber for warning text
    ERROR = "#991B1B"                 # Dark red for error text
    INFO = "#1E40AF"                  # Dark blue for info text