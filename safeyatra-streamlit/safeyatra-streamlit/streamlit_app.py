"""SafeYatra for Streamlit: route planning, journey monitor, check-ins and AI guidance."""
import json
import os
import time

import pydeck as pdk
import requests
import streamlit as st

st.set_page_config(page_title="SafeYatra", page_icon="🧭", layout="centered")
UA = {"User-Agent": "SafeYatra-streamlit/1.0"}

st.markdown("""<style>
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;600&display=swap');
h1,h2,h3{font-family:'Playfair Display',Georgia,serif!important;font-weight:400!important;letter-spacing:-.01em}
[data-testid="stMetricValue"]{font-family:'Playfair Display',Georgia,serif}
[data-testid="stVerticalBlockBorderWrapper"],[data-testid="stForm"]{background:#fffdf8;border-color:#e2ded2!important;border-radius:10px}
[data-testid="stAppViewContainer"]{background:#f6f4ee}
header[data-testid="stHeader"]{background:transparent}
</style>""", unsafe_allow_html=True)


def secret(name, default=None):
    try:
        return st.secrets[name]
    except Exception:
        return os.getenv(name, default)


def fmt(m):
    m = max(0, m)
    return f"{int(m // 60)} h {int(m % 60)} min" if m >= 60 else f"{int(m)} min"


@st.cache_data(ttl=3600, show_spinner=False)
def geocode(place):
    r = requests.get("https://nominatim.openstreetmap.org/search",
                     params={"q": place, "format": "json", "limit": 1}, headers=UA, timeout=15)
    r.raise_for_status()
    hits = r.json()
    if not hits:
        raise ValueError(f"Could not find “{place}”. Try adding the state or country.")
    return float(hits[0]["lat"]), float(hits[0]["lon"]), hits[0]["display_name"]


@st.cache_data(ttl=3600, show_spinner=False)
def plan(origin, dest):
    a, b = geocode(origin), geocode(dest)
    r = requests.get(f"https://router.project-osrm.org/route/v1/driving/{a[1]},{a[0]};{b[1]},{b[0]}",
                     params={"overview": "simplified", "geometries": "geojson"}, headers=UA, timeout=20)
    r.raise_for_status()
    rt = r.json()["routes"][0]
    return {"a": a, "b": b, "km": round(rt["distance"] / 1000, 1), "min": round(rt["duration"] / 60),
            "path": rt["geometry"]["coordinates"]}


WMO = {0: "Clear sky", 1: "Mostly clear", 2: "Partly cloudy", 3: "Overcast", 45: "Fog", 48: "Fog",
       51: "Light drizzle", 53: "Drizzle", 55: "Heavy drizzle", 61: "Light rain", 63: "Rain",
       65: "Heavy rain", 80: "Rain showers", 81: "Rain showers", 82: "Violent showers",
       95: "Thunderstorm", 96: "Thunderstorm", 99: "Thunderstorm"}


@st.cache_data(ttl=900, show_spinner=False)
def weather(lat, lon):
    try:
        r = requests.get("https://api.open-meteo.com/v1/forecast", timeout=15, params={
            "latitude": lat, "longitude": lon, "timezone": "auto",
            "current": "temperature_2m,weather_code,wind_speed_10m,precipitation"})
        r.raise_for_status()
        c = r.json()["current"]
        return {"temp": round(c["temperature_2m"]), "wind": round(c["wind_speed_10m"]),
                "rain": c["precipitation"], "text": WMO.get(c["weather_code"], "Mixed conditions")}
    except Exception:
        return None


def rule_guidance(km, mins, wx):
    tips = []
    if km > 300:
        tips.append("Split the drive into legs and plan a rest stop at least every 2 hours.")
    if mins > 360:
        tips.append("Leave early so most of the drive is in daylight, and avoid night driving if you can.")
    if wx and (wx["rain"] > 0 or any(w in wx["text"].lower() for w in ("rain", "storm", "shower"))):
        tips.append("Rain at the destination: allow extra time and keep the speed down.")
    tips += ["Fill the tank before you leave and carry water and a charged power bank.",
             "Share your live location with your trusted contact for the whole journey."]
    return {"summary": f"A {km:.0f} km drive of about {mins / 60:.1f} hours. Prepare before you leave.",
            "tips": tips[:5], "source": "Built-in guidance"}


