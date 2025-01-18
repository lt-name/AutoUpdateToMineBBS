import json
import os

import requests

# GitHub 仓库名称
repo_owner = 'CloudburstMC'
repo_name = 'Nukkit'

# GitHub API URL
github_url = f'https://api.github.com/repos/{repo_owner}/{repo_name}/commits'

# minebbs的token
minebbs_token = ''
# minebbs资源id
minebbs_id = '32'
# minebbs资源下载地址
file_url = "https://ci.opencollab.dev/job/NukkitX/job/Nukkit/job/master/lastSuccessfulBuild/artifact/target/nukkit-1.0-SNAPSHOT.jar"

minebbs_api_url = f'https://api.minebbs.com/api/openapi/v1/resources/{minebbs_id}/update'

# 缓存文件路径
cache_file_dir = os.getcwd()

def save_last_commit_id(commit_id):
    with open(f'{cache_file_dir}/last_commit_id.txt', 'w') as f:
        f.write(commit_id)

def get_last_commit_id():
    with open(f'{cache_file_dir}/last_commit_id.txt', 'r') as f:
        return f.read()

if __name__ == '__main__':
    response = requests.get(github_url)

    if response.status_code == 200:
        commits = response.json()
        commit = commits[0] #只获取最新的一次提交

        sha = commit['sha']
        message = commit['commit']['message']

        if sha == get_last_commit_id():
            print('No new commit')
            exit(0)

        headers = {
            'Authorization': f'Bearer {minebbs_token}',
        }

        data = {
            'title': f'master-{sha[:7]}',
            'description': message,
            'new_version': f'master-{sha[:7]}',
            'file_url': file_url
        }

        response = requests.post(minebbs_api_url, headers=headers, data=json.dumps(data))

        if response.status_code == 200:
            print('Uploaded successfully')
            save_last_commit_id(sha)
        else:
            print(f'Error uploading: {response.status_code} {response.text}')
    else:
        print(f'Error fetching commits: {response.status_code}')

    exit(0)