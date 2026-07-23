import streamlit as st
import pandas as pd
import json
import os

st.set_page_config(page_title="Macro Day Tracker", layout="wide")

# ---------------------------------------------------------
# MECHANIZM ZAPISU I ODCZYTU STANU (PERSISTENCE)
# ---------------------------------------------------------
CACHE_FILE = "user_selection.json"

def load_saved_state():
    """Wczytuje stan z pliku JSON przy pierwszym uruchomieniu."""
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_current_state():
    """Zapisuje aktualnie wybrane produkty oraz ich gramatury do pliku JSON."""
    saved_data = {
        "selected_products": st.session_state.get("selected_products", []),
        "amounts": {
            food: st.session_state.get(f"input_{food}", 0)
            for food in st.session_state.get("selected_products", [])
        }
    }
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(saved_data, f, ensure_ascii=False, indent=2)

# Inicjalizacja session_state na podstawie pliku z pamięcią
if "initialized" not in st.session_state:
    saved_data = load_saved_state()
    st.session_state.selected_products = saved_data.get("selected_products", [])
    
    # Przywrócenie zapisanych gramatur dla produktów
    for food, grams in saved_data.get("amounts", {}).items():
        st.session_state[f"input_{food}"] = grams
        
    st.session_state.initialized = True

# ---------------------------------------------------------
# BAZA DANYCH I KONFIGURACJA
# ---------------------------------------------------------
FOODS = {
    # Bogate w jednonienasycone kwasy tłuszczowe, potas (approx. 485mg/100g), witaminę E, K, B6 oraz foliany.
    "Awokado": {"kcal": 1.60, "protein": 0.020, "fat": 0.150, "carbs": 0.090},

    # Cały kompleks B (zwłaszcza B12 i B2), znaczne ilości wapnia (approx. 80mg/100g), fosforu i selenu.
    "Biały ser tłusty": {"kcal": 1.75, "protein": 0.170, "fat": 0.120, "carbs": 0.030},

    # Obfite źródło folianów (B9 - approx. 420mcg/100g), potasu, magnezu, żelaza i miedzi.
    "Bób": {"kcal": 0.88, "protein": 0.071, "fat": 0.004, "carbs": 0.176},

    # Wybitne źródło antocyjanów, witaminy C, witaminy K (approx. 19mcg/100g) oraz manganu.
    "Borówka leśna": {"kcal": 0.57, "protein": 0.007, "fat": 0.003, "carbs": 0.145},

    # Potężny aktywator sulforafanu; bogaty w witaminę C (approx. 89mg/100g), K1, kwas foliowy i potas.
    "Brokuł": {"kcal": 0.35, "protein": 0.028, "fat": 0.004, "carbs": 0.070},

    # Źródło kwercetyny, witaminy C, B6, potasu oraz siarki organicznej wspierającej syntezę glutationu.
    "Cebula": {"kcal": 0.40, "protein": 0.011, "fat": 0.001, "carbs": 0.093},

    # Błonnik, witaminy z grupy B (B1, B3, B6), magnez, żelazo, cynk oraz mangan.
    "Chleb żytni": {"kcal": 2.30, "protein": 0.070, "fat": 0.015, "carbs": 0.460},

    # Wysoka zawartość potasu (approx. 260mg/100g), witaminy C, B6 oraz luteiny.
    "Cukinia": {"kcal": 0.17, "protein": 0.012, "fat": 0.003, "carbs": 0.031},

    # Związki siarkowe (alicyna), witamina C, B6, mangan, selen (approx. 14mcg/100g) i wapń.
    "Czosnek": {"kcal": 1.49, "protein": 0.064, "fat": 0.005, "carbs": 0.330},

    # Chude źródło białka, potasu, selenu (approx. 33mcg/100g), fosforu oraz witaminy B12 i choliny.
    "Dorsz": {"kcal": 0.82, "protein": 0.180, "fat": 0.007, "carbs": 0.000},

    # Wysoka ilość witaminy B3 (niacyny - approx. 8mg/100g), B6, B12, fosforu, selenu i cynku.
    "Filet z indyka": {"kcal": 1.14, "protein": 0.230, "fat": 0.0125, "carbs": 0.000},

    # Niewielkie ilości witaminy C, potasu i kwercetyny; wysoki udział pektyn (błonnik rozpuszczalny).
    "Jabłko Ligol": {"kcal": 0.52, "protein": 0.003, "fat": 0.002, "carbs": 0.138},

    # Doskonały profil choliny (approx. 250mg/100g), luteiny, witamin A, D, E, B12, selenu i żelaza.
    "Jajko całe": {"kcal": 1.43, "protein": 0.126, "fat": 0.095, "carbs": 0.011},

    # Bioaktywny superfood; bardzo bogaty w witaminę K1 (approx. 700mcg/100g), witaminę C, A, luteinę i potas.
    "Jarmuż": {"kcal": 0.49, "protein": 0.043, "fat": 0.009, "carbs": 0.088},

    # Skondensowane źródło sodu, witamin z grupy B (B1, B3, B6, B12) oraz cynku, selenu i tłuszczów nasyconych.
    "Kabanos": {"kcal": 3.27, "protein": 0.240, "fat": 0.260, "carbs": 0.010},

    # Bardzo bogate źródło biodostępnego żelaza hemowego (approx. 6-12mg/100g), cynku, miedzi, B12 oraz potasu.
    "Kaszanka": {"kcal": 2.35, "protein": 0.095, "fat": 0.120, "carbs": 0.125},

    # Znakomite źródło rutyny i antyoksydantów (mniej uszkodzone termicznie niż w palonej), magnez (approx. 220mg/100g), potas, cynk, miedź i witaminy B1, B2, B3, B6.
    "Kasza gryczana niepalona": {"kcal": 3.40, "protein": 0.126, "fat": 0.031, "carbs": 0.693},

    # Witaminy z grupy B (B1, B2, B3, B6), magnez (approx. 230mg/100g), cynk, miedź, mangan i żelazo.
    "Kasza gryczana sucha": {"kcal": 3.43, "protein": 0.130, "fat": 0.034, "carbs": 0.710},

    # Lekkostrawna, zasadotwórcza; bogate źródło krzemionki (krzem na włosy/skórę/stawy), miedzi, mosiądzu, magnezu, żelaza oraz witamin B1, B2, B6 i kwasu foliowego.
    "Kasza jaglana": {"kcal": 3.78, "protein": 0.110, "fat": 0.042, "carbs": 0.729},

    # Bardzo wysoki udział frakcji błonnika beta-glukanu (regulacja mikrobiomu/lipidów), bogata w witaminę B1, B3, B6, magnez, fosfor, potas, cynk i miedź.
    "Kasza jęczmienna pęczak": {"kcal": 3.52, "protein": 0.098, "fat": 0.021, "carbs": 0.735},

    # Probiotyki, wapń (approx. 120mg/100g), fosfor, witamina B12, B2 (ryboflawina) oraz witamina K2 (MK-7).
    "Kefir naturalny": {"kcal": 0.51, "protein": 0.034, "fat": 0.020, "carbs": 0.049},

    # Wysokie stężenie kwasów Omega-3 (EPA/DHA), witaminy D3 (approx. 500 IU/100g), B12, selenu i potasu.
    "Łosoś": {"kcal": 2.08, "protein": 0.200, "fat": 0.130, "carbs": 0.000},

    # Wysoce biodostępne kwasy tłuszczowe Omega-3 (EPA/DHA), łatwo przyswajalne białko, witamina D3, B12, B6, selen i potas.
    "Łosoś pieczony": {"kcal": 2.21, "protein": 0.220, "fat": 0.145, "carbs": 0.000},

    # Omega-3, witamina D3, B12, B6, sod, selen oraz fosfor.
    "Łosoś wędzony": {"kcal": 1.17, "protein": 0.183, "fat": 0.043, "carbs": 0.000},

    # Witaminy z grupy B (B1, B2, B3), cynk, magnez, żelazo, mangan i miedź.
    "Makaron żytni suchy": {"kcal": 3.40, "protein": 0.120, "fat": 0.020, "carbs": 0.680},

    # Bogata w witaminę B12, B3, D, selen (approx. 36mcg/100g), fosfor oraz potas.
    "Makrela wędzona": {"kcal": 3.05, "protein": 0.180, "fat": 0.250, "carbs": 0.000},

    # Bogata w elagotaniny, witaminę C (approx. 26mg/100g), witaminę K, mangan, magnez i miedź.
    "Malina": {"kcal": 0.52, "protein": 0.012, "fat": 0.0065, "carbs": 0.119},

    # Czyste tłuszcze; zawiera śladowe ilości rozpuszczalnych w tłuszczach witamin A, E, D, K oraz kwas maślan (butyrate).
    "Masło klarowane": {"kcal": 8.84, "protein": 0.000, "fat": 1.000, "carbs": 0.000},

    # Kwas mlekowy, bakterie probiotyczne, wapń, potas, witamina B2 i B12.
    "Maślanka naturalna": {"kcal": 0.37, "protein": 0.030, "fat": 0.010, "carbs": 0.040},

    # Najbogatsze roślinne źródło witaminy E (approx. 26mg/100g), magnezu, ryboflawiny (B2), miedzi i wapnia.
    "Migdały": {"kcal": 5.79, "protein": 0.210, "fat": 0.500, "carbs": 0.220},

    # Dobrze przyswajalne żelazo hemowe, cynk, selen, potas oraz kompleks witamin B (B1, B3, B6, B12).
    "Mięso mielone wieprzowe": {"kcal": 2.63, "protein": 0.169, "fat": 0.211, "carbs": 0.000},

    # Obfite źródło biowydajnego cynku (approx. 4.5-5.5mg/100g), żelaza hemowego, selenu, B12, B3 (niacyny) i kreatyny.
    "Mięso mielone wołowe": {"kcal": 2.15, "protein": 0.186, "fat": 0.150, "carbs": 0.000},

    # Wapń (approx. 505mg/100g), fosfor, cynk, witamina B12, A oraz sod.
    "Mozzarella": {"kcal": 2.54, "protein": 0.180, "fat": 0.190, "carbs": 0.020},

    # Koncentracja białka; wapń, fosfor, B12, selen i cynk przy obniżonej zawartości tłuszczu.
    "Mozzarella light": {"kcal": 1.80, "protein": 0.240, "fat": 0.100, "carbs": 0.030},

    # Baza flawonoli i teobrominy; potężna dawka magnezu (approx. 500mg/100g), żelaza, miedzi i cynku.
    "Mączka z surowego kakao": {"kcal": 2.28, "protein": 0.200, "fat": 0.110, "carbs": 0.580},

    # Kwasy ALA Omega-3, magnez, wapń (approx. 630mg/100g), fosfor, mangan i rozpuszczalny błonnik.
    "Nasiona Chia": {"kcal": 4.86, "protein": 0.165, "fat": 0.307, "carbs": 0.421},

    # Śladowe ilości witamin C i K, potas; głównie woda strukturyzowana i krzem.
    "Ogórek": {"kcal": 0.15, "protein": 0.007, "fat": 0.001, "carbs": 0.036},

    # Kwas mlekowy, bakterie probiotyczne, sod, potas, niewielka ilość witaminy C i witamin z grupy B.
    "Ogórek kiszony": {"kcal": 0.11, "protein": 0.005, "fat": 0.001, "carbs": 0.023},

    # Czyste średniołańcuchowe kwasy tłuszczowe (C8/C10); brak mikroskładników mineralnych i witamin.
    "Olej MCT": {"kcal": 8.30, "protein": 0.000, "fat": 0.920, "carbs": 0.000},

    # Witamina E (approx. 14mg/100g), witamina K oraz polifenole (oleokantal, hydroksytyrozol).
    "Oliwa z oliwek": {"kcal": 8.84, "protein": 0.000, "fat": 1.000, "carbs": 0.000},

    # Witamina E, żelazo, miedź, wapń, sod oraz silne antyoksydanty (oleuropeina).
    "Oliwki": {"kcal": 1.15, "protein": 0.008, "fat": 0.110, "carbs": 0.060},

    # Najwyższe znane naturalne źródło selenu (approx. 1917mcg/100g), magnez, miedź, cynk i fosfor.
    "Orzechy brazylijskie": {"kcal": 6.59, "protein": 0.143, "fat": 0.671, "carbs": 0.123},

    # Magnez, cynk (approx. 5.8mg/100g), miedź, żelazo, fosfor, mangan oraz witamina K.
    "Orzechy nerkowca": {"kcal": 5.53, "protein": 0.182, "fat": 0.438, "carbs": 0.302},

    # Kwasy ALA Omega-3, witamina E, B6, kwas foliowy, magnez, miedź, mangan i cynk.
    "Orzechy włoskie": {"kcal": 6.54, "protein": 0.150, "fat": 0.650, "carbs": 0.140},

    # Sylimaryna (flawonolignany), witamina E, cynk, miedź i błonnik wspierający wątrobę.
    "Ostropest mielony": {"kcal": 4.02, "protein": 0.200, "fat": 0.340, "carbs": 0.150},

    # Rekordowe źródło witaminy C (approx. 128mg/100g), witamina A (beta-karoten), B6, K1, potas i kwas foliowy.
    "Papryka czerwona": {"kcal": 0.31, "protein": 0.010, "fat": 0.003, "carbs": 0.060},

    # Koncentrat wapnia (approx. 1180mg/100g), fosforu, cynku, witaminy B12, B2 oraz sodu.
    "Parmezan": {"kcal": 4.31, "protein": 0.380, "fat": 0.290, "carbs": 0.040},

    # Wysoka zawartość wapnia, fosforu, witaminy B12, B2, cynku i bioaktywnych peptydów.
    "Pecorino": {"kcal": 3.87, "protein": 0.280, "fat": 0.310, "carbs": 0.030},

    # Wybitne źródło cynku (approx. 7.8mg/100g), magnezu (approx. 535mg/100g), fosforu, miedzi i żelaza.
    "Pestki dyni lekko prażone": {"kcal": 5.59, "protein": 0.302, "fat": 0.490, "carbs": 0.107},

    # Niskokaloryczne źródło miedzi, selenu, ergotioneiny (silny antyoksydant), riboflawiny (B2), niacyny (B3) i potasu.
    "Pieczarki": {"kcal": 0.22, "protein": 0.031, "fat": 0.003, "carbs": 0.033},

    # Uśredniona pierś / filet: chude białko, bogate w witaminy B3 (approx. 12mg/100g), B6, B12, fosfor, selen i potas.
    "Pierś / Filet z kurczaka": {"kcal": 1.20, "protein": 0.230, "fat": 0.023, "carbs": 0.000},

    # Beta-glukany (błonnik), witamina B1 (tiamina), magnez, żelazo, mangan, cynk, miedź.
    "Płatki owsiane": {"kcal": 3.79, "protein": 0.130, "fat": 0.069, "carbs": 0.670},

    # Potężne źródło likopenu, potas (approx. 237mg/100g), witamina C, K, kwas foliowy.
    "Pomidory": {"kcal": 0.18, "protein": 0.009, "fat": 0.002, "carbs": 0.039},

    # Niewielkie ilości witamin z grupy B, cynku, miedzi, magnezu i manganu.
    "Ryż basmati biały": {"kcal": 3.50, "protein": 0.074, "fat": 0.006, "carbs": 0.780},

    # Niewielkie ilości witamin z grupy B (B1, B3, B6), fosforu, magnezu, manganu.
    "Ryż jaśminowy suchy": {"kcal": 3.56, "protein": 0.070, "fat": 0.006, "carbs": 0.790},

    # Bardzo chude białko, bogate w witaminę B12, B3, B6, fosfor, selen i potas.
    "Sandacz surowy filet": {"kcal": 0.93, "protein": 0.190, "fat": 0.020, "carbs": 0.000},

    # Niezwykle gęste źródło wapnia z kości (approx. 380mg/100g), Omega-3, D3, B12, selenu i cynku.
    "Sardynki w puszce (z ośćmi)": {"kcal": 2.08, "protein": 0.250, "fat": 0.115, "carbs": 0.000},

    # Wapń (approx. 490mg/100g), fosfor, sod, witamina B12, B2, A oraz cynk.
    "Ser feta": {"kcal": 2.65, "protein": 0.140, "fat": 0.210, "carbs": 0.040},

    # Wysoka biodostępność wapnia, fosforu, witaminy A, B12, B2 (ryboflawiny) oraz cynku.
    "Ser kozi twardy": {"kcal": 3.64, "protein": 0.220, "fat": 0.300, "carbs": 0.020},

    # Znakomite źródło kwasów ALA Omega-3, lignanów, magnezu, manganu, miedzi, fosforu i cynku.
    "Siemię lniane": {"kcal": 5.34, "protein": 0.180, "fat": 0.420, "carbs": 0.290},

    # Wysoko skoncentrowane białko, wapń, fosfor, potas, witamina B12 i B2.
    "Skyr naturalny": {"kcal": 0.63, "protein": 0.110, "fat": 0.002, "carbs": 0.040},

    # Najbardziej odżywcza alga; źródło witamin B1, B2, B3, żelaza, miedzi i fikocyjaniny.
    "Spirulina (proszek)": {"kcal": 2.90, "protein": 0.570, "fat": 0.080, "carbs": 0.240},

    # Bogaty w luteinę, zeaksantynę, witaminę K1 (approx. 480mcg/100g), A, C, kwas foliowy, żelazo i magnez.
    "Szpinak": {"kcal": 0.23, "protein": 0.029, "fat": 0.004, "carbs": 0.036},

    # Witaminy z grupy B (szczególnie B1/tiamina, B3, B6, B12), cynk, żelazo, sod i selen.
    "Szynka": {"kcal": 1.18, "protein": 0.215, "fat": 0.035, "carbs": 0.005},

    # Białko, witaminy B1, B3, B6, B12, fosfor, żelazo, cynk oraz sod.
    "Szynka tradycyjna": {"kcal": 1.31, "protein": 0.180, "fat": 0.062, "carbs": 0.011},

    # Wapń, fosfor, selen, witamina B12, B2 oraz potas przy umiarkowanym poziomie tłuszczu.
    "Twaróg półtłusty": {"kcal": 1.33, "protein": 0.190, "fat": 0.050, "carbs": 0.035},

    # Absolutne "królestwo" mikroelementów: ogrom witaminy A (retinol - approx. 5000mcg/100g), B12 (approx. 60mcg/100g), miedzi, żelaza hemowego, folianów i choliny.
    "Wątróbka wołowa": {"kcal": 1.35, "protein": 0.204, "fat": 0.036, "carbs": 0.038},

    # Najlepsze źródło biodostępnego żelaza hemowego, cynku (approx. 6mg/100g), witaminy B12, B3, B6 i selenu.
    "Wołowina chuda": {"kcal": 1.55, "protein": 0.210, "fat": 0.075, "carbs": 0.000},

    # Kwas mlekowy, azotan NO3-, betalainy, bogate źródło potasu, sodu i magnezu.
    "Zakwas z buraków": {"kcal": 0.12, "protein": 0.005, "fat": 0.001, "carbs": 0.023},

    # Węglowodany złożone, bogate źródło potasu (approx. 400-500mg/100g po upieczeniu), witaminy B6, C, miedzi i manganu.
    "Ziemniaki pieczone": {"kcal": 0.93, "protein": 0.025, "fat": 0.001, "carbs": 0.212}
}

