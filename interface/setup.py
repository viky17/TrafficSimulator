import streamlit as st 
from streamlit_folium import st_folium
import folium 
from geopy.geocoders import Nominatim 
from geopy.distance import geodesic
import pandas as pd
import engine 

# --- WRAPPER CACHE: Risolve i conflitti di runtime tra Streamlit e i Worker ---
@st.cache_data(show_spinner=False)
def cached_run_simulation(coords, distRange, vehicles, pedestrian, duration, barriers, timeOfDay):
    """Esegue la simulazione e memorizza il risultato nel thread principale."""
    return engine.RunSimulation(coords, distRange, vehicles, pedestrian, duration, barriers, timeOfDay)

@st.cache_data
def getCordinates(address):
    geolocator = Nominatim(user_agent="urban_traffic_sim_v2")
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
            st.session_state.barriers = [] # Reset barriere al cambio citta
            st.rerun()

def show():
    """Funzione principale chiamata da app.py per visualizzare l'interfaccia"""
    
    # Inizializzazione Session State
    if 'coords' not in st.session_state:
        st.session_state.coords = (45.4642, 9.1900)  # Default: Milano
    if 'barriers' not in st.session_state:
        st.session_state.barriers = []
    if 'city_name' not in st.session_state:
        st.session_state['city_name'] = "Milan, Italy"

    # --- SIDEBAR: CONFIGURAZIONE PARAMETRI ---
    with st.sidebar:
        st.header("Settings")
        
        add_vehiclesInput = st.number_input("Vehicles", 1, max_value=50000, value=1000, step=500)
        add_pedestrianInput = st.number_input("Pedestrians", 0, max_value=50000, value=500, step=100)
        add_simulationDuration = st.number_input("Duration (Ticks)", 1, 1000, 150)
        
        time_choice = st.radio(
            "Time Slot:",
            options=["Morning", "Evening"],
            index=0,
            help="Determine the direction of the flow (toward the center in the morning, outward in the evening)"
        )
        
        st.markdown("---")
        st.subheader("Blocks Editor")
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
        
        st.caption(f"Active barriers: {len(st.session_state.barriers)}")
        st.markdown("---")
        
        add_submitButton = st.button("START SIMULATION", type="primary", use_container_width=True)

    # --- INTERFACCIA PRINCIPALE ---
    st.markdown("<h2 style='margin-bottom: 0rem;'>Urban Traffic Simulator</h2>", unsafe_allow_html=True)
    
    col_txt, col_sld = st.columns([2, 2])
    with col_txt:
        st.text_input("City", placeholder="Enter city...", key="city_search_key", on_change=handle_search, label_visibility="collapsed")
    with col_sld:
        selectRange = st.slider("Range (m)", 100, 3000, 500)

    # Rendering Mappa Folium (Stile OpenStreetMap)
    m = folium.Map(location=st.session_state.coords, zoom_start=16, tiles="OpenStreetMap")
    
    # Area di Simulazione (Cerchio Giallo)
    folium.Circle(
        location=st.session_state.coords, 
        radius=selectRange, 
        color="yellow", 
        fill=True, 
        fill_opacity=0.15
    ).add_to(m)
    
    # Marker Barriere (Icona X rossa)
    for b in st.session_state.barriers:
        folium.Marker(location=b, icon=folium.Icon(color='red', icon='times', prefix='fa')).add_to(m)
    
    # Chiave dinamica per forzare l'aggiornamento della mappa solo al cambio coordinate o barriere
    map_key = f"map_{st.session_state.coords[0]}_{st.session_state.coords[1]}_{len(st.session_state.barriers)}"
    st_data = st_folium(m, width='stretch', height=500, key=map_key)

    # Logica interazione Mappa
    if st_data and st_data.get("last_clicked"):
        click_lat = st_data["last_clicked"]["lat"]
        click_lng = st_data["last_clicked"]["lng"]
        click_pos = (click_lat, click_lng)
        
        if edit_mode:
            # Controllo distanza dal centro per validita barriera
            dist = geodesic(st.session_state.coords, click_pos).meters
            if dist <= selectRange:
                if [click_lat, click_lng] not in st.session_state.barriers:
                    st.session_state.barriers.append([click_lat, click_lng])
                    st.rerun()
        else:
            # Spostamento centro simulazione
            if round(click_lat, 4) != round(st.session_state.coords[0], 4):
                st.session_state.coords = (click_lat, click_lng)
                st.rerun()
                
    # --- PROCESSO DI AVVIO SIMULAZIONE ---
    if add_submitButton:
        if 'city_name' not in st.session_state:
            st.session_state['city_name'] = "Custom Area"

        with st.status("Engine Working...", expanded=True) as status:
            st.write("Downloading network data and calculating paths...")
            
            try:
                # Esecuzione tramite wrapper cache
                df_results, roads = cached_run_simulation(
                    coords=st.session_state.coords, 
                    distRange=selectRange, 
                    vehicles=add_vehiclesInput, 
                    pedestrian=add_pedestrianInput, 
                    duration=add_simulationDuration, 
                    barriers=st.session_state.barriers,
                    timeOfDay=time_choice
                )
                
                if df_results is not None and not df_results.empty:
                    st.write(f"Success: Generated {len(df_results)} data points.")
                    
                    # Persistenza dati nel Session State
                    st.session_state['results'] = df_results
                    st.session_state['roads_data'] = roads
                    st.session_state['selectRange'] = selectRange
                    st.session_state['vehiclesNumber'] = add_vehiclesInput
                    st.session_state['pedestrianNumber'] = add_pedestrianInput
                    
                    status.update(label="Simulation Complete", state="complete", expanded=False)
                    st.session_state['page'] = 'simulation'
                    st.rerun()
                else:
                    status.update(label="Simulation Failed", state="error")
                    st.error("No paths could be generated. Try increasing the range or removing barriers.")
            
            except Exception as e:
                status.update(label="Engine Error", state="error")
                st.error(f"Critical error during simulation: {e}")
