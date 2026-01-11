import streamlit as st
import requests
from bs4 import BeautifulSoup
from google import genai
import time
import re
from streamlit_autorefresh import st_autorefresh

# --- 1. KONFIGURACJA ---
st.set_page_config(page_title="Śląski Bard: Pogoda AI", page_icon="⚒️", layout="centered")

def get_weather_theme(text):
    text = text.lower()
    if any(word in text for word in ["deszcz", "loć", "opady"]):
        return "linear-gradient(180deg, #1e3c72 0%, #2a5298 100%)", "🌧️", "white"
    if any(word in text for word in ["śnieg", "mróz", "pizgo"]):
        return "linear-gradient(180deg, #83a4d4 0%, #b6fbff 100%)", "❄️", "#1e3c72"
    if any(word in text for word in ["słońce", "słoneczn", "pogodn", "hic"]):
        return "linear-gradient(180deg, #f8b500 0%, #fceabb 100%)", "☀️", "#212121"
    return "linear-gradient(180deg, #0f2027 0%, #2c5364 100%)", "🌤️", "white"

# --- 2. POBIERANIE DANYCH ---
def fetch_data():
    try:
        api_key = st.secrets["GEMINI_API_KEY"]
        res = requests.get("https://pogodadlaslaska.pl/", timeout=15)
        res.raise_for_status()
        soup = BeautifulSoup(res.text, 'html.parser')
        tekst_strony = soup.get_text(separator=' ', strip=True)[:10000]

        client = genai.Client(api_key=api_key)
        
        prompt = (
            f"Jesteś Śląskim Bardem. Zanalizuj dane i odpowiedz PO ŚLĄSKU.\n"
            f"DANE: \n{tekst_strony}\n\n"
            f"FORMAT ODPOWIEDZI (DOKŁADNIE TAKI):\n"
            f"TEMP: [sama liczba stopni]\n"
            f"INFO: [wiatr km/h], [jakość powietrza]\n"
            f"RADA: [błyskotliwa rada po śląsku]\n"
            f"PROGNOZA:\n"
            f"[Ikona] [Pora]| [Temperatura]| [Opis po śląsku]"
        )
        
        response = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
        st.session_state['last_forecast'] = response.text
        st.session_state['last_update'] = time.strftime("%H:%M:%S")
        st.session_state['update_status'] = "success"
    except Exception as e:
        st.session_state['update_status'] = "error"
        st.error(f"Feler: {e}")

# --- 3. LOGIKA WYŚWIETLANIA ---
if 'last_forecast' not in st.session_state:
    st.session_state['last_forecast'] = None

st_autorefresh(interval=3600000, key="weather_refresh")

if st.session_state['last_forecast']:
    raw_text = st.session_state['last_forecast']
    
    # Ekstrakcja danych za pomocą wyrażeń regularnych (odporna na puste linie)
    temp_search = re.search(r"TEMP:\s*([\d+-]+)", raw_text)
    info_search = re.search(r"INFO:\s*(.*)", raw_text)
    rada_search = re.search(r"RADA:\s*(.*)", raw_text)
    
    clean_temp = temp_search.group(1) if temp_search else "??"
    info_text = info_search.group(1) if info_search else "Brak danych"
    advice = rada_search.group(1) if rada_search else "Bard mo dzisiej wolne..."

    # Wycinanie części prognozy (wszystko po słowie PROGNOZA:)
    forecast_part = raw_text.split("PROGNOZA:")[-1].strip()
    forecast_lines = [line for line in forecast_part.split('\n') if "|" in line]

    bg_color, main_icon, font_color = get_weather_theme(raw_text)

    st.markdown(f"""
        <style>
        .stApp {{ background: {bg_color}; background-attachment: fixed; }}
        h1, h2, h3, p, span, div {{ color: {font_color} !important; font-family: 'Arial'; }}
        .main-card {{ background: rgba(0,0,0,0.1); padding: 20px; border-radius: 25px; text-align: center; border: 1px solid rgba(255,255,255,0.1); }}
        .advice-card {{ background: rgba(0, 255, 127, 0.2); padding: 15px; border-radius: 15px; border-left: 5px solid #008f4f; margin: 20px 0; font-style: italic; }}
        .forecast-card {{ background: rgba(255, 255, 255, 0.2); padding: 15px; border-radius: 18px; margin-bottom: 10px; backdrop-filter: blur(10px); }}
        </style>
    """, unsafe_allow_html=True)

    st.title("⚒️ Śląski Bard godo:")

    st.markdown(f"""
        <div class="main-card">
            <div style="font-size: 80px;">{main_icon}</div>
            <div style="font-size: 70px; font-weight: bold;">{clean_temp}°C</div>
            <div style="font-size: 18px; opacity: 0.9;">{info_text}</div>
        </div>
    """, unsafe_allow_html=True)

    st.markdown(f"<div class='advice-card'>💡 {advice}</div>", unsafe_allow_html=True)

    for line in forecast_lines:
        parts = line.split('|')
        if len(parts) == 3:
            st.markdown(f"""
                <div class="forecast-card">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <b>{parts[0].strip()}</b>
                        <span style="background: rgba(0,0,0,0.1); padding: 3px 10px; border-radius: 10px; font-weight: bold;">{parts[1].strip()}</span>
                    </div>
                    <div style="margin-top: 5px; font-size: 0.9em;">{parts[2].strip()}</div>
                </div>
            """, unsafe_allow_html=True)

    if st.button("Odśwież dane"):
        fetch_data()
        st.rerun()
else:
    st.info("Pobieranie danych...")
    fetch_data()
    st.rerun()
