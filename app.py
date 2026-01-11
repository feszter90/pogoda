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
    if any(word in text for word in ["deszcz", "loć", "opady", "deszczowo"]):
        return "linear-gradient(180deg, #1e3c72 0%, #2a5298 100%)", "🌧️", "white"
    if any(word in text for word in ["śnieg", "mróz", "pizgo", "zimno"]):
        return "linear-gradient(180deg, #83a4d4 0%, #b6fbff 100%)", "❄️", "#1e3c72"
    if any(word in text for word in ["słońce", "słoneczn", "pogodn", "ciepło"]):
        return "linear-gradient(180deg, #f8b500 0%, #fceabb 100%)", "☀️", "#212121"
    return "linear-gradient(180deg, #0f2027 0%, #2c5364 100%)", "🌤️", "white"

# --- 2. POBIERANIE DANYCH ---
def fetch_data():
    try:
        api_key = st.secrets["GEMINI_API_KEY"]
        res = requests.get("https://pogodadlaslaska.pl/", timeout=15)
        res.raise_for_status()
        soup = BeautifulSoup(res.text, 'html.parser')
        tekst_strony = soup.get_text(separator=' ', strip=True)[:15000]

        client = genai.Client(api_key=api_key)
        
        # PROMPT: Śląski Bard - Wersja Przystępna (Lekki Akcent)
        prompt = (
            f"Analizuj dane pogodowe: \n{tekst_strony}\n\n"
            f"Jesteś Śląskim Bardem, ale piszesz w sposób zrozumiały dla każdego Polaka. "
            f"Używaj poprawnej polszczyzny z lekkim śląskim zabarwieniem (akcentem). "
            f"Zamiast trudnych gwarowych słów, używaj tylko tych powszechnie znanych i sympatycznych. "
            f"Nie przesadzaj z gwarą – ma być klimatycznie, ale czytelnie!\n"
            f"Odpowiedz DOKŁADNIE według tego wzoru:\n"
            f"TEMP_TERAZ: [sama liczba]\n"
            f"WIATR: [liczba]\n"
            f"LUFT: [ocena]\n"
            f"RADA: [krótka rada z lekkim śląskim humorem]\n"
            f"PROGNOZA_LISTA:\n"
            f"[Ikona] [Pora]| [Temperatura]| [Opis zrozumiały dla każdego]"
        )
        
        response = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
        st.session_state['last_forecast'] = response.text
        st.session_state['last_update'] = time.strftime("%H:%M:%S")
        st.session_state['update_status'] = "success"
    except Exception as e:
        st.session_state['update_status'] = "error"
        st.error(f"Feler: {e}")

# --- 3. LOGIKA APLIKACJI ---
if 'last_forecast' not in st.session_state:
    st.session_state['last_forecast'] = None

st_autorefresh(interval=3600000, key="weather_refresh")

if st.session_state['last_forecast']:
    raw_text = st.session_state['last_forecast']
    
    # Wyciąganie danych
    temp_match = re.search(r"TEMP_TERAZ:\s*([\d+-]+)", raw_text)
    wiatr_match = re.search(r"WIATR:\s*([\d+-]+)", raw_text)
    luft_match = re.search(r"LUFT:\s*(.*)", raw_text)
    rada_match = re.search(r"RADA:\s*(.*)", raw_text)
    
    clean_temp = temp_match.group(1) if temp_match else "??"
    clean_wiatr = wiatr_match.group(1) if wiatr_match else "--"
    clean_luft = luft_match.group(1).split('\n')[0] if luft_match else "Nie wiadomo"
    advice = rada_match.group(1).split('\n')[0] if rada_match else "Miejcie się dobrze!"

    # Przetwarzanie listy
    forecast_lines = []
    if "PROGNOZA_LISTA:" in raw_text:
        list_part = raw_text.split("PROGNOZA_LISTA:")[-1].strip()
        forecast_lines = [l.strip() for l in list_part.split('\n') if "|" in l]

    bg_color, main_icon, font_color = get_weather_theme(raw_text)

    # STYLE
    st.markdown(f"""
        <style>
        .stApp {{ background: {bg_color}; background-attachment: fixed; }}
        h1, h2, h3, p, span, div {{ color: {font_color} !important; font-family: 'Segoe UI', Tahoma, sans-serif; }}
        .main-card {{ background: rgba(0,0,0,0.1); padding: 25px; border-radius: 30px; text-align: center; border: 1px solid rgba(255,255,255,0.1); margin-top: -30px; }}
        .advice-card {{ background: rgba(0, 255, 127, 0.15); padding: 15px; border-radius: 20px; border-left: 6px solid #008f4f; margin: 20px 0; font-size: 1.1em; }}
        .forecast-card {{ background: rgba(255, 255, 255, 0.18); padding: 15px; border-radius: 20px; margin-bottom: 10px; backdrop-filter: blur(15px); border: 1px solid rgba(255,255,255,0.1); }}
        </style>
    """, unsafe_allow_html=True)

    st.title("⚒️ Śląski Bard godo:")

    # Główny widok
    st.markdown(f"""
        <div class="main-card">
            <div style="font-size: 85px; margin-bottom: 10px;">{main_icon}</div>
            <div style="font-size: 90px; font-weight: 900; line-height: 0.8; margin-bottom: 20px;">{clean_temp}°</div>
            <div style="font-size: 18px; font-weight: 500; opacity: 0.9;">
                💨 Wiatr: {clean_wiatr} km/h | 🌫️ Luft: {clean_luft}
            </div>
        </div>
    """, unsafe_allow_html=True)

    st.markdown(f"<div class='advice-card'>💡 {advice}</div>", unsafe_allow_html=True)

    if forecast_lines:
        st.markdown("### 🗓️ Co nas czeka:")
        for line in forecast_lines:
            parts = line.split('|')
            if len(parts) >= 3:
                st.markdown(f"""
                    <div class="forecast-card">
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <span style="font-size: 1.1em; font-weight: bold;">{parts[0].strip()}</span>
                            <span style="background: rgba(0,0,0,0.1); padding: 4px 15px; border-radius: 12px; font-weight: 900; font-size: 1.1em;">{parts[1].strip()}</span>
                        </div>
                        <div style="margin-top: 8px; font-size: 1.05em; line-height: 1.4;">{parts[2].strip()}</div>
                    </div>
                """, unsafe_allow_html=True)

    if st.button("Odśwież pogodę"):
        fetch_data()
        st.rerun()

    st.caption(f"Aktualizacja: {st.session_state.get('last_update', '---')}")

else:
    st.info("Bard sprawdza co tam w pogodzie słychać...")
    fetch_data()
    st.rerun()
