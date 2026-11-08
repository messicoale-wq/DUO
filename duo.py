import os, json, time
from datetime import datetime
from curl_cffi import requests

TARGETS = [
    {"cap": "10095", "want": "grugliasco", "nome": "Le Gru"},
    {"cap": "20089", "want": "rozzano", "nome": "Fiordaliso"},
]
PARTS = ["MK2D4QN/A", "MK2F4QN/A"]
TOPIC = os.environ["NTFY_TOPIC"]
PING = "https://hc-ping.com/d9ba624b-eaf3-4cea-b4d0-13d99bab793b"

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

S = None
N = 0
last = {}


def fresh(caldo=False):
    global S, N
    S = requests.Session(impersonate="chrome")
    N = 0
    if caldo:
        try:
            S.get("https://www.apple.com/it/shop/buy-iphone/iphone-duo", timeout=25)
            print("sessione nuova con cookie")
        except Exception as e:
            print("warm err", e)


def push(titolo, testo):
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
        print("inviato:", titolo, testo)
    except Exception as e:
        print("push err", e)


def chiama(url):
    global N
    for tentativo in range(2):
        if N >= 10:
            fresh()
        u = url if tentativo == 0 else url.replace("retail/pickup-message", "fulfillment-messages")
        try:
            r = S.get(u, headers=HDRS, timeout=20)
            N += 1
            print(u.split("/")[-2], r.status_code, "req", N)
            if r.status_code == 200:
                try:
                    return r.json()
                except Exception:
                    pass
            else:
                fresh()
        except Exception as e:
            print("err", e)
            fresh()
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

        data = chiama(url)
        if not data:
            continue
        ok += 1

        for s in data.get("body", {}).get("stores", []):
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


if __name__ == "__main__":
    print("avvio", datetime.now())
    fresh(caldo=True)
    ko = 0
    for n in range(18):
        if giro() == 0:
            ko += 1
            if ko >= 4:
                print("bloccato, esco")
                break
        else:
            ko = 0
        if n < 17:
            time.sleep(10)
    try:
        requests.get(PING, timeout=15)
    except Exception:
        pass
    print("fine")
