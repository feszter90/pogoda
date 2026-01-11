import streamlit as st
import requests
from bs4 import BeautifulSoup
from google import genai
import time
import re
from streamlit_autorefresh import st_autorefresh

# --- 1. KONFIGURACJA ---
st.set_page_config(page_title="Pogoda u Kamila", page_icon="🌤️", layout="centered")

def get_weather_theme(text):
    text = text.lower()
    if any(word in text for word in ["deszcz", "loć", "opady"]):
        return "linear-gradient(180deg, #1e3c72 0%, #2a5298 100%)", "🌧️", "white"
    if any(word in text for word in ["śnieg", "mróz", "zimno"]):
        return "linear-gradient(180deg, #83a4d4 0%, #b6fbff 100%)", "❄️", "#1e3c72"
    if any(word in text for word in ["słońce", "słoneczn", "pogodn", "ciepło"]):
        return "linear-gradient(180deg, #f8b500 0%, #fceabb 100%)", "☀️", "#212121"
    return "linear-gradient(180deg, #0f2027 0%, #2c5364 100%)", "🌤️", "white"

def get_precise_temp():
    try:
        url = "https://api.open-meteo.com/v1/forecast?latitude=50.0971&longitude=18.5417&current_weather=true"
        response = requests.get(url).json()
        return response['current_weather']['temperature']
    except:
        return None

# --- 2. SILNIK AI ---
def fetch_data():
    try:
        api_key = st.secrets["GEMINI_API_KEY"]
        precise_now = get_precise_temp()
        
        res = requests.get("https://pogodadlaslaska.pl/", timeout=15)
        res.raise_for_status()
        soup = BeautifulSoup(res.text, 'html.parser')
        tekst_strony = soup.get_text(separator=' ', strip=True)[:15000]

        client = genai.Client(api_key=api_key)
        
        prompt = (
            f"Analizuj dane pogodowe: \n{tekst_strony}\n\n"
            f"Aktualna temperatura to {precise_now}°C.\n"
            f"Przygotuj prognozę w dwóch częściach:\n"
            f"1. SZCZEGÓŁY NA DZIŚ: rano, południe, wieczór, noc.\n"
            f"2. KOLEJNE DNI: ogólnie na cały dzień.\n\n"
            f"Zwróć odpowiedź DOKŁADNIE według tego wzoru:\n"
            f"INFO: [wiatr km/h], [jakość powietrza]\n"
            f"RADA: [krótka rada z humorem dla Kamila]\n"
            f"DZISIAJ:\n"
            f"[Ikona] [Pora]| [Temp]| [Opis]\n"
            f"PROGNOZA_DNI:\n"
            f"[Ikona] [Dzień]| [Zakres]| [Opis]"
        )
        
        response = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
        
        st.session_state['last_forecast'] = response.text
        st.session_state['current_temp'] = precise_now
        st.session_state['last_update'] = time.strftime("%H:%M:%S")
    except Exception as e:
        st.error(f"Feler: {e}")

# --- 3. LOGIKA WYŚWIETLANIA ---
if 'last_forecast' not in st.session_state:
    st.session_state['last_forecast'] = None

st_autorefresh(interval=3600000, key="weather_refresh")

