# RoutedRAG

Modulares System zur zustandsbehafteten LLM-Orchestrierung mit dynamischem Modell-Routing, Retrieval-Augmented Generation (RAG) und einer integrierten Web-Benutzeroberfläche.

## Projektübersicht

RoutedRAG ist eine serviceorientierte Anwendung, die Anfragen über ein regelbasiertes Matching an unterschiedliche LLM-Provider und Modelle leitet, externe Werkzeuge (Tools) einbindet und domänenspezifisches Wissen über einen lokalen Vektorindex bereitstellt. Der Verlauf von Konversationen wird persistent in einer relationalen Datenbank gespeichert. Neben einer HTTP- und Streaming-API existieren ein browserbasiertes Frontend.

## Architektur

Das System gliedert sich in folgende logische Schichten:

1. **Präsentationsschicht**:
   - Browserbasiertes Single-Page-Frontend auf Basis von JavaScript und CSS (im Atomic Design).
   - Command-Line-Interface (`main.py`) für terminalbasierte Konversationen.
2. **API- und Transportschicht**:
   - FastAPI-Anwendung mit synchronen REST-Endpunkten und Server-Sent Events für Streaming-Ausgaben.
3. **Agenten- und Routing-Ebene**:
   - LangGraph- und LangChain-Pipeline mit Middlewares für die dynamische Modellauswahl (`dynamic_model_selection`) und Kontext-Injektion (`user_role_prompt`).
   - Dynamische Werkzeug-Registrierung (`ToolRegistry`) mit automatischer Erkennung im Verzeichnis `src/tools/`.
4. **Retrieval-Augmented Generation (RAG)**:
   - In-Memory-Vektordatenbank (FAISS) mit automatischer Erfassung lokaler Dokumente und Text-Splitting.
5. **Persistenzschicht**:
   - SQLite-Datenbank für Chats, Einzelnachrichten, Tool-Aufrufe und Token-Metadaten.
   - JSON-Konfigurationen für Routing-Regeln, Provider-Verbindungen und Anwendungseinstellungen.

---

## Technologie-Stack nach Komponenten

### Backend und API
- **Python 3.12**: Basis-Laufzeitumgebung.
- **FastAPI (>= 0.115.0)**: Bereitstellung der HTTP-Endpunkte (`src/server.py`, `src/routes/`), Routing, Request-Handling und Dependency-Struktur.
- **Uvicorn (>= 0.30.0)**: Asynchroner ASGI-Server zur Ausführung der FastAPI-Anwendung.
- **Pydantic (>= 2.8.0)**: Datenvalidierung, Typisierung und Serialisierung von Anfrage- und Antwortmodellen (`src/schemas.py`).
- **aiofiles (>= 24.1.0) & python-multipart (>= 0.0.9)**: Asynchrone Dateiverarbeitung für Dokumentenuploads im RAG-Modul (`src/routes/rag.py`).
- **python-dotenv (>= 1.0.0)**: Laden von Umgebungsvariablen aus `.env`-Dateien (`src/models.py`).

### Agenten-Framework und LLM-Integration
- **LangChain (>= 0.3.0) & LangChain Core**: Standardisierte Schnittstellen für Sprachmodelle, Embeddings, Messages und Tool-Definitionen.
- **LangGraph (>= 0.2.0)**: Steuerung des Ausführungsgraphen des Agenten über `create_agent` mit Checkpointing (`src/agent.py`).
- **langchain-openai (>= 0.2.0)**:
  - `ChatOpenAI`: Einheitlicher Client für OpenAI-kompatible Schnittstellen (z.B. Ollama, Open-WebUI, vLLM oder OpenAI).
  - `OpenAIEmbeddings`: Generierung von Vektoreinbettungen für die Dokumentenindizierung.
- **Routing-Middleware (`src/models.py`)**:
  - Implementierung von `@wrap_model_call` zur dynamischen Auswertung von Benutzeranfragen anhand definierter Schlüsselwörter (`evaluate_rules`).
  - Zuweisung des Zielmodells und der passenden Provider-Verbindung zur Laufzeit vor Ausführung des Agenten-Aufrufs.
- **Persona-Middleware (`src/sys_prompt.py`)**:
  - `@dynamic_prompt`: Injektion definierter System-Prompts abhängig von der gewählten Persönlichkeit oder benutzerdefinierten Anweisungen.

### RAG und Vektorsuche
- **FAISS (faiss-cpu >= 1.8.0)**: Lokaler Vektorindex zur Durchführung von Kosinus- bzw. L2-Ähnlichkeitssuchen (`src/rag_manager.py`).
- **Dokumenten-Ingestion (`src/rag_manager.py`)**: Rekursive Erfassung von Dateien (`.txt`, `.md`, `.markdown`, `.json`, `.csv`, `.py`) aus `data/documents/`, Chunking anhand von Textabsätzen und Erzeugung von `Document`-Objekten.

### Agenten-Tools (`src/tools/`)
- **`registry.py`**: Automatische Entdeckung (`auto_discover`) aller von `BaseTool` abgeleiteten Objekte im Ordner `src/tools/` per `importlib`.
- **`knowledge.py`**: Schnittstelle zwischen dem LangChain-Agenten und dem `RagManager`.
- **`calculator.py`**: Mathematische Funktionsauswertung mit beschränktem Namensraum (`abs`, `round`, `min`, `max`).
- **`clock.py`**: Zeit- und Datumsabfrage via Python-Standardbibliothek (`datetime`).
- **`weather.py`**: Wetterabfrage über die HTTP-Schnittstelle von `wttr.in`.