@st.cache_data(ttl=1800, show_spinner=False)
def guidance(origin, dest, km, mins, wx):
    key = secret("GEMINI_API_KEY")
    if key:
        prompt = (f"A solo traveller is driving from {origin} to {dest}: {km} km, about {mins} minutes. "
                  f"Destination weather: {json.dumps(wx)}. Give practical road-safety guidance. Reply with "
                  'JSON only, no markdown: {"summary": "one calm sentence", "tips": ["3 to 5 short tips"]}')
        models = [secret("GEMINI_MODEL", "gemini-3.5-flash"), "gemini-3.1-flash-lite", "gemini-3-flash-preview"]
        for model in dict.fromkeys(models):
            try:
                r = requests.post(
                    f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
                    headers={"x-goog-api-key": key}, timeout=40,
                    json={"contents": [{"parts": [{"text": prompt}]}],
                          "generationConfig": {"responseMimeType": "application/json"}})
                if r.status_code in (404, 429, 500, 502, 503, 504):
                    continue
                r.raise_for_status()
                text = r.json()["candidates"][0]["content"]["parts"][0]["text"]
                out = json.loads(text.strip().strip("`").removeprefix("json").strip())
                return {"summary": out["summary"], "tips": out["tips"][:5], "source": "AI guidance"}
            except Exception:
                break
    return rule_guidance(km, mins, wx)


# ---------------------------------------------------------------- state
S = st.session_state
for k, v in {"route": None, "journey": False, "log": [], "el": 0.0, "last": 0.0,
             "next_at": 60, "status": "", "done": False}.items():
    S.setdefault(k, v)

st.caption("safeyatra")
st.title("Drive far. Stay checked in.")
st.write("Plan your route, name someone who has your back, and confirm you are safe at the interval you choose.")

with st.form("plan"):
    c1, c2 = st.columns(2)
    origin = c1.text_input("From", "Hyderabad")
    dest = c2.text_input("To", "Goa")
    go = st.form_submit_button("Plan my journey", type="primary")
if go:
    try:
        with st.spinner("Planning your route…"):
            S.route = plan(origin.strip(), dest.strip())
            S.names = (origin.strip(), dest.strip())
            S.journey, S.done, S.log, S.el = False, False, [], 0.0
    except ValueError as e:
        st.error(str(e))
    except Exception:
        st.error("The route service is not responding. Try again in a moment.")

