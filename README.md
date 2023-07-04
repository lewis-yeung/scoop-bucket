<div align="center">

# 📦 Scoop Bucket

Just a [Scoop][scoop] [bucket][scoop-buckets].

</div>

## Q&A

### How to install apps from this bucket?

1. You should have [Scoop][scoop] properly installed.

2. Run the following command in PowerShell to add this bucket:

   ```powershell
   scoop bucket add "lewis-yeung" "https://github.com/lewis-yeung/scoop-bucket"
   ```

   <details><summary>For users in <b>Chinese mainland</b></summary>
   If you have an internet connection issue, try this:

   ```powershell
   scoop bucket add "lewis-yeung" "https://ghproxy.com/https://github.com/lewis-yeung/scoop-bucket"
   ```
   </details>

3. Install apps from this bucket:

   ```powershell
   scoop install "lewis-yeung/<app_name>"
   ```

### Anything special about this bucket?

The download URLs of some apps are optimized for users in **Chinese mainland**, which means using mirrors (e.g., [GitHub Proxy][ghproxy]).

## Credits

- [GitHub Proxy][ghproxy] maintained by [stilleshan][stilleshan]
- [TUNA Mirrors][tuna-mirrors] maintained by [TUNA][tuna]

[scoop]: https://scoop.sh/
[scoop-buckets]: https://github.com/ScoopInstaller/Scoop/wiki/Buckets
[ghproxy]: https://ghproxy.com/
[stilleshan]: https://github.com/stilleshan
[tuna-mirrors]: https://mirrors.tuna.tsinghua.edu.cn/
[tuna]: https://github.com/tuna
