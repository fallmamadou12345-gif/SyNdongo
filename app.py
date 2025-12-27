import streamlit as st
import pandas as pd
import os
import urllib.parse
from datetime import datetime

# --- CONFIGURATION ---
st.set_page_config(page_title="Yango Unity Sentinel", layout="wide", page_icon="🛡️")

SAVE_DIR = "donnees_controle"
if not os.path.exists(SAVE_DIR): os.makedirs(SAVE_DIR)

PATH_SY = os.path.join(SAVE_DIR, "base_sy.csv")
PATH_NDONGO = os.path.join(SAVE_DIR, "base_ndongo.csv")
LOG_DISCIPLINE = os.path.join(SAVE_DIR, "rapport_discipline.csv")

# --- GESTION DES ACCÈS (Codes PIN) ---
# Ici, les clés sont les noms des agents qui utilisent le logiciel
DB_ACCES = {
    "COUMBA BA": "1111",
    "ADAMA MBAYE": "2222",
    "RAMATA GAYE": "3333",
    "ADMIN": "3289"
    "EL HADJI THIAM": "4444",
    "THIERNO SADOU": "6666",
    "ADJA SY": "5555",
    "IBRAHIMA SY": "1000"
    "MARIETOU": "1044",
    "NDONGO GAYE": "5616",
    "LAMINE NDIAYE": "2055",
    "IBRAHIMA SY": "1000"
}

# --- FONCTIONS TECHNIQUES ---

def trouver_colonne(df, mots_cles):
    for col in df.columns:
        if any(mot.lower() in col.lower() for mot in mots_cles):
            return col
    return None

def standardiser_donnees(df, label_parc):
    if df is None or df.empty: return pd.DataFrame()
    df.columns = df.columns.str.strip().str.replace('"', '')
    
    # Identification précise selon vos fichiers
    c_nom = trouver_colonne(df, ["Nom complet"])
    c_permis = trouver_colonne(df, ["Permis"])
    c_agent = trouver_colonne(df, ["Employé responsable"]) # L'agent qui suit le chauffeur
    c_cond = trouver_colonne(df, ["Conditions du partenariat"]) # Ex: Membre du personnel, etc.
    c_courses = trouver_colonne(df, ["Commandes terminées"])
    c_tel = trouver_colonne(df, ["téléphone"])

    df_std = pd.DataFrame()
    df_std['NOM'] = df[c_nom] if c_nom else "Inconnu"
    df_std['PERMIS'] = df[c_permis].astype(str).str.strip() if c_permis else "N/A"
    df_std['AGENT'] = df[c_agent].fillna("Non assigné") if c_agent else "Non assigné"
    df_std['CONDITIONS'] = df[c_cond] if c_cond else "N/A"
    df_std['COURSES'] = pd.to_numeric(df[c_courses], errors='coerce').fillna(0) if c_courses else 0
    df_std['TEL'] = df[c_tel].astype(str).str.replace('+', '').str.strip() if c_tel else ""
    df_std['PARC'] = label_parc
    return df_std

def log_erreur(agent_connecte, permis, info):
    data = {
        "Date": [datetime.now().strftime("%d/%m/%Y %H:%M")],
        "Agent_Controleur": [agent_connecte],
        "Permis_Saisi": [permis],
        "Resultat": [info]
    }
    df_log = pd.DataFrame(data)
    if not os.path.exists(LOG_DISCIPLINE):
        df_log.to_csv(LOG_DISCIPLINE, index=False, sep=';', encoding='utf-8-sig')
    else:
        df_log.to_csv(LOG_DISCIPLINE, mode='a', header=False, index=False, sep=';', encoding='utf-8-sig')

# --- CHARGEMENT ---
def charger_base_complete():
    sy_raw = pd.read_csv(PATH_SY, sep=';') if os.path.exists(PATH_SY) else None
    nd_raw = pd.read_csv(PATH_NDONGO, sep=';') if os.path.exists(PATH_NDONGO) else None
    df_sy = standardiser_donnees(sy_raw, "SY")
    df_nd = standardiser_donnees(nd_raw, "NDONGO")
    return pd.concat([df_sy, df_nd], ignore_index=True)

# --- INTERFACE ---
st.sidebar.title("🔐 Authentification")
agent_user = st.sidebar.selectbox("Agent en poste", list(DB_ACCES.keys()))
code_pin = st.sidebar.text_input("Code PIN", type="password")

if code_pin == DB_ACCES.get(agent_user):
    base_globale = charger_base_complete()
    menu = st.sidebar.radio("Navigation", ["🔍 Scanner de Contrôle", "📊 Rapport Hebdo Doublons", "📥 Importation Yango"])

    if menu == "🔍 Scanner de Contrôle":
        st.header("🛡️ Vérification Anti-Doublon")
        p_input = st.text_input("Entrez ou Scannez le numéro de Permis")
        
        if p_input and not base_globale.empty:
            p_input = p_input.strip()
            match = base_globale[base_globale['PERMIS'] == p_input]
            
            if not match.empty:
                st.error("🚨 DOUBLON DÉTECTÉ : Chauffeur déjà présent !")
                # Règle : Le plus grand nombre de courses gagne
                gagnant = match.sort_values(by='COURSES', ascending=False).iloc[0]
                
                for _, r in match.iterrows():
                    st.warning(f"📍 Parc: {r['PARC']} | Agent Responsable: {r['AGENT']} | Courses: {int(r['COURSES'])}")
                
                st.info(f"👉 **DECISION :** Le chauffeur doit rester chez **{gagnant['AGENT']}** ({gagnant['PARC']}).")
                log_erreur(agent_user, p_input, f"Tentative sur chauffeur de {gagnant['AGENT']}")
            else:
                st.success("✅ LIBRE : Ce permis n'existe pas. Inscription autorisée.")

    elif menu == "📊 Rapport Hebdo Doublons":
        st.header("Analyse des Doublons de la Semaine")
        if not base_globale.empty:
            doublons = base_globale[base_globale.duplicated(subset=['PERMIS'], keep=False)]
            
            st.metric("Nombre de Doublons à régulariser", len(doublons)//2)
            
            if not doublons.empty:
                st.dataframe(doublons.sort_values(by="PERMIS"), use_container_width=True)
                csv = doublons.to_csv(index=False, sep=';').encode('utf-8')
                st.download_button("📥 Télécharger la liste des doublons", csv, "doublons_hebdo.csv")
            else:
                st.success("Aucun doublon détecté.")

    elif menu == "📥 Importation Yango":
        st.header("Mise à jour des données")
        up_sy = st.file_uploader("Fichier SY (CSV)", type="csv")
        up_nd = st.file_uploader("Fichier NDONGO (CSV)", type="csv")
        if st.button("🚀 Actualiser la Base Centrale"):
            if up_sy: pd.read_csv(up_sy, sep=';').to_csv(PATH_SY, index=False, sep=';')
            if up_nd: pd.read_csv(up_nd, sep=';').to_csv(PATH_NDONGO, index=False, sep=';')
            st.success("Mémoire actualisée ! Les anciens doublons sont mis à jour.")
            st.rerun()
else:

    st.info("Entrez votre PIN pour accéder au contrôle.")
