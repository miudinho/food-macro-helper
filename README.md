# Macro Diet App – Low-carb / IF Macro Tracker

Streamlit + SQLite, uruchamiany w kontenerze z trwałym wolumenem danych.

## Co nowego

| Funkcja | Opis |
|---|---|
| Trwały stan | Każda zmiana (produkty, gramatury, tryb dnia, suwaki) jest autozapisywana w SQLite (`app_state`). Po zatrzymaniu i ponownym uruchomieniu kontenera ostatnie wpisy są przywracane. |
| Przycisk „Zapisz wybrane ustawienia / makro” | Tworzy zapis w tabelach `snapshots` + `snapshot_items` (tryb, cele, sumy kcal/makro/SFA/UFA, lista produktów z gramaturą). |
| Historia zapisów | Podgląd, przywrócenie, usunięcie i eksport CSV dowolnego zapisu. |
| foods.json | Produkty nadal w JSON (ten sam format: wartości na 1 g). Przy pierwszym starcie plik z obrazu jest kopiowany do wolumenu `/app/data/foods.json`; formularz „Dodaj / nadpisz produkt” zapisuje go atomowo. |
| Tłuszcze SFA / UFA | Osobne paski: % SFA i % UFA w całym tłuszczu + % energii, pasek złożony 100% z linią granicy ~1/3 SFA, rekomendacje w nawiasach i alert WHO/AHA. |
| Import starego stanu | `user_selection.json` (z katalogu projektu) jest jednorazowo importowany do bazy przez `exec.sh`. |

## Rekomendacje użyte w aplikacji

- WHO 2023: SFA ≤ 10% energii, tłuszcz głównie nienasycony, tłuszcz ogółem ≤ 30% energii – https://www.who.int/news/item/17-07-2023-who-updates-guidelines-on-fats-and-carbohydrates
- AHA: SFA < 6% energii – https://www.heart.org/en/healthy-living/healthy-eating/eat-smart/fats/saturated-fats
- EFSA: tłuszcz 20–35% energii – https://knowledge-for-policy.ec.europa.eu/health-promotion-knowledge-gateway/dietary-fats-table-4_en
- „~1/3 SFA w tłuszczu / ≥ 2/3 UFA” – wartość orientacyjna wynikająca z relacji 10% E SFA przy 30% E tłuszczu. W diecie low-carb (więcej tłuszczu) kryterium nadrzędnym jest % energii z SFA.

## Uruchomienie

```bash
# Wariant 1: docker run z hardeningiem
./exec.sh                      # http://127.0.0.1:8501

# Wariant 2: docker compose (zalecany)
./start.sh
```

Zmienne `exec.sh`: `IMAGE`, `NAME`, `VOLUME` (domyślnie `macro-data`), `PORT`, `BIND_ADDR` (domyślnie `127.0.0.1`), `DOCKER` (domyślnie `sudo docker`).

Test persystencji:

```bash
./exec.sh            # wybierz produkty, kliknij "Zapisz..."
# Ctrl+C / docker stop macro-diet-app  (kontener --rm zostaje usunięty)
./exec.sh            # stan wraca z wolumenu macro-data
```

## Dane i backup

```bash
sudo docker volume inspect macro-data
./backup.sh                                   # spójny backup SQLite (backup API) + foods.json -> ./backups
sudo docker exec -it macro-diet-app python -c \
  "import sqlite3;c=sqlite3.connect('/app/data/macro.db');print(c.execute('select id,created_at,kcal,sat_fat from snapshots').fetchall())"
```

Schemat bazy (`/app/data/macro.db`):

- `app_state(id=1, payload JSON, updated_at)` – ostatni stan UI
- `snapshots(id, created_at, note, day_mode, current_carbs, target_carbs, target_*, kcal, protein, fat, sat_fat, unsat_fat, carbs)`
- `snapshot_items(snapshot_id FK ON DELETE CASCADE, product, grams, kcal, protein, fat, sat_fat, unsat_fat, carbs, position)`

## DevSecOps – zastosowane zabezpieczenia

- Multi-stage build, venv, przypięte wersje zależności, `apt-get upgrade` w obrazie bazowym.
- Użytkownik nieuprzywilejowany (UID 10001), kod `root:root 0644` (aplikacja nie może zmodyfikować własnego kodu), jedynym zapisywalnym katalogiem jest `/app/data` (0700), baza `0600`.
- Runtime: `--read-only`, `tmpfs /tmp`, `--cap-drop ALL`, `no-new-privileges`, limity pamięci/CPU/PID, port tylko na `127.0.0.1`.
- `HEALTHCHECK` na `/_stcore/health`.
- Streamlit: XSRF włączone, brak telemetrii, brak stack trace w UI, `fileWatcherType=none`, toolbar w trybie viewer.
- SQL wyłącznie parametryzowany, transakcje `BEGIN IMMEDIATE`/`ROLLBACK`, WAL + `busy_timeout`.
- Walidacja wejścia: zakresy gramatur/suwaków, filtr produktów z bazy, regex nazwy produktu, kontrola SFA ≤ tłuszcz i sumy makro ≤ 100 g.
- Atomowy zapis `foods.json` (plik tymczasowy + `os.replace`).

Zalecane w CI: `hadolint Dockerfile`, `pip-audit -r requirements.txt`, `trivy image macro-diet-app`. Przy wystawieniu poza localhost – reverse proxy z TLS i uwierzytelnianiem (aplikacja nie ma własnego logowania).
