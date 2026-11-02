import json
import os

import requests
from openai import OpenAI

# 工作路径 用于存储配置文件等
work_file_dir = os.getcwd()

# MineBBS 开放平台 API 文档：https://open.minebbs.com/api/docs/
MINEBBS_API_BASE = "https://open.minebbs.com/api/openapi/v1"


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


def build_update_message(config, message):
    """按需拼接 DeepSeek 机翻结果"""
    deepseek_api_key = config['deepseek']['token']
    if len(deepseek_api_key) > 0:
        return (f"{message}\n\n"
                f"以下为机器翻译，请注意内容的准确性\n\n"
                f"{translate_commit_message(deepseek_api_key, message)}")
    return message


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
    response = requests.get(f'{MINEBBS_API_BASE}/resources/{res_id}', headers=headers)
    ok, body = check_response(response)
    if not ok:
        raise RuntimeError(f'获取 MineBBS 资源信息失败: {response.status_code} {response.text}')
    version = (body.get('data') or {}).get('version')
    return [version] if version else []


def has_update_log(token, res_id, title):
    """检查指定标题的更新日志是否已发布"""
    response = requests.get(f'{MINEBBS_API_BASE}/resources/{res_id}/updates',
                            headers={'Authorization': f'Bearer {token}'})
    ok, body = check_response(response)
    if not ok:
        # 查询失败时按未发布处理，重复发帖交给 Idempotency-Key 兜底
        return False
    return any(u.get('title') == title for u in body.get('data') or [] if isinstance(u, dict))


def create_version(token, res_id, version, file_url):
    """发布新版本。开放平台中版本与更新日志是两个独立端点，这里先发版本"""
    response = requests.post(
        f'{MINEBBS_API_BASE}/resources/{res_id}/versions',
        headers={
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {token}',
            'Idempotency-Key': f'res{res_id}-v-{version}',
        },
        data=json.dumps({'version_string': version, 'file_url': file_url})
    )
    ok, body = check_response(response)
    if not ok:
        raise RuntimeError(f'发布版本失败: {response.status_code} {response.text}')
    return body


def post_update_log(token, res_id, title, message):
    """发布更新日志（展示提交信息），Idempotency-Key 在 24 小时内重试不会重复发帖"""
    response = requests.post(
        f'{MINEBBS_API_BASE}/resources/{res_id}/updates',
        headers={
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {token}',
            'Idempotency-Key': f'res{res_id}-u-{title}',
        },
        data=json.dumps({'title': title, 'message': message})
    )
    ok, body = check_response(response)
    if not ok:
        raise RuntimeError(f'发布更新日志失败: {response.status_code} {response.text}')
    return body


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

    token = config['minebbs']['token']
    res_id = config['minebbs']['res_id']

    # 以 MineBBS 上实际已发布的版本为准，不再依赖本地记录
    published_versions = get_published_versions(token, res_id)

    try:
        if version in published_versions:
            print(f'No new commit ({version} 已发布到 MineBBS)')
            # 版本已发布但更新日志缺失时补发（上次运行中途失败的情况）
            if not has_update_log(token, res_id, version):
                post_update_log(token, res_id, version, build_update_message(config, message))
                print('Missing update log posted')
        else:
            print(f'Detected new commit, publishing version {version} to MineBBS')
            # 发布失败时直接报错退出，下次运行会重新从 MineBBS 检查并重试
            create_version(token, res_id, version, config['minebbs']['res_file_url'])
            post_update_log(token, res_id, version, build_update_message(config, message))
            print('Uploaded successfully')
    except Exception as e:
        print(e)
        exit(1)
