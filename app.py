import streamlit as st
import pandas as pd
import os
from datetime import datetime, date
import plotly.express as px

# --- CONFIGURATION ---
st.set_page_config(page_title="SyNdongo Central Sentinel", layout="wide", page_icon="🛡️")

SAVE_DIR = "donnees_controle"
if not os.path.exists(SAVE_DIR): os.makedirs(SAVE_DIR)

# Chemins vers les fichiers
PATH_SY = os.path.join(SAVE_DIR, "base_sy.csv")
PATH_NDONGO = os.path.join(SAVE_DIR, "base_ndongo.csv")
PATH_TEMP_INSCRIPTIONS = os.path.join(SAVE_DIR, "inscriptions_semaine.csv")
LOG_MOUVEMENTS = os.path.join(SAVE_DIR, "log_mouvements.csv")

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
    cols = ['NOM', 'PERMIS', 'AGENT_RESP', 'COURSES', 'DERNIERE_ACT', 'DATE_DEBUT', 'PARC']
    if df is None or df.empty: return pd.DataFrame(columns=cols)
    df.columns = df.columns.str.strip().str.replace('"', '').str.replace("'", "")
    
    c_permis = trouver_colonne(df, ["Permis"])
    c_nom = trouver_colonne(df, ["Nom complet", "Nom"])
    c_agent = trouver_colonne(df, ["Employé responsable", "Agent"])
    c_courses = trouver_colonne(df, ["Commandes terminées"])
    c_last = trouver_colonne(df, ["Date de la dernière commande"])
    c_debut = trouver_colonne(df, ["Date de début"])
    
    df_std = pd.DataFrame()
    df_std['NOM'] = df[c_nom] if c_nom else "Inconnu"
    df_std['PERMIS'] = df[c_permis].astype(str).str.strip() if c_permis else "N/A"
    df_std['AGENT_RESP'] = df[c_agent].fillna("Inconnu") if c_agent else "Inconnu"
    df_std['COURSES'] = pd.to_numeric(df[c_courses], errors='coerce').fillna(0) if c_courses else 0
    df_std['DERNIERE_ACT'] = pd.to_datetime(df[c_last], errors='coerce') if c_last else pd.NaT
    df_std['DATE_DEBUT'] = pd.to_datetime(df[c_debut], errors='coerce') if c_debut else pd.NaT
    df_std['PARC'] = label_parc
    return df_std[cols]

def charger_base_complete():
    sy = pd.read_csv(PATH_SY, sep=';') if os.path.exists(PATH_SY) else None
    nd = pd.read_csv(PATH_NDONGO, sep=';') if os.path.exists(PATH_NDONGO) else None
    df_csv = pd.concat([standardiser_donnees(sy, "SY"), standardiser_donnees(nd, "NDONGO")], ignore_index=True)
    
    if os.path.exists(PATH_TEMP_INSCRIPTIONS):
        df_temp = pd.read_csv(PATH_TEMP_INSCRIPTIONS, sep=';', dtype={'PERMIS': str})
        for col in ['DERNIERE_ACT', 'DATE_DEBUT']:
            if col in df_temp.columns: df_temp[col] = pd.to_datetime(df_temp[col], errors='coerce')
        df_csv = pd.concat([df_csv, df_temp], ignore_index=True)
    return df_csv

def enregistrer_action(agent, permis, nom, source, cible, motif, type_act):
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_data = {
        "DATE": [datetime.now().strftime("%Y-%m-%d")], "HEURE": [datetime.now().strftime("%H:%M")],
        "AGENT": [agent], "CHAUFFEUR": [nom], "PERMIS": [permis],
        "SOURCE": [source], "CIBLE": [cible], "MOTIF": [motif], "TYPE": [type_act]
    }
    pd.DataFrame(log_data).to_csv(LOG_MOUVEMENTS, mode='a', index=False, sep=';', header=not os.path.exists(LOG_MOUVEMENTS), encoding='utf-8-sig')
    
    if type_act == "INSCRIPTION":
        temp_data = {
            "NOM": [nom], "PERMIS": [str(permis)], "AGENT_RESP": [agent], 
            "COURSES": [0], "DERNIERE_ACT": [now_str], "DATE_DEBUT": [now_str], "PARC": [cible]
        }
        pd.DataFrame(temp_data).to_csv(PATH_TEMP_INSCRIPTIONS, mode='a', index=False, sep=';', header=not os.path.exists(PATH_TEMP_INSCRIPTIONS), encoding='utf-8-sig')

# --- CONNEXION ---
st.sidebar.title("🏢 Bureau SyNdongo")
agent_user = st.sidebar.selectbox("Identifiant", list(DB_ACCES.keys()))
pin = st.sidebar.text_input("Code PIN", type="password")
btn_connect = st.sidebar.button("Se Connecter 🔓")

if "auth" not in st.session_state: st.session_state.auth = False

if btn_connect:
    if pin == DB_ACCES.get(agent_user):
        st.session_state.auth = True
        st.session_state.user = agent_user
    else: st.sidebar.error("PIN Incorrect")

