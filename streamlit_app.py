import random
import requests
import streamlit as st

DATA_URL = "https://raw.githubusercontent.com/Purukitto/pokemon-data.json/master/pokedex.json"

st.set_page_config(page_title="Who's That Pokémon?", page_icon="⚡", layout="centered")


@st.cache_data(show_spinner="Pokémon-Daten werden geladen …")
def lade_daten():
    response = requests.get(DATA_URL, timeout=30)
    response.raise_for_status()
    return response.json()


try:
    data = lade_daten()
except Exception as exc:
    st.error("Die Pokémon-Daten konnten nicht geladen werden. Bitte lade die Seite später neu.")
    st.caption(f"Technischer Hinweis: {exc}")
    st.stop()


def generation(pokemon):
    nummer = int(pokemon["id"])
    if nummer <= 151:
        return "Kanto"
    elif nummer <= 251:
        return "Johto"
    elif nummer <= 386:
        return "Hoenn"
    elif nummer <= 493:
        return "Sinnoh"
    elif nummer <= 649:
        return "Unova"
    elif nummer <= 721:
        return "Kalos"
    elif nummer <= 809:
        return "Alola"
    elif nummer <= 905:
        return "Galar"
    return "Paldea"


def evolution_line(pokemon):
    evolution = pokemon.get("evolution", {})
    vorherige = evolution.get("prev")
    naechste = evolution.get("next")
    if vorherige and naechste:
        return ["Middle"]
    elif naechste:
        return ["Base"]
    elif vorherige:
        return ["Final"]
    return ["Base", "Middle", "Final"]


def evolution_stages(pokemon):
    def zaehle_vorgaenger(p):
        prev = p.get("evolution", {}).get("prev")
        if not prev:
            return 0
        vorheriges = next((x for x in data if str(x["id"]) == str(prev[0])), None)
        return 0 if vorheriges is None else 1 + zaehle_vorgaenger(vorheriges)

    def zaehle_nachfolger(p):
        next_evo = p.get("evolution", {}).get("next")
        if not next_evo:
            return 0
        anzahl = 0
        for entwicklung in next_evo:
            if isinstance(entwicklung, list) and entwicklung:
                naechstes = next((x for x in data if str(x["id"]) == str(entwicklung[0])), None)
                if naechstes is not None:
                    anzahl = max(anzahl, 1 + zaehle_nachfolger(naechstes))
        return anzahl

    gesamt = 1 + zaehle_vorgaenger(pokemon) + zaehle_nachfolger(pokemon)
    if gesamt == 1:
        return ["Single Stage"]
    elif gesamt == 2:
        return ["Two Stage"]
    return ["Three Stage"]


def suche(eingabe, daten):
    if isinstance(daten, dict):
        if "id" in daten and "name" in daten:
            if eingabe.casefold() == "dual type":
                return len(daten.get("type", [])) == 2
            if eingabe.casefold() in ["mono type", "single type", "monotype"]:
                return len(daten.get("type", [])) == 1
            if eingabe.casefold() in [x.casefold() for x in evolution_line(daten)]:
                return True
            if eingabe.casefold() in [x.casefold() for x in evolution_stages(daten)]:
                return True
            if eingabe.casefold() == generation(daten).casefold():
                return True
        return any(suche(eingabe, wert) for wert in daten.values())
    elif isinstance(daten, list):
        return any(suche(eingabe, wert) for wert in daten)
    return str(daten).casefold() == eingabe.casefold()


def pokemon_raten(eingabe, pokemon):
    return (
        eingabe.casefold() == pokemon["name"]["english"].casefold()
        or eingabe == str(pokemon["id"])
    )


def ist_pokemon(eingabe, pokedex):
    return any(
        eingabe.casefold() == p["name"]["english"].casefold()
        or eingabe == str(p["id"])
        for p in pokedex
    )


def pokemon_nach_name(eingabe):
    return next(
        (p for p in data if p["name"]["english"].casefold() == eingabe.casefold()),
        None,
    )


TYPEN = [
    "Normal", "Fire", "Water", "Electric", "Grass", "Ice", "Fighting",
    "Poison", "Ground", "Flying", "Psychic", "Bug", "Rock", "Ghost",
    "Dragon", "Dark", "Steel", "Fairy"
]
REGIONEN = ["Kanto", "Johto", "Hoenn", "Sinnoh", "Unova", "Kalos", "Alola", "Galar", "Paldea"]

st.title("⚡ WHO'S THAT POKÉMON?")
st.write(
    "Finde das Pokémon! Du kannst nach Typen, Fähigkeiten und anderen Eigenschaften fragen. "
    "Errätst du den englischen Namen oder gibst die richtige Pokédexnummer ein, gewinnst du."
)

if "pokemon" not in st.session_state:
    st.session_state.pokemon = None
if "mode" not in st.session_state:
    st.session_state.mode = "classic"
if "history" not in st.session_state:
    st.session_state.history = []
if "hint_used" not in st.session_state:
    st.session_state.hint_used = False
if "finished" not in st.session_state:
    st.session_state.finished = False


