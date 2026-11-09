import os, json, time, random, sys
from curl_cffi import requests as creq

TOPIC = "duo-v-8f3k2"
NTFY_TOKEN = "tk_drixexlcrotml35bgcnzt0q51n0c7"
TG_TOKEN = os.environ.get("TG_TOKEN", "")
TG_CHAT = os.environ.get("TG_CHAT", "")
HC = "https://hc-ping.com/d9ba624b-eaf3-4cea-b4d0-13d99bab793b"
BAG = "https://www.apple.com/it/shop/bag"

WUSER = ["ibkewoalresidential-it-%d" % i for i in range(1, 11)]
WPASS = "3e1m9fvhgohd"
PHOST = "p.webshare.io:80"
PROXIES = ["http://%s:%s@%s" % (u, WPASS, PHOST) for u in WUSER]

CODES = [("256", "MK2D4QN/A"), ("512", "MK2F4QN/A")]
STORES = [("Le Gru", "10095"), ("Fiordaliso", "20089"), ("Via Roma", "10121")]

S = creq.Session(impersonate="chrome")
tent = 0
ok = 0
err = 0
pieni = 0
vuoti = 0
mn = 999999
mx = 0
ult = "-"
pt1 = "-"
pt2 = "-"
di_fila = 0
diretto = False
gia = set()


def ntfy(msg, prio=3):
    h = {"Authorization": "Bearer " + NTFY_TOKEN, "Priority": str(prio)}
    for _ in range(3):
        try:
            creq.post("https://ntfy.sh/" + TOPIC, data=msg.encode(), headers=h, timeout=15)
            return
        except Exception:
            time.sleep(2)


def tg(msg):
    if not TG_TOKEN or not TG_CHAT:
        return
    try:
        creq.post("https://api.telegram.org/bot" + TG_TOKEN + "/sendMessage",
                  data={"chat_id": TG_CHAT, "text": msg,
                        "disable_web_page_preview": True}, timeout=15)
    except Exception:
        pass


def hc(path=""):
    try:
        creq.get(HC + path, timeout=10)
    except Exception:
        pass


def probe(url, p):
    try:
        r = creq.get(url, proxies={"http": p, "https": p},
                     impersonate="chrome", timeout=25)
        return "%s %s" % (r.status_code, (r.text or "")[:50])
    except Exception as e:
        return "ERR %s %s" % (type(e).__name__, str(e)[:110])


def prova_proxy():
    p = random.choice(PROXIES)
    print("PROXY", p.replace(WPASS, "***"), flush=True)
    a = probe("http://api.ipify.org?format=json", p)
    print("PT1", a, flush=True)
    b = probe("https://api.ipify.org?format=json", p)
    print("PT2", b, flush=True)
    return a, b


def match(a, b):
    a = a.lower()
    b = b.lower()
    return a in b or b in a


def trovato(nome, size, code):
    k = nome + size
    if k in gia:
        return
    gia.add(k)
    m = "DUO %s BIANCO %s\n%s\n%s" % (size, nome, code, BAG)
    ntfy(m, 5)
    tg(m)
    print("TROVATO", m.replace("\n", " "), flush=True)


def giro():
    global tent, ok, err, pieni, vuoti, mn, mx, ult, di_fila, diretto
    for nome, cap in STORES:
        url = ("https://www.apple.com/it/shop/retail/pickup-message"
               "?parts.0=%s&parts.1=%s&location=%s"
               % (CODES[0][1], CODES[1][1], cap))
        p = None if diretto else random.choice(PROXIES)
        tent += 1
        try:
            kw = {"timeout": 25, "impersonate": "chrome"}
            if p:
                kw["proxies"] = {"http": p, "https": p}
            r = S.get(url, **kw)
            txt = r.text or ""
            n = len(txt)
            if n < mn:
                mn = n
            if n > mx:
                mx = n
            if r.status_code == 200 and '"stores"' in txt:
                pieni += 1
                ok += 1
                di_fila = 0
                j = json.loads(txt)
                stores = ((j.get("body") or {}).get("stores") or {})
                for sv in stores.values():
                    sn = sv.get("storeName") or ""
                    if not match(nome, sn):
                        continue
                    pa = sv.get("partsAvailability") or {}
                    for size, code in CODES:
                        x = pa.get(code) or {}
                        if (x.get("pickupDisplay") or "").lower() == "available":
                            trovato(nome, size, code)
            elif r.status_code == 200:
                vuoti += 1
                ult = "vuoto"
            else:
                vuoti += 1
                ult = str(r.status_code)
                if p:
                    di_fila += 1
        except Exception as e:
            err += 1
            ult = "%s %s" % (type(e).__name__, str(e)[:110])
            if p:
                di_fila += 1
        if p and di_fila >= 4:
            diretto = True
        print(nome, tent, ok, err, pieni, vuoti, ult, flush=True)


def manda_diag():
    m = ("DIAG tent=%d ok=%d err=%d pieni=%d vuoti=%d min=%d max=%d dir=%d pt1=[%s] pt2=[%s] ult=[%s]"
         % (tent, ok, err, pieni, vuoti, mn if mn < 999999 else 0, mx,
            1 if diretto else 0, pt1, pt2, ult))
    ntfy(m, 2)
    print(m, flush=True)


def main():
    global pt1, pt2
    hc("/start")
    pt1, pt2 = prova_proxy()
    for i in range(6):
        giro()
        if i < 5:
            time.sleep(1.0 + random.random() * 0.8)
    manda_diag()
    hc()


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        try:
            hc("/fail")
            ntfy("DUO script morto: %s %s" % (type(e).__name__, str(e)[:80]), 4)
        except Exception:
            pass
        sys.exit(1)
