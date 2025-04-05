"""Tests for the App class storage functionality."""

import pytest
from uplan.app import UplanApp


class TestAppStorage:
    """Test suite for App class storage operations."""

    def test_set_storage_item_initializes_storage(self):
        """Test that storage is initialized on first set operation."""
        app = UplanApp()
        assert not hasattr(app, "storage"), "Storage should not exist before first set"

        app.set_storage_item("test_key", "test_value")
        assert hasattr(app, "storage"), "Storage should be initialized after first set"
        assert isinstance(app.storage, dict), "Storage should be a dictionary"

    def test_set_storage_item_stores_values(self):
        """Test that values are correctly stored in app storage."""
        app = UplanApp()
        test_data = [
            ("string", "test_value"),
            ("number", 42),
            ("boolean", True),
            ("list", [1, 2, 3]),
            ("dict", {"key": "value"}),
        ]

        for key, value in test_data:
            app.set_storage_item(key, value)
            assert app.storage[key] == value, f"Value for {key} not stored correctly"

    def test_set_storage_item_overwrites_existing(self):
        """Test that existing keys are overwritten with new values."""
        app = UplanApp()
        app.set_storage_item("test_key", "initial_value")
        assert app.storage["test_key"] == "initial_value"

        app.set_storage_item("test_key", "updated_value")
        assert app.storage["test_key"] == "updated_value"
