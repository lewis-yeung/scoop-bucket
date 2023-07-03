<div align="center">

# 📦 Scoop Bucket

Just a [Scoop][scoop] [bucket][scoop-buckets].

</div>

- **OPTIMIZED FOR USERS IN CHINA:** The download URLs of some apps use proxies/mirrors (e.g., [GitHub Proxy][ghproxy]).

## Q&A

### How to install apps from this bucket?

1. You should have [Scoop][scoop] properly installed.

2. Run any of the following commands in PowerShell to add this bucket:

   ```powershell
   scoop bucket add "lewis-yeung" "https://github.com/lewis-yeung/scoop-bucket"
   scoop bucket add "lewis-yeung" "https://ghproxy.com/https://github.com/lewis-yeung/scoop-bucket" # FOR USERS IN CHINA
   ```

3. Install apps from this bucket:

   ```powershell
   scoop install "lewis-yeung/<app_name>"
   ```

### How to add an app manifest to this bucket?

📃 Please create a PR.

## Credits

- [GitHub Proxy][ghproxy] maintained by [stilleshan][stilleshan]
- [TUNA Mirrors][tuna-mirrors] maintained by [TUNA][tuna]

[scoop]: https://scoop.sh/
[scoop-buckets]: https://github.com/ScoopInstaller/Scoop/wiki/Buckets
[ghproxy]: https://ghproxy.com/
[stilleshan]: https://github.com/stilleshan
[tuna-mirrors]: https://mirrors.tuna.tsinghua.edu.cn/
[tuna]: https://github.com/tuna