if st.session_state.auth:
    base_globale = charger_base_complete()
    menu_opt = ["🔍 Recherche & Scan"]
    if st.session_state.user in ADMINS_AUTORISES: menu_opt += ["📊 Performance & Flux", "📥 Importation Yango"]
    menu = st.sidebar.radio("Navigation", menu_opt)

    if menu == "🔍 Recherche & Scan":
        st.header("🔍 Contrôle des Doublons")
        p_input = st.text_input("Numéro de Permis")
        if st.button("Lancer la Recherche 🚀"):
            if p_input:
                p_clean = str(p_input).strip()
                match = base_globale[base_globale['PERMIS'] == p_clean] if not base_globale.empty else pd.DataFrame()
                if not match.empty:
                    r = match.iloc[-1]
                    st.error(f"⚠️ EXISTANT SUR : {r['PARC']}")
                    st.warning(f"Responsable: {r['AGENT_RESP']} | Courses: {int(r['COURSES'])}")
                    st.divider()
                    motif = st.selectbox("Raison du transfert", ["Décision Propriétaire", "Changement Véhicule", "Souhait Chauffeur"])
                    if st.button(f"Valider Transfert ✅"):
                        enregistrer_action(st.session_state.user, p_clean, r['NOM'], r['PARC'], "TRANSFERT", motif, "TRANSFERT")
                        st.success("Transfert Logué")
                else:
                    st.success("✅ LIBRE : Ce chauffeur peut être recruté.")
                    with st.expander("Enregistrer Inscription"):
                        p_cible = st.radio("Parc cible", ["SY", "NDONGO"], horizontal=True)
                        if st.button("Confirmer Inscription"):
                            enregistrer_action(st.session_state.user, p_clean, "NOUVEAU", "AUCUN", p_cible, "Recrutement", "INSCRIPTION")
                            st.rerun()

    elif menu == "📊 Performance & Flux":
        st.header("📊 Analyses Avancées")
        d_range = st.date_input("Période", [date.today(), date.today()])
        
        t1, t2, t3 = st.tabs(["🏆 Meilleur Agent", "📉 Analyse de Pêche", "📋 Journal"])
        
        with t1:
            if os.path.exists(LOG_MOUVEMENTS):
                df_log = pd.read_csv(LOG_MOUVEMENTS, sep=';')
                df_log['DATE'] = pd.to_datetime(df_log['DATE']).dt.date
                df_f = df_log[(df_log['DATE'] >= d_range[0]) & (df_log['DATE'] <= d_range[1])]
                
                # Calcul robuste de la performance
                df_ins = df_f[df_f['TYPE'] == 'INSCRIPTION']['AGENT'].value_counts().reset_index()
                df_ins.columns = ['Agent', 'Inscriptions']
                
                df_doub = df_f[df_f['TYPE'] == 'TRANSFERT']['AGENT'].value_counts().reset_index()
                df_doub.columns = ['Agent', 'Doublons']
                
                df_perf = pd.merge(df_ins, df_doub, on='Agent', how='outer').fillna(0)
                df_perf['Score'] = df_perf['Inscriptions'] - df_perf['Doublons']
                df_perf = df_perf.sort_values(by='Score', ascending=False).reset_index(drop=True)
                
                if not df_perf.empty:
                    for i, row in df_perf.head(3).iterrows():
                        medal = "🥇" if i == 0 else "🥈" if i == 1 else "🥉"
                        st.info(f"{medal} **{row['Agent']}** | Score: {int(row['Score'])} (✅ {int(row['Inscriptions'])} inscr. / ❌ {int(row['Doublons'])} doublons)")
                    st.table(df_perf)
                else: st.info("Aucune activité.")

        with t2:
            st.subheader("Qui récupère le plus de chauffeurs ?")
            if os.path.exists(PATH_SY) and os.path.exists(PATH_NDONGO):
                sy_b = standardiser_donnees(pd.read_csv(PATH_SY, sep=';'), "SY")
                nd_b = standardiser_donnees(pd.read_csv(PATH_NDONGO, sep=';'), "NDONGO")
                common = set(sy_b['PERMIS']).intersection(set(nd_b['PERMIS']))
                if common:
                    m = pd.merge(sy_b[sy_b['PERMIS'].isin(common)], nd_b[nd_b['PERMIS'].isin(common)], on='PERMIS', suffixes=('_SY', '_ND'))
                    m['DATE_MAX'] = m[['DATE_DEBUT_SY', 'DATE_DEBUT_ND']].max(axis=1)
                    m_f = m[(m['DATE_MAX'].dt.date >= d_range[0]) & (m['DATE_MAX'].dt.date <= d_range[1])]
                    sy_p = len(m_f[m_f['DATE_DEBUT_SY'] > m_f['DATE_DEBUT_ND']])
                    nd_p = len(m_f[m_f['DATE_DEBUT_ND'] > m_f['DATE_DEBUT_SY']])
                    c1, c2 = st.columns(2)
                    c1.metric("SY a pris à NDONGO", sy_p)
                    c2.metric("NDONGO a pris à SY", nd_p)
                    st.plotly_chart(px.bar(x=["SY Recruteur", "NDONGO Recruteur"], y=[sy_p, nd_p], color=["SY", "NDONGO"], title="Flux de recrutement concurrentiel"))
            else: st.warning("Veuillez importer les fichiers CSV.")

        with t3:
            if os.path.exists(LOG_MOUVEMENTS): st.dataframe(pd.read_csv(LOG_MOUVEMENTS, sep=';'), use_container_width=True)

    elif menu == "📥 Importation Yango":
        st.header("📥 Mise à jour Hebdomadaire")
        f_sy = st.file_uploader("Fichier SY", type="csv")
        f_nd = st.file_uploader("Fichier NDONGO", type="csv")
        if st.button("🚀 Synchroniser"):
            if f_sy: pd.read_csv(f_sy, sep=';').to_csv(PATH_SY, index=False, sep=';')
            if f_nd: pd.read_csv(f_nd, sep=';').to_csv(PATH_NDONGO, index=False, sep=';')
            if os.path.exists(PATH_TEMP_INSCRIPTIONS): os.remove(PATH_TEMP_INSCRIPTIONS)
            st.success("Bases synchronisées."); st.rerun()
else:
    st.info("Saisissez votre PIN et cliquez sur 'Se Connecter'.")
