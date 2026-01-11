import streamlit as st
import requests
from bs4 import BeautifulSoup
from google import genai
import time
import re
from streamlit_autorefresh import st_autorefresh

# --- KONFIGURACJA STRONY ---
st.set_page_config(page_title="Pogoda & Air Śląsk AI", page_icon="🌤️", layout="centered")

# --- FUNKCJE POMOCNICZE ---
def get_weather_theme(text):
    """Dobiera kolor tła i ikonę główną na podstawie tekstu prognozy"""
    text = text.lower()
    if "deszcz" in text or "opady" in text:
        return "linear-gradient(180deg, #1e3c72 0%, #2a5298 100%)", "🌧️"
    if "śnieg" in text:
        return "linear-gradient(180deg, #83a4d4 0%, #b6fbff 100%)", "❄️"
    if "słońce" in text or "słoneczn" in text or "pogodn" in text:
        return "linear-gradient(180deg, #f8b500 0%, #fceabb 100%)", "☀️"
    if "pochmurno" in text or "chmury" in text:
        return "linear-gradient(180deg, #373b44 0%, #4286f4 100%)", "☁️"
    return "linear-gradient(180deg, #0f2027 0%, #2c5364 100%)", "🌤️"

def fetch_data():
    """Pobiera dane ze strony i przetwarza je przez AI"""
    try:
        api_key = st.secrets["GEMINI_API_KEY"]
        res = requests.get("https://pogodadlaslaska.pl/", timeout=15)
        res.raise_for_status()
        soup = BeautifulSoup(res.text, 'html.parser')
        tekst_strony = soup.get_text(separator=' ', strip=True)[:8000]

        client = genai.Client(api_key=api_key)
        prompt = (
            "Jesteś profesjonalnym pogodynką na Śląsku. Przeanalizuj dane: " + tekst_strony + "\n\n"
            "Zwróć odpowiedź DOKŁADNIE w tym formacie:\n"
            "Linia 1: temperatura,wiatr,jakość_powietrza (same wartości, np: 12,15,Dobra)\n"
            "Linia 2: Jedna krótka, inteligentna rada życiowa na dziś (max 15 słów)\n"
            "Reszta: Krótka prognoza w punktach z ikonami emoji."
        )
        
        response = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
        st.session_state['last_forecast'] = response.text
        st.session_state['last_update'] = time.strftime("%H:%M:%S")
    except Exception as e:
        st.error(f"Błąd podczas pobierania danych: {e}")

# --- INICJALIZACJA SESJI ---
if 'last_forecast' not in st.session_state:
    st.session_state['last_forecast'] = None

# Automatyczne odświeżanie co 1 godzinę (3600000 ms)
st_autorefresh(interval=3600000, key="weather_refresh")

# --- WYŚWIETLANIE INTERFEJSU ---
if st.session_state['last_forecast']:
    try:
        raw_text = st.session_state['last_forecast']
        lines = raw_text.split('\n')
        
        # Wyciąganie danych z pierwszej linii
        data_line = lines[0].split(',')
        raw_temp = data_line[0]
        wind = data_line[1]
        air = data_line[2]
        
        # Wyciąganie rady i reszty tekstu
        advice = lines[1]
        main_text = "\n".join(lines[2:])
        
        # Oczyszczanie temperatury (zostawiamy tylko cyfry)
        clean_temp = "".join(re.findall(r"[-+]?\d+", raw_temp))
        
        # Dobieranie motywu
        bg_color, main_icon = get_weather_theme(main_text)

        # Aplikowanie stylów CSS
        st.markdown(f"""
            <style>
            .stApp {{
                background: {bg_color};
                background-attachment: fixed;
                color: white !important;
            }}
            .card {{
                background: rgba(255, 255, 255, 0.15);
                padding: 20px;
                border-radius: 20px;
                backdrop-filter: blur(15px);
                border: 1px solid rgba(255, 255, 255, 0.2);
                color: white;
                margin-top: 20px;
            }}
            .advice-card {{
                background: rgba(0, 255, 127, 0.25);
                padding: 15px;
                border-left: 5px solid #00ff7f;
                border-radius: 12px;
                color: white;
                font-weight: 500;
                margin: 15px 0;
            }}
            h1, h2, h3, p, span, div {{
                color: white !important;
            }}
            </style>
        """, unsafe_allow_html=True)

        # NAGŁÓWEK
        st.title("🌤️ Śląsk AI Dashboard")
        
        col1, col2 = st.columns([1, 1])
        with col1:
            # Ikona i Temp obok siebie
            st.markdown(f"""
                <div style="display: flex; align-items: center; justify-content: center; background: rgba(0,0,0,0.1); border-radius: 20px; padding: 10px;">
                    <span style="font-size: 70px;">{main_icon}</span>
                    <span style="font-size: 60px; font-weight: bold; margin-left: 10px;">{clean_temp}°</span>
                </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.write(f"💨 Wiatr: **{wind} km/h**")
            st.write(f"🌫️ Powietrze: **{air}**")
            if st.button("ODŚWIEŻ TERAZ"):
                fetch_data()
                st.rerun()

        # RADA DNIA
        st.markdown(f"<div class='advice-card'>💡 {advice}</div>", unsafe_allow_html=True)
        
        # PROGNOZA SZCZEGÓŁOWA
        st.markdown("### 📝 Prognoza szczegółowa")
        st.markdown(f"<div class='card'>{main_text}</div>", unsafe_allow_html=True)
        
        st.caption(f"Ostatnia aktualizacja: {st.session_state.get('last_update', '---')}")

    except Exception as e:
        st.error("Błąd parsowania danych przez AI. Spróbuj odświeżyć.")
        if st.button("RESTART"):
            fetch_data()
            st.rerun()
else:
    st.title("🌤️ Witaj w Śląsk AI")
    st.info("Pobieram najnowszą prognozę...")
    fetch_data()
    st.rerun()
