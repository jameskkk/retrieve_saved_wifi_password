import unittest

from wifi_passwords.backends.windows import _xml_value


PROFILE_XML = """<?xml version="1.0"?>
<WLANProfile xmlns="http://www.microsoft.com/networking/WLAN/profile/v1">
  <name>Office Wi-Fi</name>
  <SSIDConfig><SSID><name>Office Wi-Fi</name></SSID></SSIDConfig>
  <MSM><security><sharedKey><keyMaterial>correct horse battery staple</keyMaterial></sharedKey></security></MSM>
</WLANProfile>
"""


class WindowsBackendTests(unittest.TestCase):
    def test_profile_xml_with_namespace(self):
        self.assertEqual(_xml_value(PROFILE_XML, "name"), "Office Wi-Fi")
        self.assertEqual(
            _xml_value(PROFILE_XML, "keyMaterial"),
            "correct horse battery staple",
        )


if __name__ == "__main__":
    unittest.main()
