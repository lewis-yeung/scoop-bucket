if __name__ != '__main__':
  raise RuntimeError('not allowed to be imported')

import sys

if sys.platform != 'win32':
  raise RuntimeError('cannot run on OS other than Windows')
if sys.version_info < (3, 8):
  raise RuntimeError('cannot run with Python version lower than 3.8')

import ctypes
import os
import platform
import winreg
from argparse import (
  ArgumentParser,
  RawTextHelpFormatter,
)
from enum import (
  Enum,
  IntEnum,
)
from typing import (
  Callable,
  cast,
)

PYTHON_ROOT = os.path.realpath(os.path.dirname(sys.executable))
PYTHON_ARCH_BIT = platform.architecture()[0][:2]
PYTHON_VERSION_TUPLE = platform.python_version_tuple()
PYTHON_VERSION_FULL = '.'.join(PYTHON_VERSION_TUPLE)

class StringEnum(str, Enum):
  def __str__(self):
    return cast(str, self.value)

class CLIName(StringEnum):
  USAGE = 'USAGE'
  FLAGS = 'FLAGS'
  WRITE = 'write'
  REMOVE = 'remove'
  GLOBAL = 'global'

class BaseRegKey(IntEnum):
  HKLM = winreg.HKEY_LOCAL_MACHINE
  HKCU = winreg.HKEY_CURRENT_USER

def parse_args():
  help_formatter = RawTextHelpFormatter
  original_add_usage = cast(
    Callable,
    getattr(help_formatter, 'add_usage'),
  )

  def _add_usage(*args, **kwargs):
    if len(args) < 5:
      kwargs['prefix'] = f'{CLIName.USAGE}: '
    return original_add_usage(*args, **kwargs)

  help_formatter.add_usage = _add_usage
  root_parser = ArgumentParser(
    description='Write/Remove Python installation info to/from Windows registry, which allows/disallows apps and third-party installers to discover the installation of Python that runs this script.',
    epilog=f'''\nNOTES:
  - Elevated privileges are required for modifying the registry.
  - This script is intended to be run as:
    <path_to_python_exe> "{__file__}" [{CLIName.FLAGS}]
where `<path_to_python_exe>` should be an absolute path to the Python executable that you want to register/unregister.
  - Info about the current Python running this script:
    - Installation directory: "{PYTHON_ROOT}"
    - Architecture: {PYTHON_ARCH_BIT}-bit
    - Version: {PYTHON_VERSION_FULL}''',
    formatter_class=help_formatter,
  )
  root_parser._optionals.title = CLIName.FLAGS
  root_parser.add_argument(
    '-g',
    '--global',
    action='store_true',
    help='operate on subkeys under "HKLM" (for all users)',
    dest=CLIName.GLOBAL,
  )
  operation_group = root_parser.add_mutually_exclusive_group()
  operation_group.add_argument(
    '-w',
    '--write',
    action='store_true',
    help='write installation info to registry',
    dest=CLIName.WRITE,
  )
  operation_group.add_argument(
    '-r',
    '--remove',
    action='store_true',
    help='remove installation info from registry',
    dest=CLIName.REMOVE,
  )
  formatter = root_parser._get_formatter()
  formatter.add_usage(
    usage=root_parser.usage,
    actions=root_parser._get_positional_actions(),
    groups=root_parser._mutually_exclusive_groups,
    prefix='Usage: ',
  )
  if len(sys.argv) == 1:
    root_parser.print_help()
    root_parser.exit(0)
  global cli_args
  cli_args = vars(root_parser.parse_args())
  if (not cli_args[CLIName.WRITE]) and (not cli_args[CLIName.REMOVE]):
    root_parser.error('no operation specified')
  if not bool(ctypes.windll.shell32.IsUserAnAdmin()):
    root_parser.error('administrator privileges are required for modifying the registry')

parse_args()

import logging
import signal
from dataclasses import dataclass
from typing import (
  Dict,
  List,
  Optional,
  Union,
)

if cli_args[CLIName.WRITE]:
  OPERATION = CLIName.WRITE
else:
  OPERATION = CLIName.REMOVE
PYTHON_VERSION = '.'.join(PYTHON_VERSION_TUPLE[:2])
PYTHON_VERSION_CLEAN = ''.join(PYTHON_VERSION_TUPLE)
if cli_args[CLIName.GLOBAL]:
  BASE_REG_KEY = BaseRegKey.HKLM
else:
  BASE_REG_KEY = BaseRegKey.HKCU

REG_ACCESS_MASK = winreg.KEY_READ | winreg.KEY_WRITE
if PYTHON_ARCH_BIT == '64':
  REG_ACCESS_MASK |= winreg.KEY_WOW64_64KEY
else:
  REG_ACCESS_MASK |= winreg.KEY_WOW64_32KEY

@dataclass
class RegValue:
  name: Optional[str] = None
  type: Optional[int] = None
  data: Optional[Union[str, int]] = None
  delete: bool = False

