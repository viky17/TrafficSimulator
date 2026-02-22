import streamlit as st 
import pydeck as pdk

# --- MAPPATURA COLORI RGB ---
def get_color(type_str):
    if type_str == 'Vehicle':
        return [49, 134, 204, 200]    # Blu (Auto)
    elif type_str == 'HeavyVehicle':
        return [253, 126, 20, 230]    # Arancione (Camion)
    elif type_str == 'Pedestrian':
        return [40, 167, 69, 200]     # Verde (Pedoni)
    return [200, 200, 200, 200]       # Grigio (Default)


def show():
    df = st.session_state.get('results')
    
    if df is None or df.empty:
        st.error("The simulation did not produce any results. Check the radius or the position of the barriers.")
        if st.button("Torna al Setup"):
            st.session_state['page'] = 'setup'
            st.rerun()
        return
    else:
        tick_max = int(df['tick'].max())
        
        col_slider, col_btn = st.columns([4, 1])

        with col_slider:
            st.markdown(f"<p style='margin-bottom: -35px; font-size: 0.8rem; opacity: 0.7;'>Simulation Timeline (Tick: {currentTick if 'currentTick' in locals() else 0})</p>", unsafe_allow_html=True)
            
            currentTick = st.select_slider(
                "Simulation Timeline",
                options=range(tick_max + 1),
                label_visibility="hidden"
            )

        with col_btn:
            st.markdown("<div style='padding-top: 25px;'></div>", unsafe_allow_html=True)
            if st.button("Generate Report", width='stretch', type="primary"):
                st.session_state['page']='report'
                st.rerun()
                
        # Trova tutti i tick effettivamente presenti nel database
        ticks_presenti = df['tick'].unique()
        # Trova il tick più vicino (uguale o precedente) a quello selezionato dallo slider
        # Questo evita che la mappa sia vuota nei tick "saltati" dal downsampling
        tick_effettivo = max([t for t in ticks_presenti if t <= currentTick], default=0)
        # Filtra i dati usando il tick_effettivo invece di quello dello slider
        data_filtrata = df[df['tick'] == tick_effettivo]
        activeAgents = len(data_filtrata)
        trafficState = round((currentTick / tick_max) * 100) if tick_max > 0 else 0

        with st.sidebar:
            st.subheader("Configuration Summary")
            c1, c2 = st.columns(2)
            with c1:
                st.metric("Range", f"{st.session_state.get('selectRange', 0)}m")
                st.metric("Vehicles", st.session_state.get('vehiclesNumber', 0))
            with c2:
                st.metric("City", st.session_state.get('city_name',0))
                st.metric("Pedestrian", st.session_state.get('pedestrianNumber', 0))

            st.subheader("Simulation Monitoring")
            st.metric("Active agents", activeAgents) 
            st.metric("Completetion percentage", f"{trafficState}%")
            st.metric("Current Tick", currentTick)
            st.subheader("Legends")
            st.markdown("""
                <div style="font-size: 0.9rem; margin-bottom: 10px;">
                    <span style="color: #3186cc;">●</span> Vehicles &nbsp;&nbsp;
                    <span style="color: #fd7e14;">●</span> Heavy Vehicles &nbsp;&nbsp;
                    <span style="color: #28a745;">●</span> Pedestrian &nbsp;&nbsp;
                    <span style="color: #FF0000;">✖</span> Barriers
                </div>
            """, unsafe_allow_html=True)
            showVehicles = st.checkbox("Show Vehicles", value=True)
            showTrucks = st.checkbox("Show Heavy Vehicles", value=True)
            showPedestrian = st.checkbox("Show Pedestrians", value=True)
            showBarriers = st.checkbox("Show Barriers", value=True)
        
        excluded_types = []
        if not showVehicles: excluded_types.append('Vehicle')
        if not showTrucks: excluded_types.append('HeavyVehicle')
        if not showPedestrian: excluded_types.append('Pedestrian')
        data_filtrata = data_filtrata[~data_filtrata['type'].isin(excluded_types)].copy()
        data_filtrata['color'] = data_filtrata['type'].apply(get_color)

        view_state = pdk.ViewState(
            latitude=st.session_state.coords[0],
            longitude=st.session_state.coords[1],
            zoom=15,
            pitch=0
        )

        
        road_layer = pdk.Layer(
            "PathLayer",
            st.session_state.get('roads_data', []),
            get_path="path",
            get_color=[180, 180, 180, 150],
            width_min_pixels=1
        )

        agent_layer = pdk.Layer(
            "ScatterplotLayer",
            data_filtrata,
            get_position='[lon, lat]',
            get_color='color',
            get_radius=8,
            pickable=True
        )

        layers_to_show = [road_layer]

        if showBarriers and 'barriers' in st.session_state:
            ICON_URL = "https://img.icons8.com/ios-filled/50/000000/cancel.png" 
            
            barriers_data = [{
                "lat": b[0], 
                "lon": b[1],
                "icon_data": {
                    "url": ICON_URL,
                    "width": 128,
                    "height": 128,
                    "anchorY": 128
                }
            } for b in st.session_state.barriers]

            barrier_layer = pdk.Layer(
                "IconLayer",
                barriers_data,
                get_icon="icon_data",
                get_position='[lon, lat]',
                get_size=4,
                size_scale=10,
                get_color=[255, 165, 0], 
                pickable=True,
            )
            layers_to_show.append(barrier_layer)
                
        layers_to_show.append(agent_layer)

        # 6. RENDERING FINALE
        st.pydeck_chart(pdk.Deck(
            layers=layers_to_show,
            initial_view_state=view_state,
            map_style=None,
            tooltip={"text": "ID: {agent_id}\nType: {type}"}
        ), height=800)

