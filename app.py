import streamlit as st
import pandas as pd

st.set_page_config(page_title="Macro Day Tracker", layout="wide")

FOODS = {
    "Awokado": {"kcal": 1.60, "protein": 0.020, "fat": 0.150, "carbs": 0.090},
    "Biały ser tłusty": {"kcal": 1.75, "protein": 0.170, "fat": 0.120, "carbs": 0.030},
    "Bób": {"kcal": 0.88, "protein": 0.071, "fat": 0.004, "carbs": 0.176},
    "Borówka leśna": {"kcal": 0.57, "protein": 0.007, "fat": 0.003, "carbs": 0.145},
    "Brokuł": {"kcal": 0.35, "protein": 0.028, "fat": 0.004, "carbs": 0.070},
    "Cebula": {"kcal": 0.40, "protein": 0.011, "fat": 0.001, "carbs": 0.093},
    "Chleb żytni": {"kcal": 2.30, "protein": 0.070, "fat": 0.015, "carbs": 0.460},
    "Cukinia": {"kcal": 0.17, "protein": 0.012, "fat": 0.003, "carbs": 0.031},
    "Czosnek": {"kcal": 1.49, "protein": 0.064, "fat": 0.005, "carbs": 0.330},
    "Dorsz": {"kcal": 0.82, "protein": 0.180, "fat": 0.007, "carbs": 0.000},
    "Indyk": {"kcal": 1.14, "protein": 0.240, "fat": 0.015, "carbs": 0.000},
    "Jabłko Ligol": {"kcal": 0.52, "protein": 0.003, "fat": 0.002, "carbs": 0.138},
    "Jajko całe": {"kcal": 1.43, "protein": 0.126, "fat": 0.095, "carbs": 0.011},
    "Kasza gryczana sucha": {"kcal": 3.43, "protein": 0.130, "fat": 0.034, "carbs": 0.710},
    "Kefir naturalny": {"kcal": 0.51, "protein": 0.034, "fat": 0.020, "carbs": 0.049},
    "Łosoś": {"kcal": 2.08, "protein": 0.200, "fat": 0.130, "carbs": 0.000},
    "Łosoś wędzony": {"kcal": 1.17, "protein": 0.183, "fat": 0.043, "carbs": 0.000},
    "Makaron żytni suchy": {"kcal": 3.40, "protein": 0.120, "fat": 0.020, "carbs": 0.680},
    "Maślanka naturalna": {"kcal": 0.37, "protein": 0.030, "fat": 0.010, "carbs": 0.040},
    "Malina": {"kcal": 0.52, "protein": 0.012, "fat": 0.0065, "carbs": 0.119},
    "Masło klarowane": {"kcal": 8.84, "protein": 0.000, "fat": 1.000, "carbs": 0.000},
    "Migdały": {"kcal": 5.79, "protein": 0.210, "fat": 0.500, "carbs": 0.220},
    "Mozzarella": {"kcal": 2.54, "protein": 0.180, "fat": 0.190, "carbs": 0.020},
    "Mozzarella light": {"kcal": 1.80, "protein": 0.240, "fat": 0.100, "carbs": 0.030},
    "Makrela wędzona": {"kcal": 3.05, "protein": 0.180, "fat": 0.250, "carbs": 0.000},
    "Ogórek": {"kcal": 0.15, "protein": 0.007, "fat": 0.001, "carbs": 0.036},
    "Ogórek kiszony": {"kcal": 0.11, "protein": 0.005, "fat": 0.001, "carbs": 0.023},
    "Olej MCT": {"kcal": 8.30, "protein": 0.000, "fat": 0.920, "carbs": 0.000},
    "Oliwa z oliwek": {"kcal": 8.84, "protein": 0.000, "fat": 1.000, "carbs": 0.000},
    "Oliwki": {"kcal": 1.15, "protein": 0.008, "fat": 0.110, "carbs": 0.060},
    "Ostropest mielony": {"kcal": 4.02, "protein": 0.200, "fat": 0.340, "carbs": 0.150},
    "Orzechy brazylijskie": {"kcal": 6.59, "protein": 0.143, "fat": 0.671, "carbs": 0.123},
    "Orzechy nerkowca": {"kcal": 5.53, "protein": 0.182, "fat": 0.438, "carbs": 0.302},
    "Orzechy włoskie": {"kcal": 6.54, "protein": 0.150, "fat": 0.650, "carbs": 0.140},
    "Papryka czerwona": {"kcal": 0.31, "protein": 0.010, "fat": 0.003, "carbs": 0.060},
    "Parmezan": {"kcal": 4.31, "protein": 0.380, "fat": 0.290, "carbs": 0.040},
    "Pestki dyni lekko prażone": {"kcal": 5.59, "protein": 0.302, "fat": 0.490, "carbs": 0.107},
    "Pomidory": {"kcal": 0.18, "protein": 0.009, "fat": 0.002, "carbs": 0.039},
    "Płatki owsiane": {"kcal": 3.79, "protein": 0.130, "fat": 0.069, "carbs": 0.670},
    "Pecorino": {"kcal": 3.87, "protein": 0.280, "fat": 0.310, "carbs": 0.030},
    "Pierś z kurczaka": {"kcal": 1.20, "protein": 0.230, "fat": 0.026, "carbs": 0.000},
    "Ryż basmati biały": {"kcal": 3.50, "protein": 0.074, "fat": 0.006, "carbs": 0.780},
    "Ryż jaśminowy suchy": {"kcal": 3.56, "protein": 0.070, "fat": 0.006, "carbs": 0.790},
    "Sandacz surowy filet": {"kcal": 0.93, "protein": 0.190, "fat": 0.020, "carbs": 0.000},
    "Ser feta": {"kcal": 2.65, "protein": 0.140, "fat": 0.210, "carbs": 0.040},
    "Ser kozi twardy": {"kcal": 3.64, "protein": 0.220, "fat": 0.300, "carbs": 0.020},
    "Siemię lniane": {"kcal": 5.34, "protein": 0.180, "fat": 0.420, "carbs": 0.290},
    "Skyr naturalny": {"kcal": 0.63, "protein": 0.110, "fat": 0.002, "carbs": 0.040},
    "Szpinak": {"kcal": 0.23, "protein": 0.029, "fat": 0.004, "carbs": 0.036},
    "Szynka": {"kcal": 1.18, "protein": 0.215, "fat": 0.035, "carbs": 0.005},
    "Szynka tradycyjna": {"kcal": 1.31, "protein": 0.180, "fat": 0.062, "carbs": 0.011},
    "Twaróg półtłusty": {"kcal": 1.33, "protein": 0.190, "fat": 0.050, "carbs": 0.035},
    "Wołowina chuda": {"kcal": 1.55, "protein": 0.210, "fat": 0.075, "carbs": 0.000},
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
selected = st.multiselect(
    "Wybierz produkty",
    list(FOODS.keys()),
    default=["Jajko całe", "Pierś z kurczaka", "Ryż jaśminowy suchy", "Awokado", "Oliwa z oliwek"]
)

# Callback bezpośrednio aktualizujący wartość w session_state przypisaną do widgetu
def adjust_grams(key, delta):
    current = st.session_state.get(key, 0)
    st.session_state[key] = max(0, min(1000, current + delta))

amounts = {}
for food in selected:
    input_key = f"input_{food}"
    
    if input_key not in st.session_state:
        st.session_state[input_key] = 0

    c1, c2, c3 = st.columns([6, 2, 2])
    
    # Pole numeryczne — pozwala wpisać z palca oraz ma fabryczne strzałki krokowe
    c1.number_input(
        f"{food} [g]", 
        min_value=0, 
        max_value=1000, 
        step=1,
        key=input_key
    )
    
    # Dedykowane przyciski skokowe +/- 10g
    c2.button("-10 g", key=f"minus_{food}", on_click=adjust_grams, args=(input_key, -10))
    c3.button("+10 g", key=f"plus_{food}", on_click=adjust_grams, args=(input_key, 10))
    
    amounts[food] = st.session_state[input_key]

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
