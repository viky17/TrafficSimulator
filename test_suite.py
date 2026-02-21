import pytest
import time
import psutil
import gc
import networkx as nx
import numpy as np
from engine import populationAgents, run_ticks, get_edge_occupancy, Vehicle, HeavyVehicle, runSimulation

# --- FIXTURES ---

@pytest.fixture
def benchmark_graph():
    """Generates a controlled graph for physical and logic validation."""
    G = nx.MultiDiGraph()
    G.add_node(1, x=0.0, y=0.0)
    G.add_node(2, x=0.0, y=1.0)
    G.add_node(3, x=1.0, y=1.0) 
    G.add_edge(1, 2, key=0, length=100.0, weight=100.0, capacity=2)
    G.add_edge(2, 3, key=0, length=100.0, weight=100.0, capacity=2)
    G.graph['crs'] = 'epsg:4326'
    return G

# --- 1. TEST DI OTTIMIZZAZIONE (CACHE & SETUP) ---

def test_caching_optimization_performance():
    """Measures the efficiency gain from the GraphML caching system."""
    coords = (45.4642, 9.1900) 
    dist = 500
    
    # Primo avvio (Cold Start)
    start_cold = time.perf_counter()
    runSimulation(coords, dist, vehicles=1, pedestrian=0, duration=1, barriers=None)
    cold_duration = time.perf_counter() - start_cold
    
    # Secondo avvio (Cached Start)
    start_cached = time.perf_counter()
    runSimulation(coords, dist, vehicles=1, pedestrian=0, duration=1, barriers=None)
    cached_duration = time.perf_counter() - start_cached
    
    print("\n" + "="*60)
    print(f"{'CACHE OPTIMIZATION REPORT':^60}")
    print("-" * 60)
    print(f"Cold Start (Network + I/O) : {cold_duration:.4f} s")
    print(f"Cached Start (Disk Load)    : {cached_duration:.4f} s")
    print(f"Optimization Factor         : {((cold_duration/cached_duration)):.1f}x faster")
    print("="*60)
    assert cached_duration < cold_duration

# --- 2. STRESS TEST (POPOLAZIONE & SCALABILITÀ) ---

def test_engine_scalability_and_unit_cost(benchmark_graph):
    """Benchmarks creation cost per agent and total throughput."""
    scales = [1000, 10000, 50000]
    
    print("\n" + "="*80)
    print(f"{'QUANTITATIVE POPULATION ANALYSIS':^80}")
    print("-" * 80)
    print(f"{'AGENTS':<12} | {'TIME (s)':<12} | {'µs/AGENT':<12} | {'THROUGHPUT (ag/s)':<20}")
    print("-" * 80)
    
    for count in scales:
        gc.collect()
        start = time.perf_counter()
        agents = populationAgents(benchmark_graph, benchmark_graph, count, 0)
        duration = time.perf_counter() - start
        
        us_per_agent = (duration / count) * 1_000_000
        throughput = int(count / duration)
        
        print(f"{count:<12,} | {duration:<12.4f} | {us_per_agent:<12.2f} | {throughput:<20,}")
    
    print("="*80)
    assert duration < 2.5

# --- 3. TEST MEMORIA (STABILITÀ & FOOTPRINT) ---

def test_memory_efficiency_per_k_agents(benchmark_graph):
    """Calculates RAM usage per 1000 agents to verify lightweight architecture."""
    process = psutil.Process()
    gc.collect()
    mem_initial = process.memory_info().rss
    
    count = 50000
    agents = populationAgents(benchmark_graph, benchmark_graph, count, 0)
    mem_peak = process.memory_info().rss
    
    total_mem_mb = (mem_peak - mem_initial) / (1024 * 1024)
    kb_per_agent = (total_mem_mb * 1024) / count
    
    print("\n" + "="*60)
    print(f"{'MEMORY STABILITY DIAGNOSTICS':^60}")
    print("-" * 60)
    print(f"Baseline Memory   : {mem_initial / 1024 / 1024:.2f} MB")
    print(f"Peak (50k agents) : {mem_peak / 1024 / 1024:.2f} MB")
    print(f"Net Growth        : {total_mem_mb:.2f} MB")
    print(f"Cost per 1k Agents: {kb_per_agent * 1000:.2f} KB")
    
    del agents
    gc.collect()
    mem_final = process.memory_info().rss
    print(f"Post-Cleanup      : {mem_final / 1024 / 1024:.2f} MB")
    print("="*60)
    assert (mem_final - mem_initial) / 1024 / 1024 < 10.0

# --- 4. TEST INTEGRITÀ FISICA (PCE & CONGESTIONE) ---

def test_pce_and_congestion_dynamics(benchmark_graph):
    """Validates PCE Load calculation and stochastic congestion response."""
    # 1. PCE Logic Test (Truck 3.0 + Car 1.0 = 4.0)
    truck = HeavyVehicle("T1", benchmark_graph, 1, 2)
    car = Vehicle("C1", benchmark_graph, 1, 2)
    occupancy = get_edge_occupancy([truck, car])
    actual_load = occupancy.get((1,2), 0)
    
    # 2. Congestion Test (100 agents on capacity 2)
    benchmark_graph[1][2][0]['capacity'] = 2
    agents = [Vehicle(f"v_{i}", benchmark_graph, 1, 2) for i in range(100)]
    results = run_ticks(agents, duration=1)
    congested = [r for r in results if r['status'] == 'congested']
    
    print("\n" + "="*60)
    print(f"{'PHYSICS & CONGESTION REPORT':^60}")
    print("-" * 60)
    print(f"PCE Load (Truck+Car) : {actual_load} (Expected 4.0)")
    print(f"Oversaturation Test  : {len(congested)} agents congested")
    print("="*60)
    assert actual_load == 4.0
    assert len(congested) > 0