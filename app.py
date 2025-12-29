import streamlit as st
import pandas as pd
import os
from datetime import datetime

# --- CONFIGURATION ---
st.set_page_config(page_title="SyNdongo Central Sentinel", layout="wide", page_icon="🛡️")

SAVE_DIR = "donnees_controle"
if not os.path.exists(SAVE_DIR): os.makedirs(SAVE_DIR)

PATH_SY = os.path.join(SAVE_DIR, "base_sy.csv")
PATH_NDONGO = os.path.join(SAVE_DIR, "base_ndongo.csv")
PATH_TEMP_INSCRIPTIONS = os.path.join(SAVE_DIR, "inscriptions_semaine.csv")

# --- ACCÈS ---
DB_ACCES = {
    "COUMBA BA": "1111", "ADAMA MBAYE": "2222", "RAMATA GAYE": "3333",
    "EL HADJI THIAM": "4444", "ADJA SY": "5555", "THIERNO SADOU": "6666",
    "IBRAHIMA SY": "1000", "MARIETOU": "1044", "NDONGO GAYE": "5616",
    "LAMINE NDIAYE": "2055", "ALIOU CISSE": "2010", "ADMIN": "3289"
}
ADMINS_AUTORISES = ["ADMIN", "IBRAHIMA SY", "ALIOU CISSE"]

# --- FONCTIONS ---
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
    
    df_std = pd.DataFrame()
    df_std['NOM'] = df[c_nom] if c_nom else "Inconnu"
    df_std['PERMIS'] = df[c_permis].astype(str).str.strip() if c_permis else "N/A"
    df_std['AGENT_RESP'] = df[c_agent].fillna("Non assigné") if c_agent else "Non assigné"
    df_std['COURSES'] = 0
    df_std['TEL'] = "None"
    df_std['PARC'] = label_parc
    return df_std[cols]

def charger_base_complete():
    # Charger Yango
    sy = pd.read_csv(PATH_SY, sep=';') if os.path.exists(PATH_SY) else None
    nd = pd.read_csv(PATH_NDONGO, sep=';') if os.path.exists(PATH_NDONGO) else None
    df_globale = pd.concat([standardiser_donnees(sy, "SY"), standardiser_donnees(nd, "NDONGO")], ignore_index=True)
    
    # Charger Temporaire
    if os.path.exists(PATH_TEMP_INSCRIPTIONS):
        try:
            df_temp = pd.read_csv(PATH_TEMP_INSCRIPTIONS, sep=';', dtype={'PERMIS': str})
            if not df_temp.empty:
                df_globale = pd.concat([df_globale, df_temp], ignore_index=True)
        except:
            pass
    return df_globale

def enregistrer_inscription(agent, permis, parc):
    # Dictionnaire strict pour éviter les décalages vus sur vos photos
    nouveau = pd.DataFrame([{
        "NOM": "NOUVELLE_INSCRIPTION",
        "PERMIS": str(permis).strip(),
        "AGENT_RESP": agent,
        "COURSES": 0,
        "TEL": "None",
        "PARC": parc,
        "DATE_INSCRIPTION": datetime.now().strftime("%d/%m/%Y %H:%M")
    }])
    
    if not os.path.exists(PATH_TEMP_INSCRIPTIONS):
        nouveau.to_csv(PATH_TEMP_INSCRIPTIONS, index=False, sep=';', encoding='utf-8-sig')
    else:
        nouveau.to_csv(PATH_TEMP_INSCRIPTIONS, mode='a', header=False, index=False, sep=';', encoding='utf-8-sig')

# --- INTERFACE ---
st.sidebar.title("🏢 Bureau SyNdongo")
agent_user = st.sidebar.selectbox("Agent", list(DB_ACCES.keys()))
code_pin = st.sidebar.text_input("PIN", type="password")

if code_pin == DB_ACCES.get(agent_user):
    base_globale = charger_base_complete()
    
    menu_options = ["🔍 Scanner Anti-Doublon", "📊 Rapport Semaine", "📥 Importation Yango"] if agent_user in ADMINS_AUTORISES else ["🔍 Scanner Anti-Doublon"]
    menu = st.sidebar.radio("Navigation", menu_options)

    if menu == "🔍 Scanner Anti-Doublon":
        st.header("🛡️ Contrôle d'Inscription Obligatoire")
        p_input = st.text_input("Entrez le numéro de Permis à vérifier")
        
        if p_input:
            p_clean = str(p_input).strip()
            # On cherche dans la base fusionnée
            match = base_globale[base_globale['PERMIS'] == p_clean]
            
            if not match.empty:
                st.error(f"🚨 DOUBLON DÉTECTÉ : Le permis {p_clean} est déjà réservé !")
                r = match.iloc[-1]
                st.warning(f"📍 Parc: {r['PARC']} | Responsable: {r['AGENT_RESP']}")
            else:
                st.success(f"✅ LIBRE : Le permis {p_clean} est disponible.")
                st.markdown("---")
                st.subheader("💾 Enregistrer l'inscription immédiatement")
                p_choisi = st.radio("Dans quel parc ?", ["SY", "NDONGO"], horizontal=True)
                if st.button("Confirmer l'inscription"):
                    enregistrer_inscription(agent_user, p_clean, p_choisi)
                    st.success(f"BLOQUÉ ! Le permis {p_clean} est enregistré.")
                    st.rerun()

    elif menu == "📊 Rapport Semaine":
        st.header("Analyse de la semaine")
        if os.path.exists(PATH_TEMP_INSCRIPTIONS):
            df_temp = pd.read_csv(PATH_TEMP_INSCRIPTIONS, sep=';')
            st.subheader("📝 Inscriptions en temps réel")
            st.dataframe(df_temp, use_container_width=True)

    elif menu == "📥 Importation Yango":
        st.header("Mise à jour Hebdomadaire")
        if st.button("🚀 Vider la mémoire et Synchroniser"):
            if os.path.exists(PATH_TEMP_INSCRIPTIONS): os.remove(PATH_TEMP_INSCRIPTIONS)
            st.success("Mémoire vidée ! Le décalage des colonnes est corrigé.")
            st.rerun()
else:
    st.info("Entrez votre PIN.")