DAY_MODES = {
    "Dzień nietreningowy": {"kcal": 2000, "protein": 140, "fat": 105, "carbs": 120},
    "Dzień treningowy": {"kcal": 2400, "protein": 150, "fat": 115, "carbs": 130},
}

st.title("Low-carb / IF Macro Tracker")
st.caption("Licznik makroskładników z możliwością wpisania gramatury z palca oraz przyciskami +/- 10 g.")

mode = st.radio("Tryb dnia", list(DAY_MODES.keys()), horizontal=True)
target = DAY_MODES[mode]

with st.sidebar:
    st.header("Kalibracja celu")
    current_carbs = st.slider("Obecne spożycie węgli [g/dzień]", min_value=120, max_value=300, value=250, step=10)
    target_carbs = st.slider("Docelowe węglowodany [g/dzień]", min_value=100, max_value=180, value=target["carbs"], step=5)
    carb_drop = max(0, current_carbs - target_carbs)
    kcal_to_replace = carb_drop * 4
    st.metric("Redukcja węgli", f"{carb_drop} g")
    st.metric("Kalorie do rekompozycji", f"{kcal_to_replace} kcal")
    st.markdown("**Sugestia rekompozycji energii**")
    st.write(f"• +{round(kcal_to_replace * 0.45 / 4)} g białka")
    st.write(f"• +{round(kcal_to_replace * 0.55 / 9)} g tłuszczu")

