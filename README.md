# AutoUpdateToMineBBS

这是一个用于自动更新 [MineBBS](https://www.minebbs.com/) 资源的 Python 脚本。它通过 GitHub API 获取最新的提交信息，并将其翻译后上传到 MineBBS。

## 功能

- 从 GitHub 仓库获取最新的提交信息。
- 使用 DeepSeek API 将提交信息翻译成英文。 (可选)
- 将翻译后的提交信息上传到 MineBBS。

## 配置

在运行脚本之前，你需要将 [`config.json`](https://github.com/lt-name/AutoUpdateToMineBBS/blob/master/config.json) 文件放置在脚本所在的目录中。`config.json` 文件的结构如下：

```json
{
  "minebbs": { #MineBBS 配置
    "token": "YOUR_TOKEN_HERE", # MineBBS API 密钥 申请密钥：https://api.minebbs.com/
    "res_id": 32, # MineBBS 资源 ID (通常为资源路径最后的 .xx )
    "res_file_url": "https://ci.opencollab.dev/job/NukkitX/job/Nukkit/job/master/lastSuccessfulBuild/artifact/target/nukkit-1.0-SNAPSHOT.jar" # MineBBS 资源更新后的下载链接
  },
  "github": { #GitHub 配置
    "repo_owner": "CloudburstMC", # GitHub 仓库所有者名称
    "repo_name": "Nukkit" # GitHub 仓库名称
  },
  "deepseek": {
    "token": "YOUR_TOKEN_HERE" # DeepSeek 密钥 (可选) 申请密钥：https://platform.deepseek.com/api_keys
  }
```

## 注意事项
如果脚本无法获取到配置文件，请手动修改 work_file_dir 变量为脚本所在的路径。  
如果 DeepSeek API 密钥为空，脚本将不会进行翻译。