if st.session_state['last_forecast']:
    raw_text = st.session_state['last_forecast']
    
    info_match = re.search(r"INFO:\s*(.*)", raw_text)
    rada_match = re.search(r"RADA:\s*(.*)", raw_text)
    info_text = info_match.group(1).split('\n')[0] if info_match else "Brak danych"
    advice = rada_match.group(1).split('\n')[0] if rada_match else "Udanego dnia, Kamil!"
    clean_temp = st.session_state.get('current_temp', '??')

    # Rozdzielanie sekcji "Dzisiaj" i "Kolejne dni"
    today_lines = []
    future_lines = []
    
    if "DZISIAJ:" in raw_text and "PROGNOZA_DNI:" in raw_text:
        parts = raw_text.split("PROGNOZA_DNI:")
        today_part = parts[0].split("DZISIAJ:")[-1].strip()
        future_part = parts[1].strip()
        
        today_lines = [l.strip() for l in today_part.split('\n') if "|" in l]
        future_lines = [l.strip() for l in future_part.split('\n') if "|" in l]

    bg_color, main_icon, font_color = get_weather_theme(raw_text)

    st.markdown(f"""
        <style>
        .stApp {{ background: {bg_color}; background-attachment: fixed; }}
        h1, h2, h3, p, span, div {{ color: {font_color} !important; font-family: 'Segoe UI', sans-serif; }}
        .main-card {{ background: rgba(0,0,0,0.1); padding: 30px; border-radius: 30px; text-align: center; border: 1px solid rgba(255,255,255,0.1); }}
        .advice-card {{ background: rgba(255, 255, 255, 0.2); padding: 15px; border-radius: 15px; margin: 20px 0; border-left: 5px solid orange; }}
        .forecast-card {{ background: rgba(255, 255, 255, 0.15); padding: 12px; border-radius: 20px; margin-bottom: 8px; backdrop-filter: blur(10px); border: 1px solid rgba(255,255,255,0.05); }}
        .section-title {{ margin: 25px 0 10px 5px; font-weight: bold; font-size: 1.2em; opacity: 0.9; }}
        </style>
    """, unsafe_allow_html=True)

    st.title("⚒️ Pogoda u Kamila")

    # Główna temperatura
    st.markdown(f"""
        <div class="main-card">
            <div style="font-size: 80px; margin-bottom: 5px;">{main_icon}</div>
            <div style="font-size: 20px; text-transform: uppercase; letter-spacing: 2px; opacity: 0.8;">Kamil, dzisiaj jest</div>
            <div style="font-size: 100px; font-weight: 900; line-height: 1;">{clean_temp}°</div>
            <div style="font-size: 18px; margin-top: 15px; opacity: 0.9;">{info_text}</div>
        </div>
    """, unsafe_allow_html=True)

    st.markdown(f"<div class='advice-card'>💡 {advice}</div>", unsafe_allow_html=True)

    # --- SEKCJA: DZISIAJ (Szczegóły) ---
    if today_lines:
        st.markdown("<div class='section-title'>🕒 Plan na dzisiaj:</div>", unsafe_allow_html=True)
        for line in today_lines:
            parts = line.split('|')
            if len(parts) >= 3:
                st.markdown(f"""
                    <div class="forecast-card">
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <span style="font-weight: bold;">{parts[0].strip()}</span>
                            <span style="background: rgba(0,0,0,0.1); padding: 2px 10px; border-radius: 10px; font-weight: bold;">{parts[1].strip()}</span>
                        </div>
                        <div style="margin-top: 5px; font-size: 0.9em;">{parts[2].strip()}</div>
                    </div>
                """, unsafe_allow_html=True)

    # --- SEKCJA: KOLEJNE DNI ---
    if future_lines:
        st.markdown("<div class='section-title'>🗓️ Nadchodzące dni:</div>", unsafe_allow_html=True)
        for line in future_lines:
            parts = line.split('|')
            if len(parts) >= 3:
                st.markdown(f"""
                    <div class="forecast-card" style="background: rgba(0,0,0,0.05);">
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <span style="font-weight: 500;">{parts[0].strip()}</span>
                            <span style="font-weight: 900;">{parts[1].strip()}</span>
                        </div>
                        <div style="margin-top: 3px; font-size: 0.85em; opacity: 0.8;">{parts[2].strip()}</div>
                    </div>
                """, unsafe_allow_html=True)

    if st.button("Odśwież dane"):
        fetch_data()
        st.rerun()

    st.caption(f"Aktualizacja: {st.session_state.get('last_update', '---')}")

else:
    fetch_data()
    st.rerun()

