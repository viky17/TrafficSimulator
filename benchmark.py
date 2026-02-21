import time
import pandas as pd
import numpy as np
import psutil
import os
# Importiamo la funzione con il nuovo nome
from engine import RunSimulation

def RunSystemBenchmark(coords=(51.509865, -0.118092), radius=1000):
    """
    Esegue uno stress test controllato del motore di simulazione parallelizzato.
    """
    scenarios = [
        {"agents": 100, "ticks": 100, "label": "Baseline"},
        {"agents": 1000, "ticks": 100, "label": "Standard"},
        {"agents": 5000, "ticks": 200, "label": "Urban Load"},
        {"agents": 15000, "ticks": 200, "label": "Heavy Stress"},
        {"agents": 25000, "ticks": 300, "label": "Massive Population"}
    ]
    
    results = []
    
    print(f"--- STARTING SYSTEM INTEGRITY & PERFORMANCE BENCHMARK ---")
    print(f"Location: {coords} | Radius: {radius}m")
    print(f"Parallel Engine: Active\n")

    for sc in scenarios:
        process = psutil.Process(os.getpid())
        mem_before = process.memory_info().rss / (1024 * 1024)
        
        start_time = time.time()
        
        try:
            # Chiamata alla funzione UpperCamelCase e parametri corretti
            df, roads = RunSimulation(
                coords=coords, 
                distRange=radius, 
                vehicles=sc['agents'] // 2, 
                pedestrian=sc['agents'] // 2, 
                duration=sc['ticks'], 
                barriers=[], 
                timeOfDay="Morning"
            )
            
            end_time = time.time()
            elapsed = end_time - start_time
            mem_after = process.memory_info().rss / (1024 * 1024)
            
            rows = len(df) if not df.empty else 0
            throughput = rows / elapsed if elapsed > 0 else 0
            
            results.append({
                "Scenario": sc['label'],
                "Agents": sc['agents'],
                "Ticks": sc['ticks'],
                "Elapsed_s": round(elapsed, 4),
                "Rows_Generated": rows,
                "Throughput_Rows_s": round(throughput, 0),
                "RAM_Usage_MB": round(mem_after - mem_before, 2),
                "Peak_RAM_MB": round(mem_after, 2)
            })
            
            print(f"DONE: {sc['label']} - {sc['agents']} agents in {round(elapsed, 2)}s")
            
        except Exception as e:
            print(f"FAILED: {sc['label']} due to {str(e)}")

    return pd.DataFrame(results)

def RunStressTest():
    # Definiamo step incrementali aggressivi
    # (Agenti, Range, Ticks)
    stress_scenarios = [
        (30000, 1500, 100),  # Limite "Safe"
        (50000, 2000, 100),  # Oltre la soglia standard
        (75000, 3000, 150),  # Verso il limite della RAM
        (100000, 5000, 200)  # "The Wall" (Punto di rottura probabile)
    ]

    for agents, radius, ticks in stress_scenarios:
        print(f"\n>>> TESTING: {agents} agents | {radius}m radius | {ticks} ticks")
        start = time.time()
        
        try:
            df, roads = RunSimulation(
                coords=(51.509865, -0.118092),
                distRange=radius,
                vehicles=agents // 2,
                pedestrian=agents // 2,
                duration=ticks,
                barriers=[],
                timeOfDay="Morning"
            )
            elapsed = time.time() - start
            print(f"SUCCESS: Completed in {round(elapsed, 2)}s")
            print(f"Data Generated: {len(df)} rows")
        except MemoryError:
            print("CRASH: Memory Limit Reached (RAM Full)")
            break
        except Exception as e:
            print(f"CRASH: System Error - {e}")
            break

if __name__ == "__main__":
    print("Stress Test\n")
    RunStressTest()
    
    # La protezione __main__ è obbligatoria per il multiprocessing
    report = RunSystemBenchmark()
    
    print("\n" + "="*50)
    print("FINAL BENCHMARK REPORT (Parallel Version)")
    print("="*50)
    print(report.to_string(index=False))