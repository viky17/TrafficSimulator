from interface import setup,simulation,report
import streamlit as st 

st.set_page_config(layout="wide", page_title="Urban Mobility Simulator")
st.markdown("""
    <style>

    /* Nasconde la barra superiore (Header) */
    header {visibility: hidden;}
    
    /* Nasconde il menu a tre linee in alto a destra */
    #MainMenu {visibility: hidden;}
    
    /* Nasconde il footer "Made with Streamlit" (opzionale) */
    footer {visibility: hidden;}
    
    /* Rimuove lo spazio vuoto lasciato dall'header per alzare tutto il contenuto */
    .stAppDeployButton {
        display: none;
    }
    /* Riduciamo il codice CSS all'essenziale */
    .stApp {
        background-color: #f8f9fa;
    }
    
    .block-container {
        padding-top: 1rem;
        margin-top: -1rem;
    }

    /* Sidebar Bianca pulita */
    [data-testid="stSidebar"] {
        background-color: #ffffff;
        border-right: 1px solid #eeeeee;
    }

    /* Bottone Start Simulation: Rosso Streamlit */
    div.stButton > button {
        background-color: #FF4B4B !important; /* Il rosso originale di Streamlit */
        color: white !important;
        border: none !important;
        font-weight: bold;
        width: 100%;
        border-radius: 8px;
    }
    
    /* Metriche: Rosso per i valori */
    [data-testid="stMetricValue"] {
        color: #FF4B4B !important;
    }

    /* Slider e Input useranno ora il tema nativo rosso senza sforzo */
    </style>
    """, unsafe_allow_html=True)



if 'page' not in st.session_state:
    st.session_state['page'] = 'setup'

try:
    if st.session_state['page'] == 'setup':
        setup.show()
    elif st.session_state['page'] == 'simulation':
        simulation.show()
    elif st.session_state['page'] == 'report':
        report.show()
except Exception as e:
    st.error(f" ERRORE RILEVATO: {e}")
    st.write("Dettaglio tecnico dell'errore:")
    st.exception(e) # Questo ti mostra esattamente in quale riga di quale file c'è il problema

