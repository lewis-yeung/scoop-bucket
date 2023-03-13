import argparse
import ctypes
import os
import platform
import signal
import sys
import winreg
import logging
from typing import Union

class RegValueInfo:
	def __init__(
	  self,
	  name: Union[str, None],
	  type: Union[int, None] = None,
	  data: Union[str, int, None] = None,
	  delete: bool = False,
	):
		self.name = name
		self.type = type
		self.data = data
		self.delete = delete

class Installer:
	REG_BASE_KEYS = {
	  'HKCR': winreg.HKEY_CLASSES_ROOT,
	  'HKCU': winreg.HKEY_CURRENT_USER,
	  'HKLM': winreg.HKEY_LOCAL_MACHINE,
	  'HKU': winreg.HKEY_USERS,
	  'HKCC': winreg.HKEY_CURRENT_CONFIG,
	}
	PYTHON_ROOT = os.path.realpath(os.path.dirname(sys.executable))
	PYTHON_VERSION_TUPLE = platform.python_version_tuple()
	PYTHON_VERSION = '.'.join(PYTHON_VERSION_TUPLE[:2])
	PYTHON_VERSION_FULL = '.'.join(PYTHON_VERSION_TUPLE)
	PYTHON_VERSION_CLEAN = ''.join(PYTHON_VERSION_TUPLE)
	PYTHON_ARCH = platform.architecture()[0][:2]
	REG_VIEW = winreg.KEY_WOW64_64KEY if PYTHON_ARCH == '64' else winreg.KEY_WOW64_32KEY

	FLAG_WRITE = 'write'
	FLAG_REMOVE = 'remove'
	FLAG_GLOBAL = 'global'

	@classmethod
	def run(cls):
		if sys.platform != 'win32':
			logging.error('Cannot run on OS other than Windows.')
			sys.exit(1)
		if sys.version_info < (3, 8):
			logging.error('This script requires Python 3.8 or higher.')
			sys.exit(1)
		signal.signal(signal.SIGINT, signal.SIG_IGN)
		signal.signal(signal.SIGBREAK, signal.SIG_IGN)
		cls.parse_args()
		if not cls.is_admin():
			logging.error('The operation requires administrator privileges.')
			sys.exit(1)
		cls.actions = {
		  cls.FLAG_WRITE: cls.write_installation_info,
		  cls.FLAG_REMOVE: cls.remove_installation_info,
		}
		cls.failed_installation = False
		cls.original_regs: dict[str, list[RegValueInfo]] = {}
		cls.base_key_name = 'HKLM' if cls.args[cls.FLAG_GLOBAL] else 'HKCU'
		sys.exit(cls.actions[cls.action]())

	@classmethod
	def is_admin(cls) -> bool:
		return ctypes.windll.shell32.IsUserAnAdmin()

	@classmethod
	def parse_args(cls):
		parser = argparse.ArgumentParser(
		  description='Write/Remove Python installation info to/from Windows registry, which allows/disallows apps and third-party installers to discover the Python installation that runs this script.',
		  epilog=f'''
NOTES:
  - Elevated privileges are required for modifying the registry.
  - Run this script as:
      <path_to_python_exe> "{os.path.basename(__file__)}" [flags]
    where `<path_to_python_exe>` should be an absolute path to the Python executable that you want to register/unregister.
''',
		  formatter_class=argparse.RawTextHelpFormatter,
		)
		group_actions = parser.add_mutually_exclusive_group()
		group_actions.add_argument(
		  '-w',
		  '--write',
		  action='store_true',
		  help='write installation info to registry',
		  dest=cls.FLAG_WRITE,
		)
		group_actions.add_argument(
		  '-r',
		  '--remove',
		  action='store_true',
		  help='remove installation info from registry',
		  dest=cls.FLAG_REMOVE,
		)
		parser.add_argument(
		  '-g',
		  '--global',
		  action='store_true',
		  help='operate on subkeys under "HKLM" (for all users)',
		  dest=cls.FLAG_GLOBAL,
		)
		if len(sys.argv) == 1:
			parser.print_help()
			sys.exit(0)
		cls.args = vars(parser.parse_args())
		if cls.args[cls.FLAG_WRITE]:
			cls.action = cls.FLAG_WRITE
		elif cls.args[cls.FLAG_REMOVE]:
			cls.action = cls.FLAG_REMOVE
		else:
			logging.error('No operation specified.')
			sys.exit(1)

	@classmethod
	def write_installation_info(cls) -> int:
		regs: dict[str, list[RegValueInfo]] = {
		  f'{cls.base_key_name}\\Software\\Python\\PythonCore': [
		    RegValueInfo('DisplayName', winreg.REG_SZ, 'Python Software Foundation'),
		    RegValueInfo('SupportUrl', winreg.REG_SZ, 'http://www.python.org/'),
		  ],
		  f'{cls.base_key_name}\\Software\\Python\\PythonCore\\{cls.PYTHON_VERSION}': [
		    RegValueInfo('DisplayName', winreg.REG_SZ, f'Python {cls.PYTHON_VERSION} ({cls.PYTHON_ARCH}-bit)'),
		    RegValueInfo('SupportUrl', winreg.REG_SZ, 'http://www.python.org/'),
		    RegValueInfo('SysArchitecture', winreg.REG_SZ, f'{cls.PYTHON_ARCH}bit'),
		    RegValueInfo('SysVersion', winreg.REG_SZ, cls.PYTHON_VERSION),
		    RegValueInfo('Version', winreg.REG_SZ, cls.PYTHON_VERSION_FULL),
		  ],
		  f'{cls.base_key_name}\\Software\\Python\\PythonCore\\{cls.PYTHON_VERSION}\\Help\\Main Python Documentation': [
		    RegValueInfo(None, winreg.REG_SZ, f'{cls.PYTHON_VERSION}\\Doc\\python{cls.PYTHON_VERSION_CLEAN}.chm'),
		    RegValueInfo('DisplayName', winreg.REG_SZ, f'Python {cls.PYTHON_VERSION_FULL} Documentation'),
		  ],
		  f'{cls.base_key_name}\\Software\\Python\\PythonCore\\{cls.PYTHON_VERSION}\\InstallPath': [
		    RegValueInfo(None, winreg.REG_SZ, cls.PYTHON_ROOT),
		    RegValueInfo('ExecutablePath', winreg.REG_SZ, f'{cls.PYTHON_ROOT}\\python.exe'),
		    RegValueInfo('WindowedExecutablePath', winreg.REG_SZ, f'{cls.PYTHON_ROOT}\\pythonw.exe'),
		  ],
		  f'{cls.base_key_name}\\Software\\Python\\PythonCore\\{cls.PYTHON_VERSION}\\PythonPath': [
		    RegValueInfo(None, winreg.REG_SZ, f'{cls.PYTHON_ROOT}\\Lib\\;{cls.PYTHON_ROOT}\\DLLs\\'),
		  ],
		}
		logging.info('Writing installation info...')
		if not cls.write_regs(regs, True):
			cls.failed_installation = True
			logging.error('Aborted.')
			logging.info('Cleaning up...')
			cls.write_regs(cls.original_regs, False)
			return 1
		logging.info('All done.')
		return 0

	@classmethod
	def remove_installation_info(cls) -> int:
		regs: dict[str, list[RegValueInfo]] = {
		  f'-{cls.base_key_name}\\Software\\Python\\PythonCore\\{cls.PYTHON_VERSION}': None,
		}
		logging.info('Removing installation info...')
		if not cls.write_regs(regs, False):
			logging.error('Aborted.')
			return 1
		logging.info('All done.')
		return 0

	@classmethod
	def add_reg_key(cls, full_key_path: str, values: list[RegValueInfo], backup: bool):
		if cls.failed_installation:
			backup = False
		new_key = False
		basekey_name, key_path = full_key_path.split('\\', 1)
		try:
			winreg.OpenKeyEx(cls.REG_BASE_KEYS[basekey_name], key_path, access=winreg.KEY_READ | winreg.KEY_WRITE | cls.REG_VIEW).Close()
		except OSError:
			if backup and (('-' + full_key_path) not in cls.original_regs):
				# Store the hyphen-prefixed path of an nonexistent key.
				cls.original_regs['-' + full_key_path] = None
				new_key = True
		else:
			if backup and (full_key_path not in cls.original_regs):
				# Store the path of an existing key.
				cls.original_regs[full_key_path] = []
		try:
			with winreg.CreateKeyEx(cls.REG_BASE_KEYS[basekey_name], key_path, access=winreg.KEY_READ | winreg.KEY_WRITE | cls.REG_VIEW) as key:
				if len(values) == 0:
					return True
				for v in values:
					if backup and not new_key:
						try:
							data, type = winreg.QueryValueEx(key, v.name)
						except:
							cls.original_regs[full_key_path].append(RegValueInfo(v.name, delete=True))
						else:
							# Store the original value.
							cls.original_regs[full_key_path].append(RegValueInfo(v.name, type, data))
					if v.delete:
						try:
							winreg.DeleteValue(key, v.name)
						except:
							if cls.failed_installation:
								continue
							else:
								logging.error(f'Failed to remove value [{v.name}] under [{full_key_path}] in the {cls.PYTHON_ARCH}-bit registry view.')
								return False
					else:
						try:
							winreg.SetValueEx(key, v.name, 0, v.type, v.data)
						except Exception as e:
							if cls.failed_installation:
								continue
							else:
								logging.error(f'Failed to set value [{v.name}] (type: [{v.type}], data: [{v.data}]) under [{full_key_path}] in the {cls.PYTHON_ARCH}-bit registry view.')
								return False
		except OSError as e:
			if cls.failed_installation:
				pass
			else:
				logging.error(f'Failed to open/create key [{full_key_path}] in the {cls.PYTHON_ARCH}-bit registry view.')
				return False
		return True

	@classmethod
	def delete_reg_keytree(cls, full_key_path: str, backup: bool):
		if cls.failed_installation:
			backup = False
		basekey_name, key_path = full_key_path.split('\\', 1)
		try:
			with winreg.OpenKeyEx(cls.REG_BASE_KEYS[basekey_name], key_path, access=winreg.KEY_READ | winreg.KEY_WRITE | cls.REG_VIEW) as key:
				if backup and (full_key_path not in cls.original_regs):
					# Store the path of the key to be deleted.
					cls.original_regs[full_key_path] = []
				while True:
					try:
						if not cls.delete_reg_keytree(os.path.join(full_key_path, winreg.EnumKey(key, 0)), backup):
							return False
					except OSError:
						break
				while True:
					try:
						value_name, value_data, data_type = winreg.EnumValue(key, 0)
						if backup:
							# Store the original value.
							cls.original_regs[full_key_path].append(RegValueInfo(value_name, data_type, value_data))
						try:
							winreg.DeleteValue(key, value_name)
						except Exception as e:
							if cls.failed_installation:
								continue
							else:
								logging.error(f'Failed to remove value [{value_name}] under [{full_key_path}] in the {cls.PYTHON_ARCH}-bit registry view.')
								return False
					except OSError:
						break
		except OSError:
			# No such key, just return.
			return True
		supkey_path, key_name = key_path.rsplit('\\', 1)
		try:
			with winreg.OpenKeyEx(cls.REG_BASE_KEYS[basekey_name], supkey_path, access=winreg.KEY_READ | winreg.KEY_WRITE | cls.REG_VIEW) as supkey:
				winreg.DeleteKey(supkey, key_name)
		except OSError as e:
			if cls.failed_installation:
				pass
			else:
				logging.error(f'Failed to remove key [{full_key_path}] in the {cls.PYTHON_ARCH}-bit registry view.')
				return False
		return True

	@classmethod
	def write_regs(cls, regs: dict[str, list[RegValueInfo]], backup: bool):
		for (full_key_path, values) in regs.items():
			# Check if a keytree should be deleted.
			if full_key_path.startswith('-'):
				delete_key = True
				full_key_path = full_key_path[1:]
			else:
				delete_key = False
			if delete_key:
				if not cls.delete_reg_keytree(full_key_path, backup):
					return False
			else:
				if not cls.add_reg_key(full_key_path, values, backup):
					return False
		return True

if __name__ == '__main__':
	logging.basicConfig(
	  format='[%(asctime)s] (%(levelname)s) {%(module)s}: %(message)s',
	  datefmt='%Y-%m-%d %H:%M:%S',
	  level=logging.NOTSET,
	)
	for (level, name) in {
	  logging.CRITICAL: 'F',
	  logging.ERROR: 'E',
	  logging.WARNING: 'W',
	  logging.INFO: 'I',
	  logging.DEBUG: 'D',
	}.items():
		logging.addLevelName(level, name)
	Installer.run()
