"""
Low-carb / IF Macro Tracker (Streamlit)

Persystencja:
- foods.json            -> baza produktów (format JSON jak dotychczas, wartości na 1 g)
- data/macro.db (SQLite) -> bieżący stan (autozapis) + historia zapisów (przycisk "Zapisz")
Katalog /app/data jest wolumenem Dockera, więc dane przeżywają zatrzymanie kontenera.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import tempfile

import pandas as pd
import streamlit as st

import db

st.set_page_config(page_title="Macro Day Tracker", layout="wide")

# ---------------------------------------------------------
# KONFIGURACJA
# ---------------------------------------------------------
APP_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = db.DATA_DIR
BUNDLED_FOODS = os.path.join(APP_DIR, "foods.json")          # z obrazu (seed)
FOODS_FILE = os.environ.get("MACRO_FOODS_FILE", os.path.join(DATA_DIR, "foods.json"))
LEGACY_STATE_FILES = [
    os.path.join(DATA_DIR, "user_selection.json"),
    os.path.join(tempfile.gettempdir(), "macro_user_selection.json"),
]

MAX_GRAMS = 1000
CURRENT_CARBS_RANGE = (120, 300)
TARGET_CARBS_RANGE = (100, 180)

DAY_MODES = {
    "Dzień nietreningowy": {"kcal": 2000, "protein": 140, "fat": 105, "carbs": 120},
    "Dzień treningowy": {"kcal": 2400, "protein": 150, "fat": 115, "carbs": 130},
}

# Rekomendacje zdrowotne (WHO 2023, AHA, EFSA)
SFA_WHO_MAX_E = 10.0   # % energii – WHO: maks. 10% energii z tłuszczów nasyconych
SFA_AHA_MAX_E = 6.0    # % energii – AHA: < 6% energii (profil sercowo-naczyniowy)
SFA_MAX_OF_FAT = 33.0  # % tłuszczu – ok. 1/3 (10% E SFA przy 30% E tłuszczu)
UFA_MIN_OF_FAT = 67.0  # % tłuszczu – co najmniej ok. 2/3 tłuszczu nienasyconego
FAT_E_RANGE = (20.0, 35.0)  # % energii – EFSA 20–35% (WHO: ≤ 30%)


# ---------------------------------------------------------
# BAZA PRODUKTÓW (foods.json)
# ---------------------------------------------------------
def ensure_foods_file() -> None:
    """Przy pierwszym starcie kopiuje foods.json z obrazu do wolumenu danych."""
    if os.path.abspath(FOODS_FILE) == os.path.abspath(BUNDLED_FOODS):
        return
    if not os.path.exists(FOODS_FILE) and os.path.exists(BUNDLED_FOODS):
        os.makedirs(os.path.dirname(FOODS_FILE), exist_ok=True)
        shutil.copyfile(BUNDLED_FOODS, FOODS_FILE)


@st.cache_data
def load_foods(_mtime: float) -> dict:
    """Wczytuje bazę produktów. _mtime unieważnia cache po zmianie pliku."""
    try:
        with open(FOODS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            raise ValueError("foods.json musi zawierać obiekt JSON {nazwa: {...}}")
        return dict(sorted(data.items(), key=lambda kv: kv[0].lower()))
    except FileNotFoundError:
        st.error(f"Nie znaleziono pliku {FOODS_FILE}!")
    except Exception as e:  # noqa: BLE001
        st.error(f"Błąd podczas odczytu {FOODS_FILE}: {e}")
    return {}


def foods_mtime() -> float:
    try:
        return os.path.getmtime(FOODS_FILE)
    except OSError:
        return 0.0


def write_foods_atomic(foods: dict) -> None:
    """Atomowy zapis JSON (tmp + os.replace) – brak uszkodzonego pliku przy awarii."""
    directory = os.path.dirname(os.path.abspath(FOODS_FILE))
    fd, tmp = tempfile.mkstemp(prefix=".foods.", suffix=".json", dir=directory)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(foods, f, ensure_ascii=False, indent=2)
            f.write("\n")
        os.replace(tmp, FOODS_FILE)
    except Exception:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


ensure_foods_file()
db.init_db()
FOODS = load_foods(foods_mtime())


# ---------------------------------------------------------
# STAN APLIKACJI (SQLite) – odtwarzany po restarcie kontenera
# ---------------------------------------------------------
def _clamp_int(value, lo: int, hi: int, default: int) -> int:
    try:
        return max(lo, min(hi, int(value)))
    except (TypeError, ValueError):
        return default


def collect_state() -> dict:
    selected = st.session_state.get("selected_products", [])
    return {
        "day_mode": st.session_state.get("day_mode"),
        "current_carbs": st.session_state.get("current_carbs"),
        "target_carbs": st.session_state.get("target_carbs"),
        "selected_products": selected,
        "amounts": {f: st.session_state.get(f"input_{f}", 0) for f in selected},
    }


def apply_state(state: dict) -> None:
    """Wpisuje stan do session_state z walidacją (tylko przed renderem widgetów)."""
    mode = state.get("day_mode")
    if mode not in DAY_MODES:
        mode = next(iter(DAY_MODES))
    st.session_state.day_mode = mode
    st.session_state.current_carbs = _clamp_int(
        state.get("current_carbs"), *CURRENT_CARBS_RANGE, default=250
    )
    st.session_state.target_carbs = _clamp_int(
        state.get("target_carbs"), *TARGET_CARBS_RANGE, default=DAY_MODES[mode]["carbs"]
    )
    # Tylko produkty istniejące w foods.json (inaczej multiselect rzuci wyjątek)
    selected = [p for p in state.get("selected_products", []) if p in FOODS]
    st.session_state.selected_products = selected
    amounts = state.get("amounts", {}) or {}
    for food in selected:
        st.session_state[f"input_{food}"] = _clamp_int(amounts.get(food), 0, MAX_GRAMS, 0)


def load_legacy_state() -> dict:
    """Jednorazowy import ze starego user_selection.json (jeśli istnieje)."""
    for path in LEGACY_STATE_FILES:
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:  # noqa: BLE001
                continue
    return {}


def persist_state() -> None:
    try:
        db.save_state(collect_state())
    except Exception as e:  # noqa: BLE001
        st.error(f"Błąd zapisu stanu do bazy SQL: {e}")


if "initialized" not in st.session_state:
    saved, updated_at = db.load_state()
    if not saved:
        saved = load_legacy_state()
        if saved:
            db.save_state(saved)
    apply_state(saved)
    st.session_state.restored_at = updated_at
    st.session_state.initialized = True


# ---------------------------------------------------------
# CALLBACKI
# ---------------------------------------------------------
def on_mode_change() -> None:
    st.session_state.target_carbs = DAY_MODES[st.session_state.day_mode]["carbs"]
    persist_state()


def adjust_grams(key: str, delta: int) -> None:
    current = st.session_state.get(key, 0)
    st.session_state[key] = max(0, min(MAX_GRAMS, current + delta))
    persist_state()


def restore_snapshot(snapshot_id: int) -> None:
    snap, items = db.get_snapshot(snapshot_id)
    if not snap:
        st.session_state.flash = ("error", f"Nie znaleziono zapisu #{snapshot_id}")
        return
    missing = [i["product"] for i in items if i["product"] not in FOODS]
    apply_state(
        {
            "day_mode": snap["day_mode"],
            "current_carbs": snap["current_carbs"],
            "target_carbs": snap["target_carbs"],
            "selected_products": [i["product"] for i in items],
            "amounts": {i["product"]: i["grams"] for i in items},
        }
    )
    persist_state()
    msg = f"Przywrócono zapis #{snapshot_id} z {snap['created_at']}"
    if missing:
        msg += f" (pominięto produkty spoza foods.json: {', '.join(missing)})"
    st.session_state.flash = ("success", msg)


def remove_snapshot(snapshot_id: int) -> None:
    db.delete_snapshot(snapshot_id)
    st.session_state.flash = ("success", f"Usunięto zapis #{snapshot_id}")


# ---------------------------------------------------------
# OBLICZENIA
# ---------------------------------------------------------
def get_fat_breakdown(food_name: str, total_fat_g: float, vals: dict, grams: float):
    """Zwraca (SFA, UFA); zawsze SFA + UFA == total_fat_g."""
    if "sat_fat" in vals:
        sat_g = min(vals["sat_fat"] * grams, total_fat_g)
        return sat_g, total_fat_g - sat_g

    name = food_name.lower()
    if any(x in name for x in ["mct", "masło", "boczek", "parmezan", "pecorino",
                               "ser", "mozzarella", "twaróg", "szynka", "kefir"]):
        sat_ratio = 0.65
    elif any(x in name for x in ["oliwa", "olej", "orzech", "migdał", "awokado",
                                 "oliwki", "łosoś", "dorsz", "sandacz", "siemię"]):
        sat_ratio = 0.15
    elif any(x in name for x in ["jajko", "wołowina", "kurczak", "indyk"]):
        sat_ratio = 0.35
    else:
        sat_ratio = 0.30

    sat_g = total_fat_g * sat_ratio
    return sat_g, total_fat_g - sat_g


def compute(amounts: dict) -> tuple[list[dict], dict]:
    items, totals = [], dict.fromkeys(
        ["kcal", "protein", "fat", "sat_fat", "unsat_fat", "carbs"], 0.0
    )
    for food, grams in amounts.items():
        if grams <= 0:
            continue
        vals = FOODS.get(food, {})
        fat_g = round(vals.get("fat", 0.0) * grams, 1)
        sat_g, _ = get_fat_breakdown(food, fat_g, vals, grams)
        sat_g = round(sat_g, 1)
        item = {
            "product": food,
            "grams": int(grams),
            "kcal": round(vals.get("kcal", 0.0) * grams, 1),
            "protein": round(vals.get("protein", 0.0) * grams, 1),
            "fat": fat_g,
            "sat_fat": sat_g,
            "unsat_fat": round(fat_g - sat_g, 1),
            "carbs": round(vals.get("carbs", 0.0) * grams, 1),
        }
        items.append(item)
        for k in totals:
            totals[k] += item[k]
    return items, {k: round(v, 1) for k, v in totals.items()}


def pct(part: float, whole: float) -> float:
    return (part / whole * 100.0) if whole > 0 else 0.0


# ---------------------------------------------------------
# UI – NAGŁÓWEK I USTAWIENIA
# ---------------------------------------------------------
st.title("Low-carb / IF Macro Tracker")
st.caption(
    "Licznik makroskładników z rozbiciem profilu tłuszczowego (SFA / UFA). "
    "Stan zapisywany w SQLite (wolumen /app/data) – przetrwa restart kontenera."
)

if st.session_state.get("restored_at"):
    st.info(f"Przywrócono ostatnie wpisy z bazy (ostatnia zmiana: {st.session_state.restored_at} UTC).")
    st.session_state.restored_at = None

if flash := st.session_state.pop("flash", None):
    getattr(st, flash[0])(flash[1])

mode = st.radio(
    "Tryb dnia", list(DAY_MODES.keys()), horizontal=True,
    key="day_mode", on_change=on_mode_change,
)
target = DAY_MODES[mode]

with st.sidebar:
    st.header("Kalibracja celu")
    current_carbs = st.slider(
        "Obecne spożycie węgli [g/dzień]", *CURRENT_CARBS_RANGE, step=10,
        key="current_carbs", on_change=persist_state,
    )
    target_carbs = st.slider(
        "Docelowe węglowodany [g/dzień]", *TARGET_CARBS_RANGE, step=5,
        key="target_carbs", on_change=persist_state,
    )
    carb_drop = max(0, current_carbs - target_carbs)
    kcal_to_replace = carb_drop * 4
    st.metric("Redukcja węgli", f"{carb_drop} g")
    st.metric("Kalorie do rekompozycji", f"{kcal_to_replace} kcal")
    st.markdown("Sugestia rekompozycji energii")
    st.write(f"• +{round(kcal_to_replace * 0.45 / 4)} g białka")
    st.write(f"• +{round(kcal_to_replace * 0.55 / 9)} g tłuszczu")

st.subheader("Dzienne cele")
cols = st.columns(4)
cols[0].metric("Kcal", target["kcal"])
cols[1].metric("Białko", f"{target['protein']} g")
cols[2].metric("Tłuszcz", f"{target['fat']} g")
cols[3].metric("Węglowodany", f"{target_carbs} g")

# ---------------------------------------------------------
# UI – PRODUKTY
# ---------------------------------------------------------
st.subheader("Produkty w ciągu dnia")
selected = st.multiselect(
    "Wybierz produkty", options=list(FOODS.keys()),
    key="selected_products", on_change=persist_state,
)

amounts: dict[str, int] = {}
for food in selected:
    input_key = f"input_{food}"
    if input_key not in st.session_state:
        st.session_state[input_key] = 0
    c1, c2, c3 = st.columns([6, 2, 2])
    c1.number_input(
        f"{food} [g]", min_value=0, max_value=MAX_GRAMS, step=1,
        key=input_key, on_change=persist_state,
    )
    c2.button("-10 g", key=f"minus_{food}", on_click=adjust_grams, args=(input_key, -10))
    c3.button("+10 g", key=f"plus_{food}", on_click=adjust_grams, args=(input_key, 10))
    amounts[food] = st.session_state[input_key]

items, totals = compute(amounts)

# ---------------------------------------------------------
# UI – ZAPIS DO BAZY SQL
# ---------------------------------------------------------
st.subheader("Zapis do bazy")
with st.form("save_form", clear_on_submit=True, border=True):
    note = st.text_input("Notatka (opcjonalnie)", max_chars=200,
                         placeholder="np. poniedziałek, trening siłowy")
    submitted = st.form_submit_button(
        "Zapisz wybrane ustawienia / makro", type="primary"
    )
if submitted:
    try:
        persist_state()
        snap_id = db.save_snapshot(
            note=note, day_mode=mode, current_carbs=current_carbs,
            target_carbs=target_carbs, target=target, totals=totals, items=items,
        )
        st.success(
            f"Zapisano #{snap_id}: {totals['kcal']:.0f} kcal, {len(items)} produktów "
            f"(tryb: {mode}, cel węgli: {target_carbs} g)."
        )
    except Exception as e:  # noqa: BLE001
        st.error(f"Nie udało się zapisać do bazy SQL: {e}")

# ---------------------------------------------------------
# UI – TABELA I PODSUMOWANIE
# ---------------------------------------------------------
if items:
    df = pd.DataFrame(items).rename(columns={
        "product": "Produkt", "grams": "g", "kcal": "kcal",
        "protein": "Białko [g]", "fat": "Tłuszcz łącznie [g]",
        "sat_fat": "Nasycone (SFA) [g]", "unsat_fat": "Nienasycone (UFA) [g]",
        "carbs": "Węglowodany [g]",
    })
    df["SFA % tłuszczu"] = [
        round(pct(s, f)) if f > 0 else None for s, f in zip(df["Nasycone (SFA) [g]"], df["Tłuszcz łącznie [g]"])
    ]
    st.dataframe(df, width="stretch", hide_index=True)

    st.subheader("Podsumowanie dnia")
    summary_cols = st.columns(4)
    summary_cols[0].metric("Zjedzone kcal", f"{totals['kcal']:.0f}",
                           f"{totals['kcal'] - target['kcal']:.0f}")
    summary_cols[1].metric("Białko", f"{totals['protein']:.1f} g",
                           f"{totals['protein'] - target['protein']:.1f} g")
    summary_cols[2].metric(
        "Tłuszcz łącznie", f"{totals['fat']:.1f} g", f"{totals['fat'] - target['fat']:.1f} g",
        help=f"Podział: {totals['sat_fat']:.1f} g nasyconych / {totals['unsat_fat']:.1f} g nienasyconych",
    )
    summary_cols[3].metric("Węglowodany", f"{totals['carbs']:.1f} g",
                           f"{totals['carbs'] - target_carbs:.1f} g")

    st.progress(
        min(totals["protein"] / max(target["protein"], 1), 1.0),
        text=f"Białko: {totals['protein']:.1f} / {target['protein']} g",
    )

    # ---------------- TŁUSZCZE: SFA vs UFA ----------------
    fat, sat, unsat, kcal = totals["fat"], totals["sat_fat"], totals["unsat_fat"], totals["kcal"]
    sat_pct_fat = round(pct(sat, fat), 1)
    unsat_pct_fat = round(100.0 - sat_pct_fat, 1) if fat > 0 else 0.0
    fat_e = pct(fat * 9, kcal)
    sat_e = pct(sat * 9, kcal)
    unsat_e = pct(unsat * 9, kcal)
    sfa_limit_who_g = target["kcal"] * SFA_WHO_MAX_E / 100 / 9
    sfa_limit_aha_g = target["kcal"] * SFA_AHA_MAX_E / 100 / 9

    st.progress(
        min(fat / max(target["fat"], 1), 1.0),
        text=(f"Tłuszcz łącznie: {fat:.1f} / {target['fat']} g — {fat_e:.0f}% energii "
              f"(zalecane: 20–35% energii wg EFSA, ≤30% wg WHO; w low-carb świadomie więcej)"),
    )

    st.markdown("**Skład tłuszczu – udział w całości (100% = cały tłuszcz)**")
    # Pasek złożony SFA | UFA – treść to wyłącznie liczby wyliczone w kodzie (brak danych od użytkownika)
    st.markdown(
        f"""