st.subheader("Dzienne cele")
cols = st.columns(4)
cols[0].metric("Kcal", target["kcal"])
cols[1].metric("Białko", f"{target['protein']} g")
cols[2].metric("Tłuszcz", f"{target['fat']} g")
cols[3].metric("Węglowodany", f"{target_carbs} g")

st.subheader("Produkty w ciągu dnia")

# Wybór produktów z automatycznym zapisem stanu
selected = st.multiselect(
    "Wybierz produkty",
    options=list(FOODS.keys()),
    key="selected_products",
    on_change=save_current_state
)

# Callback bezpośrednio aktualizujący wartość w session_state oraz zapisujący plik
def adjust_grams(key, delta):
    current = st.session_state.get(key, 0)
    st.session_state[key] = max(0, min(1000, current + delta))
    save_current_state()

amounts = {}
for food in selected:
    input_key = f"input_{food}"
    
    if input_key not in st.session_state:
        st.session_state[input_key] = 0

    c1, c2, c3 = st.columns([6, 2, 2])
    
    # Pole numeryczne — zmiana wartości automatycznie odpala zapis do pliku
    c1.number_input(
        f"{food} [g]", 
        min_value=0, 
        max_value=1000, 
        step=1,
        key=input_key,
        on_change=save_current_state
    )
    
    # Przyciski skokowe
    c2.button("-10 g", key=f"minus_{food}", on_click=adjust_grams, args=(input_key, -10))
    c3.button("+10 g", key=f"plus_{food}", on_click=adjust_grams, args=(input_key, 10))
    
    amounts[food] = st.session_state[input_key]

