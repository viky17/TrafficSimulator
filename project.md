### UML Class Diagram

```mermaid
classDiagram
   

    class Manager{
        +id: String
        +coords: List
        +distRange: int
        +status: String
        +agents: List
        +raodsGeometry: List
        +spawn_errors: int
        +tick_attuale: int
        +current_congestion: int
        -gDrive: Graph
        -gWalk: Graph
        +buildWorld(barriers)
        +populationWorld(vehicles, pedestrian, timeOfDay)
        +step()
    }

    class Agent{
        +id: String
        +type: String
        +active: bool
        +stuckTicks: int
        +ticksAlive: int
        +isHeavy: bool
        -path: List
        -pathCoords: List
        -currentNode: Node
        -currentStep: int
        +step()
    }
   note for Agent "stuckTicks: conta i giri in cui l'agente è rimasto fermo.<br/>isHeavy: se True l'agente occupa più spazio sulla strada.<br/>currentStep: punta alla posizione attuale nella lista del percorso."
Manager "1" *-- "*" Agent
