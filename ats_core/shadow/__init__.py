"""
Shadow testing framework for CryptoSignal v6.0 → newstandards migration.

This module provides infrastructure for running new implementations alongside
existing code without affecting production signals.
"""

from .config import ShadowConfig
from .comparator import ShadowComparator
from .logger import ShadowLogger

__all__ = ['ShadowConfig', 'ShadowComparator', 'ShadowLogger']
