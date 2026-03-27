### UML Class Diagram

```mermaid
classDiagram
   

    class Manager{
        +id: String
        +coords: List
        +distRange: integer
        +status: String
        +agents: List
        +raodsGeometry: List
        +spawn_errors: integer
        +tick_attuale: integer
        +current_congestion: integer
        -gDrive: Graph
        -gWalk: Graph
        +buildWorld(barriers)
        +populationWorld(vehicles, pedestrian, timeOfDay)
        +step(): List
    }
      note for Manager "status: contiene lo stato della simulazione.<br/>current_congestion: attuale situazione del traffico.<br/>raodsGeometry: lista di coordinate."
    class Agent{
        +id: String
        +type: String
        +active: Boolean
        +stuckTicks: integer
        +ticksAlive: integer
        +isHeavy: Boolean
        -path: List
        -pathCoords: List
        -currentNode: Node
        -currentStep: integer
        +step()
    }

   note for Agent "stuckTicks: conta i giri in cui l'agente è rimasto fermo.<br/>isHeavy: se True l'agente occupa più spazio sulla strada.<br/>currentStep: punta alla posizione attuale nella lista del percorso."

   class Utils{
      <<Utility>>
      +ComputePathWorker(args: Tuple): Dictionary
      +IsGreenLight(u: integer, v: integer, tick: integer) Boolean
      +GetEdgeOccupancy(allAgents: List): Dictionary
      +ValidateMovement(agent, graph, occupancy, tick): Boolean
      +ApplyBarriers(graph, barriers: integer): void
      +PreProcessing(graph, timeOfDay: String): Tuple
   }
Manager "1" *-- "*" Agent
