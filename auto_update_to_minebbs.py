import json
import requests
from openai import OpenAI

# 工作路径 用于存储配置文件等
work_file_dir = os.getcwd()

MINEBBS_API_BASE = "https://api.minebbs.com/api/openapi/v1"


def load_config(file_path):
    with open(file_path, 'r') as file:
        return json.load(file)


def translate_commit_message(key, msg):
    if len(key) == 0 or len(msg) == 0:
        return "翻译错误"
    client = OpenAI(api_key=key, base_url="https://api.deepseek.com")

    res = client.chat.completions.create(
        model="deepseek-flash",
        messages=[
            {"role": "system", "content": "翻译中文到英文，其他语言全部翻译为中文，只需要回复翻译后的语句"},
            {"role": "user", "content": msg},
        ],
        stream=False
    )

    return res.choices[0].message.content


def check_response(response):
    # MineBBS OpenAPI 的 HTTP 状态码恒为 200，业务结果要看 body 里的 status 字段（2000 为成功）
    try:
        body = response.json()
    except ValueError:
        body = {}
    if not isinstance(body, dict):
        body = {}
    return response.status_code == 200 and body.get('status') == 2000, body


def get_published_versions(token, res_id):
    """从 MineBBS 读取该资源已发布的版本号列表"""
    headers = {'Authorization': f'Bearer {token}'}

    response = requests.get(f'{MINEBBS_API_BASE}/resources/{res_id}/versions', headers=headers)
    ok, body = check_response(response)
    if ok:
        return [v['version_string'] for v in body.get('data') or []
                if isinstance(v, dict) and v.get('version_string')]

    # 版本列表接口不可用时，退回资源详情接口，至少拿到最新版本号
    response = requests.get(f'{MINEBBS_API_BASE}/me/resources/{res_id}', headers=headers)
    ok, body = check_response(response)
    if not ok:
        raise RuntimeError(f'获取 MineBBS 资源信息失败: {response.status_code} {response.text}')
    version = (body.get('data') or {}).get('version')
    return [version] if version else []


if __name__ == '__main__':
    config = load_config(f'{work_file_dir}/config.json')

    response = requests.get(
        f"https://api.github.com/repos/{config['github']['repo_owner']}/{config['github']['repo_name']}/commits")
    if response.status_code != 200:
        print(f'Error fetching commits: {response.status_code} {response.text}')
        exit(1)

    commit = response.json()[0]  # 只获取最新的一次提交
    sha = commit['sha']
    message = commit['commit']['message']
    version = f'master-{sha[:7]}'

    # 以 MineBBS 上实际已发布的版本为准，不再依赖本地记录
    published_versions = get_published_versions(config['minebbs']['token'], config['minebbs']['res_id'])
    if version in published_versions:
        print(f'No new commit ({version} 已发布到 MineBBS)')
        exit(0)

    print(f'Detected new commit, publishing version {version} to MineBBS')

    headers = {
        'Content-Type': 'application/json',
        'Authorization': f"Bearer {config['minebbs']['token']}",
    }

    # 翻译
    deepseek_api_key = config['deepseek']['token']
    if len(deepseek_api_key) > 0:
        message = (f"{message}\n\n"
                   f"以下为机器翻译，请注意内容的准确性\n\n"
                   f"{translate_commit_message(deepseek_api_key, message)}")

    data = {
        'title': version,
        'description': message,
        'new_version': version,
        'file_url': config['minebbs']['res_file_url']
    }

    try:
        response = requests.post(
            f"{MINEBBS_API_BASE}/resources/{config['minebbs']['res_id']}/update",
            headers=headers,
            data=json.dumps(data)
        )

        ok, body = check_response(response)
        if ok:
            print('Uploaded successfully')
        else:
            # 发布失败时直接报错退出，下次运行会重新从 MineBBS 检查并重试
            print(f'Error uploading: {response.status_code} {response.text}')
            exit(1)
    except Exception as e:
        print(e)
        exit(1)