# ---------------------------------------------------------
# OBLICZENIA I TABELA
# ---------------------------------------------------------
rows = []
totals = {"kcal": 0.0, "protein": 0.0, "fat": 0.0, "carbs": 0.0}
for food, grams in amounts.items():
    if grams > 0:
        vals = FOODS[food]
        row = {
            "Produkt": food,
            "g": grams,
            "kcal": round(vals["kcal"] * grams, 1),
            "Białko [g]": round(vals["protein"] * grams, 1),
            "Tłuszcz [g]": round(vals["fat"] * grams, 1),
            "Węglowodany [g]": round(vals["carbs"] * grams, 1),
        }
        rows.append(row)
        totals["kcal"] += row["kcal"]
        totals["protein"] += row["Białko [g]"]
        totals["fat"] += row["Tłuszcz [g]"]
        totals["carbs"] += row["Węglowodany [g]"]

if rows:
    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True)

st.subheader("Podsumowanie dnia")
summary_cols = st.columns(4)
summary_cols[0].metric("Zjedzone kcal", f"{totals['kcal']:.0f}", f"{totals['kcal'] - target['kcal']:.0f}")
summary_cols[1].metric("Białko", f"{totals['protein']:.1f} g", f"{totals['protein'] - target['protein']:.1f} g")
summary_cols[2].metric("Tłuszcz", f"{totals['fat']:.1f} g", f"{totals['fat'] - target['fat']:.1f} g")
summary_cols[3].metric("Węglowodany", f"{totals['carbs']:.1f} g", f"{totals['carbs'] - target_carbs:.1f} g")

