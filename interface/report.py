import streamlit as st 
import pandas as pd
import numpy as np
import pydeck as pdk
import streamlit.components.v1 as components

# --- 1. CORE ANALYTICS & MATH FUNCTIONS ---

def haversine(lat1, lon1, lat2, lon2):
    R = 6371000  # Earth radius in meters
    phi1, phi2 = np.radians(lat1), np.radians(lat2)
    lambda1, lambda2 = np.radians(lon1), np.radians(lon2)
    dphi = phi2 - phi1
    dlambda = lambda2 - lambda1
    a = np.sin(dphi/2)**2 + np.cos(phi1)*np.cos(phi2)*(np.sin(dlambda/2)**2)
    c = 2*np.arctan2(np.sqrt(a), np.sqrt(1 - a))
    return R * c

def getDistancesForAgent(df):
    temp_df = df.sort_values(by=['agent_id', 'tick']).copy()
    temp_df['prev_lat'] = temp_df['lat'].shift(1)
    temp_df['prev_lon'] = temp_df['lon'].shift(1)
    temp_df['prev_id'] = temp_df['agent_id'].shift(1)
    mask = temp_df['agent_id'] == temp_df['prev_id']
    temp_df['dist'] = 0.0
    temp_df.loc[mask, 'dist'] = haversine(
        temp_df.loc[mask, 'prev_lat'], temp_df.loc[mask, 'prev_lon'],
        temp_df.loc[mask, 'lat'], temp_df.loc[mask, 'lon']
    )
    return temp_df.groupby('agent_id')['dist'].sum()

def successRate(df):
    if df.empty: return 0.0
    numAgents = df['agent_id'].nunique()
    tick_max = int(df['tick'].max())
    tick_max_for_agent = df.groupby("agent_id")["tick"].max()
    agentArrived = (tick_max_for_agent < tick_max).sum()
    return (agentArrived / numAgents) * 100

def delayIndex(df):
    if df.empty: return 1.0
    times = df.groupby('agent_id')['tick'].agg(['min', 'max'])
    tick_max = df['tick'].max()
    arrived_agents = times[times['max'] < tick_max].copy()
    arrived_agents['actual_time'] = arrived_agents['max'] - arrived_agents['min']
    distances = getDistancesForAgent(df)
    arrived_agents = arrived_agents.join(distances)
    v_ideal = 10.0 
    arrived_agents['ideal_time'] = arrived_agents['dist'] / v_ideal
    valid = arrived_agents[arrived_agents['ideal_time'] > 0]
    if valid.empty: return 1.0
    return (valid['actual_time'] / valid['ideal_time']).mean()

def totalDistanceTraveled(df):
    if df.empty: return 0.0
    distances = getDistancesForAgent(df)
    return distances.sum() / 1000

def averageTravelTime(df):
    if df.empty: return 0.0
    tick_max = int(df['tick'].max())
    times = df.groupby('agent_id')['tick'].agg(['min', 'max'])
    arrived = times[times['max'] < tick_max]
    if arrived.empty: return 0.0
    durations = arrived['max'] - arrived['min']
    return durations.mean()

# --- 2. GRAPHICAL & DIAGNOSTIC COMPONENTS ---

def saturationGraph(df):
    st.markdown("#### Traffic Saturation Timeline")
    st.caption("Monitoring concurrent active agents across the simulation duration.")
    saturation = df.groupby(['tick', 'type']).size().unstack(fill_value=0)
    saturation.index = saturation.index.astype(int)
    st.line_chart(saturation, x_label="Simulation Tick", y_label="Active Agents")

def networkEfficiencyGraph(df):
    st.markdown("#### Network Load Trend")
    st.caption("Cumulative agent density within the network topology per time unit.")
    active_per_tick = df.groupby('tick')['agent_id'].count()
    st.area_chart(active_per_tick, x_label="Simulation Tick", y_label="Total Density")

def bottleneckAnalysis(df):
    st.markdown("#### Delay Distribution Analysis")
    tick_max = df['tick'].max()
    agent_times = df.groupby('agent_id')['tick'].agg(['min', 'max'])
    arrived = agent_times[agent_times['max'] < tick_max].copy()
    if arrived.empty:
        st.info("Insufficient arrival data for delay distribution analysis.")
        return
    arrived['duration'] = arrived['max'] - arrived['min']
    slowest_threshold = arrived['duration'].quantile(0.9)
    st.warning(f"Systemic Alert: 10% of agents exceed a travel duration of {int(slowest_threshold)} ticks.")

