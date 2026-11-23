"""Test de charge simple (sans dependance externe) : python tools/loadtest.py http://localhost:5000 200 60
   arguments : URL, nombre d'utilisateurs simultanes, duree en secondes."""
import sys, time, threading, random, urllib.request, statistics

base = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:5000"
users = int(sys.argv[2]) if len(sys.argv) > 2 else 100
duree = int(sys.argv[3]) if len(sys.argv) > 3 else 30
pages = ["/", "/about", "/formations", "/healthz", "/static/css/style.css"]
lat, err, lock = [], [0], threading.Lock()


def visiteur():
    fin = time.time() + duree
    while time.time() < fin:
        url = base + random.choice(pages)
        t0 = time.time()
        try:
            with urllib.request.urlopen(url, timeout=30) as r:
                r.read()
            ok = True
        except Exception:
            ok = False
        dt = time.time() - t0
        with lock:
            lat.append(dt)
            if not ok:
                err[0] += 1
        time.sleep(random.uniform(0.5, 2.0))   # temps de lecture d'un visiteur


th = [threading.Thread(target=visiteur) for _ in range(users)]
[t.start() for t in th]
[t.join() for t in th]
lat.sort()
n = len(lat)
print(f"Requetes : {n}  |  erreurs : {err[0]}  |  debit : {n / duree:.1f} req/s")
if n:
    print(f"Latence moyenne : {statistics.mean(lat) * 1000:.0f} ms  |  p95 : {lat[int(n * .95) - 1] * 1000:.0f} ms  |  max : {lat[-1] * 1000:.0f} ms")
    print("Verdict :", "OK" if err[0] / n < .01 and lat[int(n * .95) - 1] < 2 else "A AMELIORER (erreurs ou lenteur)")