st.progress(min(totals['protein'] / max(target['protein'], 1), 1.0), text=f"Białko: {totals['protein']:.1f} / {target['protein']} g")
st.progress(min(totals['fat'] / max(target['fat'], 1), 1.0), text=f"Tłuszcz: {totals['fat']:.1f} / {target['fat']} g")
st.progress(min(totals['carbs'] / max(target_carbs, 1), 1.0), text=f"Węglowodany: {totals['carbs']:.1f} / {target_carbs} g")

remaining = {
    "Kcal do celu": round(target['kcal'] - totals['kcal'], 1),
    "Białko do celu [g]": round(target['protein'] - totals['protein'], 1),
    "Tłuszcz do celu [g]": round(target['fat'] - totals['fat'], 1),
    "Węglowodany do celu [g]": round(target_carbs - totals['carbs'], 1),
}
st.subheader("Ile jeszcze brakuje / nadwyżka")
st.table(pd.DataFrame([remaining]))

st.subheader("Sugestie podziału dnia")
st.markdown("""
- **08:30** – kawa kuloodporna: 10 g masła klarowanego + 10 g MCT.
- **12:00** – posiłek wysokobiałkowy z jajkami.
- **14:00–16:30** – obiad lub dwa mniejsze posiłki; większość węgli wokół aktywności.
- **21:00** – kolacja / posiłek potreningowy, bogatszy w dni treningowe.
""")