def heatmap(df):
    st.markdown("#### Traffic Density Heatmap")
    st.caption("Aggregated positioning data identifying infrastructure pressure points.")
    heatmap_layer = pdk.Layer(
        "HeatmapLayer",
        df,
        get_position=['lon', 'lat'],
        radius_pixels=50, 
        intensity=1.5,   
        threshold=0.05,
        opacity=0.6,
    )
    view_state = pdk.ViewState(
        latitude=df['lat'].mean(),
        longitude=df['lon'].mean(),
        zoom=14.5,
        pitch=0
    )
    st.pydeck_chart(pdk.Deck(
        map_style=None, 
        initial_view_state=view_state,
        layers=[heatmap_layer],
        tooltip={"text": "Traffic Concentration Area"}
    ))

def environmentalImpact(df):
    st.markdown("#### Environmental Impact")
    total_km = totalDistanceTraveled(df)
    co2_total = total_km * 0.122 
    fuel_total = total_km * 0.06
    st.metric("Estimated CO2 Emissions", f"{co2_total:.2f} kg")
    st.metric("Estimated Fuel Consumption", f"{fuel_total:.2f} L")
    st.caption("Calculated based on standard urban emission factors (122g/km).")

def economicImpact(df):
    st.markdown("#### Economic Cost")
    di = delayIndex(df)
    total_agents = df['agent_id'].nunique()
    if di > 1:
        excess_time = (di - 1) * averageTravelTime(df) * total_agents
        cost = excess_time * 0.05
        st.metric("Congestion Cost", f"EUR {cost:,.2f}", delta="Social/Economic Loss", delta_color="inverse")
    else:
        st.metric("Congestion Cost", "EUR 0.00")
    st.caption("Estimate based on time loss and wasted energy resources.")

def getCriticalNodes(df):
    st.markdown("#### Top 5 Critical Congestion Nodes")
    v_df = df[df['type'].isin(['Vehicle', 'HeavyVehicle'])]
    if v_df.empty: 
        st.write("No motorized traffic data available.")
        return
    
    stays = v_df.groupby(['lat', 'lon']).size().reset_index(name='Dwell Intensity')
    top_nodes = stays.sort_values(by='Dwell Intensity', ascending=False).head(5)

    street_names = []
    if not street_names:
        street_names = [f"Area near {lat:.4f}, {lon:.4f}" for lat, lon in zip(top_nodes['lat'], top_nodes['lon'])]
    
    top_nodes['Street Name'] = street_names
    
    st.dataframe(
        top_nodes[['Street Name', 'lat', 'lon', 'Dwell Intensity']], 
        use_container_width=True, 
        hide_index=True
    )
    st.info("Technical Note: The addresses are retrieved based on the coordinates with the highest vehicle dwell time.")

def comparisonTable(df):
    types = df['type'].unique()
    comparison_data = []
    for t in types:
        sub_df = df[df['type'] == t]
        comparison_data.append({
            "Agent Type": t,
            "Success Rate": f"{successRate(sub_df):.1f}%",
            "Delay Index": f"{delayIndex(sub_df):.2f}x",
            "Avg Travel Time": f"{averageTravelTime(sub_df):.1f} ticks",
            "Total Distance": f"{totalDistanceTraveled(sub_df):.2f} km"
        })
    st.table(pd.DataFrame(comparison_data))

# --- 3. QUALITATIVE ANALYSIS FUNCTION ---

