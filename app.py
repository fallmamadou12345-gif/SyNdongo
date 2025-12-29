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

def log_transfert(agent, permis, nom, ancien_parc, motif):
    date_h = datetime.now().strftime("%d/%m/%Y %H:%M")
    data = {
        "Date": [date_h], "Agent_Saisissant": [agent], "Chauffeur": [nom],
        "Permis": [permis], "Ancien_Parc": [ancien_parc], "Motif": [motif]
    }
    df = pd.DataFrame(data)
    header = not os.path.exists(LOG_TRANSFERTS)
    df.to_csv(LOG_TRANSFERTS, mode='a', index=False, sep=';', header=header, encoding='utf-8-sig')
    return date_h

def charger_base_complete():
    sy = pd.read_csv(PATH_SY, sep=';') if os.path.exists(PATH_SY) else None
    nd = pd.read_csv(PATH_NDONGO, sep=';') if os.path.exists(PATH_NDONGO) else None
    return pd.concat([standardiser_donnees(sy, "SY"), standardiser_donnees(nd, "NDONGO")], ignore_index=True)

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
                st.error("🚨 CHAUFFEUR DÉJÀ EXISTANT")
                gagnant = match.sort_values(by='COURSES', ascending=False).iloc[0]
                for _, r in match.iterrows():
                    st.warning(f"📍 {r['PARC']} | Agent: {r['AGENT_RESP']} | {int(r['COURSES'])} courses")
                
                st.markdown("---")
                st.subheader("🔄 Demande de changement de parc")
                motif = st.selectbox("Motif du changement", ["Changement de véhicule", "Décision du Propriétaire", "Souhait du chauffeur", "Autre"])
                
                if st.button("📝 Enregistrer la demande"):
                    date_val = log_transfert(agent_user, p_input, gagnant['NOM'], gagnant['PARC'], motif)
                    st.success("✅ Demande enregistrée !")
                    
                    st.markdown(f"""
                    <div style="border:2px solid #000; padding:20px; background-color:#ffffff; color:#000; font-family:Arial, sans-serif; border-radius:10px;">
                        <h2 style="text-align:center; color:#FF5000; margin-bottom:0;">BUREAU SYNDONGO</h2>
                        <p style="text-align:center; margin-top:0;"><b>DAKAR, SÉNÉGAL</b></p>
                        <div style="border-top: 1px solid #000; margin: 10px 0;"></div>
                        <h3 style="text-align:center; text-decoration:underline;">REÇU DE DEMANDE DE TRANSFERT</h3>
                        <table style="width:100%; border:none;">
                            <tr><td style="width:40%"><b>Date/Heure:</b></td><td>{date_val}</td></tr>
                            <tr><td><b>Nom Chauffeur:</b></td><td>{gagnant['NOM']}</td></tr>
                            <tr><td><b>N° Permis:</b></td><td>{p_input}</td></tr>
                            <tr><td><b>Ancien Parc:</b></td><td>{gagnant['PARC']}</td></tr>
                            <tr><td><b>Motif:</b></td><td>{motif}</td></tr>
                        </table>
                        <div style="border-top: 1px solid #000; margin: 10px 0;"></div>
                        <p style="font-size:11px; text-align:center; color:#555;">
                            <i>Ce document atteste l'enregistrement de la demande de mobilité.<br>
                            Sous réserve de validation par la direction SY/NDONGO.</i>
                        </p>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.success("✅ LIBRE : Inscription autorisée.")

    elif menu == "📊 Rapport & Transferts":
        st.header("Analyse & Mobilité")
        t1, t2 = st.tabs(["🔄 Demandes de Transfert", "🆕 Doublons Semaine"])
        with t1:
            if os.path.exists(LOG_TRANSFERTS):
                df_trans = pd.read_csv(LOG_TRANSFERTS, sep=';')
                st.dataframe(df_trans, use_container_width=True)
            else: st.info("Aucun transfert.")
        with t2:
            if not base_globale.empty:
                doublons = base_globale[base_globale.duplicated(subset=['PERMIS'], keep=False)]
                st.dataframe(doublons, use_container_width=True)

    elif menu == "📥 Importation Yango":
        st.header("Mise à jour")
        up_sy = st.file_uploader("Fichier SY", type="csv")
        up_nd = st.file_uploader("Fichier NDONGO", type="csv")
        if st.button("🚀 Synchroniser"):
            if up_sy: pd.read_csv(up_sy, sep=';').to_csv(PATH_SY, index=False, sep=';')
            if up_nd: pd.read_csv(up_nd, sep=';').to_csv(PATH_NDONGO, index=False, sep=';')
            st.success("Bases actualisées !")
            st.rerun()
else:
    st.info("Veuillez entrer votre PIN pour accéder au bureau numérique.")
