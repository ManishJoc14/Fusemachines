
---

## 1. FastAPI Project Structure
- **`main.py`** – Application entry point; creates the FastAPI app instance.
- **`create_app()`** – App factory pattern used to configure the application in one place.
- **`api/v1/router.py`** – Collects versioned routers and keeps endpoints organized.
- **`core/`** – Shared app settings, logging, and configuration.
- **`db/`** – Database engine, session handling, and base model setup.
- **`models/`** – SQLAlchemy ORM models that map to database tables.
- **`schemas/`** – Pydantic models for request and response validation.
- **`services/`** – Business logic layer between routes and the database.

---

## 2. Application Lifecycle and Configuration
- **Lifespan events** – Startup and shutdown logic handled with `@asynccontextmanager`.
- **Startup tasks** – Initialize logging and create database tables with `Base.metadata.create_all`.
- **Shutdown tasks** – Dispose the async engine cleanly.
- **Environment settings** – Loaded with Pydantic settings from `.env`.
- **Why it matters:** Centralized config makes the app easier to deploy and maintain.

---

## 3. API Design and REST Endpoints
- **GET** – Retrieve resources.
- **POST** – Create new resources.
- **PATCH** – Partially update existing resources.
- **DELETE** – Remove resources.
- **Path parameters** – Use values like `/{customer_id}` to identify a record.
- **Nested routes** – Use routes like `/{customer_id}/orders` and `/{customer_id}/payments` for related data.
- **`response_model`** – Controls the shape of the API response and improves validation.
- **`HTTPException`** – Returns proper error responses, such as `404 Not Found` when a record does not exist.

---

## 4. Request Dependencies and Database Sessions
- **`Depends(get_db)`** – Injects a database session into each route.
- **`AsyncSession`** – Async SQLAlchemy session used for database operations.
- **Session flow:** create session -> yield to route -> rollback on error -> close session.
- **`autoflush=False`** – Prevents automatic flushes before queries.
- **`expire_on_commit=False`** – Keeps objects usable after `commit()`.
- **Why it matters:** Each request gets a safe, temporary DB connection.

---

## 5. Schemas and Validation
- **`BaseModel`** – Pydantic base class for validation and serialization.
- **Base schema** – Shared fields used by create and response models.
- **Create schema** – Required fields for `POST` requests.
- **Update schema** – Optional fields for partial `PATCH` updates.
- **Response schema** – Includes database-generated fields such as primary keys.
- **`from_attributes = True`** – Allows Pydantic to read from ORM objects directly.
- **`model_dump()`** – Converts validated data into a dictionary for model creation or updates.

---

## 6. SQLAlchemy ORM Models
- **`Base`** – Shared declarative base for all table models.
- **`Column(...)`** – Defines table fields and constraints.
- **Primary keys** – Unique record identifiers, such as `customerNumber`.
- **Nullable fields** – Optional database columns like `addressLine2`, `state`, and `postalCode`.
- **Foreign keys** – Represent relationships between tables, such as `salesRepEmployeeNumber`.
- **Data types** – Use `String`, `Integer`, and `Numeric` to match stored values.
- **Why it matters:** ORM models define the database structure the service layer works with.

---

## 7. Service Layer Pattern
- **Route handlers** – Keep HTTP concerns only: request parsing, status codes, and responses.
- **Service classes** – Contain reusable business logic and database queries.
- **Separation of concerns** – Makes code easier to test and maintain.
- **Example methods** – `get_all_customers()`, `create_customer()`, `update_customer()`, `delete_customer()`.
- **Relationship queries** – Fetch related orders and payments through the service layer.

---

## 8. Querying and CRUD Operations
- **`select(Model)`** – Build SQLAlchemy select queries.
- **`.where(...)`** – Filter records by condition.
- **`result.scalars().all()`** – Return all matching ORM objects.
- **`result.scalars().first()`** – Return the first match or `None`.
- **`add()` + `commit()`** – Insert a new row.
- **`refresh()`** – Reload the object after commit so generated values are available.
- **`delete()` + `commit()`** – Remove a row safely.
- **Update flow:** fetch object -> apply changes -> commit -> refresh.

---

## 9. Logging and Error Handling
- **Logging** – Track app events and database actions for debugging.
- **Info logs** – Useful for successful operations like fetch, create, and update.
- **Warning logs** – Useful when a record is not found.
- **HTTP status codes** – Communicate success and failure clearly to API clients.
- **Why it matters:** Logging and explicit errors make API behavior easier to trace.

---

## 10. CORS and Frontend Integration
- **CORS middleware** – Allows approved frontend origins to call the API.
- **`allow_origins`** – Restricts which clients can access the backend.
- **`allow_credentials`** – Supports authenticated browser requests when needed.
- **`allow_methods=["*"]`** – Permits all HTTP methods during development.
- **Why it matters:** Frontend apps often run on a different port or domain than the API.

---

## 11. Data Modeling Checklist
- ✓ Is the endpoint using the correct HTTP method?
- ✓ Are request and response schemas separated?
- ✓ Is the DB session managed per request?
- ✓ Are missing records returning `404`?
- ✓ Are nullable fields marked correctly in the model?
- ✓ Are create and update flows validated before hitting the database?
- ✓ Is the service layer handling business logic instead of the route?

---

## One-line summary of all terms

| Term | Meaning |
|------|---------|
| FastAPI | Python web framework for APIs |
| App factory | Function that creates and configures the app |
| Lifespan | Startup/shutdown lifecycle hooks |
| CORS | Browser security policy for cross-origin requests |
| Dependency injection | FastAPI pattern for providing shared resources |
| `Depends(get_db)` | Inject a database session into a route |
| `AsyncSession` | Async SQLAlchemy database session |
| Pydantic `BaseModel` | Schema validation and serialization model |
| `response_model` | Controls and validates API output |
| `HTTPException` | FastAPI error response helper |
| ORM model | Python class mapped to a database table |
| Primary key | Unique identifier for a database row |
| Foreign key | Column that references another table |
| Nullable field | Column allowed to store `NULL` |
| Service layer | Business logic between routes and DB |
| `select()` | Build a SQLAlchemy query |
| `scalars().all()` | Return all ORM rows from a query |
| `scalars().first()` | Return the first matching row |
| `commit()` | Save database changes |
| `refresh()` | Reload object values from DB |
| Logging | Record runtime events for debugging |
| CORS middleware | Allows approved browser clients to call API |

---