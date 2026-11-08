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
}
last = {}


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


def giro():
    for t in TARGETS:
        url = (
            "https://www.apple.com/it/shop/retail/pickup-message"
            f"?little=false&pl=true&location={t['cap']}"
        )
        for i, p in enumerate(PARTS):
            url += f"&parts.{i}={p}"

        try:
            r = requests.get(url, headers=HDRS, impersonate="chrome", timeout=20)
            if r.status_code != 200:
                print(t["nome"], "status", r.status_code)
                continue
            data = r.json()
        except Exception as e:
            print(t["nome"], "err", e)
            continue

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


if __name__ == "__main__":
    print("avvio", datetime.now())
    for n in range(30):
        giro()
        if n < 29:
            time.sleep(10)
    try:
        requests.get(PING, timeout=15)
    except Exception:
        pass
    print("fine")