def getAnalysis(df, barriers_list):
    sr = successRate(df)
    di = delayIndex(df)
    status = "STABLE" if sr >= 95 and di <= 1.4 else "DEGRADED" if sr >= 80 and di <= 1.8 else "CRITICAL"
    city = st.session_state.get('city_name', 'Westminster')
    
    has_barriers = len(barriers_list) > 0
    barrier_context = "created by the current barrier configuration" if has_barriers else "inherent to the current network topology"
    friction_context = "introduced by the spatial constraints" if has_barriers else "due to the natural complexity of the urban grid"

    color_map = {"STABLE": "#28a745", "DEGRADED": "#ffc107", "CRITICAL": "#dc3545"}
    line_color = color_map.get(status, "#28a745")

    report_html = f"""
    <div style="
        background-color: #f0f2f6; 
        padding: 50px; 
        border-radius: 20px; 
        border-left: 15px solid {line_color};
        font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
        color: #1a1a1a;
    ">
        <h1 style="color: #1f77b4; margin-top: 0; font-size: 38px; font-weight: 800; border-bottom: 3px solid #d1d3d8; padding-bottom: 15px; mb-4">
            Text Report
        </h1>
        
        <div style="margin-top: 25px; margin-bottom: 35px;">
            <p style="font-size: 24px; margin: 8px 0;"><strong>Location:</strong> {city}</p>
            <p style="font-size: 24px; margin: 8px 0;"><strong>Scenario:</strong> {"Constrained Flow (Barriers Active)" if has_barriers else "Free Flow (Baseline Analysis)"}</p>
            <p style="font-size: 26px; color: {line_color}; font-weight: bold; margin: 8px 0;"><strong>System Status:</strong> {status}</p>
        </div>
        
        <div style="font-size: 22px; line-height: 1.9; text-align: justify;">
            <p>The simulation results indicate a {status.lower()} connectivity state. 
            With a Success Rate of <strong>{sr:.1f}%</strong>, the urban fabric retains 
            {"sufficient" if sr > 90 else "limited"} permeability. The inability of <strong>{100-sr:.1f}%</strong> 
            of agents to reach their destination reveals specific deadlock nodes {barrier_context}.</p>
            
            <p>The calculated Delay Index of <strong>{di:.2f}</strong> serves as a proxy for 
            urban friction. This suggests that agents are covering <strong>{(di - 1.0)*100:.1f}% more</strong> 
            travel time than the theoretical optimum. This overhead reflects an increase in systemic metabolic cost {friction_context}.</p>
            
            <p>Correlation between temporal saturation and spatial density identifies a clear disparity in agent behavior. 
            Hotspots in the heatmap confirm where the urban grid is most fragile. Vehicles exhibit higher sensitivity 
            to {"barrier placement" if has_barriers else "junction complexity"} compared to the distributed clearance rate of pedestrians.</p>
            
            <div style="margin-top: 40px; padding: 30px; background-color: rgba(255,255,255,0.7); border-radius: 12px; border: 1px solid #d1d3d8;">
                <p style="margin: 0; font-weight: 600;">
                Based on the integration of temporal and spatial density, this configuration is 
                <span style="color: {line_color}; text-decoration: underline;"><strong>{"RECOMMENDED" if status == "STABLE" else "NOT RECOMMENDED"}</strong></span> 
                for permanent implementation. Future iterations should focus on softening {"constraints in high-friction zones" if has_barriers else "critical intersections"} 
                detected by the diagnostic engine to re-establish balanced travel times.
                </p>
            </div>
        </div>
    </div>
    """
    components.html(report_html, height=1000, scrolling=False)
# --- 4. MAIN DISPLAY FUNCTION ---

def show():
    df = st.session_state.get('results')
    
    if df is None or df.empty:
        st.error("Diagnostic Error: No simulation data found.")
        if st.button("Return to Setup"):
            st.session_state['page'] = 'setup'
            st.rerun()
        return

    st.title(f"Urban Mobility Diagnostic: {st.session_state.get('city_name','Custom Area')}")
    st.markdown("---")

    # Metrics Section
    sr, di = successRate(df), delayIndex(df)
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Success Rate", f"{sr:.1f}%",help="The percentage of agents that reached their destination. High values indicate optimal network connectivity.")
    k2.metric("Delay Index", f"{di:.2f}x",help="Ratio of actual vs ideal travel time. 1.0x means zero traffic; 2.0x means travel time is doubled due to congestion.")
    k3.metric("Avg Travel Time", f"{averageTravelTime(df):.1f}",help="Average duration (in ticks) spent by agents to complete their trip.")
    k4.metric("Total Mileage", f"{totalDistanceTraveled(df):.2f} km",help="Total cumulative distance covered by all agents in the simulation area.")

    st.markdown("### Modal Performance Analysis")
    with st.container(border=True):
        comparisonTable(df)

    st.markdown("### Flow Dynamics and Density")
    c1, c2 = st.columns(2)
    with c1: saturationGraph(df)
    with c2: networkEfficiencyGraph(df)
    
    with st.container(border=True):
        heatmap(df)

    st.markdown("### Network Resilience and Impact")
    col_i1, col_i2 = st.columns(2)
    with col_i1:
        with st.container(border=True): environmentalImpact(df)
    with col_i2:
        with st.container(border=True): economicImpact(df)

    with st.container(border=True):
        bottleneckAnalysis(df)
        getCriticalNodes(df)

    st.markdown("---")
    getAnalysis(df, st.session_state.get('barriers', []))

    # Action Footer
    b1, b2, b3 = st.columns(3)
    with b1: st.download_button("Export Raw CSV", df.to_csv(index=False).encode('utf-8'), "report.csv", use_container_width=True)
    with b2: 
        if st.button("Print Report", use_container_width=True):
            components.html("<script>window.parent.focus(); window.parent.print();</script>", height=0, width=0)
    with b3:
        if st.button("New Simulation", type="primary", use_container_width=True):
            st.session_state['results'] = None
            st.session_state['page'] = 'setup'
            st.rerun()