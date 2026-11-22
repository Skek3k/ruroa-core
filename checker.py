import urllib.request
import urllib.parse
import socket
import ssl
import json
import base64
import time
import re
from operator import itemgetter
from concurrent.futures import ThreadPoolExecutor

GH = "".join(["https://", "raw.", "://githubusercontent.com"])
TG = "".join(["https://", "t.", "me/s/"])

GITHUB_SOURCES = [
    GH + "barry-far/V2ray-Config/main/Sub1.txt",
    GH + "barry-far/V2ray-Config/main/Sub2.txt",
    GH + "barry-far/V2ray-Config/main/Sub3.txt",
    GH + "barry-far/V2ray-Config/main/Sub4.txt",
    GH + "Epodonios/v2ray-configs/main/All_Configs_Sub.txt",
    GH + "Epodonios/v2ray-configs/main/Splitted-By-Protocol/vless.txt",
    GH + "mahdibland/V2RayAggregator/master/sub/sub_merge.txt",
    GH + "mahdibland/V2RayAggregator/master/Eternity",
    GH + "yebekhe/TVC/main/subscriptions/xray/normal/vless",
    GH + "yebekhe/TVC/main/subscriptions/xray/normal/reality",
    GH + "peasoft/NoMoreWalls/master/list.txt",
    GH + "Pawdroid/Free-servers/main/sub",
    GH + "mfuu/v2ray/master/v2ray",
    GH + "aiboboxx/v2rayfree/main/v2",
    GH + "soroushmirzaei/telegram-configs-collector/main/protocols/vless",
    GH + "soroushmirzaei/telegram-configs-collector/main/protocols/reality",
    GH + "Leon406/SubCrawler/main/sub/share/vless",
    GH + "ALIILAPRO/v2rayNG-Config/main/sub.txt",
    GH + "ts-sf/fly/main/v2",
    GH + "freefq/free/master/v2",
    GH + "ermaozi/get_subscribe/main/subscribe/v2ray.txt",
    GH + "w1770946466/Auto_proxy/main/Long_term_subscription_num",
    GH + "peasoft/NoMoreWalls/master/list_raw.txt",
    GH + "MrPooyaX/VpnsFucking/main/Shenzo.txt",
    GH + "ZywChannel/free/main/sub"
]

TG_CHANNELS = [
    TG + "vless_keys",
    TG + "free_v2ray_configs",
    TG + "vless_vpn_free",
    TG + "v2rayng_org",
    TG + "v2ray_free_conf",
    TG + "ConfigsHUB",
    TG + "OutlineVpnOfficial",
    TG + "vless_reality_free",
    TG + "reality_configs",
    TG + "V2rayCollector",
    TG + "FreeV2rayVPN",
    TG + "v2ray_configs_pool",
    TG + "proxy_kafee",
    TG + "vless_config"
]

BAD_KEYWORDS = [
    "russia", "🇷🇺", "belarus", "🇧🇾", "china", "🇨🇳",
    "iran", "🇮🇷", "ru-", "ir-", "cn-", "127.0.0.", "0.0.0.0",
    "192.168.", "10.0.", "timeweb", "selectel", "reg.ru", "moscow", "spb"
]

BAD_COUNTRIES = {"RU", "BY", "CN", "IR", "KP", "SY"}
PRIORITY_COUNTRIES = {"FI": 0, "EE": 1, "LV": 1, "LT": 1, "SE": 2, "DE": 3, "NL": 4, "PL": 5, "FR": 6, "GB": 7}
COUNTRY_FLAGS = {
    "FI": "🇫🇮 FI", "DE": "🇩🇪 DE", "NL": "🇳🇱 NL", "SE": "🇸🇪 SE",
    "EE": "🇪🇪 EE", "LV": "🇱🇻 LV", "LT": "🇱🇹 LT", "PL": "🇵🇱 PL",
    "FR": "🇫🇷 FR", "GB": "🇬🇧 UK", "US": "🇺🇸 US", "TR": "🇹🇷 TR",
    "JP": "🇯🇵 JP", "CA": "🇨🇦 CA", "CH": "🇨🇭 CH", "AT": "🇦🇹 AT"
}

BAD_SNI_TLDS = (".ru", ".su", ".by", ".ir", ".cn", ".rkn", ".local", ".test")
CF_TLS_PORTS = {443, 8443, 2053, 2083, 2087, 2096}
def decode_if_base64(text):
    clean = text.strip()
    if "vless://" in clean:
        return clean
    try:
        padded = clean + "=" * ((4 - len(clean) % 4) % 4)
        decoded = base64.b64decode(padded).decode("utf-8", errors="ignore")
        if "://" in decoded:
            return decoded
    except Exception:
        pass
    return clean

def fetch_url_text(url):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=8) as response:
            return response.read().decode("utf-8", errors="ignore")
    except Exception:
        return ""

