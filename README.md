# Large-Scale Urban Mobility Engine
Questo progetto nasce dalla curiosità di capire come piccole modifiche alla struttura di una città, come un cantiere, un incidente o una zona pedonale, possano influenzare la mobilità di un'intera città.

## Funzionalità
Il simulatore permette di trasformare qualsiasi coordinata geografica del mondo, tramite integrazione con *OpenStreetMap*, in un ecosistema dinamico e reattivo. Le funzionalità principali includono:

- Puoi scaricare il grafo stradale di un quartiere storico, di un'area industriale o di una zona urbana moderna. Il sistema distingue automaticamente tra strade percorribili da veicoli e percorsi esclusivamente pedonali, permettendo di studiare come la morfologia della città influenzi naturalmente il movimento dei suoi abitanti.

- Il simulatore gestisce simultaneamente tre classi di entità, ognuna con un'identità precisa:

    - Pedoni: Si muovono su reti dedicate, ignorando i sensi di marcia ma limitati dalla velocità di camminata.

    - Veicoli Standard: Seguono le regole del grafo stradale, cercando il percorso più rapido.

    - Mezzi Pesanti: Hanno un "ingombro" maggiore sulla carreggiata e velocità ridotte, diventando una delle  principali cause di rallentamenti.

- Lavorando sugli input, è possibile simulare:
    - La chiusura improvvisa di un incrocio per un guasto
    - L'aggiunta di una Zona a Traffico Limitato
    - L'impatto di un cantiere a lungo termine su una strada principale
Gli agenti ricalcolano i loro percorsi in tempo reale, permettendo di osservare come il traffico influisce sulle strade secondarie o dove si vanno a creare colli di bottiglia.

- Le strade hanno un limite fisico. Il motore calcola la capacità residua di ogni segmento stradale. Quando troppi veicoli occupano una strada, la velocità di percorrenza cala seguendo modelli di flusso realistici e causando ingorghi.

## Evoluzione dell'architettura
Nelle prime fasi del progetto, ogni veicolo e pedone era gestito come un oggetto indipendente (OOP). Era una scelta logica e intuitiva, ma con un difetto fatale: superati i 75.000 agenti, la gestione dei singoli oggetti saturava la memoria e rallentava drasticamente la CPU.
Di conseguenza ho dovuto cambiare radicalmente approccio, passando da una logica basata sugli oggetti a una Data-Oriented.

Ho trasformato la simulazione in un flusso di dati gestito interamente tramite *vettorializzazione* con NumPy. Invece di iterare su ogni singolo oggetto, per calcolarne la posizione, il motore vede la popolazione come un blocco di matrici coordinate. Questo permette di muovere oltre *250.000* agenti applicando singole operazioni matematiche all'intera mole di dati, rendendo lo spostamento quasi istantaneo a prescindere dal numero di entità.

## Prestazioni
Il secondo ostacolo più grande era il tempo di attesa, calcolare i percorsi per centinaia di migliaia di agenti su un grafo urbano reale è un operazione molto pesante per la CPU.

*Parallelizzazione*: invece di calcolare un percorso alla volta, il simulatore utilizza tutti i core disponibili della CPU. Ognuno lavora su una porzione della popolazione in totale autonomia, abbattendo i tempi di inizializzazione.
Questa scelta mi ha permesso di superare i limiti di Python dati dal Global Interpreter Lock, garantendo che la potenza di calcolo cresca linearmente con il numero di core a disposizione.

## Interfaccia
Il simulatore non è un blocco chiuso, ma un servizio esposto tramite FastAPI. Questa scelta architetturale permette di separare nettamente il motore di calcolo dalla visualizzazione o dal controllo utente. Il ciclo di vita della città è gestito in modo asincrono: dalla creazione del grafo stradale alla generazione parallela della popolazione, ogni fase può essere monitorata in tempo reale tramite endpoint dedicati. Questo design permette di intervenire sulla simulazione "in corsa", ad esempio inserendo barriere o modificando i flussi, ricevendo indietro flussi di dati ottimizzati per la visualizzazione 3D.

**Setup e avvio**
Assicurati di avere Python 3.9+ e le librerie geospaziali installate.

1.  **Installazione**:
    ```bash
    pip install -r requirements.txt
    ```
2.  **Esecuzione**:
    ```bash
    uvicorn main:app --reload
    ```
3.  **Utilizzo**:
    Accedi alla documentazione interattiva su `http://localhost:8000/docs` per iniziare a modellare e popolare la tua città.
