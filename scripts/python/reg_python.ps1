#Requires -Version 3

<#
.SYNOPSIS

Writes/Removes the installation info to/from the registry, which allows/disallows apps and third-party installers to discover this Python installation.

.NOTES

The installation info of an existing distribution with the same architecture and the same major and minor version number as this one will be overwritten or removed. E.g., if this distribution is PythonCore v3.9.12 (64-bit), it can overwrite the installation info of an existing PythonCore v3.9.13 (64-bit).
#>

[CmdletBinding(DefaultParameterSetName = 'Default')]
param(
	[Parameter(ParameterSetName = 'Register')]
	# Writes the installation info to the registry.
	[switch]$Register = $false,
	[Parameter(ParameterSetName = 'Unregister')]
	# Removes the installation info from the registry.
	[switch]$Unregister = $false,
	# Operates on subkeys under 'HKLM' (for all users). By default it writes/removes the installation info only for the current user.
	[Parameter(ParameterSetName = 'Register')]
	[Parameter(ParameterSetName = 'Unregister')]
	[switch]$Global = $false
)

Set-StrictMode -Off

function Test-ElevatedProcess {
	$id = [System.Security.Principal.WindowsIdentity]::GetCurrent()
	$p = [System.Security.Principal.WindowsPrincipal]::new($id)
	if ($p.IsInRole([System.Security.Principal.WindowsBuiltInRole]::Administrator)) {
		return $true
	}
	return $false
}

function Write-Msg {
	param(
		[Parameter(Position = 0)]
		[string]$Msg,
		[Parameter(ParameterSetName = 'Info')]
		[switch]$Info = $false,
		[Parameter(ParameterSetName = 'Err')]
		[switch]$Err = $false
	)
	$prefix = switch ($true) {
		$Info { "`e[1;32m[*]`e[0m " }
		$Err { "`e[1;31m[!]`e[0m " }
	}
	$prefix += "`e[1;33m[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')]`e[0m "
	Write-Host -NoNewline ($prefix + $Msg)
}

function Remove-Regs {
	param(
		[hashtable]$Regs
	)
	Write-Msg -Info "Cleaning up the registry...`n"
	$Regs.Keys | ForEach-Object {
		$key = $_
		$fullKey = $key -split '\\', 2
		$baseKey = [Microsoft.Win32.RegistryKey]::OpenBaseKey($script:RegBaseKeyMaps[$fullKey[0]], $script:RegistryView)
		$subKey = $baseKey.OpenSubKey(($fullKey[1]), $true)
		if ($null -ne $subKey) {
			if ($null -ne $Regs[$key]) {
				# Remove specified values under the subkey.
				$Regs[$key] | ForEach-Object {
					$value = $_
					try {
						$subKey.DeleteValue($value)
					} catch {
						if (!$script:FailedToRegister) {
							Write-Msg -Err "Failed to remove the value [`e[95m$value`e[0m] under [`e[96m$key`e[0m] in the $script:PythonArch-bit registry view. `e[1;31mERROR:`e[0m $_`n"
							return $false
						}
					}
				}
				$subKey.Close()
			} else {
				$subKey.Close()
				# Remove the subkey tree.
				try {
					$baseKey.DeleteSubKeyTree(($fullKey[1]))
				} catch {
					if (!$script:FailedToRegister) {
						Write-Msg -Err "Failed to remove the key [`e[96m$key`e[0m] in the $script:PythonArch-bit registry view. `e[1;31mERROR:`e[0m $_`n"
						return $false
					}
				}
			}
		}
		$baseKey.Close()
	}
	return $true
}

function Write-Regs {
	param(
		[hashtable]$Regs
	)
	Write-Msg -Info "Writing to the registry...`n"
	$Regs.Keys | ForEach-Object {
		$key = $_
		$fullKey = $key -split '\\', 2
		$baseKey = [Microsoft.Win32.RegistryKey]::OpenBaseKey($script:RegBaseKeyMaps[$fullKey[0]], $script:RegistryView)
		try {
			$subKey = $baseKey.CreateSubKey(($fullKey[1]), $true)
		} catch {
			if (!$script:FailedToRegister) {
				Write-Msg -Err "Failed to open/create the key [`e[96m$key`e[0m] in the $script:PythonArch-bit registry view. `e[1;31mERROR:`e[0m $_`n"
				return $false
			}
		}
		if ($null -ne $Regs[$key]) {
			$Regs[$key] | ForEach-Object {
				$value = $_['Value']
				$type = $script:RegValueKindMaps[$_['Type']]
				$data = $_['Data']
				try {
					$subKey.SetValue($value, $data, $type)
				} catch {
					if (!$script:FailedToRegister) {
						Write-Msg -Err "Failed to set the value [`e[95m$value`e[0m] (with type [`e[94m$type`e[0m] and data [`e[92m$data`e[0m]) under [`e[96m$key`e[0m] in the $script:PythonArch-bit registry view. `e[1;31mERROR:`e[0m $_`n"
						return $false
					}
				}
			}
		}
		$subKey.Close()
		$baseKey.Close()
	}
	return $true
}

