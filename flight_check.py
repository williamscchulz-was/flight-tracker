"""
Flight tracker: NVT → MEX, 30/10/2026
Data: Google Flights via fast-flights (sem API key).
Notificação: Discord webhook.
Roda diariamente via Claude Code Routines.
"""
import os
import re
import sys
import requests
from datetime import datetime, timezone
from fast_flights import FlightData, Passengers, get_flights

# ---------- CONFIG ----------
ORIGIN = "NVT"
DESTINATION = "MEX"
DEPARTURE_DATE = "2026-10-30"
MAX_DURATION_HOURS = 16
MAX_PRICE_PER_ADULT = 4000.0
TOP_N = 5

# Busca com 1 adulto → preço puro de adulto.
# Pra grupo (2A + 1I), multiplica por ~2.1.
SEARCH_ADULTS = 1
SEARCH_INFANTS_ON_LAP = 0

# Cores do embed do Discord
COLOR_SUCCESS = 0x57F287
COLOR_NO_RESULTS = 0xFEE75C
COLOR_ERROR = 0xED4245

# ---------- ENV ----------
DISCORD_WEBHOOK_URL = os.environ["DISCORD_WEBHOOK_URL"]


# ---------- PARSERS ----------
def parse_duration_to_hours(s):
    """'10 hr 30 min' ou '1 day 4 hr' -> float em horas"""
    if not s:
        return 0.0
    days = re.search(r"(\d+)\s*day", s)
    hours = re.search(r"(\d+)\s*hr", s)
    mins = re.search(r"(\d+)\s*min", s)
    d = int(days.group(1)) if days else 0
    h = int(hours.group(1)) if hours else 0
    m = int(mins.group(1)) if mins else 0
    return d * 24 + h + m / 60.0


def parse_price(s):
    """'R$ 2.345' / '$1,234' / 'BRL 2345' -> float"""
    if not s:
        return None
    cleaned = re.sub(r"[^\d,\.]", "", str(s))
    if not cleaned:
        return None
    if "," in cleaned and "." in cleaned:
        if cleaned.rfind(",") > cleaned.rfind("."):
            cleaned = cleaned.replace(".", "").replace(",", ".")
        else:
            cleaned = cleaned.replace(",", "")
    elif "," in cleaned:
        last_part = cleaned.split(",")[-1]
        if len(last_part) == 3:
            cleaned = cleaned.replace(",", "")
        else:
            cleaned = cleaned.replace(",", ".")
    try:
        return float(cleaned)
    except ValueError:
        return None


# ---------- SEARCH ----------
def fetch_flights():
    result = get_flights(
        flight_data=[
            FlightData(
                date=DEPARTURE_DATE,
                from_airport=ORIGIN,
                to_airport=DESTINATION,
            )
        ],
        trip="one-way",
        seat="economy",
        passengers=Passengers(
            adults=SEARCH_ADULTS,
            children=0,
            infants_in_seat=0,
            infants_on_lap=SEARCH_INFANTS_ON_LAP,
        ),
        fetch_mode="local",
    )
    return result.flights


def filter_and_rank(flights):
    out = []
    for f in flights:
        price = parse_price(getattr(f, "price", None))
        if price is None or price >= MAX_PRICE_PER_ADULT:
            continue
        duration_h = parse_duration_to_hours(getattr(f, "duration", ""))
        if duration_h > MAX_DURATION_HOURS:
            continue
        out.append({
            "price": price,
            "duration_h": duration_h,
            "airline": getattr(f, "name", "?"),
            "stops": getattr(f, "stops", "?"),
            "departure": getattr(f, "departure", "?"),
            "arrival": getattr(f, "arrival", "?"),
            "arrival_ahead": getattr(f, "arrival_time_ahead", "") or "",
            "is_best": bool(getattr(f, "is_best", False)),
        })
    out.sort(key=lambda x: x["price"])
    return out


# ---------- DISCORD ----------
def fmt_hours(h):
    hh = int(h)
    mm = int(round((h - hh) * 60))
    return f"{hh}h{mm:02d}m"


def google_flights_url():
    # Link de busca pro Google Flights — abre a mesma pesquisa, mostra todas as
    # agências/sites onde comprar (Latam direto, Decolar, MaxMilhas, etc.)
    return (
        f"https://www.google.com/travel/flights?q="
        f"Flights%20from%20{ORIGIN}%20to%20{DESTINATION}%20on%20{DEPARTURE_DATE}"
    )


def fmt_stops(n):
    if n == 0:
        return "direto"
    if n == 1:
        return "1 conexão"
    return f"{n} conexões"


def build_embed(matches, total_raw):
    footer = f"até {MAX_DURATION_HOURS}h • < R${int(MAX_PRICE_PER_ADULT)}/adulto • busca 1 ADT • grupo 2A+1I = ~×2.1"
    now_iso = datetime.now(timezone.utc).isoformat()
    gf_link = f"\n\n[🔗 Abrir no Google Flights]({google_flights_url()})"

    if not matches:
        return {
            "title": "✈️ NVT → MEX • 30/10/26",
            "description": f"❌ Nenhuma opção dentro dos critérios hoje\n*{total_raw} ofertas analisadas*{gf_link}",
            "color": COLOR_NO_RESULTS,
            "footer": {"text": footer},
            "timestamp": now_iso,
        }

    fields = []
    for i, m in enumerate(matches[:TOP_N], 1):
        star = "⭐ " if m["is_best"] else ""
        ahead = f" ({m['arrival_ahead']})" if m["arrival_ahead"] else ""
        fields.append({
            "name": f"{star}{i}. R$ {m['price']:.0f}/adulto • {fmt_hours(m['duration_h'])}",
            "value": f"**{m['airline']}**\n{m['departure']} → {m['arrival']}{ahead} • {fmt_stops(m['stops'])}",
            "inline": False,
        })

    return {
        "title": "✈️ NVT → MEX • 30/10/26",
        "description": f"✅ **{len(matches)} opções** abaixo do teto. Top {min(TOP_N, len(matches))}:{gf_link}",
        "color": COLOR_SUCCESS,
        "fields": fields,
        "footer": {"text": footer + " • ⭐ = melhor opção segundo o Google"},
        "timestamp": now_iso,
    }


def send_discord(embed):
    r = requests.post(
        DISCORD_WEBHOOK_URL,
        json={"embeds": [embed]},
        timeout=30,
    )
    r.raise_for_status()


def send_discord_error(msg):
    embed = {
        "title": "❌ Flight tracker error",
        "description": f"```{msg[:1500]}```",
        "color": COLOR_ERROR,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    requests.post(DISCORD_WEBHOOK_URL, json={"embeds": [embed]}, timeout=30)


# ---------- MAIN ----------
def main():
    print(f"[{datetime.now().isoformat()}] {ORIGIN}→{DESTINATION} {DEPARTURE_DATE}")
    flights = fetch_flights()
    print(f"Raw flights: {len(flights)}")
    matches = filter_and_rank(flights)
    print(f"After filter: {len(matches)}")
    embed = build_embed(matches, total_raw=len(flights))
    send_discord(embed)
    print("Discord delivered.")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        msg = f"{type(e).__name__}: {e}"
        try:
            send_discord_error(msg)
        except Exception:
            pass
        print(msg, file=sys.stderr)
        sys.exit(1)
