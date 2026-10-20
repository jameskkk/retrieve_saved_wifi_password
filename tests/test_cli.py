import io
import unittest
from contextlib import redirect_stdout
from unittest.mock import Mock, patch

from wifi_passwords.cli import main
from wifi_passwords.models import SavedNetwork


class CliTests(unittest.TestCase):
    @patch("wifi_passwords.cli.get_backend")
    def test_list_does_not_request_passwords_by_default(self, get_backend):
        backend = Mock()
        backend.list_networks.return_value = [SavedNetwork(ssid="Home")]
        get_backend.return_value = backend
        output = io.StringIO()
        with redirect_stdout(output):
            status = main(["list"])
        self.assertEqual(status, 0)
        self.assertEqual(output.getvalue(), "Home\n")
        backend.list_networks.assert_called_once_with(include_passwords=False)

    @patch("wifi_passwords.cli.get_backend")
    def test_get_prints_only_password(self, get_backend):
        backend = Mock()
        backend.get_network.return_value = SavedNetwork(ssid="Home", password="secret")
        get_backend.return_value = backend
        output = io.StringIO()
        with redirect_stdout(output):
            status = main(["get", "Home"])
        self.assertEqual(status, 0)
        self.assertEqual(output.getvalue(), "secret\n")


if __name__ == "__main__":
    unittest.main()
