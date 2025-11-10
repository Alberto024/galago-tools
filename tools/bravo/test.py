import winreg
import os

# Search for the COM object by CLSID
clsid = "{c912fe20-06a6-4b7c-9bfb-f7b3ee29092e}"

# Check registry for the native DLL path
try:
    key_path = f"CLSID\\{clsid}\\InprocServer32"
    key = winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, key_path)
    dll_path, _ = winreg.QueryValueEx(key, None)
    print(f"Native DLL found: {dll_path}")
    winreg.CloseKey(key)
except Exception as e:
    print(f"Error: {e}")

# Also check TypeLib
try:
    key_path = f"CLSID\\{clsid}\\TypeLib"
    key = winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, key_path)
    typelib_guid, _ = winreg.QueryValueEx(key, None)
    print(f"TypeLib GUID: {typelib_guid}")
    winreg.CloseKey(key)
except Exception as e:
    print(f"Error: {e}")