# Initial Security Lifecycle Plan

## 1. Project Overview

The project will implement a small multi-tier application called **Private Document Processing Service**.

The application allows authenticated users to create and access their own private text documents and request an automated analysis of a selected document. The analysis will be performed by a separate processing service using a small external helper package developed as part of the project.

The main security goal is to ensure that users can access only resources they are authorized to access, including when a request passes through multiple application components.

The project will intentionally introduce selected vulnerabilities during development, demonstrate their security impact, and then correct them. The final version of the application is expected to enforce the documented security guarantees.

---

## 2. Scope

### In scope

The application will provide:

1. User authentication using seeded accounts.
2. Creation of private text documents.
3. Listing and retrieving documents owned by the authenticated user.
4. Searching documents.
5. Generation of a text analysis for a selected document.
6. Retrieval of generated analysis results.
7. One privileged administrative operation.
8. Authorization enforcement across service boundaries.
9. Automated functional and security tests.
10. Static and dependency analysis through Jenkins.

The analysis functionality will involve all three application components.

### Out of scope

The following features will not be implemented:

- graphical user interface,
- user registration,
- password recovery,
- email functionality,
- public hosting,
- real cloud deployment,
- high availability,
- large-scale performance,
- asynchronous message queues,
- Docker or other containerization,
- optional supply-chain attack experiments,
- malicious versions of the helper dependency.

The application will be operated through HTTP requests using tools such as curl, Postman, or automated tests.

---

## 3. Technology

The planned implementation will use:

- Python
- FastAPI
- Uvicorn
- SQLite
- PyJWT or another established JWT library
- pytest
- Bandit
- pip-audit
- Jenkins

The three application components will run as independent operating-system processes on separate localhost ports.

A SQLite database and local result storage will belong to the Resource Service and do not count as separate application components.

---

# 4. Architecture

The system consists of three application components.

## 4.1 Application API

Responsibilities:

- expose the public application interface,
- authenticate users,
- verify user roles,
- coordinate requests between services,
- create scoped authorization information for downstream operations.

The Application API will not directly access document storage.

---

## 4.2 Resource Service

Responsibilities:

- own private documents,
- own generated analysis results,
- store document ownership information,
- enforce authorization when protected resources are accessed,
- access the SQLite database and result files.

The Resource Service is the final security boundary protecting user-owned resources.

It must not assume that a request is authorized only because it originates from another application service.

---

## 4.3 Processing Service

Responsibilities:

- receive document-analysis jobs,
- obtain only the document required for the requested job,
- process the document,
- use the external helper package,
- return or store the generated result.

The Processing Service must not receive unrestricted authority to access all user documents.

---

## 4.4 External Helper Package

A small Python package called `textstats-lib` will be created separately from the three application services.

Its functionality will include simple text analysis such as:

- word count,
- character count,
- sentence count.

The Processing Service will install and use this package as a declared dependency.

The package will not simply be copied into the Processing Service source code.

The optional malicious supply-chain version of the dependency will not be implemented.

---

# 5. Planned Process Layout

The services will run independently, for example:

- Application API: `localhost:8000`
- Resource Service: `localhost:8001`
- Processing Service: `localhost:8002`

Example architecture:

```text
                         +------------------+
                         |       User       |
                         +--------+---------+
                                  |
                                  | HTTP
                                  v
                         +------------------+
                         | Application API  |
                         |     :8000        |
                         +----+---------+---+
                              |         |
                    HTTP      |         | HTTP
                              |         |
                              v         v
                    +-------------+   +------------------+
                    |  Resource   |<--|    Processing    |
                    |   Service   |   |     Service      |
                    |    :8001    |   |      :8002       |
                    +------+------+   +--------+---------+
                           |                    |
                           |                    |
                      SQLite/files        textstats-lib
```
