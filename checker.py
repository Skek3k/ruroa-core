import urllib.request
import urllib.parse
import socket
import ssl
import json
import base64
import time
import re
import os
import shutil
import subprocess
import tempfile
from operator import itemgetter
from concurrent.futures import ThreadPoolExecutor

GH = "".join(["https://", "raw.", "githubusercontent.com/"])
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
    base, *_ = key.split("#", 1)
    match = re.match(r'^vless://([^@]+)@(\[[^\]]+\]|[^:/?#]+):(\d+)\??(.*)$', base, re.IGNORECASE)
    if not match:
        return None
    uuid, host, port_str, query = match.groups()
    uuid = uuid.strip()
    if len(uuid) < 32:
        return None
    params = dict(urllib.parse.parse_qsl(query, keep_blank_values=True))
    return {"uuid": uuid, "host": host.strip("[]").lower(), "port": int(port_str), "params": params}


def is_valid_sni(sni):
    sni = sni.strip().lower()
    if "." not in sni or len(sni) < 4 or re.match(r'^\d+\.\d+\.\d+\.\d+$', sni):
        return False
    return not (sni.endswith(BAD_SNI_TLDS) or "fuck" in sni)


def is_good_reality(key):
    key_lower = key.lower()
    if "allowinsecure=1" in key_lower or "allowinsecure=true" in key_lower:
        return False
    if any(bad in key_lower for bad in BAD_KEYWORDS):
        return False

    parsed = parse_vless_params(key)
    if not parsed:
        return False
    p = {k.lower(): v for k, v in parsed["params"].items()}
    if p.get("security", "").lower() != "reality":
        return False

    pbk = p.get("pbk", "").strip()
    sid = p.get("sid", "").strip()
    sni = p.get("sni", "").strip()
    if len(pbk) < 40 or not is_valid_sni(sni):
        return False
    if sid and (len(sid) > 16 or not re.fullmatch(r'[0-9a-fA-F]+', sid)):
        return False
    return True


def check_tls_handshake(key):
    parsed = parse_vless_params(key)
    if not parsed:
        return None
    host, port, p = parsed["host"], parsed["port"], {k.lower(): v for k, v in parsed["params"].items()}
    sni = p.get("sni") or host
    try:
        start = time.time()
        with socket.create_connection((host, port), timeout=1.8) as raw_sock:
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            with ctx.wrap_socket(raw_sock, server_hostname=sni):
                ping = int((time.time() - start) * 1000)
                if ping > 1600:
                    return None
                return {"key": key, "parsed": parsed, "host": host, "port": port, "ping": ping}
    except Exception:
        return None


