<div align="center">
	<h1 align="center">📦 Scoop Bucket</h1>
	<p align="center">Just a <a href="https://scoop.sh">Scoop</a> <a href="https://github.com/ScoopInstaller/Scoop/wiki/Buckets">bucket</a>.</p>
</div>

- **OPTIMIZED FOR USERS IN CHINA:** The download URLs of some apps use proxies/mirrors (e.g., [GitHub Proxy](https://ghproxy.com/)).

## Q&A

### How to install apps from this bucket?

1. You should have [Scoop](https://scoop.sh) properly installed.

2. Run any of the following commands in PowerShell to add this bucket:

	``` powershell
	scoop bucket add "lewis-yeung" "https://github.com/lewis-yeung/scoop-bucket"
	scoop bucket add "lewis-yeung" "https://ghproxy.com/https://github.com/lewis-yeung/scoop-bucket" # FOR USERS IN CHINA
	```

3. Install apps from this bucket:

	``` powershell
	scoop install "lewis-yeung/<app_name>"
	```

### How to add an app manifest to this bucket?

📃 Please create a PR.
