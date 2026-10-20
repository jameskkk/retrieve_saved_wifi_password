import unittest
from unittest.mock import patch

from wifi_passwords.backends.linux import NetworkManagerBackend, _split_escaped


class LinuxBackendTests(unittest.TestCase):
    def test_split_escaped_nmcli_fields(self):
        self.assertEqual(
            _split_escaped(r"Cafe\: upstairs:abc-123:802-11-wireless"),
            ["Cafe: upstairs", "abc-123", "802-11-wireless"],
        )

    @patch("wifi_passwords.backends.linux.run")
    def test_profiles_and_password(self, run):
        run.side_effect = [
            "Cafe\\: upstairs:abc-123:802-11-wireless\nWired:def:802-3-ethernet\n",
            "Cafe: upstairs\nhunter2\n",
        ]
        network = NetworkManagerBackend().get_network("Cafe: upstairs")
        self.assertEqual(network.ssid, "Cafe: upstairs")
        self.assertEqual(network.password, "hunter2")
        self.assertEqual(network.profile_id, "abc-123")


if __name__ == "__main__":
    unittest.main()
