import streamlit as st
import pandas as pd
import os
from datetime import datetime

# --- CONFIGURATION DE LA PAGE ---
st.set_page_config(page_title="SyNdongo Central Sentinel", layout="wide", page_icon="🛡️")

# Dossiers de stockage
SAVE_DIR = "donnees_controle"
if not os.path.exists(SAVE_DIR): os.makedirs(SAVE_DIR)

PATH_SY = os.path.join(SAVE_DIR, "base_sy.csv")
PATH_NDONGO = os.path.join(SAVE_DIR, "base_ndongo.csv")
PATH_TEMP_INSCRIPTIONS = os.path.join(SAVE_DIR, "inscriptions_semaine.csv")

# --- BASE DE DONNÉES DES AGENTS & CODES PIN ---
DB_ACCES = {
    "COUMBA BA": "1111", "ADAMA MBAYE": "2222", "RAMATA GAYE": "3333",
    "EL HADJI THIAM": "4444", "ADJA SY": "5555", "THIERNO SADOU": "6666",
    "IBRAHIMA SY": "1000", "MARIETOU": "1044", "NDONGO GAYE": "5616",
    "LAMINE NDIAYE": "2055", "ALIOU CISSE": "2010", "ADMIN": "3289"
}
# Seuls ces noms verront les options "Importation" et "Rapport"
ADMINS_AUTORISES = ["ADMIN", "IBRAHIMA SY", "ALIOU CISSE"]

# --- FONCTIONS TECHNIQUES ---
def trouver_colonne(df, mots_cles):
    for col in df.columns:
        if any(mot.lower() in col.lower() for mot in mots_cles): return col
    return None

def standardiser_donnees(df, label_parc):
    cols = ['NOM', 'PERMIS', 'AGENT_RESP', 'COURSES', 'TEL', 'PARC']
    if df is None or df.empty: return pd.DataFrame(columns=cols)
    df.columns = df.columns.str.strip().str.replace('"', '').str.replace("'", "")
    c_permis = trouver_colonne(df, ["Permis"])
    c_nom = trouver_colonne(df, ["Nom complet", "Nom"])
    c_agent = trouver_colonne(df, ["Employé responsable", "Agent"])
    c_courses = trouver_colonne(df, ["Commandes terminées", "Commandes au sein"])
    
    df_std = pd.DataFrame()
    df_std['NOM'] = df[c_nom] if c_nom else "Inconnu"
    df_std['PERMIS'] = df[c_permis].astype(str).str.strip() if c_permis else "N/A"
    df_std['AGENT_RESP'] = df[c_agent].fillna("Non assigné") if c_agent else "Non assigné"
    df_std['COURSES'] = pd.to_numeric(df[c_courses], errors='coerce').fillna(0) if c_courses else 0
    df_std['TEL'] = "None"
    df_std['PARC'] = label_parc
    return df_std[cols]

def charger_base_complete():
    sy = pd.read_csv(PATH_SY, sep=';') if os.path.exists(PATH_SY) else None
    nd = pd.read_csv(PATH_NDONGO, sep=';') if os.path.exists(PATH_NDONGO) else None
    df_globale = pd.concat([standardiser_donnees(sy, "SY"), standardiser_donnees(nd, "NDONGO")], ignore_index=True)
    if os.path.exists(PATH_TEMP_INSCRIPTIONS):
        df_temp = pd.read_csv(PATH_TEMP_INSCRIPTIONS, sep=';')
        df_globale = pd.concat([df_globale, df_temp], ignore_index=True)
    return df_globale

def enregistrer_inscription(agent, permis, parc):
    nouveau = pd.DataFrame([{
        "NOM": "NOUVELLE_INSCRIPTION", "PERMIS": str(permis).strip(),
        "AGENT_RESP": agent, "COURSES": 0, "TEL": "None", "PARC": parc,
        "DATE_INSCRIPTION": datetime.now().strftime("%d/%m/%Y %H:%M")
    }])
    header = not os.path.exists(PATH_TEMP_INSCRIPTIONS)
    nouveau.to_csv(PATH_TEMP_INSCRIPTIONS, mode='a', index=False, sep=';', header=header, encoding='utf-8-sig')

# --- INTERFACE ---
st.sidebar.title("🏢 Bureau SyNdongo")
agent_user = st.sidebar.selectbox("Sélectionner votre nom", list(DB_ACCES.keys()))
code_pin = st.sidebar.text_input("Entrez votre Code PIN", type="password")

if code_pin == DB_ACCES.get(agent_user):
    base_globale = charger_base_complete()
    
    # CONDITION POUR LE MENU ADMIN
    if agent_user in ADMINS_AUTORISES:
        menu = st.sidebar.radio("Navigation", ["🔍 Scanner Anti-Doublon", "📊 Rapport Hebdo", "📥 Importation Yango"])
    else:
        st.sidebar.info("🔓 Mode Agent : Accès au Scanner uniquement")
        menu = "🔍 Scanner Anti-Doublon"

    if menu == "🔍 Scanner Anti-Doublon":
        st.header("🛡️ Contrôle d'Inscription Obligatoire")
        p_input = st.text_input("Scanner ou Entrer le numéro de Permis")
        if p_input:
            p_clean = str(p_input).strip()
            match = base_globale[base_globale['PERMIS'] == p_clean] if not base_globale.empty else pd.DataFrame()
            if not match.empty:
                st.error("🚨 DOUBLON DÉTECTÉ !")
                r = match.iloc[-1]
                st.warning(f"📍 Parc: {r['PARC']} | Responsable: {r['AGENT_RESP']}")
            else:
                st.success(f"✅ LIBRE : Le permis {p_clean} est disponible.")
                st.subheader("💾 Enregistrer l'inscription")
                parc_choisi = st.radio("Dans quel parc ?", ["SY", "NDONGO"], horizontal=True)
                if st.button("Confirmer l'inscription"):
                    enregistrer_inscription(agent_user, p_clean, parc_choisi)
                    st.success("BLOQUÉ ! Inscription enregistrée.")
                    st.rerun()

    elif menu == "📊 Rapport Hebdo":
        st.header("Analyse des Doublons")
        doublons = base_globale[base_globale.duplicated(subset=['PERMIS'], keep=False)]
        st.dataframe(doublons, use_container_width=True)

    elif menu == "📥 Importation Yango":
        st.header("Mise à jour des fichiers")
        up_sy = st.file_uploader("Télécharger SY.csv", type="csv")
        up_nd = st.file_uploader("Télécharger NDONGO.csv", type="csv")
        if st.button("🚀 Synchroniser les bases"):
            if up_sy: pd.read_csv(up_sy, sep=';').to_csv(PATH_SY, index=False, sep=';')
            if up_nd: pd.read_csv(up_nd, sep=';').to_csv(PATH_NDONGO, index=False, sep=';')
            if os.path.exists(PATH_TEMP_INSCRIPTIONS): os.remove(PATH_TEMP_INSCRIPTIONS)
            st.success("Synchronisation réussie !")
            st.rerun()
else:
    st.info("Veuillez entrer votre PIN.")
