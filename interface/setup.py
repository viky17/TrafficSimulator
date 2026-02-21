import streamlit as st 
from streamlit_folium import st_folium
import folium 
from geopy.geocoders import Nominatim 
from geopy.distance import geodesic
from engine import RunSimulation
import pandas as pd

@st.cache_data
def getCordinates(address):
    geolocator = Nominatim(user_agent="my_traffic_sim_app")
    try:
        location = geolocator.geocode(address)
        if location:
            return (location.latitude, location.longitude)
        return None
    except Exception:
        return None

def handle_search():
    query = st.session_state.city_search_key
    if query:
        new_pos = getCordinates(query)
        if new_pos:
            st.session_state.coords = new_pos
            st.session_state['city_name'] = query.title()
            st.rerun()

def show():
    if 'coords' not in st.session_state:
        st.session_state.coords = (51.509865, -0.118092)
    if 'barriers' not in st.session_state:
        st.session_state.barriers = []

    # Sidebar UI
    with st.sidebar:
        st.header("Settings")
        
        # 1. Parametri sempre presenti: non spariranno mai
        add_vehiclesInput = st.number_input("Vehicles", 1, max_value=50000, value=1000, step=500)
        add_pedestrianInput = st.number_input("Pedestrians", 0, max_value=50000, value=500, step=100)
        add_simulationDuration = st.number_input("Duration (Ticks)", 1, 1000, 150)
        
        time_choice = st.sidebar.radio(
            "Time Slot:",
            options=["Morning", "Evening"],
            index=0, # Default su Morning
            help="Determine the direction of the flow (toward the center in the morning, outward in the evening)"
        )
        st.markdown("---")
        
        # 2. Editor dei blocchi come sezione dedicata
        st.subheader("Blocks Editor")
        # Un toggle invece di un radio switch pesante
        edit_mode = st.toggle("Enable Click-to-Block", value=False, help="Enable this to add barriers by clicking on the map")
        
        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            if st.button("Undo", use_container_width=True) and st.session_state.barriers:
                st.session_state.barriers.pop()
                st.rerun()
        with col_btn2:
            if st.button("Clear", use_container_width=True):
                st.session_state.barriers = []
                st.rerun()
        
        # Mostra il contatore dei blocchi attivi
        st.caption(f"Active barriers: {len(st.session_state.barriers)}")
        add_submitButton = st.button(" START SIMULATION", type="primary", use_container_width=True)

    # Main UI
    st.markdown("<h2 style='margin-bottom: 0rem;'>Urban Traffic Simulator</h2>", unsafe_allow_html=True)
    
    col_txt, col_sld = st.columns([2, 2])
    with col_txt:
        st.text_input("City", placeholder="Enter city...", key="city_search_key", on_change=handle_search, label_visibility="collapsed")
    with col_sld:
        selectRange = st.slider("Range (m)", 100, 3000, 500)

    # Map Rendering
    m = folium.Map(location=st.session_state.coords, zoom_start=16)
    folium.Circle(location=st.session_state.coords, radius=selectRange, color="yellow", fill=True).add_to(m)
    for b in st.session_state.barriers:
        folium.Marker(location=b, icon=folium.Icon(color='red', icon='times', prefix='fa')).add_to(m)
    
    map_key = f"map_{st.session_state.coords[0]}_{st.session_state.coords[1]}"
    st_data = st_folium(m, use_container_width=True, height=500, key=map_key)

    # Map Logic
    if st_data and st_data.get("last_clicked"):
        click_lat = st_data["last_clicked"]["lat"]
        click_lng = st_data["last_clicked"]["lng"]
        if edit_mode:
            # Modalità Blocchi: calcola distanza dal centro
            dist = geodesic(st.session_state.coords, (click_lat, click_lng)).meters
            if dist <= selectRange:
                # Evita duplicati
                if [click_lat, click_lng] not in st.session_state.barriers:
                    st.session_state.barriers.append([click_lat, click_lng])
                    st.rerun()
        else:
            # Modalità Navigazione: sposta il centro
            if round(click_lat, 4) != round(st.session_state.coords[0], 4):
                st.session_state.coords = (click_lat, click_lng)
                st.rerun()
                
    # --- SIMULATION TRIGGER ---
    if add_submitButton:
        # Inizializzazione city_name se mancante
        if 'city_name' not in st.session_state:
            st.session_state['city_name'] = "Custom Area"

        # Esecuzione Engine
        with st.status(" Engine Working...", expanded=True) as status:
            st.write("Downloading OSM data and calculating paths...")
            try:
                df_results, roads = RunSimulation(
                    coords=st.session_state.coords, 
                    distRange=selectRange, 
                    vehicles=add_vehiclesInput, 
                    pedestrian=add_pedestrianInput, 
                    duration=add_simulationDuration, 
                    barriers=st.session_state.barriers,
                    timeOfDay="Morning" # Assicurati che il nome sia timeOfDay
                )
                if df_results is not None:
                    st.write(f" Data generated: {len(df_results)} rows.")
                
                status.update(label="Simulation Complete!", state="complete", expanded=False)
            except Exception as e:
                st.error(f"Engine Error: {e}")
                return

        if df_results is not None and not df_results.empty:
            # Salvataggio dati nel Session State
            st.session_state['results'] = df_results
            st.session_state['roads_data'] = roads
            st.session_state['selectRange'] = selectRange
            st.session_state['vehiclesNumber'] = add_vehiclesInput
            st.session_state['pedestrianNumber'] = add_pedestrianInput
            
            # CAMBIO PAGINA
            st.session_state['page'] = 'simulation'
            
            # Notifica a video prima del rerun
            st.toast("Switching to Simulation View...")
            
            # RERUN FORZATO
            st.rerun()
        else:
            st.error("The simulation returned no data. Try increasing the range or changing location.")