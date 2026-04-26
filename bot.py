from flask import Flask, request
import requests
import os

app = Flask(__name__)

# ===================== 从环境变量读取配置（安全！不会泄露Cookie） =====================
GROUP_ID = int(os.getenv("GROUP_ID", "753474636"))
ROBLOX_COOKIE = os.getenv("ROBLOX_COOKIE")
TARGET_RANK_LEVEL = int(os.getenv("TARGET_RANK_LEVEL", "3"))
# ====================================================

# 全局变量，存XSRF Token
xsrf_token = None

# 先获取一次有效的XSRF Token
def get_xsrf_token():
    global xsrf_token
    headers = {"Cookie": f".ROBLOSECURITY={ROBLOX_COOKIE}"}
    # 用一个简单的POST请求来触发XSRF响应
    r = requests.post("https://auth.roblox.com/v2/logout", headers=headers)
    if r.status_code == 403 and "x-csrf-token" in r.headers:
        xsrf_token = r.headers["x-csrf-token"]
        print("✅ 已获取XSRF Token:", xsrf_token)
    else:
        print("❌ 获取XSRF Token失败")

# 获取对应等级的角色ID
def get_role_id(group_id, rank_level):
    try:
        url = f"https://groups.roblox.com/v1/groups/{group_id}/roles"
        res = requests.get(url)
        roles = res.json()["roles"]
        for role in roles:
            if role["rank"] == rank_level:
                return role["id"]
    except Exception as e:
        print("获取角色ID失败:", e)
    return None

# WebHook 接收入口
@app.route('/webhook', methods=['POST'])
def webhook():
    global xsrf_token
    try:
        data = request.json
        player_userid = data.get("robloxUserId")

        if not player_userid:
            return {"code": 0, "msg": "缺少玩家ID"}

        role_id = get_role_id(GROUP_ID, TARGET_RANK_LEVEL)
        if not role_id:
            return {"code": 0, "msg": "未找到等级3的角色"}

        # 如果Token失效了，重新获取
        if not xsrf_token:
            get_xsrf_token()

        headers = {
            "Cookie": f".ROBLOSECURITY={ROBLOX_COOKIE}",
            "Content-Type": "application/json",
            "X-CSRF-Token": xsrf_token
        }

        api_url = f"https://groups.roblox.com/v1/groups/{GROUP_ID}/users/{player_userid}"
        response = requests.patch(api_url, json={"roleId": role_id}, headers=headers)

        if response.status_code in (200, 204):
            print(f"✅ 成功！玩家ID {player_userid} 已升到群组3级")
            return {"code": 1, "msg": "升级成功"}
        elif response.status_code == 403 and "XSRF token invalid" in response.text:
            print("❌ Token失效，正在重新获取...")
            get_xsrf_token()
            return {"code": 0, "msg": "Token失效，请重试"}
        else:
            print(f"❌ 升级失败：{response.text}")
            return {"code": 0, "msg": "API请求失败"}

    except Exception as e:
        print("错误:", e)
        return {"code": 0, "msg": str(e)}

# 保活路由，防止Glitch休眠
@app.route('/')
def keep_alive():
    return "✅ Bot is running!"

if __name__ == '__main__':
    # 启动时先获取一次Token
    get_xsrf_token()
    # Glitch必须用 0.0.0.0 和端口 3000
    app.run(host='0.0.0.0', port=3000)
