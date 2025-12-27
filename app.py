import streamlit as st
import pandas as pd
import os
import urllib.parse
from datetime import datetime

# --- CONFIGURATION DE LA PAGE ---
st.set_page_config(page_title="SyNdongo Central Sentinel", layout="wide", page_icon="🛡️")

# Dossiers de stockage pour le web
SAVE_DIR = "donnees_controle"
if not os.path.exists(SAVE_DIR): os.makedirs(SAVE_DIR)

PATH_SY = os.path.join(SAVE_DIR, "base_sy.csv")
PATH_NDONGO = os.path.join(SAVE_DIR, "base_ndongo.csv")
LOG_DISCIPLINE = os.path.join(SAVE_DIR, "rapport_discipline.csv")

# --- BASE DE DONNÉES DES AGENTS & CODES PIN ---
DB_ACCES = {
    "COUMBA BA": "1111",
    "ADAMA MBAYE": "2222",
    "RAMATA GAYE": "3333",
    "EL HADJI THIAM": "4444",
    "ADJA SY": "5555",
    "THIERNO SADOU": "6666",
    "IBRAHIMA SY": "1000", # ACCÈS ADMIN
    "MARIETOU": "1044",
    "NDONGO GAYE": "5616",
    "LAMINE NDIAYE": "2055",
    "ALIOU CISSE": "2010", # ACCÈS ADMIN
    "ADMIN": "3289"        # ACCÈS ADMIN
}

# Liste des profils autorisés à importer et voir les rapports
ADMINS_AUTORISES = ["ADMIN", "IBRAHIMA SY", "ALIOU CISSE"]

# --- FONCTIONS TECHNIQUES ---

def trouver_colonne(df, mots_cles):
    """Détecte les colonnes Yango automatiquement"""
    for col in df.columns:
        if any(mot.lower() in col.lower() for mot in mots_cles):
            return col
    return None

def standardiser_donnees(df, label_parc):
    if df is None or df.empty: return pd.DataFrame()
    df.columns = df.columns.str.strip().str.replace('"', '').str.replace("'", "")
    
    c_nom = trouver_colonne(df, ["Nom complet", "Nom"])
    c_permis = trouver_colonne(df, ["Permis"])
    c_agent = trouver_colonne(df, ["Employé responsable", "Agent"])
    c_courses = trouver_colonne(df, ["Commandes terminées", "Commandes au sein"])
    c_tel = trouver_colonne(df, ["Numéro de téléphone", "téléphone"])

    df_std = pd.DataFrame()
    df_std['NOM'] = df[c_nom] if c_nom else "Inconnu"
    df_std['PERMIS'] = df[c_permis].astype(str).str.strip() if c_permis else "N/A"
    df_std['AGENT_RESP'] = df[c_agent].fillna("Non assigné") if c_agent else "Non assigné"
    df_std['COURSES'] = pd.to_numeric(df[c_courses], errors='coerce').fillna(0) if c_courses else 0
    df_std['TEL'] = df[c_tel].astype(str).str.replace('+', '').str.strip() if c_tel else ""
    df_std['PARC'] = label_parc
    return df_std

def log_erreur(agent_connecte, permis, info):
    data = {
        "Date": [datetime.now().strftime("%d/%m/%Y %H:%M")],
        "Agent_Controleur": [agent_connecte],
        "Permis_Saisi": [permis],
        "Verdict": [info]
    }
    df_log = pd.DataFrame(data)
    if not os.path.exists(LOG_DISCIPLINE):
        df_log.to_csv(LOG_DISCIPLINE, index=False, sep=';', encoding='utf-8-sig')
    else:
        df_log.to_csv(LOG_DISCIPLINE, mode='a', header=False, index=False, sep=';', encoding='utf-8-sig')

def charger_base_complete():
    sy_raw = pd.read_csv(PATH_SY, sep=';') if os.path.exists(PATH_SY) else None
    nd_raw = pd.read_csv(PATH_NDONGO, sep=';') if os.path.exists(PATH_NDONGO) else None
    df_sy = standardiser_donnees(sy_raw, "SY")
    df_nd = standardiser_donnees(nd_raw, "NDONGO")
    return pd.concat([df_sy, df_nd], ignore_index=True)

