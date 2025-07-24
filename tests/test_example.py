"""Tests for the example module."""

from uptimer_python_sdk.example import add_numbers, hello_world


class TestHelloWorld:
    """Test cases for hello_world function."""

    def test_hello_world_returns_string(self) -> None:
        """Test that hello_world returns a string."""
        result = hello_world()
        assert isinstance(result, str)
        assert result == "Hello, World!"


class TestAddNumbers:
    """Test cases for add_numbers function."""

    def test_add_positive_numbers(self) -> None:
        """Test adding two positive numbers."""
        result = add_numbers(2, 3)
        assert result == 5

    def test_add_negative_numbers(self) -> None:
        """Test adding two negative numbers."""
        result = add_numbers(-2, -3)
        assert result == -5

    def test_add_zero(self) -> None:
        """Test adding zero to a number."""
        result = add_numbers(5, 0)
        assert result == 5

    def test_add_large_numbers(self) -> None:
        """Test adding large numbers."""
        result = add_numbers(1000000, 2000000)
        assert result == 3000000
