import unittest
from unittest.mock import patch

from wifi_passwords.backends.macos import MacOSBackend


HARDWARE = """Hardware Port: Wi-Fi
Device: en0
Ethernet Address: aa:bb:cc:dd:ee:ff

Hardware Port: Thunderbolt Bridge
Device: bridge0
Ethernet Address: 00:00:00:00:00:00
"""


class MacOSBackendTests(unittest.TestCase):
    @patch("wifi_passwords.backends.macos.run")
    def test_get_network(self, run):
        run.side_effect = [
            HARDWARE,
            "Preferred networks on en0:\n\tHome Wi-Fi\n\tCafe\n",
            "secret with spaces\n",
        ]
        network = MacOSBackend().get_network("Home Wi-Fi")
        self.assertEqual(network.ssid, "Home Wi-Fi")
        self.assertEqual(network.password, "secret with spaces")
        self.assertEqual(network.interface, "en0")


if __name__ == "__main__":
    unittest.main()
