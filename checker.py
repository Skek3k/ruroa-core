import urllib.request
import urllib.parse
import socket
import base64
import time
import re
from operator import itemgetter
from concurrent.futures import ThreadPoolExecutor

PROTO = "https" + "://"
GH = PROTO + "://githubusercontent.com"
TG = PROTO + "t.me/s/"

GITHUB_SOURCES = [
    GH + "barry-far/V2ray-Config/main/Sub1.txt",
    GH + "barry-far/V2ray-Config/main/Sub2.txt",
    GH + "Epodonios/v2ray-configs/main/All_Configs_Sub.txt",
    GH + "mahdibland/V2RayAggregator/master/sub/sub_merge.txt",
    GH + "yebekhe/TVC/main/subscriptions/xray/normal/vless",
    GH + "peasoft/NoMoreWalls/master/list.txt",
    GH + "Pawdroid/Free-servers/main/sub",
    GH + "mfuu/v2ray/master/v2ray",
    GH + "aiboboxx/v2rayfree/main/v2",
    GH + "soroushmirzaei/telegram-configs-collector/main/protocols/vless"
]

TG_CHANNELS = [
    TG + "vless_keys",
    TG + "free_v2ray_configs",
    TG + "vless_vpn_free",
    TG + "v2rayng_org",
    TG + "v2ray_free_conf",
    TG + "ConfigsHUB",
    TG + "OutlineVpnOfficial"
]

BAD_KEYWORDS = ["russia", "🇷🇺", "belarus", "🇧🇾", "china", "🇨🇳", "iran", "🇮🇷", "ru-", "ir-", "cn-"]

def fetch_github():
    keys = set()
    for url in GITHUB_SOURCES:
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=12) as response:
                content = response.read().decode('utf-8', errors='ignore')
                try:
                    decoded = base64.b64decode(content).decode('utf-8', errors='ignore')
                    if "://" in decoded:
                        content = decoded
                except Exception:
                    pass
                for line in content.splitlines():
                    line = line.strip()
                    if line.startswith("vless://"):
                        keys.add(line)
        except Exception:
            pass
    return keys

def fetch_telegram():
    keys = set()
    for url in TG_CHANNELS:
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            html = urllib.request.urlopen(req, timeout=12).read().decode('utf-8', errors='ignore')
            found = re.findall(r'vless://[^\s"<>\']+', html)
            for key in found:
                keys.add(key.replace('&amp;', '&').strip())
        except Exception:
            pass
    return keys

def is_good_for_ru(key):
    key_lower = key.lower()
    if "security=reality" not in key_lower:
        return False
    for bad in BAD_KEYWORDS:
        if bad in key_lower:
            return False
    return True

def extract_host_port(key):
    match = re.search(r'@([^:/?#]+):(\d+)', key)
    if match:
        return match.group(1), int(match.group(2))
    return None, None

def check_server(key):
    host, port = extract_host_port(key)
    if not host or not port:
        return None
    try:
        start = time.time()
        with socket.create_connection((host, port), timeout=2.0):
            ping = int((time.time() - start) * 1000)
            base_key, *_ = key.split('#')
            new_name = urllib.parse.quote(f"⚡ Сервер #{ping}ms")
            return (ping, f"{base_key}#{new_name}")
    except Exception:
        return None

def main():
    all_keys = fetch_github().union(fetch_telegram())
    filtered_keys = [k for k in all_keys if is_good_for_ru(k)]
    working = []
    with ThreadPoolExecutor(max_workers=60) as executor:
        for res in executor.map(check_server, filtered_keys[:800]):
            if res is not None:
                working.append(res)
    working.sort(key=itemgetter(0))
    best_keys = list(map(itemgetter(1), working[:30]))
    encoded_sub = base64.b64encode("\n".join(best_keys).encode("utf-8")).decode("utf-8")
    with open("sub.txt", "w", encoding="utf-8") as f:
        f.write(encoded_sub)

if __name__ == "__main__":
    main()
