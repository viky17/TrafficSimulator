import osmnx as ox
import pandas as pd
import random
import time
import networkx as nx
import os
import numpy as np
from scipy.spatial import KDTree
from concurrent.futures import ProcessPoolExecutor
import multiprocessing

# Create cache directory
if not os.path.exists("cache"):
    os.makedirs("cache")

# --- CLASSES ---

class Agent():
    """Optimized Agent: Stores path and coordinates, avoiding graph lookups during simulation."""
    def __init__(self, agentId, path, pathCoords, typeStr):
        self.id = agentId
        self.path = path  
        self.pathCoords = pathCoords # Pre-stored (lat, lon) for each step
        self.type = typeStr
        self.active = True if path and len(path) > 1 else False
        self.currentStep = 0
        self.currentNode = path[0] if self.active else None
        self.stuckTicks = 0
        self.ticksAlive = 0

    def step(self):
        if not self.active:
            return
        
        prevNode = self.currentNode
        if self.currentStep < len(self.path) - 1:
            self.currentStep += 1
            self.currentNode = self.path[self.currentStep]
            
            # Reset stuck counter if the agent moved to a new node
            if self.currentNode != prevNode:
                self.stuckTicks = 0
                
            if self.currentStep == len(self.path) - 1:
                self.active = False
        else:
            self.active = False

# --- MULTIPROCESSING WORKER ---

workerGraph = None

def InitWorker(graph):
    """Inizializza il grafo una sola volta per ogni core della CPU."""
    global workerGraph
    workerGraph = graph

def ComputePathWorker(args):
    """Calcola il percorso usando il grafo già presente nella memoria del core."""
    global workerGraph
    agentId, origin, target, weightType, typeStr = args
    
    try:
        # Usiamo workerGraph (già caricato) invece di passarlo tra i task
        path = ox.shortest_path(workerGraph, origin, target, weight=weightType)
        if path:
            cost = nx.path_weight(workerGraph, path, weight=weightType)
            if cost < 500000:
                coords = [(workerGraph.nodes[n]['y'], workerGraph.nodes[n]['x']) for n in path]
                return {'id': agentId, 'path': path, 'coords': coords, 'type': typeStr}
    except:
        return None
    return None

# --- SIMULATION LOGIC ---

def LoadGraphWithCache(coords, distRange, networkType):
    """Handles loading/downloading graph with local cache protection."""
    lat_r, lon_r = round(coords[0], 4), round(coords[1], 4)
    cachePath = f"cache/map_{networkType}_{lat_r}_{lon_r}_{distRange}.graphml"
    
    if os.path.exists(cachePath):
        return ox.load_graphml(cachePath)
    
    graph = ox.graph_from_point(coords, dist=distRange, network_type=networkType, simplify=True)
    ox.save_graphml(graph, cachePath)
    return graph

def ApplyBarriers(graph, barriers):
    """Modifies edge weights to simulate impassable road blocks."""
    for barrier in barriers:
        try:
            u, v, key = ox.nearest_edges(graph, barrier[1], barrier[0])
            graph[u][v][key]['weight'] = 999999 
            if graph.has_edge(v, u):
                for k in graph[v][u]: 
                    graph[v][u][k]['weight'] = 999999
        except:
            continue

def PopulationAgentsParallel(gDrive, gWalk, vehicles, pedestrian, timeOfDay):
    nodesD, weightsD = PreProcessing(gDrive, timeOfDay)
    nodesW, weightsW = PreProcessing(gWalk, timeOfDay)
    
    tasksD = [] # Task per il grafo Drive
    tasksW = [] # Task per il grafo Walk
    truckRatio = 0.20 if timeOfDay == "Morning" else 0.05

    for i in range(vehicles):
        o = random.choice(nodesD)
        t = random.choices(nodesD, weights=weightsD, k=1)[0]
        vType = "HeavyVehicle" if random.random() < truckRatio else "Vehicle"
        # NOTA: Non passiamo più gDrive qui!
        tasksD.append((f"v_{i}", o, t, 'weight', vType))

    for j in range(pedestrian):
        if nodesW:
            o = random.choice(nodesW)
            t = random.choices(nodesW, weights=weightsW, k=1)[0]
            tasksW.append((f"p_{j}", o, t, 'length', 'Pedestrian'))

    numWorkers = max(1, multiprocessing.cpu_count() - 1)
    results = []

    # Esecuzione per i Veicoli (usa gDrive)
    with ProcessPoolExecutor(max_workers=numWorkers, initializer=InitWorker, initargs=(gDrive,)) as executor:
        results.extend(list(executor.map(ComputePathWorker, tasksD)))

    # Esecuzione per i Pedoni (usa gWalk)
    with ProcessPoolExecutor(max_workers=numWorkers, initializer=InitWorker, initargs=(gWalk,)) as executor:
        results.extend(list(executor.map(ComputePathWorker, tasksW)))
    
    finalAgents = []
    for r in results:
        if r:
            agent = Agent(r['id'], r['path'], r['coords'], r['type'])
            agent.isHeavy = (r['type'] == 'HeavyVehicle')
            finalAgents.append(agent)
            
    return finalAgents