def resolve_countries(hosts):
    geo_map = {}
    unique_hosts = list(set(hosts))
    url = "".join(["http://", "ip-api.", "com/batch?fields=query,countryCode"])
    for i in range(0, len(unique_hosts), 100):
        batch = unique_hosts[i:i + 100]
        try:
            req = urllib.request.Request(
                url,
                data=json.dumps(batch).encode("utf-8"),
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                for item in json.loads(resp.read().decode("utf-8")):
                    if "query" in item and "countryCode" in item:
                        geo_map[item["query"]] = item["countryCode"]
        except Exception:
            pass
    return geo_map


def build_xray_config(parsed, local_port):
    p = {k.lower(): v for k, v in parsed["params"].items()}
    net = (p.get("type") or "tcp").lower()
    if net == "raw":
        net = "tcp"
    elif net == "splithttp":
        net = "xhttp"

    user = {
        "id": parsed["uuid"],
        "encryption": p.get("encryption") or "none",
    }
    flow = p.get("flow", "").strip()
    if flow and net == "tcp":
        user["flow"] = flow

    stream = {
        "network": net,
        "security": "reality",
        "realitySettings": {
            "serverName": p.get("sni", ""),
            "fingerprint": p.get("fp") or "chrome",
            "publicKey": p.get("pbk", ""),
            "shortId": p.get("sid", ""),
            "spiderX": p.get("spx", ""),
        },
    }
    if net == "grpc":
        stream["grpcSettings"] = {"serviceName": p.get("servicename", "")}
    elif net == "ws":
        ws_headers = {"Host": p.get("host", "")} if p.get("host") else {}
        stream["wsSettings"] = {"path": p.get("path", "/"), "headers": ws_headers}
    elif net == "xhttp":
        stream["xhttpSettings"] = {"path": p.get("path", "/"), "host": p.get("host", "")}
    elif net == "httpupgrade":
        stream["httpupgradeSettings"] = {"path": p.get("path", "/"), "host": p.get("host", "")}
    elif net == "tcp" and p.get("headertype", "").lower() == "http":
        stream["tcpSettings"] = {"header": {"type": "http"}}

    return {
        "log": {"loglevel": "none"},
        "inbounds": [
            {
                "listen": "127.0.0.1",
                "port": local_port,
                "protocol": "http",
                "settings": {},
            }
        ],
        "outbounds": [
            {
                "protocol": "vless",
                "settings": {
                    "vnext": [
                        {
                            "address": parsed["host"],
                            "port": parsed["port"],
                            "users": [user],
                        }
                    ]
                },
                "streamSettings": stream,
            }
        ],
    }


def verify_with_xray(xray_bin, item, port):
    cfg_path = None
    proc = None
    try:
        cfg = build_xray_config(item["parsed"], port)
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as tf:
            json.dump(cfg, tf)
            cfg_path = tf.name

        proc = subprocess.Popen(
            [xray_bin, "run", "-c", cfg_path],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        ready = False
        for _ in range(25):
            if proc.poll() is not None:
                return None
            try:
                with socket.create_connection(("127.0.0.1", port), timeout=0.15):
                    ready = True
                    break
            except Exception:
                time.sleep(0.06)
        if not ready:
            return None

        proxy_url = f"http://127.0.0.1:{port}"
        opener = urllib.request.build_opener(
            urllib.request.ProxyHandler({"http": proxy_url, "https": proxy_url})
        )
        test_url = "".join(["https://", "www.gstatic.com", "/generate_204"])
        req = urllib.request.Request(test_url, headers={"User-Agent": "Mozilla/5.0"})
        start = time.time()
        with opener.open(req, timeout=4.0) as resp:
            if resp.status in (200, 204):
                real_ms = int((time.time() - start) * 1000)
                return {**item, "ping": real_ms}
    except Exception:
        return None
    finally:
        if proc is not None:
            proc.terminate()
            try:
                proc.wait(timeout=1.5)
            except Exception:
                proc.kill()
        if cfg_path and os.path.exists(cfg_path):
            try:
                os.remove(cfg_path)
            except Exception:
                pass
    return None


def main():
    all_keys = fetch_all_sources()
    candidates, seen = [], set()
    for k in all_keys:
        if not is_good_reality(k):
            continue
        parsed = parse_vless_params(k)
        ep = f"{parsed['host']}:{parsed['port']}"
        if ep not in seen:
            seen.add(ep)
            candidates.append(k)

    tls_ok = []
    with ThreadPoolExecutor(max_workers=100) as pool:
        for res in pool.map(check_tls_handshake, candidates[:2500]):
            if res:
                tls_ok.append(res)

    geo_map = resolve_countries([w["host"] for w in tls_ok])
    geo_filtered = []
    for w in tls_ok:
        cc = geo_map.get(w["host"], "")
        if cc in BAD_COUNTRIES:
            continue
        w["cc"] = cc
        w["prio"] = PRIORITY_COUNTRIES.get(cc, 20)
        geo_filtered.append(w)

    geo_filtered.sort(key=lambda x: (x["prio"], x["ping"]))

    xray_bin = shutil.which("xray")
    verified = []
    if xray_bin and geo_filtered:
        top_batch = geo_filtered[:250]
        with ThreadPoolExecutor(max_workers=20) as pool:
            futures = [
                pool.submit(verify_with_xray, xray_bin, item, 21000 + idx)
                for idx, item in enumerate(top_batch)
            ]
            for fut in futures:
                res = fut.result()
                if res:
                    verified.append(res)
    else:
        verified = geo_filtered[:70]

    verified.sort(key=lambda x: (x["prio"], x["ping"]))
    best_keys = []
    for w in verified[:70]:
        cc = w.get("cc", "")
        flag = COUNTRY_FLAGS.get(cc, f"🌐 {cc}" if cc else "🌐 EU/US")
        base_key, *_ = w["key"].split("#", 1)
        new_name = urllib.parse.quote(f"{flag} [REALITY] • {w['ping']}ms")
        best_keys.append(f"{base_key}#{new_name}")

    if best_keys:
        encoded = base64.b64encode("\n".join(best_keys).encode("utf-8")).decode("utf-8")
        with open("sub.txt", "w", encoding="utf-8") as f:
            f.write(encoded)


if __name__ == "__main__":
    main()