<div style="display:flex;width:100%;height:30px;border-radius:6px;overflow:hidden;
            font-size:0.85rem;font-weight:600;color:#fff;border:1px solid rgba(128,128,128,.35)">
  <div style="width:{sat_pct_fat}%;background:#d9534f;display:flex;align-items:center;
              justify-content:center;white-space:nowrap">{'SFA ' + format(sat_pct_fat, '.0f') + '%' if sat_pct_fat >= 8 else ''}</div>
  <div style="width:{unsat_pct_fat}%;background:#3c9d5d;display:flex;align-items:center;
              justify-content:center;white-space:nowrap">{'UFA ' + format(unsat_pct_fat, '.0f') + '%' if unsat_pct_fat >= 8 else ''}</div>
</div>
<div style="position:relative;height:14px;font-size:0.7rem;opacity:.75">
  <div style="position:absolute;left:{SFA_MAX_OF_FAT}%;border-left:2px dashed currentColor;height:14px;padding-left:4px">
    granica zalecana ~1/3 SFA
  </div>
</div>
""",
        unsafe_allow_html=True,
    )

    st.progress(
        min(sat_pct_fat / 100, 1.0),
        text=(f"Nasycone (SFA): {sat:.1f} g = {sat_pct_fat:.0f}% tłuszczu | {sat_e:.1f}% energii "
              f"(zalecane: ≤10% energii wg WHO, <6% wg AHA ≈ ≤{sfa_limit_who_g:.0f} g / "
              f"<{sfa_limit_aha_g:.0f} g przy {target['kcal']} kcal; ok. ≤1/3 tłuszczu)"),
    )
    st.progress(
        min(unsat_pct_fat / 100, 1.0),
        text=(f"Nienasycone (UFA): {unsat:.1f} g = {unsat_pct_fat:.0f}% tłuszczu | {unsat_e:.1f}% energii "
              f"(zalecane: większość tłuszczu, ok. ≥2/3; MUFA + PUFA z oliwy, olejów roślinnych, "
              f"orzechów, ryb – nimi zastępuj SFA)"),
    )

    if sat_e > SFA_WHO_MAX_E:
        st.error(f"SFA = {sat_e:.1f}% energii – powyżej limitu WHO (10%). Zamień część masła / "
                 f"kokosa / MCT / tłustego nabiału na oliwę, orzechy lub ryby.")
    elif sat_e > SFA_AHA_MAX_E:
        st.warning(f"SFA = {sat_e:.1f}% energii – w limicie WHO (≤10%), ale powyżej celu AHA (<6%).")
    else:
        st.success(f"SFA = {sat_e:.1f}% energii – w zalecanym zakresie (WHO ≤10%, AHA <6%).")
    if fat > 0 and unsat_pct_fat < UFA_MIN_OF_FAT:
        st.caption(f"UFA stanowi {unsat_pct_fat:.0f}% tłuszczu – sugerowane ≥ ~{UFA_MIN_OF_FAT:.0f}%.")

    st.progress(
        min(totals["carbs"] / max(target_carbs, 1), 1.0),
        text=f"Węglowodany: {totals['carbs']:.1f} / {target_carbs} g",
    )

    remaining = {
        "Kcal do celu": round(target["kcal"] - totals["kcal"], 1),
        "Białko do celu [g]": round(target["protein"] - totals["protein"], 1),
        "Tłuszcz do celu [g]": round(target["fat"] - totals["fat"], 1),
        "SFA do limitu WHO [g]": round(sfa_limit_who_g - sat, 1),
        "Węglowodany do celu [g]": round(target_carbs - totals["carbs"], 1),
    }
    st.subheader("Ile jeszcze brakuje / nadwyżka")
    st.table(pd.DataFrame([remaining]).style.format("{:.1f}"))
else:
    st.info("Wybierz produkty i wpisz gramaturę, aby zobaczyć podsumowanie.")

# ---------------------------------------------------------
# UI – HISTORIA ZAPISÓW (SQLite)
# ---------------------------------------------------------
st.subheader("Historia zapisów")
snapshots = db.list_snapshots(limit=100)
if snapshots:
    hist = pd.DataFrame(snapshots)[
        ["id", "created_at", "note", "day_mode", "target_carbs", "kcal",
         "protein", "fat", "sat_fat", "unsat_fat", "carbs", "items_count"]
    ]
    hist["SFA %"] = [round(pct(s, f)) if f else 0 for s, f in zip(hist["sat_fat"], hist["fat"])]
    hist = hist.rename(columns={
        "id": "#", "created_at": "Data (UTC)", "note": "Notatka", "day_mode": "Tryb",
        "target_carbs": "Cel węgli", "kcal": "kcal", "protein": "Białko",
        "fat": "Tłuszcz", "sat_fat": "SFA", "unsat_fat": "UFA",
        "carbs": "Węgle", "items_count": "Produkty",
    })
    st.dataframe(hist, width="stretch", hide_index=True)

    labels = {s["id"]: f"#{s['id']} – {s['created_at']} – {s['kcal']:.0f} kcal"
              + (f" – {s['note']}" if s["note"] else "") for s in snapshots}
    pick = st.selectbox("Wybierz zapis", list(labels), format_func=labels.get)
    snap, snap_items = db.get_snapshot(pick)
    if snap_items:
        st.dataframe(
            pd.DataFrame(snap_items)[["product", "grams", "kcal", "protein", "fat",
                                      "sat_fat", "unsat_fat", "carbs"]],
            width="stretch", hide_index=True,
        )
    b1, b2, b3 = st.columns(3)
    b1.button("Przywróć ten zapis", on_click=restore_snapshot, args=(pick,))
    b2.button("Usuń zapis", on_click=remove_snapshot, args=(pick,))
    b3.download_button(
        "Eksport CSV", data=pd.DataFrame(snap_items).to_csv(index=False).encode("utf-8"),
        file_name=f"macro_snapshot_{pick}.csv", mime="text/csv",
    )
else:
    st.caption("Brak zapisów – użyj przycisku „Zapisz wybrane ustawienia / makro”.")

# ---------------------------------------------------------
# UI – DODAWANIE PRODUKTU DO foods.json
# ---------------------------------------------------------
NAME_RE = re.compile(r"^[\w\s.,%()/+\-]{2,80}$", re.UNICODE)

with st.expander("Dodaj / nadpisz produkt w foods.json (wartości na 100 g)"):
    with st.form("add_food", clear_on_submit=True):
        name = st.text_input("Nazwa produktu", max_chars=80)
        f1, f2, f3 = st.columns(3)
        kcal100 = f1.number_input("kcal / 100 g", 0.0, 900.0, 0.0, 1.0)
        prot100 = f2.number_input("Białko / 100 g", 0.0, 100.0, 0.0, 0.1)
        carb100 = f3.number_input("Węglowodany / 100 g", 0.0, 100.0, 0.0, 0.1)
        f4, f5 = st.columns(2)
        fat100 = f4.number_input("Tłuszcz / 100 g", 0.0, 100.0, 0.0, 0.1)
        sat100 = f5.number_input("w tym nasycone (SFA) / 100 g", 0.0, 100.0, 0.0, 0.1)
        overwrite = st.checkbox("Nadpisz, jeśli produkt istnieje")
        add = st.form_submit_button("Zapisz produkt do foods.json")
    if add:
        name = (name or "").strip()
        if not NAME_RE.match(name):
            st.error("Nieprawidłowa nazwa (2–80 znaków: litery, cyfry, spacje, .,%()/+-).")
        elif sat100 > fat100:
            st.error("Tłuszcze nasycone nie mogą przekraczać tłuszczu łącznie.")
        elif prot100 + carb100 + fat100 > 100:
            st.error("Suma białka, tłuszczu i węglowodanów przekracza 100 g na 100 g.")
        elif name in FOODS and not overwrite:
            st.error("Produkt już istnieje – zaznacz „Nadpisz”, aby zaktualizować.")
        else:
            foods = dict(FOODS)
            foods[name] = {
                "kcal": round(kcal100 / 100, 4),
                "protein": round(prot100 / 100, 4),
                "fat": round(fat100 / 100, 4),
                "carbs": round(carb100 / 100, 4),
                "sat_fat": round(sat100 / 100, 4),
                "unsat_fat": round((fat100 - sat100) / 100, 4),
            }
            try:
                write_foods_atomic(dict(sorted(foods.items(), key=lambda kv: kv[0].lower())))
                st.success(f"Zapisano „{name}” w {FOODS_FILE}.")
                st.rerun()
            except Exception as e:  # noqa: BLE001
                st.error(f"Błąd zapisu foods.json: {e}")

st.caption(
    "Rekomendacje: WHO 2023 – SFA ≤10% energii, tłuszcz głównie nienasycony, tłuszcz ogółem ≤30% energii; "
    "AHA – SFA <6% energii; EFSA – tłuszcz 20–35% energii. "
    "Udział ~1/3 SFA w tłuszczu wynika z relacji 10% E SFA / 30% E tłuszczu. "
    "Kalkulator ma charakter informacyjny, nie zastępuje porady dietetyka/lekarza."
)