def write_installation_info():
  regs = {
    fr'Software\Python\PythonCore': [
      RegValue(
        name='DisplayName',
        type=winreg.REG_SZ,
        data='Python Software Foundation',
      ),
      RegValue(
        name='SupportUrl',
        type=winreg.REG_SZ,
        data='http://www.python.org/',
      ),
    ],
    fr'Software\Python\PythonCore\{PYTHON_VERSION}': [
      RegValue(
        name='DisplayName',
        type=winreg.REG_SZ,
        data=f'Python {PYTHON_VERSION} ({PYTHON_ARCH_BIT}-bit)',
      ),
      RegValue(
        name='SupportUrl',
        type=winreg.REG_SZ,
        data='http://www.python.org/',
      ),
      RegValue(
        name='SysArchitecture',
        type=winreg.REG_SZ,
        data=f'{PYTHON_ARCH_BIT}bit',
      ),
      RegValue(
        name='SysVersion',
        type=winreg.REG_SZ,
        data=PYTHON_VERSION,
      ),
      RegValue(
        name='Version',
        type=winreg.REG_SZ,
        data=PYTHON_VERSION_FULL,
      ),
    ],
    fr'Software\Python\PythonCore\{PYTHON_VERSION}\Help\Main Python Documentation': [
      RegValue(
        name=None,
        type=winreg.REG_SZ,
        data=f'{PYTHON_VERSION}\Doc\python{PYTHON_VERSION_CLEAN}.chm',
      ),
      RegValue(
        name='DisplayName',
        type=winreg.REG_SZ,
        data=f'Python {PYTHON_VERSION_FULL} Documentation',
      ),
    ],
    fr'Software\Python\PythonCore\{PYTHON_VERSION}\InstallPath': [
      RegValue(
        name=None,
        type=winreg.REG_SZ,
        data=PYTHON_ROOT,
      ),
      RegValue(
        name='ExecutablePath',
        type=winreg.REG_SZ,
        data=f'{PYTHON_ROOT}\python.exe',
      ),
      RegValue(
        name='WindowedExecutablePath',
        type=winreg.REG_SZ,
        data=f'{PYTHON_ROOT}\pythonw.exe',
      ),
    ],
    fr'Software\Python\PythonCore\{PYTHON_VERSION}\PythonPath': [
      RegValue(
        name=None,
        type=winreg.REG_SZ,
        data=f'{PYTHON_ROOT}\Lib;{PYTHON_ROOT}\DLLs',
      ),
    ],
  }
  logger.info('Writing installation info to registry...')
  update_registry(regs=regs)

def remove_installation_info():
  regs = {
    fr'Software\Python\PythonCore\{PYTHON_VERSION}': None,
  }
  logger.info('Removing installation info from registry...')
  update_registry(regs=regs)

def update_registry(regs: Dict[str, Optional[List[RegValue]]]):
  for key_path, values in regs.items():
    if values is not None:
      update_registry_keytree(key_path, values)
    else:
      delete_registry_keytree(key_path)

def update_registry_keytree(
  key_path: str,
  values: List[RegValue],
):
  full_key_path = os.path.join(BASE_REG_KEY.name, key_path)
  try:
    with winreg.CreateKeyEx(
        key=BASE_REG_KEY,
        sub_key=key_path,
        access=REG_ACCESS_MASK,
    ) as key:
      for v in values:
        try:
          if v.delete:
            winreg.DeleteValue(key, v.name)
          else:
            winreg.SetValueEx(key, v.name, 0, v.type, v.data)
        except:
          if v.name is not None:
            value_description = f'value [{v.name}]'
          else:
            value_description = 'default value'
          logger.error(str.format(
            'Failed to {} {} under [{}] in {}-bit registry view.',
            'delete' if v.delete else 'set',
            value_description,
            full_key_path,
            PYTHON_ARCH_BIT,
          ))
  except:
    logger.error(str.format(
      'Failed to open/create key [{}] in {}-bit registry view.',
      full_key_path,
      PYTHON_ARCH_BIT,
    ))

def delete_registry_keytree(key_path: str):
  full_key_path = os.path.join(BASE_REG_KEY.name, key_path)
  try:
    with winreg.OpenKeyEx(
        key=BASE_REG_KEY,
        sub_key=key_path,
        access=REG_ACCESS_MASK,
    ) as key:
      while True:
        try:
          delete_registry_keytree(os.path.join(
            key_path,
            winreg.EnumKey(key, 0),
          ))
        except OSError:
          break
      while True:
        try:
          value_name = winreg.EnumValue(key, 0)[0]
          try:
            winreg.DeleteValue(key, value_name)
          except:
            if value_name is not None:
              value_description = f'value [{value_name}]'
            else:
              value_description = 'default value'
            logger.error(str.format(
              'Failed to delete {} under [{}] in {}-bit registry view.',
              value_description,
              full_key_path,
              PYTHON_ARCH_BIT,
            ))
        except OSError:
          break
  except:
    # No such key, just return.
    return
  parent_key_path, key_name = os.path.split(key_path)
  try:
    with winreg.OpenKeyEx(
        key=BASE_REG_KEY,
        sub_key=parent_key_path,
        access=REG_ACCESS_MASK,
    ) as parent_key:
      winreg.DeleteKey(parent_key, key_name)
  except:
    logger.error(str.format(
      'Failed to delete key [{}] in {}-bit registry view.',
      full_key_path,
      PYTHON_ARCH_BIT,
    ))

def configure_logging():
  for level, name in {
      logging.CRITICAL: 'F',
      logging.ERROR: 'E',
      logging.WARNING: 'W',
      logging.INFO: 'I',
      logging.DEBUG: 'D',
  }.items():
    logging.addLevelName(level, name)
  handler = logging.StreamHandler()
  handler.setLevel(logging.DEBUG)
  handler.setFormatter(logging.Formatter(
    fmt='[%(asctime)s] (%(levelname)s): %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
  ))
  global logger
  logger = logging.getLogger(__name__)
  logger.setLevel(logging.DEBUG)
  logger.addHandler(handler)
  logger.propagate = False

try:
  configure_logging()
  signal.signal(signal.SIGINT, signal.SIG_IGN)
  signal.signal(signal.SIGBREAK, signal.SIG_IGN)
  if OPERATION is CLIName.WRITE:
    write_installation_info()
  else:
    remove_installation_info()
  logger.info(f'The operation "{OPERATION}" is complete.')
except Exception:
  logger.error(f'The operation "{OPERATION}" failed to complete.')
  sys.exit(1)
