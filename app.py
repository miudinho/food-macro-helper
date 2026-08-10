import json
import os
import tempfile
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Macro Day Tracker", layout="wide")

# ---------------------------------------------------------
# PERSISTENCE (ZAPIS POZA KATALOGIEM RENDEROWANIA APLIKACJI)
# Zapis w tempdir chroni przed pętlą Streamlit File Watchera
# ---------------------------------------------------------
CACHE_FILE = os.path.join(tempfile.gettempdir(), "macro_user_selection.json")


def load_saved_state():
    """Wczytuje stan z pliku tymczasowego JSON."""
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_current_state():
    """Zapisuje aktualny stan bez powodowania pętli re-runu serwera."""
    saved_data = {
        "selected_products": st.session_state.get("selected_products", []),
        "amounts": {
            food: st.session_state.get(f"input_{food}", 0)
            for food in st.session_state.get("selected_products", [])
        },
    }
    try:
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(saved_data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        st.error(f"Błąd zapisu pliku stanu: {e}")


# Inicjalizacja session_state
if "initialized" not in st.session_state:
    saved_data = load_saved_state()
    st.session_state.selected_products = saved_data.get(
        "selected_products", []
    )

    for food, grams in saved_data.get("amounts", {}).items():
        st.session_state[f"input_{food}"] = grams

    st.session_state.initialized = True

# ---------------------------------------------------------
# BAZA DANYCH (FOODS.JSON)
# ---------------------------------------------------------
FOODS_FILE = "foods.json"


@st.cache_data
def load_foods():
    """Wczytuje bazę produktów z pliku JSON."""
    if os.path.exists(FOODS_FILE):
        try:
            with open(FOODS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            st.error(f"Błąd podczas odczytu {FOODS_FILE}: {e}")
            return {}
    else:
        st.error(f"Nie znaleziono pliku {FOODS_FILE}!")
        return {}


FOODS = load_foods()


def get_fat_breakdown(food_name, total_fat_g, vals, grams):
    if "sat_fat" in vals and "unsat_fat" in vals:
        return vals["sat_fat"] * grams, vals["unsat_fat"] * grams

    name = food_name.lower()
    if any(
        x in name
        for x in [
            "mct",
            "masło",
            "boczek",
            "parmezan",
            "pecorino",
            "ser",
            "mozzarella",
            "twaróg",
            "szynka",
            "kefir",
        ]
    ):
        sat_ratio = 0.65
    elif any(
        x in name
        for x in [
            "oliwa",
            "olej",
            "orzech",
            "migdał",
            "awokado",
            "oliwki",
            "łosoś",
            "dorsz",
            "sandacz",
            "siemię",
        ]
    ):
        sat_ratio = 0.15
    elif any(x in name for x in ["jajko", "wołowina", "kurczak", "indyk"]):
        sat_ratio = 0.35
    else:
        sat_ratio = 0.30

    sat_g = total_fat_g * sat_ratio
    unsat_g = total_fat_g * (1 - sat_ratio)
    return sat_g, unsat_g


DAY_MODES = {
    "Dzień nietreningowy": {
        "kcal": 2000,
        "protein": 140,
        "fat": 105,
        "carbs": 120,
    },
    "Dzień treningowy": {
        "kcal": 2400,
        "protein": 150,
        "fat": 115,
        "carbs": 130,
    },
}

st.title("Low-carb / IF Macro Tracker")
st.caption(
    "Licznik makroskładników z rozbiciem profilu tłuszczowego (SFA / UFA)."
)

mode = st.radio("Tryb dnia", list(DAY_MODES.keys()), horizontal=True)
target = DAY_MODES[mode]

with st.sidebar:
    st.header("Kalibracja celu")
    current_carbs = st.slider(
        "Obecne spożycie węgli [g/dzień]", 120, 300, 250, 10
    )
    target_carbs = st.slider(
        "Docelowe węglowodany [g/dzień]", 100, 180, target["carbs"], 5
    )
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
    options=list(FOODS.keys()),
    key="selected_products",
    on_change=save_current_state,
)


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

    c1.number_input(
        f"{food} [g]",
        min_value=0,
        max_value=1000,
        step=1,
        key=input_key,
        on_change=save_current_state,
    )

    c2.button(
        "-10 g", key=f"minus_{food}", on_click=adjust_grams, args=(input_key, -10)
    )
    c3.button(
        "+10 g", key=f"plus_{food}", on_click=adjust_grams, args=(input_key, 10)
    )

    amounts[food] = st.session_state[input_key]

# ---------------------------------------------------------
# OBLICZENIA I TABELA
# ---------------------------------------------------------
rows = []
totals = {
    "kcal": 0.0,
    "protein": 0.0,
    "fat": 0.0,
    "sat_fat": 0.0,
    "unsat_fat": 0.0,
    "carbs": 0.0,
}

for food, grams in amounts.items():
    if grams > 0:
        vals = FOODS.get(food, {})
        total_fat_g = round(vals.get("fat", 0.0) * grams, 1)

        sat_fat_g, unsat_fat_g = get_fat_breakdown(
            food, total_fat_g, vals, grams
        )
        sat_fat_g = round(sat_fat_g, 1)
        unsat_fat_g = round(unsat_fat_g, 1)

        row = {
            "Produkt": food,
            "g": grams,
            "kcal": round(vals.get("kcal", 0.0) * grams, 1),
            "Białko [g]": round(vals.get("protein", 0.0) * grams, 1),
            "Tłuszcz łącznie [g]": total_fat_g,
            "Nasycone (SFA) [g]": sat_fat_g,
            "Nienasycone (UFA) [g]": unsat_fat_g,
            "Węglowodany [g]": round(vals.get("carbs", 0.0) * grams, 1),
        }
        rows.append(row)
        totals["kcal"] += row["kcal"]
        totals["protein"] += row["Białko [g]"]
        totals["fat"] += total_fat_g
        totals["sat_fat"] += sat_fat_g
        totals["unsat_fat"] += unsat_fat_g
        totals["carbs"] += row["Węglowodany [g]"]

if rows:
    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True)

