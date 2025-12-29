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
LOG_TRANSFERTS = os.path.join(SAVE_DIR, "demandes_transfert.csv")
# Nouvelle base pour les inscriptions de la semaine en cours
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
    return df_std[cols]

def charger_base_complete():
    sy = pd.read_csv(PATH_SY, sep=';') if os.path.exists(PATH_SY) else None
    nd = pd.read_csv(PATH_NDONGO, sep=';') if os.path.exists(PATH_NDONGO) else None
    df_csv = pd.concat([standardiser_donnees(sy, "SY"), standardiser_donnees(nd, "NDONGO")], ignore_index=True)
    
    # On ajoute les inscriptions faites manuellement cette semaine
    if os.path.exists(PATH_TEMP_INSCRIPTIONS):
        df_temp = pd.read_csv(PATH_TEMP_INSCRIPTIONS, sep=';')
        return pd.concat([df_csv, df_temp], ignore_index=True)
    return df_csv

def enregistrer_inscription(agent, permis, parc):
    data = {
        "NOM": ["NOUVEAU"], "PERMIS": [permis], "AGENT_RESP": [agent],
        "COURSES": [0], "TEL": [""], "PARC": [parc], 
        "DATE_INSCRIPTION": [datetime.now().strftime("%d/%m/%Y")]
    }
    df = pd.DataFrame(data)
    header = not os.path.exists(PATH_TEMP_INSCRIPTIONS)
    df.to_csv(PATH_TEMP_INSCRIPTIONS, mode='a', index=False, sep=';', header=header, encoding='utf-8-sig')

# --- INTERFACE ---
st.sidebar.title("🏢 Bureau SyNdongo")
agent_user = st.sidebar.selectbox("Agent", list(DB_ACCES.keys()))
code_pin = st.sidebar.text_input("PIN", type="password")

if code_pin == DB_ACCES.get(agent_user):
    base_globale = charger_base_complete()
    menu_options = ["🔍 Scanner Anti-Doublon", "📊 Rapport & Transferts", "📥 Importation Yango"] if agent_user in ADMINS_AUTORISES else ["🔍 Scanner Anti-Doublon"]
    menu = st.sidebar.radio("Navigation", menu_options)

    if menu == "🔍 Scanner Anti-Doublon":
        st.header("🛡️ Contrôle d'Inscription")
        p_input = st.text_input("Scanner ou Entrer le numéro de Permis")
        
        if p_input:
            p_input = p_input.strip()
            match = base_globale[base_globale['PERMIS'] == p_input] if not base_globale.empty else pd.DataFrame()
            
            if not match.empty:
                st.error("🚨 DOUBLON DÉTECTÉ : Déjà inscrit !")
                r = match.iloc[0]
                st.warning(f"📍 Parc actuel : {r['PARC']} | Responsable : {r['AGENT_RESP']}")
            else:
                st.success("✅ LIBRE : Inscription autorisée.")
                st.info("Souhaitez-vous valider l'inscription de ce chauffeur maintenant ?")
                choix_parc = st.selectbox("Inscrire dans quel parc ?", ["SY", "NDONGO"])
                if st.button(f"💾 Valider l'inscription chez {choix_parc}"):
                    enregistrer_inscription(agent_user, p_input, choix_parc)
                    st.balloons()
                    st.success(f"Chauffeur enregistré dans la mémoire de {choix_parc}. Personne d'autre ne pourra le prendre cette semaine.")
                    st.rerun()

    elif menu == "📊 Rapport & Transferts":
        st.header("Analyse & Mobilité")
        t1, t2 = st.tabs(["📝 Inscriptions de la semaine", "🔄 Demandes de Transfert"])
        with t1:
            if os.path.exists(PATH_TEMP_INSCRIPTIONS):
                st.write("Chauffeurs inscrits manuellement avant l'import hebdomadaire :")
                st.dataframe(pd.read_csv(PATH_TEMP_INSCRIPTIONS, sep=';'), use_container_width=True)
            else: st.info("Aucune inscription manuelle cette semaine.")

    elif menu == "📥 Importation Yango":
        st.header("Mise à jour Hebdomadaire")
        st.warning("⚠️ L'importation des nouveaux fichiers CSV effacera la mémoire temporaire de la semaine.")
        up_sy = st.file_uploader("Fichier SY", type="csv")
        up_nd = st.file_uploader("Fichier NDONGO", type="csv")
        if st.button("🚀 Synchroniser et Vider la mémoire temporaire"):
            if up_sy: pd.read_csv(up_sy, sep=';').to_csv(PATH_SY, index=False, sep=';')
            if up_nd: pd.read_csv(up_nd, sep=';').to_csv(PATH_NDONGO, index=False, sep=';')
            # On efface la base temporaire après l'import officiel
            if os.path.exists(PATH_TEMP_INSCRIPTIONS): os.remove(PATH_TEMP_INSCRIPTIONS)
            st.success("Bases actualisées et mémoire remise à zéro !")
            st.rerun()
else:
    st.info("Veuillez entrer votre PIN.")
