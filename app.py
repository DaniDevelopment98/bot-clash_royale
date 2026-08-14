from flask import Flask, jsonify
import requests
import os
import time
from datetime import datetime, timezone

app = Flask(__name__)

# FIX: Acepta TOKEN o CLASH_ROYALE_TOKEN
TOKEN = os.environ.get("TOKEN") or os.environ.get("CLASH_ROYALE_TOKEN")
BASE_URL = "https://api.clashroyale.com/v1"
CLAN_DEFAULT = os.environ.get("CLAN_DEFAULT") or os.environ.get("CLAN_TAG") or "#6JC9C8Y"

session = requests.Session()
if TOKEN:
    session.headers.update({"Authorization": f"Bearer {TOKEN}"})

CACHE = {}
CACHE_TTL = 90

def get_cache(key):
    if key in CACHE:
        data, t = CACHE[key]
        if time.time() - t < CACHE_TTL:
            return data
    return None

def set_cache(key, data):
    CACHE[key] = (data, time.time())

def api_fast(endpoint):
    cached = get_cache(endpoint)
    if cached:
        return cached
    try:
        r = session.get(f"{BASE_URL}{endpoint}", timeout=10)
        data = r.json()
        if r.status_code == 200:
            set_cache(endpoint, data)
        else:
            # Para ver el error real de Supercell
            data["status_code"] = r.status_code
        return data
    except Exception as e:
        return {"error": str(e)}

def get_tag(tag_param):
    if tag_param:
        return tag_param.replace("#","").strip().upper()
    return CLAN_DEFAULT.replace("#","").strip().upper()

@app.route("/")
def home():
    return jsonify({"status": "Bot Royale PRO V4 TURBO - Cache 90s", "clan_default": CLAN_DEFAULT, "token_ok": bool(TOKEN)})

@app.route("/ip")
def ip_route():
    try:
        ip = requests.get("https://api.ipify.org", timeout=5).text
        return jsonify({"ip_railway": ip})
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route("/perfil/<tag>")
def perfil(tag):
    return jsonify(api_fast(f"/players/%23{tag.replace('#','').strip().upper()}"))

@app.route("/clan/<tag>")
def clan(tag):
    return jsonify(api_fast(f"/clans/%23{tag.replace('#','').upper()}"))

@app.route("/guerra")
@app.route("/guerra/<tag>")
def guerra(tag=None):
    t = get_tag(tag)
    return jsonify(api_fast(f"/clans/%23{t}/currentriverrace"))

@app.route("/faltan")
@app.route("/faltan/<tag>")
def faltan(tag=None):
    t = get_tag(tag)
    cache_key = f"/clans/%23{t}/currentriverrace"
    race = api_fast(cache_key)
    if "clan" not in race:
        return jsonify({"error": f"No hay guerra activa para {t}", "raw": race})
    participantes = race["clan"].get("participants", [])
    faltan_lista = []
    for p in participantes:
        hoy = p.get("decksUsedToday", 0)
        if hoy < 4:
            faltan_lista.append({"name": p["name"], "usados": hoy, "faltan": 4-hoy, "fama": p.get("fame",0)})
    faltan_lista = sorted(faltan_lista, key=lambda x: x["fama"])
    return jsonify({"clan": race["clan"].get("name"), "tag": t, "faltan": len(faltan_lista), "faltan_lista": faltan_lista})

@app.route("/inactivos/<tag>")
def inactivos(tag):
    c = api_fast(f"/clans/%23{tag.replace('#','').upper()}")
    if "memberList" not in c:
        return jsonify({"error": "Clan no encontrado", "raw": c})
    lista = []
    ahora = datetime.now(timezone.utc)
    for m in c.get("memberList", []):
        last_seen_str = m.get("lastSeen", "")
        dias_off = 0
        try:
            last_seen = datetime.strptime(last_seen_str, "%Y%m%dT%H%M%S.%fZ").replace(tzinfo=timezone.utc)
            dias_off = (ahora - last_seen).days
        except:
            dias_off = 0
        if dias_off >= 2:
            lista.append({"name": m["name"],"rol": m["role"],"dias_off": dias_off})
    lista.sort(key=lambda x: x["dias_off"], reverse=True)
    return jsonify({"clan": c["name"], "total": len(lista), "inactivos": lista})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