st.subheader("Podsumowanie dnia")

total_fat = totals["fat"]
if total_fat > 0:
    sat_pct = round((totals["sat_fat"] / total_fat) * 100)
    unsat_pct = round((totals["unsat_fat"] / total_fat) * 100)
    fat_subtitle = f"SFA: {sat_pct}% | UFA: {unsat_pct}%"
else:
    sat_pct = 0
    unsat_pct = 0
    fat_subtitle = "SFA: 0% | UFA: 0%"

summary_cols = st.columns(4)
summary_cols[0].metric(
    "Zjedzone kcal",
    f"{totals['kcal']:.0f}",
    f"{totals['kcal'] - target['kcal']:.0f}",
)
summary_cols[1].metric(
    "Białko",
    f"{totals['protein']:.1f} g",
    f"{totals['protein'] - target['protein']:.1f} g",
)
summary_cols[2].metric(
    "Tłuszcz łącznie",
    f"{totals['fat']:.1f} g",
    f"{totals['fat'] - target['fat']:.1f} g",
    help=f"Podział: {totals['sat_fat']:.1f}g nasyconych / {totals['unsat_fat']:.1f}g nienasyconych",
)
summary_cols[3].metric(
    "Węglowodany",
    f"{totals['carbs']:.1f} g",
    f"{totals['carbs'] - target_carbs:.1f} g",
)

st.markdown(
    f"**Stosunek tłuszczów w diecie:** Nasycone (SFA): **{totals['sat_fat']:.1f} g ({sat_pct}%)** | "
    f"Nienasycone (UFA): **{totals['unsat_fat']:.1f} g ({unsat_pct}%)**"
)

st.progress(
    min(totals["protein"] / max(target["protein"], 1), 1.0),
    text=f"Białko: {totals['protein']:.1f} / {target['protein']} g",
)
st.progress(
    min(totals["fat"] / max(target["fat"], 1), 1.0),
    text=f"Tłuszcz: {totals['fat']:.1f} / {target['fat']} g ({fat_subtitle})",
)
st.progress(
    min(totals["carbs"] / max(target_carbs, 1), 1.0),
    text=f"Węglowodany: {totals['carbs']:.1f} / {target_carbs} g",
)

remaining = {
    "Kcal do celu": round(target["kcal"] - totals["kcal"], 1),
    "Białko do celu [g]": round(target["protein"] - totals["protein"], 1),
    "Tłuszcz do celu [g]": round(target["fat"] - totals["fat"], 1),
    "Węglowodany do celu [g]": round(target_carbs - totals["carbs"], 1),
}
st.subheader("Ile jeszcze brakuje / nadwyżka")
st.table(pd.DataFrame([remaining]))