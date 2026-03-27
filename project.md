### UML Class Diagram

```mermaid
classDiagram
   

    class Manager{
        +id: String
        +status: String
        -gDrive: Graph
        -gWalk: Graph
        +agents: List
        +buildWorld(barriers)
        +populationWorld(vehicles,pedestrian,tiomOfDay)
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
    note for Agent "stuckTicks: conta i giri in cui l'agente è rimasto fermo.\nisHeavy: se True l'agente occupa più spazio sulla strada.\ncurrentStep: punta alla posizione attuale nella lista del percoso."  
    Manager "1" *-- "*" Agent