### Persistenz und Konfiguration
- **SQLite 3 (`src/chat_storage.py`)**: Lokale relationale Datenbank (`data/chats.db`) für Chat-Sessions (`chats`) und Nachrichtenhistorie (`messages`), inklusive protokollierter Tool-Aufrufe und Token-Zählungen.
- **JSON-Konfigurationsdateien (`config/`)**:
  - `connections.json`: Definition von LLM-Endpunkten (Base-URL, API-Key, Standardmodell).
  - `routing_rules.json`: Keyword-Listen, Prioritäten und Zielzuordnungen für das Modell-Routing.
  - `app_settings.json`: Globale Standardwerte (aktive Persona, Standard-RAG-Verzeichnis, Dynamic-Routing-Status).

### Frontend
- **HTML5**: Semantischer Aufbau der Web-Oberfläche (`src/static/index.html`).
- **CSS3 (Atomic Design)**: Strukturierte Stylesheets ohne externe Frameworks:
  - `01-tokens.css`: CSS-Variablen für Farben, Typografie und Abstände.
  - `02-atoms.css`: Grundelemente (Buttons, Inputs, Badges, Toggles).
  - `03-molecules.css`: Zusammengesetzte Komponenten (Chat-Nachrichten, Eingabefelder, Tool-Anzeigen).
  - `04-organisms.css`: Komplexe Bereiche (Sidebar, Chat-Bereich, Einstellungs-Modals).
  - `05-templates.css`: Layout-Raster und Container.
- **Vanilla JavaScript (`src/static/js/`)**:
  - `api.js`: Fetch- und SSE-Wrapper für die Backend-Kommunikation.
  - `state.js`: Verwaltung des lokalen Anwendungszustands im Browser.
  - `atoms.js`, `molecules.js`, `organisms.js`: Rendern und Aktualisieren der DOM-Elemente.
  - `app.js`: Initialisierung und Event-Handling.
- **Server-Sent Events (SSE)**: Asynchrone Übertragung von Token-Streams und Tool-Ausführungsstatus an den Browser (`/api/chat/stream`).

### Infrastruktur und Containerisierung
- **Docker (`Dockerfile`)**: Container-Abbild auf Basis von `python:3.12-slim` mit integriertem Healthcheck.
- **Docker Compose (`docker-compose.yml`)**: Dienstdefinition mit Volume-Mounts für Persistenzdaten (`./data`), Konfigurationen (`./config`) und Umgebungsvariablen (`./.env`).
- **Shell-Skript (`start.sh`)**: Einstiegsskript zur Wahl zwischen lokalem Uvicorn-Start und Container-Ausführung.

---

## Schnittstellenübersicht (API Endpunkte)

### Konversationen
- `GET /api/chats`: Paginierte Liste existierender Chats abrufen.
- `POST /api/chats`: Neue Chat-Session anlegen.
- `GET /api/chats/{chat_id}`: Details und Nachrichtenverlauf eines Chats abrufen.
- `PATCH /api/chats/{chat_id}`: Titel eines Chats aktualisieren.
- `DELETE /api/chats/{chat_id}`: Chat und zugehörige Nachrichten löschen.
- `POST /api/chat`: Nachricht an den Agenten senden (synchroner JSON-Response).
- `POST /api/chat/stream`: Nachricht an den Agenten senden (SSE-Streaming von Tokens und Tool-Aufrufen).

### Konfiguration und Regeln
- `GET /api/settings`: Aktuelle Anwendungseinstellungen abrufen.
- `POST /api/settings`: Anwendungseinstellungen speichern.
- `GET /api/personalities`: Verfügbare System-Prompt-Profile abrufen.
- `GET /api/rules`: Konfigurierte Routing-Regeln abrufen.
- `POST /api/rules`: Routing-Regeln speichern.
- `GET /api/connections`: Konfigurierte LLM-Verbindungen abrufen.
- `POST /api/connections`: LLM-Verbindungen speichern.
- `POST /api/connections/test`: Erreichbarkeit einer Modell-Schnittstelle prüfen.

### System
- `GET /health`: Healthcheck für Container und Monitoring.

### RAG und Werkzeuge
- `GET /api/rag/status`: Status des RAG-Index abrufen (Dokumentenanzahl, Chunks, Pfad).
- `POST /api/rag/folder`: Verzeichnis für Quelldokumente ändern und Reindizierung auslösen.
- `POST /api/rag/reindex`: Manuelle Reindizierung des Vektorindex anstoßen.
- `POST /api/rag/upload`: Dokument hochladen und indexieren.
- `GET /api/tools`: Liste der im System registrierten Werkzeuge abrufen.

---

## Installation und Ausführung

### Voraussetzungen
- Python 3.12 oder Docker
- Zugriff auf eine OpenAI-kompatible Schnittstelle (z.B. lokale Ollama-Instanz oder Cloud-Endpunkt)

### Ausführung mit Docker Compose
1. Container erstellen und starten:
   ```bash
   docker compose up --build
   ```
2. Web-Oberfläche aufrufen:
   `http://localhost:8000`

### Lokale Ausführung
1. Abhängigkeiten installieren:
   ```bash
   pip install -r requirements.txt
   ```
2. Umgebungsvariablen in `.env` konfigurieren (optional):
   ```env
   BASE_URL=http://localhost:11434/v1
   API_KEY=ollama
   DEFAULT_MODEL=gemma4:e4b
   ```
3. Server starten:
   ```bash
   uvicorn src.server:app --host 0.0.0.0 --port 8000 --reload
   ```
4. Alternativ das Start-Skript nutzen:
   ```bash
   ./start.sh
   ```
   Oder für die interaktive Terminal-Nutzung:
   ```bash
   python main.py
   ```
