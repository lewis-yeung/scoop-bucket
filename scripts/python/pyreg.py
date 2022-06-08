import argparse
import ctypes
import os
import platform
import re
import signal
import sys
import time
import typing
import winreg

class RegValueInfo:
	def __init__(self, name: 'str | None', type: 'int | None' = None, data: 'str | int | None' = None, delete: bool = False):
		self.name = name
		self.type = type
		self.data = data
		self.delete = delete

class Installer:
	OPT_WRITE = 'write'
	OPT_REMOVE = 'remove'
	OPT_GLOBAL = 'global'

	@classmethod
	def init(cls):
		if sys.platform != "win32":
			cls.error('😅 Cannot run on OS other than Windows.\n')
			sys.exit(-1)
		if sys.version_info < (3, 8):
			cls.error('You need Python 3.8+ to run this script.\n')
			sys.exit(-1)
		signal.signal(signal.SIGINT, signal.SIG_IGN)
		signal.signal(signal.SIGBREAK, signal.SIG_IGN)
		cls.parse_args()
		if not cls.is_admin():
			cls.error('Please run as administrator.\n')
			sys.exit(2)
		cls.REG_BASE_KEYS = {
		  'HKCR': winreg.HKEY_CLASSES_ROOT,
		  'HKCU': winreg.HKEY_CURRENT_USER,
		  'HKLM': winreg.HKEY_LOCAL_MACHINE,
		  'HKU': winreg.HKEY_USERS,
		  'HKCC': winreg.HKEY_CURRENT_CONFIG,
		}
		cls.failed_registration = False
		cls.original_regs: dict[str, list[RegValueInfo]] = {}
		cls.actions = {
		  cls.OPT_WRITE: cls.write_installation_info,
		  cls.OPT_REMOVE: cls.remove_installation_info,
		}
		cls.python_root = os.path.realpath(os.path.dirname(sys.executable))
		python_version = platform.python_version_tuple()
		cls.python_version = '%s.%s' % python_version[:2]
		cls.python_version_full = '%s.%s.%s' % python_version
		cls.python_version_clean = '%s%s%s' % python_version
		cls.python_arch = platform.architecture()[0][:2]
		if cls.python_arch == '64':
			cls.reg_view = winreg.KEY_WOW64_64KEY
		else:
			cls.reg_view = winreg.KEY_WOW64_32KEY
		if cls.args[cls.OPT_GLOBAL]:
			cls.base_key_name = 'HKLM'
		else:
			cls.base_key_name = 'HKCU'

	@classmethod
	def run(cls):
		cls.init()
		sys.exit(cls.actions[cls.action]())

	@classmethod
	def is_admin(cls) -> bool:
		return ctypes.windll.shell32.IsUserAnAdmin()

	@classmethod
	def parse_args(cls):
		parser = argparse.ArgumentParser(
		  prog='<path_to_python_exe> %s' % os.path.basename(__file__),
		  description="Write/Remove Python installation info to/from Windows registry, which allows/disallows apps and third-party installers to discover the Python installation that runs this script.",
		  epilog='''
NOTES:
  - Elevated privileges are required for modifying the registry.
  - <path_to_python_exe> should be an absolute path to the Python executable that you want to register/unregister.
''',
		  formatter_class=argparse.RawTextHelpFormatter,
		)
		group_actions = parser.add_mutually_exclusive_group()
		group_actions.add_argument(
		  '-w',
		  '--write',
		  action='store_true',
		  help='write installation info',
		  dest=cls.OPT_WRITE,
		)
		group_actions.add_argument(
		  '-r',
		  '--remove',
		  action='store_true',
		  help='remove installation info',
		  dest=cls.OPT_REMOVE,
		)
		parser.add_argument(
		  '-g',
		  '--global',
		  action='store_true',
		  help="operate on subkeys under 'HKLM' (for all users)",
		  dest=cls.OPT_GLOBAL,
		)
		if len(sys.argv) == 1:
			parser.print_help()
			sys.exit(0)
		cls.args = vars(parser.parse_args())
		if cls.args[cls.OPT_WRITE]:
			cls.action = cls.OPT_WRITE
		elif cls.args[cls.OPT_REMOVE]:
			cls.action = cls.OPT_REMOVE
		else:
			cls.error('No operation specified.\n')
			sys.exit(1)

	@classmethod
	def write_installation_info(cls) -> int:
		regs: dict[str, list[RegValueInfo]] = {
		  R'%s\Software\Python\PythonCore' % cls.base_key_name: [
		    RegValueInfo('DisplayName', winreg.REG_SZ, 'Python Software Foundation'),
		    RegValueInfo('SupportUrl', winreg.REG_SZ, 'http://www.python.org/'),
		  ],
		  R'%s\Software\Python\PythonCore\%s' % (cls.base_key_name, cls.python_version): [
		    RegValueInfo('DisplayName', winreg.REG_SZ, 'Python %s (%s-bit)' % (cls.python_version, cls.python_arch)),
		    RegValueInfo('SupportUrl', winreg.REG_SZ, 'http://www.python.org/'),
		    RegValueInfo('SysArchitecture', winreg.REG_SZ, '%sbit' % cls.python_arch),
		    RegValueInfo('SysVersion', winreg.REG_SZ, cls.python_version),
		    RegValueInfo('Version', winreg.REG_SZ, cls.python_version_full),
		  ],
		  R'%s\Software\Python\PythonCore\%s\Help\Main Python Documentation' % (cls.base_key_name, cls.python_version): [
		    RegValueInfo(None, winreg.REG_SZ, R'%s\Doc\python%s.chm' % (cls.python_version, cls.python_version_clean)),
		    RegValueInfo('DisplayName', winreg.REG_SZ, 'Python %s Documentation' % cls.python_version_full),
		  ],
		  R'%s\Software\Python\PythonCore\%s\InstallPath' % (cls.base_key_name, cls.python_version): [
		    RegValueInfo(None, winreg.REG_SZ, cls.python_root),
		    RegValueInfo('ExecutablePath', winreg.REG_SZ, R'%s\python.exe' % cls.python_root),
		    RegValueInfo('WindowedExecutablePath', winreg.REG_SZ, R'%s\pythonw.exe' % cls.python_root),
		  ],
		  R'%s\Software\Python\PythonCore\%s\PythonPath' % (cls.base_key_name, cls.python_version): [
		    RegValueInfo(None, winreg.REG_SZ, '%s\\Lib\\;%s\\DLLs\\' % (cls.python_root, cls.python_root)),
		  ],
		}
		cls.info('Writing installation info...\n')
		if not cls.write_regs(regs, True):
			cls.failed_registration = True
			cls.error('Aborted. Cleaning up...\n')
			cls.write_regs(cls.original_regs, False)
			return 1
		cls.info('All done.\n')
		return 0

	@classmethod
	def remove_installation_info(cls) -> int:
		regs: dict[str, list[RegValueInfo]] = {
		  R'-%s\Software\Python\PythonCore\%s' % (cls.base_key_name, cls.python_version): None,
		}
		cls.info('Removing installation info...\n')
		if not cls.write_regs(regs, False):
			cls.error('Aborted.\n')
			return 1
		cls.info('All done.\n')
		return 0

	@classmethod
	def add_reg_key(cls, full_key_path: str, values: list[RegValueInfo], backup: bool):
		if cls.failed_registration:
			backup = False
		new_key = False
		basekey_name, key_path = full_key_path.split('\\', 1)
		try:
			winreg.OpenKeyEx(cls.REG_BASE_KEYS[basekey_name], key_path, access=winreg.KEY_READ | winreg.KEY_WRITE | cls.reg_view).Close()
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
			with winreg.CreateKeyEx(cls.REG_BASE_KEYS[basekey_name], key_path, access=winreg.KEY_READ | winreg.KEY_WRITE | cls.reg_view) as key:
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
						except Exception as e:
							if cls.failed_registration:
								continue
							else:
								cls.error('Failed to remove the value [\x1b[95m%s\x1b[0m] under [\x1b[96m%s\x1b[0m] in the %s-bit registry view.\n\x1b[1;33m[DETAILS]:\x1b[0m\n%s\n' % (v.name, full_key_path, cls.python_arch, e))
								return False
					else:
						try:
							winreg.SetValueEx(key, v.name, 0, v.type, v.data)
						except Exception as e:
							if cls.failed_registration:
								continue
							else:
								cls.error('Failed to set the value [\x1b[95m%s\x1b[0m] (with type [\x1b[94m%s\x1b[0m] and data [\x1b[92m%s\x1b[0m]) under [\x1b[96m%s\x1b[0m] in the %s-bit registry view.\n\x1b[1;33m[DETAILS]:\x1b[0m\n%s\n' % (v.name, v.type, v.data, full_key_path, cls.python_arch, e))
								return False
		except OSError as e:
			if cls.failed_registration:
				pass
			else:
				cls.error('Failed to open/create the key [\x1b[96m%s\x1b[0m] in the %s-bit registry view.\n\x1b[1;33m[DETAILS]:\x1b[0m\n%s\n' % (full_key_path, cls.python_arch, e))
				return False
		return True

	@classmethod
	def delete_reg_keytree(cls, full_key_path: str, backup: bool):
		if cls.failed_registration:
			backup = False
		basekey_name, key_path = full_key_path.split('\\', 1)
		try:
			with winreg.OpenKeyEx(cls.REG_BASE_KEYS[basekey_name], key_path, access=winreg.KEY_READ | winreg.KEY_WRITE | cls.reg_view) as key:
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
							if cls.failed_registration:
								continue
							else:
								cls.error('Failed to remove the value [\x1b[95m%s\x1b[0m] under [\x1b[96m%s\x1b[0m] in the %s-bit registry view.\n\x1b[1;33m[DETAILS]:\x1b[0m\n%s\n' % (value_name, full_key_path, cls.python_arch, e))
								return False
					except OSError:
						break
		except OSError:
			# No such key, just return.
			return True
		supkey_path, key_name = key_path.rsplit('\\', 1)
		try:
			with winreg.OpenKeyEx(cls.REG_BASE_KEYS[basekey_name], supkey_path, access=winreg.KEY_READ | winreg.KEY_WRITE | cls.reg_view) as supkey:
				winreg.DeleteKey(supkey, key_name)
		except OSError as e:
			if cls.failed_registration:
				pass
			else:
				cls.error('Failed to remove the key [\x1b[96m%s\x1b[0m] in the %s-bit registry view.\n\x1b[1;33m[DETAILS]:\x1b[0m\n%s\n' % (full_key_path, cls.python_arch, e))
				return False
		return True

	@classmethod
	def write_regs(cls, regs: dict[str, list[RegValueInfo]], backup: bool):
		for full_key_path, values in regs.items():
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

	# Ref: https://en.wikipedia.org/wiki/ANSI_escape_code#CSI_(Control_Sequence_Introducer)_sequences
	_re_csi_seq = re.compile(r'(\x9b|\x1b\[)[0-?]*[ -\/]*[@-~]')

	@classmethod
	def _remove_csi_seq(cls, src: str):
		return cls._re_csi_seq.sub('', src)

	@classmethod
	def _write(cls, writer: typing.TextIO, msg: str, prefixed=True):
		if prefixed:
			if writer == sys.stdout:
				prefix = '\x1b[1;32m[*]\x1b[0m '
			else:
				prefix = '\x1b[1;31m[!]\x1b[0m '
			prefix += "\x1b[1;33m%s\x1b[0m " % time.strftime('[%Y-%m-%d %H:%M:%S]')
		else:
			prefix = ''
		text = prefix + msg
		if not writer.isatty():
			text = cls._remove_csi_seq(text)
		writer.write(text)
		writer.flush()

	@classmethod
	def info(cls, msg: str):
		cls._write(sys.stdout, msg)

	@classmethod
	def info_no_prefix(cls, msg: str):
		cls._write(sys.stdout, msg, False)

	@classmethod
	def error(cls, msg: str):
		cls._write(sys.stderr, msg)

	@classmethod
	def error_no_prefix(cls, msg: str):
		cls._write(sys.stderr, msg, False)

if __name__ == '__main__':
	Installer.run()