# --- INTERFACE UTILISATEUR ---
st.sidebar.title("🏢 Bureau SyNdongo")
agent_user = st.sidebar.selectbox("Sélectionner votre nom", list(DB_ACCES.keys()))
code_pin = st.sidebar.text_input("Entrez votre Code PIN", type="password")

if code_pin == DB_ACCES.get(agent_user):
    base_globale = charger_base_complete()
    
    # Restriction des menus
    if agent_user in ADMINS_AUTORISES:
        menu = st.sidebar.radio("Navigation", ["🔍 Scanner Anti-Doublon", "📊 Rapport Hebdo", "📥 Importation Yango"])
    else:
        st.sidebar.info("🔓 Mode Agent : Scanner déverrouillé")
        menu = "🔍 Scanner Anti-Doublon"

    # --- ONGLET 1 : LE SCANNER (ACCESSIBLE À TOUS) ---
    if menu == "🔍 Scanner Anti-Doublon":
        st.header("🛡️ Contrôle d'Inscription Obligatoire")
        p_input = st.text_input("Scanner ou Entrer le numéro de Permis")
        
        if p_input and not base_globale.empty:
            p_input = p_input.strip()
            match = base_globale[base_globale['PERMIS'] == p_input]
            
            if not match.empty:
                st.error("🚨 DOUBLON DÉTECTÉ : Ce chauffeur est déjà dans le système !")
                gagnant = match.sort_values(by='COURSES', ascending=False).iloc[0]
                
                for _, r in match.iterrows():
                    st.warning(f"📍 Parc: {r['PARC']} | Responsable: {r['AGENT_RESP']} | Activité: {int(r['COURSES'])} courses")
                
                st.info(f"👉 **ARBITRAGE :** Le chauffeur doit rester chez **{gagnant['AGENT_RESP']}** ({gagnant['PARC']}).")
                log_erreur(agent_user, p_input, f"Tentative sur doublon appartenant à {gagnant['AGENT_RESP']}")
            else:
                st.success("✅ LIBRE : Ce permis n'existe pas. Inscription autorisée.")

    # --- ONGLET 2 : RAPPORT (ADMIN SEULEMENT) ---
    elif menu == "📊 Rapport Hebdo":
        st.header("Analyse des Conflits & Discipline")
        if not base_globale.empty:
            doublons = base_globale[base_globale.duplicated(subset=['PERMIS'], keep=False)]
            st.metric("Total Doublons SY/NDONGO", len(doublons)//2)
            
            tab1, tab2 = st.tabs(["🆕 Liste des Doublons", "👮 Journal des Fautes"])
            with tab1:
                if not doublons.empty:
                    st.dataframe(doublons.sort_values(by="PERMIS"), use_container_width=True)
                    st.download_button("📥 Télécharger Doublons (CSV)", doublons.to_csv(index=False, sep=';').encode('utf-8'), "doublons.csv")
                else:
                    st.success("Aucun doublon détecté.")
            
            with tab2:
                if os.path.exists(LOG_DISCIPLINE):
                    st.dataframe(pd.read_csv(LOG_DISCIPLINE, sep=';'), use_container_width=True)
                else:
                    st.info("Aucun incident enregistré.")

    # --- ONGLET 3 : IMPORTATION (ADMIN SEULEMENT) ---
    elif menu == "📥 Importation Yango":
        st.header("Mise à jour Hebdomadaire")
        up_sy = st.file_uploader("Fichier SY (CSV)", type="csv")
        up_nd = st.file_uploader("Fichier NDONGO (CSV)", type="csv")
        if st.button("🚀 Synchroniser les bases"):
            if up_sy: pd.read_csv(up_sy, sep=';').to_csv(PATH_SY, index=False, sep=';')
            if up_nd: pd.read_csv(up_nd, sep=';').to_csv(PATH_NDONGO, index=False, sep=';')
            st.success("Bases de données actualisées !")
            st.rerun()
else:
    if code_pin: st.sidebar.error("Code PIN incorrect")
    st.info("👋 Veuillez entrer votre code PIN à gauche pour accéder au système.")
