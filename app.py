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
    """Dobiera kolor tła i ikonę na podstawie treści prognozy"""
    text = text.lower()
    if any(word in text for word in ["deszcz", "opady", "mżawka"]):
        return "linear-gradient(180deg, #1e3c72 0%, #2a5298 100%)", "🌧️"
    if "śnieg" in text:
        return "linear-gradient(180deg, #83a4d4 0%, #b6fbff 100%)", "❄️"
    if any(word in text for word in ["słońce", "słoneczn", "pogodn", "jasno"]):
        return "linear-gradient(180deg, #f8b500 0%, #fceabb 100%)", "☀️"
    if any(word in text for word in ["pochmurno", "chmury", "zachmurzenie"]):
        return "linear-gradient(180deg, #373b44 0%, #4286f4 100%)", "☁️"
    return "linear-gradient(180deg, #0f2027 0%, #2c5364 100%)", "🌤️"

def fetch_data():
    """Próbuje pobrać dane. Jeśli wystąpi błąd (np. 429), zachowuje stare dane."""
    try:
        api_key = st.secrets["GEMINI_API_KEY"]
        res = requests.get("https://pogodadlaslaska.pl/", timeout=15)
        res.raise_for_status()
        soup = BeautifulSoup(res.text, 'html.parser')
        tekst_strony = soup.get_text(separator=' ', strip=True)[:8000]

        client = genai.Client(api_key=api_key)
        prompt = (
           "Pisz w stylu śląskiego barda"
            "Jesteś profesjonalnym pogodynką na Śląsku. Przeanalizuj dane: " + tekst_strony + "\n\n"
            "Zwróć odpowiedź DOKŁADNIE w tym formacie:\n"
            "Linia 1: temperatura,wiatr,jakość_powietrza (same wartości, np: 12,15,Dobra)\n"
            "Linia 2: Jedna krótka, inteligentna rada życiowa na dziś (max 15 słów)\n"
            "Reszta: Krótka prognoza w punktach z ikonami emoji. "
            "WAŻNE: Dla każdego opisywanego okresu (np. rano, po południu, noc) "
            "PODAJ KONKRETNY ZAKRES TEMPERATUR (np. 'od 2°C do 5°C'), unikaj sformułowań typu 'będzie mroźno' bez podania stopni."
        )
        
        response = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
        
        # Sukces - aktualizujemy sesję
        st.session_state['last_forecast'] = response.text
        st.session_state['last_update'] = time.strftime("%H:%M:%S")
        st.session_state['update_status'] = "success"
    except Exception as e:
        # Błąd (np. limit API) - nie czyścimy 'last_forecast'
        st.session_state['update_status'] = "error"
        print(f"Błąd API: {e}")

# --- INICJALIZACJA SESJI ---
if 'last_forecast' not in st.session_state:
    st.session_state['last_forecast'] = None
if 'update_status' not in st.session_state:
    st.session_state['update_status'] = "idle"

# Auto-odświeżanie co 1h
st_autorefresh(interval=3600000, key="weather_refresh")

# --- INTERFEJS ---
if st.session_state['last_forecast']:
    try:
        lines = st.session_state['last_forecast'].split('\n')
        data_line = lines[0].split(',')
        raw_temp, wind, air = data_line[0], data_line[1], data_line[2]
        advice, main_text = lines[1], "\n".join(lines[2:])
        
        clean_temp = "".join(re.findall(r"[-+]?\d+", raw_temp))
        bg_color, main_icon = get_weather_theme(main_text)

        # Style CSS
        st.markdown(f"""
            <style>
            .stApp {{ background: {bg_color}; background-attachment: fixed; color: white !important; }}
            .card {{ background: rgba(255, 255, 255, 0.15); padding: 20px; border-radius: 20px; backdrop-filter: blur(15px); border: 1px solid rgba(255, 255, 255, 0.2); margin-top: 15px; }}
            .advice-card {{ background: rgba(0, 255, 127, 0.2); padding: 15px; border-left: 5px solid #00ff7f; border-radius: 10px; margin: 10px 0; }}
            h1, h2, h3, p, span {{ color: white !important; }}
            </style>
        """, unsafe_allow_html=True)

        st.title("🌤️ Śląsk AI Dashboard")
        
        # Jeśli ostatnia próba była błędem (np. 429), pokaż dyskretne info
        if st.session_state.get('update_status') == "error":
            st.info("⚠️ Aktualizacja w toku (serwer zajęty). Widzisz dane z godziny: " + st.session_state.get('last_update', '---'))

        col1, col2 = st.columns([1, 1])
        with col1:
            st.markdown(f"""
                <div style="display: flex; align-items: center; justify-content: center; background: rgba(0,0,0,0.15); border-radius: 20px; padding: 10px;">
                    <span style="font-size: 70px;">{main_icon}</span>
                    <span style="font-size: 60px; font-weight: bold; margin-left: 10px;">{clean_temp}°</span>
                </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.write(f"💨 Wiatr: **{wind} km/h**")
            st.write(f"🌫️ Powietrze: **{air}**")
            if st.button("ODŚWIEŻ"):
                fetch_data()
                st.rerun()

        st.markdown(f"<div class='advice-card'>💡 {advice}</div>", unsafe_allow_html=True)
        st.markdown("### 📝 Prognoza szczegółowa")
        st.markdown(f"<div class='card'>{main_text}</div>", unsafe_allow_html=True)
        st.caption(f"Ostatnia udana aktualizacja: {st.session_state.get('last_update', '---')}")

    except:
        st.error("Wystąpił problem z formatowaniem. Spróbuj odświeżyć.")
        if st.button("RESTART"):
            fetch_data()
            st.rerun()
else:
    st.title("🌤️ Śląsk AI")
    if st.session_state.get('update_status') == "error":
        st.error("Limit zapytań wyczerpany (Błąd 429).")
        st.info("Google Gemini potrzebuje chwili odpoczynku. Odczekaj minutę i spróbuj ponownie.")
        if st.button("PONÓW PRÓBĘ"):
            fetch_data()
            st.rerun()
     else:
         st.info("Pobieram dane startowe...")
         fetch_data()
        # Małe opóźnienie, żeby nie spamować serwera
         time.sleep(1) 
          st.rerun()