def RunTicks(allAgents, duration, graph):
    """Main simulation loop: handles movement, traffic lights, and recording."""
    simulationData = [] 
    for i in range(duration):
        if i%5 == 0:
            edgeOccupancy = GetEdgeOccupancy(allAgents)
        else:
            if 'edgeOccupancy' not in locals():
                edgeOccupancy = {}       
        for agent in allAgents:
            if not agent.active: continue

            agent.ticksAlive += 1
            if agent.ticksAlive > duration or agent.stuckTicks > 15:
                agent.active = False
                continue

            canMove = ValidateMovement(agent, graph, edgeOccupancy, i)

            if canMove:
                agent.step()
                if agent.type == 'Vehicle' and agent.active: 
                    agent.step() # Double speed for cars
            else:
                agent.stuckTicks += 1

            if agent.active:
                # Access pre-stored coordinates (Fixes the KeyError crash)
                lat, lon = agent.pathCoords[agent.currentStep]
                simulationData.append({
                    'tick': i, 
                    'agent_id': agent.id,
                    'lat': lat, 
                    'lon': lon,
                    'type': agent.type, 
                    'status': 'moving' if canMove else 'congested'
                })
    return simulationData

def ValidateMovement(agent, graph, occupancy, tick):
    """Checks if an agent can move based on traffic constraints."""
    # Pedestrians ignore vehicle-specific constraints (simplified)
    if agent.type not in ['Vehicle', 'HeavyVehicle']:
        return True 
    
    if agent.currentStep >= len(agent.path) - 1:
        return False

    u, v = agent.path[agent.currentStep], agent.path[agent.currentStep + 1]
    
    # Traffic Light logic (cycles based on tick)
    if graph.degree(u) > 2 and not IsGreenLight(u, v, tick):
        return False
    
    # Congestion/Capacity check
    edgeData = graph.get_edge_data(u, v, 0)
    if edgeData:
        capacity = edgeData.get('capacity', 5)
        if occupancy.get((u, v), 0) > capacity and random.random() < 0.7:
            return False
            
    return True

def GetEdgeOccupancy(allAgents):
    """Calculates road load for the current tick."""
    occupancy = {}
    for agent in allAgents:
        if agent.active and agent.currentStep < len(agent.path) - 1:
            u, v = agent.path[agent.currentStep], agent.path[agent.currentStep + 1]
            weight = 3.0 if getattr(agent, 'isHeavy', False) else 1.0
            occupancy[(u, v)] = occupancy.get((u, v), 0) + weight
    return occupancy

def PreProcessing(graph, timeOfDay="Morning"):
    """Determines destination popularity based on urban dynamics."""
    VEHICLE_SPACE = 7.0 
    for u, v, k, data in graph.edges(data=True, keys=True):
        data['capacity'] = max(1, int(data.get('length', 1.0) / VEHICLE_SPACE))
    
    nIds = list(graph.nodes())
    coords = np.array([(graph.nodes[n]['y'], graph.nodes[n]['x']) for n in nIds])
    weights = np.array([graph.degree(n) for n in nIds], dtype=float) + 1.0
    
    if timeOfDay == "Morning":
        center = [coords[:,0].mean(), coords[:,1].mean()]
        dist = np.linalg.norm(coords - center, axis=1)
        weights[dist < 0.008] *= 8.0 # Business center attraction
    
    return nIds, weights / weights.sum()

def IsGreenLight(u, v, tick):
    cycle = 30
    return (tick % cycle < 15) if (u + v) % 2 == 0 else (tick % cycle >= 15)

def RunSimulation(coords, distRange, vehicles, pedestrian, duration, barriers, timeOfDay="Morning"):
    """Main entry point for running the simulation."""
    try:
        gDrive = LoadGraphWithCache(coords, distRange, 'drive')
        gWalk = LoadGraphWithCache(coords, distRange, 'walk')

        nx.set_edge_attributes(gDrive, nx.get_edge_attributes(gDrive, 'length'), 'weight')
        gDrive = ox.truncate.largest_component(gDrive, strongly=True)
        gWalk = ox.truncate.largest_component(gWalk, strongly=True)

        if barriers:
            ApplyBarriers(gDrive, barriers)
            
        allAgents = PopulationAgentsParallel(gDrive, gWalk, vehicles, pedestrian, timeOfDay)
        
        # Passing gDrive to RunTicks for traffic light and congestion lookups
        results = RunTicks(allAgents, duration, gDrive)
        
        # Prepare background road layer for Pydeck
        roads = []
        for u, v, data in gDrive.edges(data=True):
            path = list(data['geometry'].coords) if 'geometry' in data else \
                   [[gDrive.nodes[u]['x'], gDrive.nodes[u]['y']], [gDrive.nodes[v]['x'], gDrive.nodes[v]['y']]]
            roads.append({"path": path})

        return pd.DataFrame(results), roads
    except Exception as e:
        print(f"ERRORE RUNTIME: {e}")
        return pd.DataFrame(), []