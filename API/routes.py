from fastapi import APIRouter,HTTPException,BackgroundTasks
from .schemas import WorldCreate,PopulationCreate
from engine.manager import Manager

router = APIRouter()
sim = Manager(sim_id="sim_01")

@router.post("/build")
async def build(world: WorldCreate):
    try:
        coords = (world.center.lat,world.center.lng) #Passaggio da oggetto Pydantic in una tupla
        sim.buildWorld(coords=coords, distRange=world.radius, barriers=world.barriers)
        return {"message": "Map loaded", "status": sim.status,"roads_count":len(sim.roadsGeometry)}
    except Exception as e:
        raise HTTPException(status_code=500,detail=str(e))

@router.post("/populate")
async def populate(world: PopulationCreate, background_tasks: BackgroundTasks):
    if sim.status != "WORLD_READY":
        raise HTTPException(status_code=400, detail="You must first initialize the world using /build")
    
    sim.status = "POPULATING"
    background_tasks.add_task(sim.populationWorld,world.vehicle_count,world.pedestrian_count,world.timeOfDay)
    return {"message":"Population process started", "status":sim.status}

@router.post("/step")
async def SimulationStep(return_data: bool=True):
    if sim.status not in ["POPULATED","RUNNING"]:
        raise HTTPException(status_code=400,detail="Simulation not ready for steps")
    try:
        data = sim.step()
        return {"tick":sim.tick_attuale,"status":sim.status,"agents_count": len(sim.current_step_idx),"data": data if return_data else []}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    
@router.get("/status")
async def get_status():
    try:
        count = 0
        if sim.agent_types_matrix is not None:
            count = len(sim.agent_types_matrix)
    except:
        count = 0

    return {
        "sim_id": sim.id,
        "status": sim.status,
        "tick": sim.tick_attuale,
        "agents": count
    }