def fetch_all_sources():
    keys = set()
    with ThreadPoolExecutor(max_workers=20) as pool:
        for raw in pool.map(fetch_url_text, GITHUB_SOURCES):
            if not raw:
                continue
            for line in decode_if_base64(raw).splitlines():
                line = line.strip()
                if line.startswith("vless://"):
                    keys.add(line)
        for html in pool.map(fetch_url_text, TG_CHANNELS):
            if not html:
                continue
            for key in re.findall(r'vless://[^\s"<>\']+', html):
                keys.add(key.replace("&amp;", "&").strip())
    return keys

def parse_vless_params(key):
    base, *_ = key.split("#")
    match = re.match(r'^vless://([^@]+)@([^:/?#]+):(\d+)\??(.*)$', base, re.IGNORECASE)
    if not match:
        return None
    uuid, host, port_str, query = match.groups()
    if len(uuid) < 32:
        return None
    params = dict(urllib.parse.parse_qsl(query, keep_blank_values=True))
    return {"host": host.lower(), "port": int(port_str), "params": params}

def is_valid_sni(sni):
    sni = sni.strip().lower()
    if "." not in sni or len(sni) < 4 or re.match(r'^\d+\.\d+\.\d+\.\d+$', sni):
        return False
    return not (sni.endswith(BAD_SNI_TLDS) or "fuck" in sni)

def is_good_for_ru(key):
    key_lower = key.lower()
    if "allowinsecure=1" in key_lower or "allowinsecure=true" in key_lower:
        return False
    if any(bad in key_lower for bad in BAD_KEYWORDS):
        return False

    parsed = parse_vless_params(key)
    if not parsed:
        return False
    p = {k.lower(): v for k, v in parsed["params"].items()}
    sec = p.get("security", "").lower()
    sni = p.get("sni", "")

    if sec == "reality":
        pbk = p.get("pbk", "")
        sid = p.get("sid", "")
        return len(pbk) >= 42 and is_valid_sni(sni) and len(sid) <= 16
    if sec == "tls" and p.get("type", "").lower() == "ws":
        return parsed["port"] in CF_TLS_PORTS and (not sni or is_valid_sni(sni))
    return False

def check_server(key):
    parsed = parse_vless_params(key)
    if not parsed:
        return None
    host, port, p = parsed["host"], parsed["port"], {k.lower(): v for k, v in parsed["params"].items()}
    sni = p.get("sni") or host
    is_reality = p.get("security", "").lower() == "reality"

    try:
        start = time.time()
        with socket.create_connection((host, port), timeout=1.8) as raw_sock:
            ctx = ssl.create_default_context()
            if is_reality:
                ctx.check_hostname = False
                ctx.verify_mode = ssl.CERT_NONE
            with ctx.wrap_socket(raw_sock, server_hostname=sni):
                ping = int((time.time() - start) * 1000)
                if ping > 1600:
                    return None
                return {"key": key, "host": host, "port": port, "ping": ping, "is_reality": is_reality}
    except Exception:
        return None

def resolve_countries(hosts):
    geo_map = {}
    unique_hosts = list(set(hosts))
    url = "".join(["http://", "ip-api.", "com/batch?fields=query,countryCode"])
    for i in range(0, len(unique_hosts), 100):
        batch = unique_hosts[i:i+100]
        try:
            req = urllib.request.Request(url, data=json.dumps(batch).encode("utf-8"), headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=5) as resp:
                for item in json.loads(resp.read().decode("utf-8")):
                    if "query" in item and "countryCode" in item:
                        geo_map[item["query"]] = item["countryCode"]
        except Exception:
            pass
    return geo_map

def main():
    all_keys = fetch_all_sources()
    candidates, seen = [], set()
    for k in all_keys:
        if not is_good_for_ru(k):
            continue
        parsed = parse_vless_params(k)
        ep = f"{parsed['host']}:{parsed['port']}"
        if ep not in seen:
            seen.add(ep)
            candidates.append(k)

    working = []
    with ThreadPoolExecutor(max_workers=100) as pool:
        for res in pool.map(check_server, candidates[:1800]):
            if res:
                working.append(res)

    geo_map = resolve_countries([w["host"] for w in working])
    filtered = []
    for w in working:
        cc = geo_map.get(w["host"], "")
        if cc in BAD_COUNTRIES:
            continue
        proto = "REALITY" if w["is_reality"] else "TLS-WS"
        flag = COUNTRY_FLAGS.get(cc, f"🌐 {cc}" if cc else "🌐 EU/US")
        base_key, *_ = w["key"].split("#")
        new_name = urllib.parse.quote(f"{flag} [{proto}] #{w['ping']}ms")
        prio = PRIORITY_COUNTRIES.get(cc, 20)
        filtered.append((0 if w["is_reality"] else 1, prio, w["ping"], f"{base_key}#{new_name}"))

    filtered.sort(key=lambda x: (x[0], x[1], x[2]))
    best_keys = list(map(itemgetter(3), filtered[:70]))
    if best_keys:
        encoded = base64.b64encode("\n".join(best_keys).encode("utf-8")).decode("utf-8")
        with open("sub.txt", "w", encoding="utf-8") as f:
            f.write(encoded)

if __name__ == "__main__":
    main()
