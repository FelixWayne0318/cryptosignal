"""
Shadow configuration manager.

Loads and manages shadow.json configuration for controlled testing of new features.
"""

import json
from pathlib import Path
from typing import Dict, List, Any, Optional


class ShadowConfig:
    """Manages shadow run configuration."""

    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize shadow configuration.

        Args:
            config_path: Path to shadow.json. If None, uses config/shadow.json
        """
        if config_path is None:
            config_path = Path(__file__).parent.parent.parent / "config" / "shadow.json"

        self.config_path = Path(config_path)
        self.config = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from JSON file."""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Shadow config not found: {self.config_path}")

        with open(self.config_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    @property
    def enabled(self) -> bool:
        """Check if shadow mode is enabled."""
        return self.config.get('enabled', False)

    @property
    def mode(self) -> str:
        """Get shadow mode: 'shadow', 'canary', or 'disabled'."""
        return self.config.get('mode', 'disabled')

    @property
    def test_symbols(self) -> List[str]:
        """Get list of symbols to test."""
        return self.config.get('test_symbols', [])

    def is_feature_enabled(self, feature: str) -> bool:
        """
        Check if a specific feature is enabled for testing.

        Args:
            feature: Feature name (e.g., 'dataqual', 'standardization_chain')

        Returns:
            True if feature should be tested
        """
        return self.config.get('features_to_test', {}).get(feature, False)

    def get_feature_config(self, feature: str) -> Dict[str, Any]:
        """
        Get configuration for a specific feature.

        Args:
            feature: Feature name

        Returns:
            Feature configuration dict
        """
        return self.config.get('feature_configs', {}).get(feature, {})

    def should_test_symbol(self, symbol: str) -> bool:
        """
        Check if symbol should be included in shadow testing.

        Args:
            symbol: Trading symbol (e.g., 'BTCUSDT')

        Returns:
            True if symbol is in test set
        """
        if not self.enabled:
            return False

        # Empty test_symbols means test all
        if not self.test_symbols:
            return True

        return symbol in self.test_symbols
