import ctypes
import xml.etree.ElementTree as ET
from typing import List, Optional

from .base import Backend
from ..errors import NetworkNotFoundError, PermissionDeniedError, WifiPasswordError
from ..models import SavedNetwork


def _xml_value(xml: str, local_name: str) -> Optional[str]:
    root = ET.fromstring(xml)
    for element in root.iter():
        if element.tag.rsplit("}", 1)[-1] == local_name:
            return element.text
    return None


class WindowsBackend(Backend):
    """Read WLAN profiles with the native Windows WLAN API."""

    ERROR_SUCCESS = 0
    ERROR_ACCESS_DENIED = 5
    WLAN_PROFILE_GET_PLAINTEXT_KEY = 4

    def _api(self):
        if not hasattr(ctypes, "WinDLL"):
            raise WifiPasswordError("The Windows WLAN backend can only run on Windows")
        return ctypes.WinDLL("wlanapi.dll")

    def _raise(self, code: int, action: str) -> None:
        if code == self.ERROR_ACCESS_DENIED:
            raise PermissionDeniedError(
                f"Windows denied permission to {action}; try an elevated terminal"
            )
        raise WifiPasswordError(f"Windows WLAN API failed to {action} (error {code})")

    def list_networks(self, include_passwords: bool = False) -> List[SavedNetwork]:
        return self._list_networks(include_passwords=include_passwords)

    def get_network(self, ssid: str) -> SavedNetwork:
        known = {network.ssid: network for network in self.list_networks()}
        if ssid not in known:
            raise NetworkNotFoundError(f"No saved Wi-Fi network named {ssid!r} was found")
        profile_name = known[ssid].profile_id or ssid
        matches = self._list_networks(
            include_passwords=True, only_profile=profile_name
        )
        if not matches:
            raise NetworkNotFoundError(f"No saved Wi-Fi network named {ssid!r} was found")
        return matches[0]

    def _list_networks(
        self, include_passwords: bool, only_profile: Optional[str] = None
    ) -> List[SavedNetwork]:
        from ctypes import wintypes

        wlanapi = self._api()

        class GUID(ctypes.Structure):
            _fields_ = [
                ("Data1", wintypes.DWORD),
                ("Data2", wintypes.WORD),
                ("Data3", wintypes.WORD),
                ("Data4", ctypes.c_ubyte * 8),
            ]

        class WLAN_INTERFACE_INFO(ctypes.Structure):
            _fields_ = [
                ("InterfaceGuid", GUID),
                ("strInterfaceDescription", wintypes.WCHAR * 256),
                ("isState", wintypes.DWORD),
            ]

        class WLAN_INTERFACE_INFO_LIST(ctypes.Structure):
            _fields_ = [
                ("dwNumberOfItems", wintypes.DWORD),
                ("dwIndex", wintypes.DWORD),
                ("InterfaceInfo", WLAN_INTERFACE_INFO * 1),
            ]

        class WLAN_PROFILE_INFO(ctypes.Structure):
            _fields_ = [
                ("strProfileName", wintypes.WCHAR * 256),
                ("dwFlags", wintypes.DWORD),
            ]

        class WLAN_PROFILE_INFO_LIST(ctypes.Structure):
            _fields_ = [
                ("dwNumberOfItems", wintypes.DWORD),
                ("dwIndex", wintypes.DWORD),
                ("ProfileInfo", WLAN_PROFILE_INFO * 1),
            ]

        wlanapi.WlanOpenHandle.argtypes = [
            wintypes.DWORD,
            wintypes.LPVOID,
            ctypes.POINTER(wintypes.DWORD),
            ctypes.POINTER(wintypes.HANDLE),
        ]
        wlanapi.WlanEnumInterfaces.argtypes = [
            wintypes.HANDLE,
            wintypes.LPVOID,
            ctypes.POINTER(ctypes.c_void_p),
        ]
        wlanapi.WlanGetProfileList.argtypes = [
            wintypes.HANDLE,
            ctypes.POINTER(GUID),
            wintypes.LPVOID,
            ctypes.POINTER(ctypes.c_void_p),
        ]
        wlanapi.WlanGetProfile.argtypes = [
            wintypes.HANDLE,
            ctypes.POINTER(GUID),
            wintypes.LPCWSTR,
            wintypes.LPVOID,
            ctypes.POINTER(ctypes.c_void_p),
            ctypes.POINTER(wintypes.DWORD),
            ctypes.POINTER(wintypes.DWORD),
        ]
        wlanapi.WlanFreeMemory.argtypes = [ctypes.c_void_p]
        wlanapi.WlanCloseHandle.argtypes = [wintypes.HANDLE, wintypes.LPVOID]

        negotiated = wintypes.DWORD()
        handle = wintypes.HANDLE()
        code = wlanapi.WlanOpenHandle(2, None, ctypes.byref(negotiated), ctypes.byref(handle))
        if code != self.ERROR_SUCCESS:
            self._raise(code, "open the WLAN service")

        networks = []
        interfaces_ptr = ctypes.c_void_p()
        try:
            code = wlanapi.WlanEnumInterfaces(handle, None, ctypes.byref(interfaces_ptr))
            if code != self.ERROR_SUCCESS:
                self._raise(code, "enumerate wireless interfaces")
            interfaces = ctypes.cast(
                interfaces_ptr, ctypes.POINTER(WLAN_INTERFACE_INFO_LIST)
            ).contents
            interface_array = ctypes.cast(
                ctypes.addressof(interfaces.InterfaceInfo),
                ctypes.POINTER(WLAN_INTERFACE_INFO * interfaces.dwNumberOfItems),
            ).contents

            for interface in interface_array:
                profiles_ptr = ctypes.c_void_p()
                code = wlanapi.WlanGetProfileList(
                    handle, ctypes.byref(interface.InterfaceGuid), None, ctypes.byref(profiles_ptr)
                )
                if code != self.ERROR_SUCCESS:
                    self._raise(code, "list wireless profiles")
                try:
                    profiles = ctypes.cast(
                        profiles_ptr, ctypes.POINTER(WLAN_PROFILE_INFO_LIST)
                    ).contents
                    profile_array = ctypes.cast(
                        ctypes.addressof(profiles.ProfileInfo),
                        ctypes.POINTER(WLAN_PROFILE_INFO * profiles.dwNumberOfItems),
                    ).contents
                    for profile in profile_array:
                        if only_profile is not None and profile.strProfileName != only_profile:
                            continue
                        password = None
                        error = None
                        ssid = profile.strProfileName
                        if include_passwords:
                            try:
                                xml = self._get_profile_xml(
                                    wlanapi, handle, interface.InterfaceGuid, ssid
                                )
                                ssid = _xml_value(xml, "name") or ssid
                                password = _xml_value(xml, "keyMaterial")
                                if password is None:
                                    error = "No PSK is stored (the network may be open or use enterprise authentication)"
                            except WifiPasswordError as exc:
                                error = str(exc)
                        networks.append(
                            SavedNetwork(
                                ssid=ssid,
                                password=password,
                                profile_id=profile.strProfileName,
                                interface=interface.strInterfaceDescription,
                                error=error,
                            )
                        )
                finally:
                    if profiles_ptr.value:
                        wlanapi.WlanFreeMemory(profiles_ptr)
        finally:
            if interfaces_ptr.value:
                wlanapi.WlanFreeMemory(interfaces_ptr)
            wlanapi.WlanCloseHandle(handle, None)

        # A profile can be visible on more than one interface.
        return list({(item.ssid, item.profile_id): item for item in networks}.values())

    def _get_profile_xml(self, wlanapi, handle, guid, profile_name: str) -> str:
        from ctypes import wintypes

        xml_ptr = ctypes.c_void_p()
        flags = wintypes.DWORD(self.WLAN_PROFILE_GET_PLAINTEXT_KEY)
        access = wintypes.DWORD()
        code = wlanapi.WlanGetProfile(
            handle,
            ctypes.byref(guid),
            profile_name,
            None,
            ctypes.byref(xml_ptr),
            ctypes.byref(flags),
            ctypes.byref(access),
        )
        if code != self.ERROR_SUCCESS:
            self._raise(code, f"read profile {profile_name!r}")
        try:
            return ctypes.wstring_at(xml_ptr)
        finally:
            wlanapi.WlanFreeMemory(xml_ptr)
