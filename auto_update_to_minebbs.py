import json
import os

import requests

# 工作路径 用于存储配置文件等
# 如果出现获取不到配置文件的情况，请手动设置为脚本所在路径
work_file_dir = os.getcwd()

def load_config(file_path):
    with open(file_path, 'r') as file:
        return json.load(file)

def save_last_commit_id(commit_id):
    with open(f'{work_file_dir}/last_commit_id.txt', 'w') as f:
        f.write(commit_id)


def get_last_commit_id():
    try:
        with open(f'{work_file_dir}/last_commit_id.txt', 'r') as f:
            return f.read()
    except FileNotFoundError:
        return ""

def translate_commit_message(key, msg):
    if len(key) == 0 or len(msg) == 0:
        return "翻译错误"
    from openai import OpenAI
    client = OpenAI(api_key=key, base_url="https://api.deepseek.com")

    res = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "system", "content": "翻译中文到英文，其他语言全部翻译为中文，只需要回复翻译后的语句"},
            {"role": "user", "content": msg},
        ],
        stream=False
    )

    return res.choices[0].message.content


if __name__ == '__main__':
    config = load_config(f'{work_file_dir}/config.json')

    response = requests.get(f"https://api.github.com/repos/{config['github']['repo_owner']}/{config['github']['repo_name']}/commits")

    if response.status_code == 200:
        commits = response.json()
        commit = commits[0]  # 只获取最新的一次提交

        sha = commit['sha']
        message = commit['commit']['message']

        if sha == get_last_commit_id():
            print('No new commit')
            exit(0)

        headers = {
            'Content-Type': 'application/json',
            'Authorization': f"Bearer {config['minebbs']['token']}",
        }

        # 翻译
        deepseek_api_key = config['deepseek']['token']
        if len(deepseek_api_key) > 0:
            message = (f"{message}\n\n"
                       f"以下为机器翻译，请注意内容的准确性\n"
                       f"{translate_commit_message(deepseek_api_key, message)}")

        data = {
            'title': f'master-{sha[:7]}',
            'description': message,
            'new_version': f'master-{sha[:7]}',
            'file_url': config['minebbs']['res_file_url']
        }

        try:
            response = requests.post(
                f"https://api.minebbs.com/api/openapi/v1/resources/{config['minebbs']['res_id']}/update",
                headers=headers,
                data=json.dumps(data),
                verify=False
            )

            if response.status_code == 200:
                print('Uploaded successfully')
                save_last_commit_id(sha)
            else:
                print(f'Error uploading: {response.status_code} {response.text}')
        except Exception as e:
            save_last_commit_id(sha)
            print(e)
    else:
        print(f'Error fetching commits: {response.status_code}')

    exit(0)