st.subheader("Plan żywieniowy – skrót kliniczny")
st.markdown("""
### 1. Bilans i makro
- **Dzień nietreningowy:** około 2000 kcal, ~140 g białka, ~105 g tłuszczu, ~120 g węgli.
- **Dzień treningowy:** około 2400 kcal, ~150 g białka, ~115 g tłuszczu, ~130 g węgli.
- Białko rozdziel na 3–4 ekspozycje po około 25–40 g pełnowartościowego białka.

### 2. Tapering węglowodanów
- Tydzień 1: bieżący poziom minus 10 g/dzień.
- Kolejne tygodnie: obniżaj o 10 g/dzień tygodniowo aż do ~120 g w dni nietreningowe i ~130 g w treningowe.
- Energię uzupełniaj głównie białkiem i tłuszczem, nie samym tłuszczem.

### 3. Uwagi kliniczne
- Przy IF + treningu oporowym priorytetem jest podaż białka i całkowitej energii.
- Przy redukcji węgli pilnuj sodu, potasu i magnezu oraz odpowiedniego nawodnienia.
- Węgle skupiaj głównie wokół obiadu i posiłku potreningowego.

### 4. Suplementacja wspierająca
- Kreatyna monohydrat: 3–5 g/dzień.
- Magnez: zwykle 200–400 mg elementarnego/dzień, zależnie od tolerancji i podaży z diety.
- Omega-3: jeśli mało tłustych ryb.
- Elektrolity: szczególnie na początku zejścia z węgli.
""")

st.subheader("Lista zakupów – baza")
st.markdown("""
- **Białko:** jaja, kurczak, indyk, chuda wołowina, łosoś, dorsz, twaróg, skyr.
- **Tłuszcze:** oliwa, MCT, masło klarowane, awokado, orzechy, oliwki.
- **Węglowodany kontrolowane:** ryż jaśminowy, kasza gryczana, makaron żytni, płatki owsiane, chleb żytni.
- **Warzywa i mikroelementy:** szpinak, brokuł, papryka, cukinia, ogórek.
""")