function init {
	if (!(Test-ElevatedProcess)) {
		Write-Msg -Err "Please run as administrator.`n"
		exit 2
	}
	$script:FailedToRegister = $false
	$script:RegBaseKeyMaps = @{
		'HKCR' = [Microsoft.Win32.RegistryHive]::ClassesRoot
		'HKCU' = [Microsoft.Win32.RegistryHive]::CurrentUser
		'HKLM' = [Microsoft.Win32.RegistryHive]::LocalMachine
		'HKU'  = [Microsoft.Win32.RegistryHive]::Users
		'HKCC' = [Microsoft.Win32.RegistryHive]::CurrentConfig
	}
	$script:RegValueKindMaps = @{
		'REG_SZ'        = [Microsoft.Win32.RegistryValueKind]::String
		'REG_MULTI_SZ'  = [Microsoft.Win32.RegistryValueKind]::MultiString
		'REG_EXPAND_SZ' = [Microsoft.Win32.RegistryValueKind]::ExpandString
		'REG_DWORD'     = [Microsoft.Win32.RegistryValueKind]::DWord
		'REG_QWORD'     = [Microsoft.Win32.RegistryValueKind]::QWord
		'REG_BINARY'    = [Microsoft.Win32.RegistryValueKind]::Binary
		'REG_NONE'      = [Microsoft.Win32.RegistryValueKind]::None
	}
	$script:BaseKey = if ($Global) { 'HKLM' } else { 'HKCU' }
	$script:PythonRoot = if ((Get-Item $PSScriptRoot).LinkType) {
		(Get-Item $PSScriptRoot).LinkTarget
	} else {
		$PSScriptRoot
	}
	$script:PythonVersion = '::PYTHON_VERSION::'
	$script:PythonVersionFull = '::PYTHON_VERSION_FULL::'
	$script:PythonVersionClean = '::PYTHON_VERSION_CLEAN::'
	$script:PythonArch = '::PYTHON_ARCH::'
	$script:RegistryView = switch ($script:PythonArch) {
		'32' { [Microsoft.Win32.RegistryView]::Registry32 }
		'64' { [Microsoft.Win32.RegistryView]::Registry64 }
	}
}

function register {
	$regs = [ordered]@{
		"$script:BaseKey\Software\Python\PythonCore"                                                      = @(
			@{ Value = 'DisplayName'; Type = 'REG_SZ'; Data = 'Python Software Foundation' }
			@{ Value = 'SupportUrl'; Type = 'REG_SZ'; Data = 'http://www.python.org/' }
		)
		"$script:BaseKey\Software\Python\PythonCore\$script:PythonVersion"                                = @(
			@{ Value = 'DisplayName'; Type = 'REG_SZ'; Data = "Python $script:PythonVersion ($script:PythonArch-bit)" }
			@{ Value = 'SupportUrl'; Type = 'REG_SZ'; Data = 'http://www.python.org/' }
			@{ Value = 'Version'; Type = 'REG_SZ'; Data = $script:PythonVersionFull }
			@{ Value = 'SysVersion'; Type = 'REG_SZ'; Data = $script:PythonVersion }
			@{ Value = 'SysArchitecture'; Type = 'REG_SZ'; Data = "${script:PythonArch}bit" }
		)
		"$script:BaseKey\Software\Python\PythonCore\$script:PythonVersion\Help\Main Python Documentation" = @(
			@{ Value = $null; Type = 'REG_SZ'; Data = "$script:PythonRoot\Doc\python$script:PythonVersionClean.chm" }
			@{ Value = 'DisplayName'; Type = 'REG_SZ'; Data = "Python $script:PythonVersionFull Documentation" }
		)
		"$script:BaseKey\Software\Python\PythonCore\$script:PythonVersion\InstallPath"                    = @(
			@{ Value = $null; Type = 'REG_SZ'; Data = $script:PythonRoot }
			@{ Value = 'ExecutablePath'; Type = 'REG_SZ'; Data = "$script:PythonRoot\python.exe" }
			@{ Value = 'WindowedExecutablePath'; Type = 'REG_SZ'; Data = "$script:PythonRoot\pythonw.exe" }
		)
		"$script:BaseKey\Software\Python\PythonCore\$script:PythonVersion\PythonPath"                     = @(
			@{ Value = $null; Type = 'REG_SZ'; Data = "$script:PythonRoot\Lib\;$script:PythonRoot\DLLs\" }
		)
	}
	if (!(Write-Regs $regs)) {
		$script:FailedToRegister = $true
		return $false
	}
	return $true
}

function unregister {
	$regs = [ordered]@{
		"$script:BaseKey\Software\Python\PythonCore\$script:PythonVersion" = $null
	}
	return Remove-Regs $regs
}

$script:InstallerScript = $PSCommandPath
switch ($true) {
	$Register {
		init
		Write-Msg -Info "`e[32mRegistering...`e[0m`n"
		if (!(register)) {
			Write-Msg -Err "Aborted. Cleaning up...`n"
			unregister
			Write-Msg -Info "Cleanup done.`n"
			exit 1
		}
		Write-Msg -Info "`e[32mAll done.`e[0m`n"
	}
	$Unregister {
		init
		Write-Msg -Info "`e[32mUnregistering...`e[0m`n"
		if (!(unregister)) {
			Write-Msg -Err "Aborted.`n"
			exit 1
		}
		Write-Msg -Info "`e[32mAll done.`e[0m`n"
	}
	Default {
		help $script:InstallerScript | Write-Output
	}
}
