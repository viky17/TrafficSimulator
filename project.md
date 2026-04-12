
Nella fase iniziale del progetto, ogni entità era un'istanza di una classe Agent. Questo approccio, pur essendo corretto, introduceva un overhead insostenibile dovuto alla gestione dinamica degli oggetti in Python e alla frammentazione della memoria. Superati i 75.000 agenti, il sistema diventava Memory-Bound e CPU-Bound a causa dei cicli for necessari per aggiornare ogni stato.

La soluzione è stata la Vettorializzazione. Ho rimosso la classe Agent e trasformato l'intera popolazione in un set di tensori e matrici NumPy. Ogni agente è identificato esclusivamente da un indice all'interno di blocchi di memoria contigui. Questo permette di sfruttare le librerie scritte in C (come NumPy) per eseguire operazioni matematiche simultanee su tutta la popolazione, massimizzando l'efficienza dei registri della CPU e minimizzando i cache miss.

Per garantire la massima velocità di accesso, i dati sono organizzati in tre strutture principali pre-allocate:
- *path_matrix*: è il database spaziale del sistema. Contiene le coordinate *(lat,lon)* per ogni agente *(N)* e per ogni step del percorso *(S)*. Utilizzando il tipo *float32* invece di *float64* standard, sono riuscito a dimezzare l'occupazione della RAM senza perdere la precisione necessaria.

- *pos_matrix*: rappresenta lo stato del sistema. Ad ogni tick, il sistema non calcola la posizione, ma estra dalla matrice *path_matrix* usando un operazione di Advanced Indexing. Matematicamente lo spostamento di 250.000 agenti avviene in un'unica operazione vettoriale:
        *pos_matrix = path_matrix[np.arange(N),current_step_idx]*
    
- *active_mask*: una maschera booleana che permette alla CPU di operare solo sugli agenti ancora in movimento escludendo istantaneamente dal calcolo chi ha già raggiunto la destinazione.

**Preparazione del Grafo e Barriere stradali**
Prima della simulazione, il Manager integra i dati di OpenStreetMap tramite OSMnx. Le barriere sono modifiche topologiche al grafo stradale. Se una strada viene bloccata, l'arco corrispondente viene rimosso dal grafo di NetworkX. Questo garantisce che l'algoritmo di Dijkstra non "veda" nemmeno la strada chiusa, forzando la generazione di percorsi alternativi reali.
Ogni arco del grafo possiede un attributo di capacità fisica. Durante il preprocessing, calcoliamo il peso delle strade non solo in base alla lunghezza, ma anche in base al tipo di traffico (veicolare vs pedonale) e all'ora del giorno, simulando la naturale propensione dei flussi verso le arterie principali.

**Popolazione tramite Multiprocessing**
Il calcolo del percorso più breve, il quale utilizza l'algoritmo di Dijkstra, per centinaia di migliaia di coppie origine-destinazione è l'operazione più onerosa. Per superare il Global Interpreter Lock (GIL) di Python, il simulatore utilizza un sistema di Parallel Population.
Il carico viene distribuito su processi worker indipendenti che operano in parallelo. Ogni core della CPU riceve un sottoinsieme di task, calcola i percorsi e restituisce i dati grezzi che vengono poi impacchettati nelle matrici finali. Questo approccio garantisce una scalabilità quasi lineare rispetto al numero di core fisici disponibili.

**Gestione degli errori**
Quando un utente inserisce delle barriere stradali (es. chiude un intero quartiere), il grafo di NetworkX viene fisicamente modificato. Questo crea un rischio concreto: un agente potrebbe ricevere un punto di partenza (Origine) o di arrivo (Destinazione) che non è più collegato al resto della città.
In un approccio standard, l'algoritmo di Dijkstra solleverebbe un'eccezione NodeNotFound o NetworkXNoPath. Se non gestita, questa fermerebbe l'intera popolazione.

Durante la fase di Parallel Population, ogni worker opera all'interno di un blocco try-except. Se un percorso non può essere calcolato, il worker non interrompe il processo, ma restituisce un valore nullo.
Il Manager raccoglie solo i risultati validi. Gli agenti "falliti" vengono conteggiati nella variabile spawn_errors, ma non vengono mai inseriti nelle matrici NumPy finali.
Questo garantisce che, una volta avviata la simulazione, ogni riga della path_matrix contenga dati certi e navigabili, eliminando alla radice il rischio di crash durante il loop di movimento.

**Diagramma di sequenza**
La scelta di utilizzare FastAPI risponde a una precisa necessità architettonica: separare la gestione delle risorse (il calcolo delle rotte e del movimento) dalla logica di visualizzazione o di comando (il Frontend o il Client).
In un sistema che gestisce centinaia di migliaia di agenti, il thread di calcolo non deve mai essere bloccato da operazioni di I/O. L'architettura API permette al Manager di:

- Operare in Background: Mentre il motore processa i tick della simulazione, le API restano in ascolto, permettendo all'utente di interrogare lo stato del sistema (es. quanti agenti sono ancora attivi) senza interrompere il calcolo.

- Controllare il Ciclo di Vita: Ogni fase della simulazione è isolata. Questo significa che il Client ha il controllo totale su "quando" costruire il mondo, "quando" popolarlo e "quando" far avanzare il tempo, garantendo una sincronizzazione perfetta tra la logica e la memoria fisica del server.

