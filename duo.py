import os, json, time, random
from datetime import datetime
from curl_cffi import requests

TARGETS = [
    {"cap": "10095", "want": "grugliasco", "nome": "Le Gru"},
    {"cap": "20089", "want": "rozzano", "nome": "Fiordaliso"},
    {"cap": "10121", "want": "via roma", "nome": "Via Roma"},
]
PARTS = ["MK2D4QN/A", "MK2F4QN/A"]
TOPIC = os.environ["NTFY_TOPIC"]
PING = "https://hc-ping.com/d9ba624b-eaf3-4cea-b4d0-13d99bab793b"

WPASS = "3e1m9fvhgohd"
WHOST = "p.webshare.io:80"
WUSERS = [
    "ibkewoalresidential-it-1",
    "ibkewoalresidential-it-2",
    "ibkewoalresidential-it-3",
    "ibkewoalresidential-it-4",
    "ibkewoalresidential-it-5",
    "ibkewoalresidential-it-6",
    "ibkewoalresidential-it-7",
    "ibkewoalresidential-it-8",
    "ibkewoalresidential-it-9",
    "ibkewoalresidential-it-10",
]
PROXIES = [f"http://{u}:{WPASS}@{WHOST}" for u in WUSERS]

HDRS = {
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Accept-Language": "it-IT,it;q=0.9,en;q=0.8",
    "Referer": "https://www.apple.com/it/shop/buy-iphone/iphone-duo",
    "X-Requested-With": "XMLHttpRequest",
    "sec-ch-ua": '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"macOS"',
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-origin",
}

SP = None
SD = None
N = 0
proxy_on = bool(PROXIES)
proxy_ko = 0
last = {}
diag = []
tent = 0
err = 0


def nuova(con_proxy):
    return requests.Session(impersonate="chrome")


def fresh(caldo=False):
    global SP, SD, N
    SP = nuova(True) if proxy_on else None
    SD = nuova(False)
    N = 0
    if caldo:
        try:
            SD.get("https://www.apple.com/it/shop/buy-iphone/iphone-duo", timeout=25)
            print("sessione nuova con cookie")
        except Exception as e:
            print("warm err", str(e)[:80])


def push(titolo, testo):
    try:
        requests.post(
            f"https://api.telegram.org/bot{os.environ['TG_TOKEN']}/sendMessage",
            json={"chat_id": os.environ["TG_CHAT"], "text": titolo + " — " + testo},
            timeout=15,
        )
        print("tg ok")
    except Exception as e:
        print("tg err", str(e)[:80])
    try:
        requests.post(
            f"https://ntfy.sh/{TOPIC}",
            data=testo.encode(),
            headers={
                "Title": titolo,
                "Priority": "5",
                "Tags": "rotating_light",
                "Click": "https://www.apple.com/it/shop/buy-iphone/iphone-duo",
            },
            timeout=15,
        )
        print("ntfy ok")
    except Exception as e:
        print("ntfy err", str(e)[:80])


def prova(url, nome, sessione, modo):
    global N, tent, err
    if sessione is None:
        return None
    if N >= 10:
        fresh()
        sessione = SP if modo == "proxy" else SD
        if sessione is None:
            return None
    kw = {}
    if modo == "proxy":
        if not PROXIES:
            return None
        tent += 1
        p = random.choice(PROXIES)
        kw["proxies"] = {"http": p, "https": p}
    try:
        r = sessione.get(url, headers=HDRS, timeout=25, **kw)
        N += 1
        lung = len(r.text)
        print(nome, modo, r.status_code, lung, "req", N)
        if modo == "proxy":
            diag.append(lung)
        if r.status_code == 200:
            try:
                return r.json()
            except Exception:
                return None
        return None
    except Exception as e:
        if modo == "proxy":
            err += 1
        print(nome, modo, "err", str(e)[:80])
        return None


def chiama(url, nome):
    global proxy_ko, proxy_on
    for tentativo in range(2):
        u = url if tentativo == 0 else url.replace("retail/pickup-message", "fulfillment-messages")
        if proxy_on and SP is not None:
            r = prova(u, nome, SP, "proxy")
            if r is not None:
                proxy_ko = 0
                return r
            proxy_ko += 1
            print("proxy ko", proxy_ko)
            if proxy_ko >= 4:
                proxy_on = False
                print("proxy disattivato, si prosegue in diretta")
            r = prova(u, nome, SD, "diretto")
            if r is not None:
                return r
        else:
            r = prova(u, nome, SD, "diretto")
            if r is not None:
                return r
    return None


def giro():
    ok = 0
    for t in TARGETS:
        url = (
            "https://www.apple.com/it/shop/retail/pickup-message"
            f"?little=false&pl=true&location={t['cap']}"
        )
        for i, p in enumerate(PARTS):
            url += f"&parts.{i}={p}"

        data = chiama(url, t["nome"])
        if not data:
            continue
        stores = data.get("body", {}).get("stores") or []
        if not stores:
            continue
        ok += 1

        for s in stores:
            nome = (s.get("storeName") or "").lower()
            if t["want"] not in nome:
                continue
            for p in PARTS:
                if s.get("partsAvailability", {}).get(p, {}).get("pickupDisplay") != "available":
                    continue
                k = s.get("storeNumber", "") + p
                now = time.time()
                if now - last.get(k, 0) < 900:
                    continue
                last[k] = now
                gb = "256" if p == "MK2D4QN/A" else "512"
                push(f"DUO {gb} BIANCO", t["nome"])
    return ok


def manda_diag(riassunto):
    h = {"Title": "DIAG", "Priority": "3"}
    for _ in range(2):
        try:
            r = requests.post(f"https://ntfy.sh/{TOPIC}", data=riassunto.encode(), headers=h, timeout=15)
            print("diag ntfy", r.status_code)
            if r.status_code == 200:
                break
        except Exception as e:
            print("diag err", str(e)[:60])
        time.sleep(3)


if __name__ == "__main__":
    print("avvio", datetime.now(), "proxy", "on" if proxy_on else "off", len(PROXIES), "ip")
    fresh(caldo=True)
    ko = 0
    for n in range(6):
        if giro() == 0:
            ko += 1
            if ko >= 4:
                print("bloccato, esco")
                break
        else:
            ko = 0
        if n < 5:
            time.sleep(4)
    pieni = sum(1 for x in diag if x >= 500)
    vuoti = sum(1 for x in diag if x < 500)
    riassunto = (
        f"tent={tent} ok={len(diag)} err={err} "
        f"pieni={pieni} vuoti={vuoti} "
        f"min={min(diag) if diag else 0} max={max(diag) if diag else 0}"
    )
    print(riassunto)
    manda_diag(riassunto)
    try:
        requests.get(PING, timeout=15)
    except Exception:
        pass
    print("fine")
