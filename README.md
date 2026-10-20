# Private Document Processing Service

This is a small Python application for private documents' management. Users can store their private text documents and generate their analysis with word, character, and sentence statistics. The project demonstrates authorization across three communicating services. Its Git history preserves the initial vulnerable implementations and their subsequent fixes.

## Architecture

The application consists of three independent processes:

| Component          | Address                 | Responsibility                                                             |
| ------------------ | ----------------------- | -------------------------------------------------------------------------- |
| Application API    | `http://127.0.0.1:8000` | Public endpoints, login, roles, and workflow coordination                  |
| Resource Service   | `http://127.0.0.1:8001` | SQLite documents, ownership checks, and stored analysis results            |
| Processing Service | `http://127.0.0.1:8002` | Document analysis using the separately installable `textstats-lib` package |

Clients should use the **Application API**. The remaining HTTP interfaces are internal application layers, even though all three processes listen on the machine's localhost in this demonstration. The **Resource Service** owns `resource_service/data/resources.db` and the generated result files. The Application API does not access SQLite directly.

The application uses **Python**, **FastAPI**, **Uvicorn**, **`sqlite3`**, **PyJWT**, **`bcrypt`**, and **`httpx`**. Tests use **`pytest`**, and CI uses **Jenkins**, **Bandit**, and **`pip-audit`**. No Docker or graphical frontend is required.

## Prerequisites

- Windows with PowerShell
- Python 3.13 (the development version used for this project)
- Git, to clone the repository
- Postman or another HTTP client

Run commands from the **repository root**, the same where this `README.md` is located.

## Installation

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
```

The `requirements-dev.txt` file also contains all the production application dependencies. The local `./textstats-lib` library directory is declared in `requirements.txt` and is installed through pip as a separate Python package.

## Seeding data

With the Resource Service stopped, run:

```powershell
python -m resource_service.seed
```

**Warning:** This command resets the Resource Service database **and saved analysis-result files**, and only seeds the predefined data. It should be used to restore a predictable test state of the database. Do not run it to start an existing application with data you want to preserve.

The seed creates two example documents: document `1` belonging to `alice`, and document `2` belonging to `bob`. The user accounts themselves are predefined in `application_api/users.py`.

| Username | Password        | Role  |
| -------- | --------------- | ----- |
| `alice`  | `AlicePass123!` | USER  |
| `bob`    | `BobPass123!`   | USER  |
| `admin`  | `AdminPass123!` | ADMIN |

These credentials and documents are synthetic and intended **only for local testing**.

## Run the application

Open **three PowerShell terminals** in the repository root and activate `.venv` in each one:

```powershell
.\.venv\Scripts\Activate.ps1
```

**Terminal 1 - Application API**

```powershell
$env:JWT_SECRET = 'local-software-security-jwt-key'
$env:RESOURCE_JWT_SECRET = 'local-resource-service-jwt-key'
$env:PROCESSING_JWT_SECRET = 'local-processing-service-jwt-key'
python -m uvicorn application_api.main:app --host 127.0.0.1 --port 8000
```

**Terminal 2 - Resource Service**

```powershell
$env:RESOURCE_JWT_SECRET = 'local-resource-service-jwt-key'
python -m uvicorn resource_service.main:app --host 127.0.0.1 --port 8001
```

**Terminal 3 - Processing Service**

```powershell
$env:PROCESSING_JWT_SECRET = 'local-processing-service-jwt-key'
python -m uvicorn processing_service.main:app --host 127.0.0.1 --port 8002
```

Signing secrets must stay consistent in the entire application. The same **`RESOURCE_JWT_SECRET`** needs to be used in both Application API and Resource Service. Same goes for the **`PROCESSING_JWT_SECRET`**, the same value has to be declared in both Application API and Processing Service. **Presented values are examples for a local demonstration, not production credentials.**

## API Usage

All operations below use the Application API at `http://127.0.0.1:8000`.

In order to perform any meaningful operations, log in first:

```http
POST /login
Content-Type: application/json

{"username":"alice","password":"AlicePass123!"}
```

Copy the returned `access_token`. Supply it in all later requests as `Authorization: Bearer <access_token>`.

| Method | Endpoint                            | Purpose                                           |
| ------ | ----------------------------------- | ------------------------------------------------- |
| `POST` | `/login`                            | Authenticate and receive a JWT                    |
| `GET`  | `/me`                               | Get the authenticated user's identity and role    |
| `POST` | `/documents`                        | Create a document from JSON `title` and `content` |
| `GET`  | `/documents`                        | List the current user's documents                 |
| `GET`  | `/documents/{document_id}`          | Retrieve an authorized document                   |
| `GET`  | `/documents/search?q=Alice`         | Search documents belonging to the current user    |
| `POST` | `/documents/{document_id}/analysis` | Request document analysis                         |
| `GET`  | `/analysis-results/{result_id}`     | Retrieve an authorized analysis result by ID      |
| `GET`  | `/admin/documents/metadata`         | View document metadata **(ADMIN role only)**      |

## Run tests

Start all three development services as described above, with the seeded documents available. In a fourth PowerShell terminal, activate `.venv`:

```powershell
python -m venv .venv
```

and run:

```powershell
python -m pytest -v
```

To run the suites separately:

```powershell
python -m pytest -v -m 'not security'
python -m pytest -v -m security
```

The test suite contains **six functional tests and four security tests**. The security tests cover all the deliberately planted vulnerabilities: **missing document authorization (CWE-862)**, **SQL injection (CWE-89)**, **path traversal (CWE-22)**, and the **service-composition vulnerability**.