def neues_spiel(mode, typ=None, region=None, name=None):
    if mode == "classic":
        pokemon = random.choice(data)
    elif mode == "monotype":
        moegliche = [p for p in data if len(p.get("type", [])) == 1 and p["type"][0].casefold() == typ.casefold()]
        pokemon = random.choice(moegliche) if moegliche else None
    elif mode == "monogeneration":
        moegliche = [p for p in data if generation(p).casefold() == region.casefold()]
        pokemon = random.choice(moegliche) if moegliche else None
    else:
        pokemon = pokemon_nach_name(name or "")

    if pokemon is None:
        st.error("Dazu wurde kein passendes Pokémon gefunden. Bitte prüfe deine Auswahl.")
        return

    st.session_state.pokemon = pokemon
    st.session_state.mode = mode
    st.session_state.history = []
    st.session_state.hint_used = False
    st.session_state.finished = False


with st.sidebar:
    st.header("Spielmodus")
    mode_choice = st.radio(
        "Wähle einen Modus:",
        ["classic", "monotype", "monogeneration", "selfselect"],
        format_func=lambda x: {
            "classic": "Classic",
            "monotype": "Monotype",
            "monogeneration": "Monogeneration",
            "selfselect": "Selfselect",
        }[x],
        key="mode_choice",
    )
    selected_type = None
    selected_region = None
    selected_name = None
    if mode_choice == "monotype":
        selected_type = st.selectbox("Einzeltyp", TYPEN)
    elif mode_choice == "monogeneration":
        selected_region = st.selectbox("Region", REGIONEN)
    elif mode_choice == "selfselect":
        selected_name = st.text_input("Englischer Pokémon-Name")

    if st.button("🎲 Neues Spiel starten", use_container_width=True):
        neues_spiel(mode_choice, selected_type, selected_region, selected_name)
        st.rerun()

if st.session_state.pokemon is None:
    st.info("Wähle links einen Spielmodus und klicke auf **Neues Spiel starten**.")
    st.markdown("**Befehle während des Spiels:** `hint`, `help`, ein einzelner Buchstabe oder eine Pokémon-Eigenschaft.")
    st.stop()

pokemon = st.session_state.pokemon

st.subheader(f"Modus: { {'classic':'Classic','monotype':'Monotype','monogeneration':'Monogeneration','selfselect':'Selfselect'}[st.session_state.mode] }")
st.caption("Das Pokémon bleibt verborgen, bis du es richtig errätst oder ein anderes Pokémon nennst.")

with st.form("guess_form", clear_on_submit=True):
    eingabe = st.text_input("Deine Eingabe", placeholder="z. B. Water, Levitate, hint oder Pikachu")
    submitted = st.form_submit_button("Eingabe prüfen", use_container_width=True)

if submitted and eingabe.strip():
    eingabe = eingabe.strip()
    lower = eingabe.casefold()

    if st.session_state.finished:
        st.warning("Diese Runde ist beendet. Starte links ein neues Spiel.")
    elif lower == "help":
        st.session_state.history.append((
            "info",
            "Mögliche Eingaben: `Dual Type`, `Mono Type`, `Single Type`, `Monotype`, "
            "`Base`, `Middle`, `Final`, `Single Stage`, `Two Stage`, `Three Stage`, "
            "ein Typ (z. B. Water), eine Fähigkeit oder eine andere Eigenschaft. "
            "Mit `hint` bekommst du einmal einen Tipp. Mit Pokémon-Name oder Pokédexnummer endet die Runde."
        ))
    elif lower == "hint":
        if st.session_state.hint_used:
            st.session_state.history.append(("warning", "Du hast schon einen Tipp angefordert!"))
        else:
            st.session_state.hint_used = True
            if st.session_state.mode == "monotype":
                hint = generation(pokemon)
            elif st.session_state.mode == "monogeneration":
                hint = pokemon.get("type", ["Unbekannt"])[0]
            else:
                hint = generation(pokemon) if random.randint(1, 2) == 1 else pokemon.get("type", ["Unbekannt"])[0]
            st.session_state.history.append(("info", f"💡 Tipp: **{hint}**"))
    elif len(eingabe) == 1 and eingabe.isalpha():
        if pokemon["name"]["english"][0].casefold() == lower:
            st.session_state.history.append(("success", "Richtig! Der erste Buchstabe stimmt."))
        else:
            st.session_state.history.append(("error", "Falsch! Der erste Buchstabe stimmt nicht."))
    elif pokemon_raten(eingabe, pokemon):
        st.session_state.history.append(("success", f"🎉 Richtig! Du hast gewonnen. Das Pokémon war **{pokemon['name']['english']}**."))
        st.session_state.finished = True
    elif ist_pokemon(eingabe, data):
        st.session_state.history.append(("error", f"❌ Falsches Pokémon! Die Runde ist verloren. Gesucht war **{pokemon['name']['english']}**."))
        st.session_state.finished = True
    elif suche(eingabe, pokemon):
        st.session_state.history.append(("success", f"**{eingabe}**: Ja, das trifft zu!"))
    else:
        st.session_state.history.append(("error", f"**{eingabe}**: Nein, das trifft nicht zu."))

for kind, message in st.session_state.history:
    if kind == "success":
        st.success(message)
    elif kind == "error":
        st.error(message)
    elif kind == "warning":
        st.warning(message)
    else:
        st.info(message)

if st.session_state.finished:
    sprite_url = pokemon.get("image", {}).get("sprite")
    if sprite_url:
        st.image(sprite_url, caption=pokemon["name"]["english"], width=180)
    if st.button("Noch eine Runde", use_container_width=True):
        st.session_state.pokemon = None
        st.session_state.history = []
        st.session_state.hint_used = False
        st.session_state.finished = False
        st.rerun()
