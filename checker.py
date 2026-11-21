import urllib.request
import urllib.parse
import socket
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
        gh_texts = pool.map(fetch_url_text, GITHUB_SOURCES)
        for raw in gh_texts:
            if not raw:
                continue
            content = decode_if_base64(raw)
            for line in content.splitlines():
                line = line.strip()
                if line.startswith("vless://"):
                    keys.add(line)

        tg_texts = pool.map(fetch_url_text, TG_CHANNELS)
        for html in tg_texts:
            if not html:
                continue
            found = re.findall(r'vless://[^\s"<>\']+', html)
            for key in found:
                keys.add(key.replace("&amp;", "&").strip())
    return keys
def extract_host_port(key):
    match = re.search(r'@([^:/?#]+):(\d+)', key)
    if match:
        return match.group(1).lower(), int(match.group(2))
    return None, None

def is_valid_sni(key):
    match = re.search(r'[?&]sni=([^&#]+)', key, re.IGNORECASE)
    if not match:
        return False
    sni = urllib.parse.unquote(match.group(1)).strip().lower()
    if "." not in sni or len(sni) < 4:
        return False
    if re.match(r'^\d+\.\d+\.\d+\.\d+$', sni):
        return False
    if sni.endswith(BAD_SNI_TLDS) or "fuck" in sni:
        return False
    return True

def is_good_for_ru(key):
    key_lower = key.lower()
    if "allowinsecure=1" in key_lower or "allowinsecure=true" in key_lower:
        return False
    for bad in BAD_KEYWORDS:
        if bad in key_lower:
            return False

    _, port = extract_host_port(key)
    if not port:
        return False

    is_reality = ("security=reality" in key_lower and "pbk=" in key_lower and is_valid_sni(key))
    is_ws_tls = ("security=tls" in key_lower and "type=ws" in key_lower and port in CF_TLS_PORTS)

    return is_reality or is_ws_tls

def detect_tag(key):
    lower = key.lower()
    proto = "REALITY" if "security=reality" in lower else "TLS-WS"
    flags = {
        "🇩🇪 DE": ["germany", "🇩🇪", "frankfurt", "de-", "hetzner"],
        "🇳🇱 NL": ["netherlands", "🇳🇱", "amsterdam", "nl-"],
        "🇫🇮 FI": ["finland", "🇫🇮", "helsinki", "fi-"],
        "🇺🇸 US": ["united states", "🇺🇸", "usa", "us-", "ashburn", "dallas"],
        "🇬🇧 UK": ["united kingdom", "🇬🇧", "london", "uk-"],
        "🇫🇷 FR": ["france", "🇫🇷", "paris", "fr-"],
        "🇸🇪 SE": ["sweden", "🇸🇪", "stockholm", "se-"],
        "🇵🇱 PL": ["poland", "🇵🇱", "warsaw", "pl-"],
        "🇹🇷 TR": ["turkey", "🇹🇷", "istanbul", "tr-"],
        "🇯🇵 JP": ["japan", "🇯🇵", "tokyo", "jp-"]
    }
    for label, hints in flags.items():
        if any(h in lower for h in hints):
            return f"{label} [{proto}]"
    return f"🌐 EU/US [{proto}]"

def check_server(key):
    host, port = extract_host_port(key)
    if not host or not port:
        return None
    try:
        start = time.time()
        with socket.create_connection((host, port), timeout=1.6):
            ping = int((time.time() - start) * 1000)
            if ping > 1500:
                return None
            base_key, *_ = key.split("#")
            tag = detect_tag(key)
            new_name = urllib.parse.quote(f"{tag} #{ping}ms")
            return (ping, f"{host}:{port}", f"{base_key}#{new_name}")
    except Exception:
        return None

def main():
    all_keys = fetch_all_sources()
    # Предварительная дедупликация по host:port до проверки сокетом
    unique_candidates = []
    seen_endpoints = set()
    for k in all_keys:
        if not is_good_for_ru(k):
            continue
        host, port = extract_host_port(k)
        endpoint = f"{host}:{port}"
        if endpoint not in seen_endpoints:
            seen_endpoints.add(endpoint)
            unique_candidates.append(k)

    working = []
    with ThreadPoolExecutor(max_workers=100) as executor:
        for res in executor.map(check_server, unique_candidates[:1500]):
            if res is not None:
                working.append(res)

    working.sort(key=itemgetter(0))
    best_keys = list(map(itemgetter(2), working[:70]))
    if best_keys:
        encoded_sub = base64.b64encode("\n".join(best_keys).encode("utf-8")).decode("utf-8")
        with open("sub.txt", "w", encoding="utf-8") as f:
            f.write(encoded_sub)

if __name__ == "__main__":
    main()
