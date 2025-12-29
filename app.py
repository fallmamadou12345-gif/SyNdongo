import streamlit as st
import pandas as pd
import os
from datetime import datetime, date

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

# --- FONCTIONS TECHNIQUES ---
def trouver_colonne(df, mots_cles):
    for col in df.columns:
        if any(mot.lower() in col.lower() for mot in mots_cles): return col
    return None

def standardiser_donnees(df, label_parc):
    cols = ['NOM', 'PERMIS', 'AGENT_RESP', 'COURSES', 'DATE_DERNIERE_COMMANDE', 'PARC']
    if df is None or df.empty: return pd.DataFrame(columns=cols)
    df.columns = df.columns.str.strip().str.replace('"', '').str.replace("'", "")
    
    c_permis = trouver_colonne(df, ["Permis"])
    c_nom = trouver_colonne(df, ["Nom complet", "Nom"])
    c_agent = trouver_colonne(df, ["Employé responsable", "Agent"])
    c_courses = trouver_colonne(df, ["Commandes terminées"])
    c_date = trouver_colonne(df, ["Date de la dernière commande"])
    
    df_std = pd.DataFrame()
    df_std['NOM'] = df[c_nom] if c_nom else "Inconnu"
    df_std['PERMIS'] = df[c_permis].astype(str).str.strip() if c_permis else "N/A"
    df_std['AGENT_RESP'] = df[c_agent].fillna("Non assigné") if c_agent else "Non assigné"
    df_std['COURSES'] = pd.to_numeric(df[c_courses], errors='coerce').fillna(0) if c_courses else 0
    # Conversion de la date pour le filtrage
    df_std['DATE_DERNIERE_COMMANDE'] = pd.to_datetime(df[c_date], errors='coerce')
    df_std['PARC'] = label_parc
    return df_std[cols]

def charger_base_complete():
    sy = pd.read_csv(PATH_SY, sep=';') if os.path.exists(PATH_SY) else None
    nd = pd.read_csv(PATH_NDONGO, sep=';') if os.path.exists(PATH_NDONGO) else None
    df_csv = pd.concat([standardiser_donnees(sy, "SY"), standardiser_donnees(nd, "NDONGO")], ignore_index=True)
    
    if os.path.exists(PATH_TEMP_INSCRIPTIONS):
        df_temp = pd.read_csv(PATH_TEMP_INSCRIPTIONS, sep=';', dtype={'PERMIS': str})
        df_temp['DATE_DERNIERE_COMMANDE'] = pd.to_datetime(df_temp['DATE_INSCRIPTION'], errors='coerce')
        df_csv = pd.concat([df_csv, df_temp], ignore_index=True)
    return df_csv

def enregistrer_inscription(agent, permis, parc):
    nouveau = pd.DataFrame([{
        "NOM": "INSCRIPTION_TEMP",
        "PERMIS": str(permis).strip(),
        "AGENT_RESP": agent,
        "COURSES": 0,
        "DATE_INSCRIPTION": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "PARC": parc
    }])
    header = not os.path.exists(PATH_TEMP_INSCRIPTIONS)
    nouveau.to_csv(PATH_TEMP_INSCRIPTIONS, mode='a', index=False, sep=';', header=header, encoding='utf-8-sig')

# --- INTERFACE ---
st.sidebar.title("🏢 Bureau SyNdongo")
agent_user = st.sidebar.selectbox("Agent", list(DB_ACCES.keys()))
code_pin = st.sidebar.text_input("PIN", type="password")

if code_pin == DB_ACCES.get(agent_user):
    base_globale = charger_base_complete()
    menu_options = ["🔍 Scanner", "📊 Rapport Filtré", "📥 Importation Yango"] if agent_user in ADMINS_AUTORISES else ["🔍 Scanner"]
    menu = st.sidebar.radio("Navigation", menu_options)

    if menu == "🔍 Scanner":
        st.header("🛡️ Contrôle d'Inscription")
        p_input = st.text_input("Tapez le numéro de Permis")
        if p_input:
            p_clean = str(p_input).strip()
            match = base_globale[base_globale['PERMIS'] == p_clean] if not base_globale.empty else pd.DataFrame()
            if not match.empty:
                st.error(f"🚨 DOUBLON DÉTECTÉ")
                r = match.iloc[-1]
                st.warning(f"📍 Ce permis est déjà chez **{r['PARC']}**")
            else:
                st.success(f"✅ LIBRE")
                st.info("### 💾 ENREGISTREMENT IMMÉDIAT")
                with st.container(border=True):
                    parc_choisi = st.radio("Inscrire dans quel parc ?", ["SY", "NDONGO"], horizontal=True)
                    if st.button("CONFIRMER L'INSCRIPTION"):
                        enregistrer_inscription(agent_user, p_clean, parc_choisi)
                        st.success(f"Permis {p_clean} bloqué !")
                        st.rerun()

    elif menu == "📊 Rapport Filtré":
        st.header("Analyse des Doublons par Période")
        
        # --- FILTRE DE DATE ---
        col1, col2 = st.columns(2)
        with col1:
            date_debut = st.date_input("Date de début", date(2025, 1, 1))
        with col2:
            date_fin = st.date_input("Date de fin", date.today())

        if not base_globale.empty:
            # Filtrage des données selon la date de dernière commande ou d'inscription
            mask = (base_globale['DATE_DERNIERE_COMMANDE'].dt.date >= date_debut) & \
                   (base_globale['DATE_DERNIERE_COMMANDE'].dt.date <= date_fin)
            df_filtre = base_globale[mask]
            
            # Recherche des doublons dans cette période
            doublons = df_filtre[df_filtre.duplicated(subset=['PERMIS'], keep=False)]
            
            st.metric("Doublons sur la période", len(doublons)//2)
            st.dataframe(doublons.sort_values(by='DATE_DERNIERE_COMMANDE', ascending=False), use_container_width=True)
            
            st.download_button("📥 Télécharger ce rapport (CSV)", 
                               doublons.to_csv(index=False, sep=';').encode('utf-8'), 
                               f"doublons_{date_debut}_{date_fin}.csv")

    elif menu == "📥 Importation Yango":
        st.header("Mise à jour Hebdomadaire")
        up_sy = st.file_uploader("Fichier SY (CSV)", type="csv")
        up_nd = st.file_uploader("Fichier NDONGO (CSV)", type="csv")
        if st.button("🚀 SYNCHRONISER"):
            if up_sy: pd.read_csv(up_sy, sep=';').to_csv(PATH_SY, index=False, sep=';')
            if up_nd: pd.read_csv(up_nd, sep=';').to_csv(PATH_NDONGO, index=False, sep=';')
            if os.path.exists(PATH_TEMP_INSCRIPTIONS): os.remove(PATH_TEMP_INSCRIPTIONS)
            st.success("Bases synchronisées !")
            st.rerun()
else:
    st.info("Entrez votre PIN.")
