# 🧭 SafeYatra — Journey Safety Companion

![Python](https://img.shields.io/badge/Python-3.10+-blue)
![Streamlit](https://img.shields.io/badge/Streamlit-App-red)
![Gemini](https://img.shields.io/badge/Gemini-Free%20Tier-green)

A solo-travel safety app that plans your drive, keeps a trusted contact in your corner, and runs a check-in timer so someone always knows you are okay.

## 🌐 Live Demo
👉 [Click here to try SafeYatra](https://YOUR-APP-NAME.streamlit.app)

## 🚀 Features
- 🗺️ Plan a route between any two places and see it on a map
- ⏱️ Distance, drive time and live destination weather
- 🤝 Add a trusted contact and choose a check-in interval
- ✅ Pre-journey checklist before you start
- 📍 Journey monitor with progress, time remaining and distance left
- 🆘 "I'm safe", "Need help", SOS and "I've reached safely" buttons with a check-in log
- 🤖 AI road-safety guidance for your route, with a built-in fallback
- 🎨 Light cream and green dashboard UI

## ⏲️ Check-in Intervals
| Option | Best for |
|--------|----------|
| Every 30 min | Night drives, unfamiliar roads |
| Every 1 hour | Normal long drives |
| Every 2 hours | Highway trips with planned stops |

## 🛠 Tech Stack
| Tool | Purpose |
|------|---------|
| Streamlit | Frontend dashboard and journey monitor |
| Gemini (free tier) | AI journey guidance |
| OpenStreetMap Nominatim | Place search |
| OSRM | Driving routes |
| Open-Meteo | Destination weather |
| PyDeck | Route map |
| Python 3.10+ | Core language |

All services used are free and need no payment. Only the Gemini key is optional; without it, built-in rules write the guidance.

## ⚙️ Run Locally
```bash
git clone https://github.com/tejaswinireddy357/safeyatra.git
cd safeyatra
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
streamlit run streamlit_app.py
```

### Optional: AI guidance
Get a free key at [Google AI Studio](https://aistudio.google.com/apikey), then create `.streamlit/secrets.toml`:
```toml
GEMINI_API_KEY = "your-key"
```
Never commit this file.

## 📂 Project Structure
```
safeyatra/
├── streamlit_app.py            # Main Streamlit app
├── requirements.txt            # Python dependencies
├── .gitignore                  # Git ignore rules
├── .streamlit/
│   ├── config.toml             # Light cream and green theme
│   └── secrets.toml.example    # Example for the optional Gemini key
└── README.md
```

## ⚠️ Limitations
- SOS and "Need help" are shown on screen only. This version does not send messages or make calls.
- The check-in log lives in your browser session and is cleared on refresh.
- Progress follows the clock, not live GPS. A "Demo speed (60x)" switch lets you test quickly.
- If you are in danger, call **112** (India) or your local emergency number.