R = S.route
if R:
    # -------------------------------------------------------------- route
    st.header("Ready when you are.")
    path = [{"path": R["path"]}]
    pts = [{"lon": R["a"][1], "lat": R["a"][0]}, {"lon": R["b"][1], "lat": R["b"][0]}]
    lats, lons = [p[1] for p in R["path"]], [p[0] for p in R["path"]]
    st.pydeck_chart(pdk.Deck(
        layers=[pdk.Layer("PathLayer", path, get_path="path", get_color=[47, 93, 74], width_min_pixels=4),
                pdk.Layer("ScatterplotLayer", pts, get_position="[lon, lat]", get_fill_color=[176, 56, 58],
                          get_radius=6000, radius_min_pixels=7)],
        initial_view_state=pdk.ViewState(latitude=(min(lats) + max(lats)) / 2,
                                         longitude=(min(lons) + max(lons)) / 2,
                                         zoom=max(2, 7.5 - max(max(lats) - min(lats), (max(lons) - min(lons)) * .8) ** .5 * 1.6)),
        map_style=None), height=360)
    m = st.columns(4)
    m[0].metric("Distance", f"{R['km']} km")
    m[1].metric("Est. drive time", fmt(R["min"]))
    m[2].metric("Mode", "Driving")
    m[3].metric("Status", "On the road" if S.journey and not S.done else "Arrived" if S.done else "Ready")
    wx = weather(R["b"][0], R["b"][1])

    # -------------------------------------------------------------- solo mode
    st.header("Travel with someone in your corner.")
    st.caption("Your details stay in this browser session. SOS and help requests are logged on screen only; "
               "this version does not send messages or make calls.")
    c1, c2 = st.columns(2)
    with c1.container(border=True):
        st.write("**Someone you trust**")
        S.contact = st.text_input("Contact name", key="cn")
        st.text_input("Phone number", key="cp", placeholder="+91")
        st.text_input("Your name", key="yn")
    with c2.container(border=True):
        label = st.radio("Check-in interval", ["Every 30 min", "Every 1 hour", "Every 2 hours"], index=1)
        interval = {"Every 30 min": 30, "Every 1 hour": 60, "Every 2 hours": 120}[label]
    with st.container(border=True):
        checks = [st.checkbox(t, key=f"chk{i}") for i, t in enumerate(
            ["Phone ready. Battery is full and data is on.", "Emergency contact added.", "Route reviewed.",
             "Essentials packed. Water, charger, ID."])]
        n = sum(checks)
        st.progress(n / 4, text=f"{n}/4 ready")
        ready = n == 4 and S.cn.strip() and len(S.cp.strip()) > 5
        if st.button("Start journey", type="primary", disabled=not ready or S.journey):
            S.journey, S.done, S.el, S.last = True, False, 0.0, time.time()
            S.next_at, S.log = interval, []
            st.rerun()
        if not ready and not S.journey:
            st.caption("Add a contact and finish the checklist to start.")
        S.interval = interval

    # -------------------------------------------------------------- monitor
    if S.journey:
        st.header("Stay aware while you travel.")
        st.toggle("Demo speed (60x)", key="demo")

        def log(kind, text):
            S.log.insert(0, f"{time.strftime('%I:%M %p')}  {text}")
            S.status = kind
            if kind == "safe":
                S.next_at = S.el + S.interval
            if kind == "arrived":
                S.done = True

        @st.fragment(run_every="1s")
        def monitor():
            now = time.time()
            if not S.done:
                S.el += (now - S.last) / 60 * (60 if S.get("demo") else 1)
            S.last = now
            pct = min(1.0, S.el / R["min"])
            with st.container(border=True):
                st.write(f"**{'Journey complete' if S.done else 'Journey in progress'}**  ·  "
                         f"trusted contact {S.cn}  ·  check-in every {S.interval} min")
                st.progress(pct)
                a = st.columns(4)
                a[0].metric("Progress", f"{round(pct * 100)}%")
                a[1].metric("Elapsed", fmt(S.el))
                a[2].metric("Est. remaining", fmt(R["min"] * (1 - pct)))
                a[3].metric("Distance left", f"{round(R['km'] * (1 - pct))} km")
                wait = S.next_at - S.el
                if not S.done:
                    if wait <= -5:
                        st.error("Check-in missed. Tap “I’m safe” now.")
                    elif wait <= 0:
                        st.warning("Check-in due. Tap “I’m safe” to confirm.")
                    else:
                        st.caption(f"Next safety check-in in {fmt(wait)}.")
                if S.status == "help":
                    st.error("Help request logged. This version does not notify your contact.")
                elif S.status == "sos":
                    st.error("SOS logged. If you are in danger, call 112 now.")
                b = st.columns(4)
                b[0].button("I’m safe", on_click=log, args=("safe", "Confirmed safe"), disabled=S.done, type="primary")
                b[1].button("Need help", on_click=log, args=("help", "Asked for help"), disabled=S.done)
                b[2].button("SOS", on_click=log, args=("sos", "SOS raised"), disabled=S.done)
                b[3].button("I’ve reached safely", on_click=log, args=("arrived", "Reached safely"), disabled=S.done)
                st.write("**Safety check-ins**")
                for line in S.log or ["No check-ins yet."]:
                    st.caption(line)

        monitor()

    # -------------------------------------------------------------- analysis
    st.header("Understand your journey.")
    h = R["min"] / 60
    cards = [("Long-distance journey" if R["km"] > 300 else "Manageable distance", f"{R['km']} km. " + (
                 "Plan rest stops and fuel ahead of time." if R["km"] > 300 else "One sitting should be fine."),
             "High" if R["km"] > 300 else "Low"),
             ("Extended drive" if h > 4 else "Short drive", f"About {fmt(R['min'])} of driving. " + (
                 "Take a break every 2 hours." if h > 4 else "One short break is enough."),
             "High" if h > 6 else "Moderate" if h > 3 else "Low"),
             (wx["text"] if wx else "Weather unknown", f"{wx['temp']}°C at the destination." if wx else
              "Check the forecast before you leave.", "Low"),
             ("Plan the travel window" if h > 6 else "Pack the basics", "Leave early so most of the drive is in "
              "daylight." if h > 6 else "Fill the tank, charge your phone, carry water.", "Moderate" if h > 6 else "Low")]
    cols = st.columns(2)
    for i, (t, d, lvl) in enumerate(cards):
        with cols[i % 2].container(border=True):
            st.caption(lvl.upper())
            st.subheader(t)
            st.write(d)

    st.header("A little more context.")
    with st.spinner("Loading guidance…"):
        g = guidance(*S.names, R["km"], R["min"], wx)
    with st.container(border=True):
        st.caption(g["source"].upper())
        st.write(f"**{g['summary']}**")
        for t in g["tips"]:
            st.write(f"- {t}")
    if wx:
        with st.container(border=True):
            st.subheader("Before you arrive.")
            w = st.columns(3)
            w[0].metric(S.names[1], f"{wx['temp']}°C", wx["text"], delta_color="off")
            w[1].metric("Wind", f"{wx['wind']} km/h")
            w[2].metric("Rain", f"{wx['rain']} mm")
