import osmnx as ox
import pandas as pd
import random
import networkx as nx
import os
import numpy as np
from scipy.spatial import KDTree
from concurrent.futures import ThreadPoolExecutor

# Configurazione OSMnx
ox.settings.timeout = 180
ox.settings.use_cache = True

if not os.path.exists("cache"):
    os.makedirs("cache")

# --- CLASSES ---

class Agent():
    def __init__(self, agentId, path, pathCoords, typeStr):
        self.id = agentId
        self.path = path  
        self.pathCoords = pathCoords 
        self.type = typeStr
        self.active = True if path and len(path) > 1 else False
        self.currentStep = 0
        self.currentNode = path[0] if self.active else None
        self.stuckTicks = 0
        self.ticksAlive = 0
        self.isHeavy = (typeStr == 'HeavyVehicle')

    def step(self):
        if not self.active: return
        if self.currentStep < len(self.path) - 1:
            self.currentStep += 1
            self.currentNode = self.path[self.currentStep]
            if self.currentStep == len(self.path) - 1:
                self.active = False
        else:
            self.active = False

# --- WORKER PER PATHFINDING ---

def ComputePathWorker(args):
    graph, agentId, origin, target, weightType, typeStr = args
    try:
        if nx.has_path(graph, origin, target):
            path = ox.shortest_path(graph, origin, target, weight=weightType)
            if path:
                coords = [(round(graph.nodes[n]['y'], 5), round(graph.nodes[n]['x'], 5)) for n in path]
                return {'id': agentId, 'path': path, 'coords': coords, 'type': typeStr}
    except:
        return None
    return None

# --- LOGICA DI TRAFFICO E SEMAFORI ---

def IsGreenLight(u, v, tick):
    """Simula semafori alternati ogni 30 tick."""
    cycle = 30
    return (tick % cycle < 15) if (u + v) % 2 == 0 else (tick % cycle >= 15)

def GetEdgeOccupancy(allAgents):
    """Calcola quanto spazio occupano gli agenti su ogni strada."""
    occupancy = {}
    for agent in allAgents:
        if agent.active and agent.currentStep < len(agent.path) - 1:
            u, v = agent.path[agent.currentStep], agent.path[agent.currentStep + 1]
            weight = 3.0 if agent.isHeavy else 1.0
            occupancy[(u, v)] = occupancy.get((u, v), 0) + weight
    return occupancy

def ValidateMovement(agent, graph, occupancy, tick):
    """Controlla semafori e congestione prima di muovere l'agente."""
    if agent.type == 'Pedestrian': return True 
    if agent.currentStep >= len(agent.path) - 1: return False
    
    u, v = agent.path[agent.currentStep], agent.path[agent.currentStep + 1]
    
    # 1. Controllo Semaforico agli incroci
    if graph.degree(u) > 2 and not IsGreenLight(u, v, tick): 
        return False
    
    # 2. Controllo Congestione (Capacity)
    edgeData = graph.get_edge_data(u, v, 0)
    if edgeData:
        capacity = edgeData.get('capacity', 5)
        if occupancy.get((u, v), 0) > capacity and random.random() < 0.7:
            return False
            
    return True

# --- PRE-PROCESSING E BARRIERE ---

def ApplyBarriers(graph, barriers):
    if not barriers: return
    nodes_list = list(graph.nodes(data=True))
    node_coords = np.array([(d['y'], d['x']) for _, d in nodes_list])
    tree = KDTree(node_coords)
    for barrier in barriers:
        _, idx = tree.query([barrier[0], barrier[1]])
        target_node = nodes_list[idx][0]
        for neighbor in list(graph.neighbors(target_node)):
            for key in graph[target_node][neighbor]:
                graph[target_node][neighbor][key]['weight'] = 999999

def PreProcessing(graph, timeOfDay="Morning"):
    """Calcola pesi e capacità delle strade."""
    VEHICLE_SPACE = 7.0 
    for u, v, k, data in graph.edges(data=True, keys=True):
        data['capacity'] = max(1, int(data.get('length', 1.0) / VEHICLE_SPACE))
    
    nIds = list(graph.nodes())
    coords = np.array([(graph.nodes[n]['y'], graph.nodes[n]['x']) for n in nIds])
    weights = np.array([graph.degree(n) for n in nIds], dtype=float) + 1.0
    
    # Flusso direzionale basato sull'orario
    if timeOfDay == "Morning":
        center = [coords[:,0].mean(), coords[:,1].mean()]
        dist = np.linalg.norm(coords - center, axis=1)
        weights[dist < 0.008] *= 8.0 
        
    return nIds, weights / weights.sum()

# --- MAIN RUNNER ---

def RunSimulation(coords, distRange, vehicles, pedestrian, duration, barriers, timeOfDay):
    gDrive = ox.graph_from_point(coords, dist=distRange, network_type='drive', simplify=True)
    gWalk = ox.graph_from_point(coords, dist=distRange, network_type='walk', simplify=True)
    
    roads = [{"path": [[round(gDrive.nodes[u]['x'], 5), round(gDrive.nodes[u]['y'], 5)], 
                       [round(gDrive.nodes[v]['x'], 5), round(gDrive.nodes[v]['y'], 5)]]} 
             for u,v in gDrive.edges()]

    if barriers: ApplyBarriers(gDrive, barriers)
    
    # Preparazione Task
    nodesD, weightsD = PreProcessing(gDrive, timeOfDay)
    nodesW, _ = PreProcessing(gWalk, timeOfDay)
    tasks = []
    
    truck_ratio = 0.15 if timeOfDay == "Morning" else 0.05
    for i in range(vehicles):
        o, t = random.choice(nodesD), random.choices(nodesD, weights=weightsD, k=1)[0]
        v_type = 'HeavyVehicle' if random.random() < truck_ratio else 'Vehicle'
        tasks.append((gDrive, f"v_{i}", o, t, 'weight', v_type))
    
    for j in range(pedestrian):
        if nodesW:
            o, t = random.choice(nodesW), random.choice(nodesW)
            tasks.append((gWalk, f"p_{j}", o, t, 'length', 'Pedestrian'))

    with ThreadPoolExecutor(max_workers=10) as executor:
        results = list(executor.map(ComputePathWorker, tasks))
    
    allAgents = [Agent(r['id'], r['path'], r['coords'], r['type']) for r in results if r]
    
    # Loop di simulazione dinamico
    simulationData = []
    for i in range(duration):
        # Calcoliamo l'occupazione delle strade ogni 5 tick per performance
        if i % 5 == 0:
            edgeOccupancy = GetEdgeOccupancy(allAgents)
        
        for agent in allAgents:
            if not agent.active: continue
            
            # Validazione movimento (Traffico + Semafori)
            if ValidateMovement(agent, gDrive, edgeOccupancy if 'edgeOccupancy' in locals() else {}, i):
                agent.step()
                # I veicoli si muovono più velocemente dei pedoni
                if agent.type != 'Pedestrian' and agent.active:
                    agent.step()
            else:
                agent.stuckTicks += 1

            # Salvataggio dati (Downsampling)
            if agent.active and (i == 0 or i % 5 == 0):
                lat, lon = agent.pathCoords[agent.currentStep]
                simulationData.append({
                    'tick': i, 'agent_id': agent.id, 'lat': lat, 'lon': lon, 'type': agent.type
                })
                
    return pd.DataFrame(simulationData), roads