Uno dei vantaggi principali di questo approccio è l'efficienza nel trasferimento dei dati. Invece di inviare strutture dati complesse e pesanti (come l'intero grafo o tutti i percorsi pre-calcolati), l'API agisce da filtro in modo che ad ogni chiamata di step(), il sistema estrae solo una "fotografia" istantanea della pos_matrix.
I dati vengono serializzati in JSON leggero, contenente solo le coordinate e gli ID necessari alla visualizzazione. Questo approccio minimizza la latenza di rete, rendendo possibile una visualizzazione fluida anche quando il motore sta processando popolazioni molto grandi.

*Rotte*:
- POST /build (Inizializzazione): Riceve le coordinate geografiche e le barriere. Il Manager modella il grafo stradale. Finché questa fase non è conclusa, il grafo è considerato "instabile" e il sistema impedisce l'accesso alle fasi successive.

- POST /populate (Popolazione): Avvia il calcolo massivo dei percorsi. Grazie all'uso dei BackgroundTasks, la rotta restituisce subito il controllo al Client, evitando timeout e permettendo una gestione fluida della UI o dei sistemi di monitoraggio.

- GET /step (Esecuzione): Ogni chiamata triggera un tick di simulazione. Il Manager esegue uno "slice" della pos_matrix e restituisce le coordinate correnti. Questo design permette di visualizzare i dati in tempo reale senza dover gestire l'intero database dei percorsi sul lato Client.

sequenceDiagram
    autonumber
    participant Client
    participant Manager
    participant Utils
    participant NumPy

    Note over Client, Manager: Fase di Inizializzazione
    Client->>Manager: buildWorld(barriers)
    Manager->>Utils: ApplyBarriers(graph, barriers)
    Manager->>Utils: PreProcessing(graph)
    Manager-->>Client: status = "WORLD_READY"

    Note over Client, Manager: Fase di Popolazione (Parallel)
    Client->>Manager: populationWorld(counts)
    Manager->>Utils: ComputePathWorker(tasks)
    Utils-->>Manager: return paths
    Manager->>NumPy: Allocate and Pack Matrices (path_matrix)
    Manager-->>Client: status = "POPULATED"

    Note over Client, Manager: Loop di Simulazione (Vectorized)
    Client->>Manager: step()
    Manager->>Utils: GetEdgeOccupancy(path_matrix, active_mask)
    
    rect rgb(240, 240, 240)
    Note right of Manager: Calcolo Vettoriale (No Loops)
    Manager->>NumPy: Apply Advanced Indexing & Active Mask
    NumPy-->>Manager: return pos_matrix
    end

    Manager-->>Client: return data_tick (JSON positions)

**La macchina a stati**
La stabilità del motore di simulazione è garantita da una macchina a stati finiti che impedisce operazioni illegali sulla memoria. Poiché il sistema lavora con matrici pre-allocate e calcoli paralleli, ogni stato funge da "checkpoint" di validazione: non è possibile avanzare se la fase precedente non ha garantito l'integrità dei dati.

*Stati*:
- CREATED: Il Manager è istanziato ma la memoria è "vuota". In questa fase il sistema è in ascolto dei parametri di configurazione (coordinate, raggio, tipologia di rete). È l'unico momento in cui è possibile definire l'ambiente senza causare inconsistenze.

- WORLD_READY: Questo stato viene raggiunto dopo il completamento della rotta /build. Il grafo stradale è stato scaricato, le barriere topologiche sono state applicate e i pesi delle strade (costi di percorrenza) sono stati calcolati. Il mondo è ora immutabile: sigillare la topologia in questo stato garantisce che i percorsi calcolati successivamente non facciano riferimento a strade rimosse o nodi inesistenti.

- POPULATING: Stato transitorio attivato dalla rotta /populate. Il sistema è occupato nel calcolo parallelo dei percorsi (Dijkstra) in background. Durante questa fase, le rotte di esecuzione (step) sono bloccate per evitare accessi a matrici non ancora completamente allocate o riempite.

- POPULATED: Il calcolo in background è terminato e i dati sono stati "impacchettati" nelle matrici NumPy. Il numero di agenti N è ora fisso e la memoria è ottimizzata. In questo stato, il sistema espone la variabile spawn_errors: se il tasso di fallimento è accettabile, il motore è pronto per la simulazione fisica.

- RUNNING: Il motore è in fase di esecuzione. Ogni chiamata alla rotta /step fa avanzare il tick globale. Il sistema utilizza la active_mask per processare solo gli indici necessari, mantenendo un carico computazionale costante.

- FINISHED: Lo stato viene raggiunto quando active_mask.any() restituisce False (tutti gli agenti sono arrivati o bloccati). Il Manager congela le telemetrie finali (es. congestione media, stuckTicks totali) per permettere al Client di scaricare un report statico definitivo senza il rischio di nuove mutazioni dei dati.


stateDiagram-v2
    direction TB

    [*] --> CREATED : Initialization
    
    state CREATED {
        direction TB
        S1: Waiting for buildWorld()
        S2: Applying Topo-Modifications
        S1 --> S2
    }

    CREATED --> WORLD_READY : status = "WORLD_READY"
    
    state WORLD_READY {
        direction TB
        S3: Waiting for populationWorld()
        S4: Parallel Pathfinding (Dijkstra)
        S5: Memory Packing (NumPy Allocation)
        S3 --> S4
        S4 --> S5
    }

    WORLD_READY --> POPULATED : status = "POPULATED"

    state RUNNING {
        direction TB
        Step: tick_attuale++
        Scan: Occupancy Vector Scan
        Update: Vectorized Indexing Update
        
        Step --> Scan
        Scan --> Update
        Update --> Step : Loop
    }

    POPULATED --> RUNNING : status = "RUNNING"
    
    RUNNING --> FINISHED : active_mask.any() == False
    FINISHED --> [*]
