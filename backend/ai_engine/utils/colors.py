"""
utils/colors.py — ANSI terminal color/style constants.

Centralised here so any module can import them without depending on the
full logger, and so switching to a rich/colorama backend only touches one file.
"""

RESET   = "\033[0m"
BOLD    = "\033[1m"
DIM     = "\033[2m"
CYAN    = "\033[96m"
GREEN   = "\033[92m"
YELLOW  = "\033[93m"
RED     = "\033[91m"
MAGENTA = "\033[95m"
BLUE    = "\033[94m"
WHITE   = "\033[97m"
