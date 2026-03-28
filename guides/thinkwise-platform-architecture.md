# The Thinkwise Platform — How It All Fits Together
*A practical guide for consultants*

---

## Part 1: The Big Picture

### 1.1 What Is the Thinkwise Platform?

The Thinkwise Platform is a model-driven enterprise low-code development environment. Instead of writing millions of lines of code to build an application, you create a model (a blueprint) that describes what your application should do. The platform then interprets that model at runtime to produce a fully working application — complete with a database, user interfaces, business logic, and integration APIs.

This is fundamentally different from traditional development. In a conventional setup, code IS the application. In Thinkwise, the model IS the application. The code (SQL procedures, views, etc.) is generated from the model and is secondary to it. This means you can change the underlying technology without rewriting the application — the model stays the same, only the interpretation changes.

### 1.2 The Five Core Components

| Component | What It Does | When It's Used |
|---|---|---|
| Software Factory (SF) | The development studio where you design your model: data, UI, processes, business logic | Development & Testing |
| Intelligent Application Manager (IAM) | Manages deployed models, handles user authorization, preferences, and application configuration | Acceptance & Production |
| Indicium Application Tier | The central service tier / API hub. All traffic between the UI and the database flows through here | All environments |
| User Interfaces (GUIs) | The presentation layer: Universal GUI (web/PWA) and legacy Windows GUI | All environments |
| Upcycler | Converts legacy applications (RPG, COBOL, Oracle, Uniface, etc.) into Thinkwise models | Migration projects |

### 1.3 The Three-Tier Architecture

Every Thinkwise application follows a classic three-tier architecture, but with a twist: the application isn't hard-coded — it's interpreted from a model at runtime.

```
Presentation Tier (GUI) → Application Tier (Indicium) → Data Tier (SQL Server / DB2 / Oracle)
```

The user never talks directly to the database. Everything passes through Indicium, which enforces security, authorization, and business rules.

Historically, Thinkwise used a two-tier architecture where the Windows GUI talked directly to the database. This is being fully phased out — the 2025 platform releases are the last to support 2-tier, and from 2026 onwards, 3-tier through Indicium is mandatory. Many existing customer environments may still be running 2-tier.

In a 2-tier setup, the GUI needs a direct database connection (typically requiring a VPN). In 3-tier, Indicium sits in between, which means applications can run from anywhere — and you get proper row-level, column-level, and even cell-level authorization without users needing direct database access.

### 1.4 How Components Communicate

- **Development:** A developer designs a model in the Software Factory. The SF stores this model in its own SQL Server database.
- **Creation:** When the model is ready, the developer runs the Creation process in the SF. This generates a platform-specific definition, validates it, generates SQL source code (CREATE scripts, stored procedures, views, triggers, etc.), and executes it against a development database.
- **Synchronization:** The model is synchronized (pushed) from the Software Factory to an IAM database — effectively "publishing" your blueprint.
- **Runtime:** Indicium reads the model from IAM, interprets it, and serves it to the GUI. End users interact through the GUI, which sends requests to Indicium, which talks to the application database.

> **Key insight:** The model never lives inside the application database itself. The application database only contains the actual tables, stored procedures, and data. The "instructions" for how to render screens, what fields to show, which buttons to display — all of that lives in IAM and is interpreted by Indicium and the GUI at runtime.

---

## Part 2: The Databases — Who Stores What

### 2.1 Database Landscape Overview

| Database | Purpose | Where It Lives |
|---|---|---|
| Software Factory DB | Stores the model/blueprint: all tables, columns, domains, references, screen types, process flows, business logic templates, translations, and more | Development environment only |
| IAM_DEV | The IAM for the development environment. Manages authorization, licensing, and configuration for the SF and development application(s) | Development environment |
| IAM (Test/Acc/Prod) | The IAM for each downstream environment. Receives the model via synchronization and manages users, roles, and preferences for that environment | One per T/A/P environment |
| Application DB (Dev) | The actual running application database in development. Contains the tables, data, stored procedures, views, and triggers generated from the model | Development environment |
| Application DB (Test/Acc/Prod) | The application database for each downstream environment. Same structure as dev, but with environment-specific data | One per T/A/P environment |
| Branch DBs | When a developer creates a branch in the SF, a separate application database is spun up for that branch, allowing isolated development | Development environment (temporary) |

### 2.2 The Software Factory Database

The SF database is a SQL Server database (always — regardless of what platform the end application targets) and stores:

- The data model definition (tables, columns, domains, references, indexes)
- User interface definitions (screen types, subjects, menus, themes, translations)
- Business logic templates and control procedures
- Process flow definitions (both user and system flows)
- Task and report definitions
- Requirements, work items, business process diagrams
- Validation rules and enrichment configurations
- Version history via temporal tables (system-versioned)

**Version control:** The SF database uses temporal tables for version control. Only the latest version of the model is stored in the main tables, while all historical versions are automatically maintained in corresponding history tables. When you "Generate the Definition" during Creation, a moment in time is marked in `model_vrs`, effectively creating a model version.

**Branching:** When a developer creates a branch, the SF doesn't duplicate the entire model database. It records a point in time and creates a new application database for that branch. The model data in the SF is shared; the branch isolation happens at the temporal level. This is why branches are lightweight — only the history tables grow.

### 2.3 The IAM Database

IAM serves two critical functions:

- **Model storage for runtime:** When you synchronize from the SF to IAM, the model is pushed here. Indicium and the GUIs read from IAM to know how to render and behave.
- **Authorization and configuration:** User accounts, roles, permissions, application configurations, theme settings, file storage locations, scheduled system flows, and user preferences all live in IAM.

You typically have at least two IAM databases:

- **IAM_DEV:** Serves the development environment. The SF itself is registered as an application in IAM_DEV (application ID: `SQLSERVER_SF`). Indicium in the dev environment connects to IAM_DEV.
- **IAM (production):** Serves the production environment(s). You may have separate IAMs for Test, Acceptance, and Production, or share one IAM across some environments.

> **Why is IAM always SQL Server?** Even if your end application runs on DB2 (AS400) or Oracle, both the Software Factory and IAM always use SQL Server. This is a platform-level design decision. Only the end application database can target other platforms.

### 2.4 The Application Database

This is the database your end users actually work with. It contains:

- The physical tables defined in your data model
- Views generated from the model
- Stored procedures (generated business logic based on your templates and control procedures)
- Triggers (insert, update, delete triggers as defined in the model)
- Functions and defaults
- Indexes (both model-defined and automatically generated)
- The actual business data

**The application database is generated, not designed by hand.** When you run the Creation process, the SF compares your current model to the previous version, performs a difference analysis, and generates SQL scripts to create or upgrade the database structure. Data is preserved during upgrades — tables are renamed, new tables are created, data is migrated, and old tables are cleaned up.

The application database can run on SQL Server, DB2 for IBM i (AS400), or Oracle Database.

### 2.5 Minimum Database Count Per Environment

| Environment | Minimum Databases | What They Are |
|---|---|---|
| Development | 3+ databases | SF DB + IAM_DEV + at least 1 application DB (more with branches) |
| Test | 2 databases | IAM_TEST + Application DB |
| Acceptance | 2 databases | IAM_ACC + Application DB |
| Production | 2 databases | IAM_PROD + Application DB |

In Azure cloud deployments, this database count matters significantly for cost. Azure SQL Database works well for fixed environments (Test, Production), but Azure SQL Managed Instance is often a better fit for development where branches create temporary databases.

---

## Part 3: Deep Dive Into Each Component

### 3.1 The Software Factory — Your Development Workbench

**Specification (the "what")**
- Business Processes — function flow diagrams
- Requirements — formal user/system requirements linked to work items
- Features & Iterations — group work into releases, sprints, or modules
- Work Items & Taskboard — track development tasks (like a built-in Jira)

**Modeling (the "how")**
- **Data Model** — design tables, columns, domains, and references using a graphical modeler
- **User Interface** — design screen types, assign them to subjects, configure menus, define themes, set up translations
- **Processes** — design process flows (user-interactive and background), tasks, and reports
- **Business Logic** — write control procedures using SQL templates that hook into pre-defined program objects (before/after insert, update, delete, etc.)

**Enrichment (the "accelerators")**
- Model enrichments — automated model improvements (generate missing indexes, add trace columns)
- AI-powered enrichments — use LLMs to generate descriptions, translations, and code summaries
- ThinkStore — built-in marketplace of ready-made solutions
- Dynamic modeling — SQL-based meta procedures that extend the model programmatically during generation

**Quality & Deployment**
- **Validations** — hundreds of built-in rules that check model quality; custom validations possible
- **Unit Tests** — test business logic in isolation
- **Smoke Tests** — run against a representative dataset to catch issues with real data (especially important for 3-tier transition)
- **Creation** — the multi-step process that turns your model into a running application
- **Synchronization to IAM** — push the model to an IAM database for downstream environments
- **Deployment Packages** — bundle everything for deployment via the Deployment Center

**The Creation Process — what actually happens:**
1. **Generate Definition:** The platform-independent model (PIM) is transformed into a platform-specific model (PSM). Dynamic model procedures run. A model version is timestamped.
2. **Validate Definition:** Hundreds of validation rules check the model for errors.
3. **Generate Source Code:** SQL scripts are compiled from program objects — CREATE scripts for new databases, UPGRADE scripts for existing ones. Business logic from templates is assembled into stored procedures.
4. **Execute Source Code:** The scripts are run against the target database. For upgrades, tables are renamed, new structures created, data migrated, and old tables dropped.
5. **Run Unit Tests:** Regression tests verify that existing business logic still works correctly.

### 3.2 Indicium — The Central Nervous System

Indicium is often described as "just the API layer" but it's really the central hub that makes everything work.

**What Indicium does:**
- Interprets the model from IAM at runtime and exposes it as a REST API (using OData protocol)
- Handles all authentication (IAM credentials, OpenID, ADFS, SSO, multi-factor)
- Enforces authorization at entity, row, column, and cell level
- Executes system flows (background process flows) on a schedule
- Handles all Creation and deployment jobs (the GUI just submits requests; Indicium does the work)
- Hot-reloads model changes without downtime — if you update the model in IAM, Indicium picks up the changes automatically
- Provides connectors for integration with AI services, Office 365/Exchange, third-party APIs, and more
- Supports webhooks so external applications can push data into Thinkwise applications

**Technology:** Indicium is an ASP.NET Core application, deployed on IIS. It's stateless by design, meaning you can horizontally scale it — run multiple Indicium instances behind a load balancer. Also suitable for containerized deployments (Docker/Kubernetes).

**Two variants:**

| Variant | Supports | Use Case |
|---|---|---|
| Indicium (Full) | Universal GUI, APIs, system flows, OpenID, full feature set | Standard deployment for 3-tier environments |
| Indicium Basic | Windows GUI and Mobile GUI only, no system flows or OpenID | Legacy / transitional environments (being phased out) |

**Connection pattern:**
- Indicium connects to IAM to read the model and authorization data
- Indicium connects to the application database to execute queries and stored procedures on behalf of the user
- The GUI connects only to Indicium — never directly to any database

### 3.3 The Intelligent Application Manager (IAM) — The Control Tower

**Core responsibilities:**
- **Model Management:** Stores synchronized models from the SF. Multiple models and branches can be deployed in a single IAM.
- **Authorization:** Manages users, user groups, roles, and permissions. Roles determine which tables, columns, tasks, reports, and processes each user can access.
- **Application Configuration:** Runtime configurations define which database an application points to.
- **User Preferences:** End users can customize their experience (column widths, sort orders, filter presets, etc.).
- **Scheduling:** System flows can be scheduled in IAM to run automatically at defined intervals.
- **File Storage Configuration:** Defines where generated scripts, reports, and other files are stored (local file system, Azure Files, AWS S3).
- **Theme & Branding:** Override themes, embed custom CSS, configure login page appearance.

> **IAM is itself a Thinkwise application.** It has its own model in the SF, its own IAM entry (it manages itself), and it runs through Indicium like any other application. The same is true for the Software Factory.

### 3.4 The Universal GUI — The Face of Your Application

The Universal GUI is a Progressive Web App (PWA) built with React, following Material Design principles.

**Key characteristics:**
- Fully responsive — works on desktop, tablet, and mobile with automatic layout adaptation
- Runs in any modern browser (Chrome recommended for best performance)
- Can be installed as a native-like app on any device via PWA install
- Deployed as a web application on IIS, alongside Indicium
- All communication goes through Indicium's REST API — the GUI has no database connection

**As of Platform 2026.1:** The Software Factory is now available in the Universal GUI. The Windows GUI is no longer supported from this release onwards. The entire Thinkwise ecosystem is now browser-based.

**How the GUI renders a screen:**
1. User navigates to a subject in the menu
2. The GUI asks Indicium for the subject's metadata: which screen type to use, which columns to show, what controls to render, what the labels are (in the user's language)
3. Indicium reads this from IAM (the synchronized model) and returns it
4. The GUI builds the screen dynamically based on this metadata, then requests the actual data via Indicium's OData API
5. When the user performs an action (insert, update, delete, run a task), the GUI sends the request to Indicium, which executes the corresponding stored procedure and returns the result

---

## Part 4: The DTAP Lifecycle

### 4.1 Development

In the development environment you have: SF database, IAM_DEV database, Indicium instance, GUI, and one or more application databases (main branch + feature branches).

Developers work in branches. Each branch gets its own application database, allowing parallel development without interference. When a feature branch is complete, it's merged back into the MAIN branch through the SF's merge process.

### 4.2 Moving to Test / Acceptance / Production

- **Option A — Direct synchronization:** The SF synchronizes a model directly to a target IAM database. The application database is upgraded using the generated code files.
- **Option B — Deployment packages:** The SF bundles everything (install scripts, upgrade scripts, IAM sync scripts, manifest) into a deployment package. The Thinkwise Deployment Center applies it to the target environment via GUI wizard or CLI. **This is the recommended approach for production deployments and CI/CD pipelines.**

### 4.3 Runtime Configurations

A Runtime Configuration in the SF / IAM defines which database server and database name an application should connect to. This is how the same model can point to different databases in different environments:

- Runtime config "DEV" → SQL Server A, database "MYAPP_DEV"
- Runtime config "PROD" → SQL Server B, database "MYAPP_PROD"

---

## Part 5: Integration & External Connectivity

### 5.1 The OData API

Indicium automatically exposes every Thinkwise application as an OData REST API. From the moment you model a table in the SF, it's accessible via a standard web service — no extra configuration needed. Third-party tools (Power BI, custom frontends, integration platforms) can query and manipulate data through this API. The API supports full CRUD operations, filtering, sorting, pagination, and function imports (for tasks and process actions).

### 5.2 Process Flows as Integration Points

- **User flows:** Guide end users step-by-step through a process in the GUI.
- **System flows:** Run in the background, scheduled or triggered. These are your integration workhorses — sync data, call external APIs, send emails, generate reports, move files.

System flow process action types: HTTP connector / Web connections, database connector, file operations, email operations, application connector (call other Thinkwise Indicium APIs), Execute SQL, subflows.

### 5.3 Exchange Integration

Thinkwise applications can synchronize appointments, tasks, emails, and contacts with Microsoft Exchange / Office 365. Incoming and outgoing emails can be linked to business records, making the full communication history visible in the application.

### 5.4 Reporting

DevExpress reports are the recommended solution for 3-tier / Universal GUI — they integrate seamlessly and don't require database or report drivers on the client. Crystal Reports is still supported for legacy setups but doesn't work in cloud PaaS deployments. For fully automated reporting, the ThinkStore offers a Reporting Service solution that adds a reporting queue to your model.

---

## Part 6: Key Concepts for Solution Architects

### 6.1 Model Interpretation vs. Code Generation

| Approach | Used For | Why |
|---|---|---|
| Model Interpretation | UI rendering, API exposure, authorization enforcement, screen layout, navigation, process flow execution | Allows instant changes — update the model, and the UI/API reflects it immediately (hot-reload) |
| Code Generation | Database schema (CREATE/UPGRADE scripts), stored procedures, views, triggers, functions | SQL code needs to exist in the database — you can't "interpret" a stored procedure at runtime |

Indicium and the GUI are model interpreters. The Creation process is a code generator.

### 6.2 Domains

Domains are a fundamental abstraction. A domain defines a data type combined with a control type. For example, a domain "Email" might specify VARCHAR(255) as the data type and a text input with email validation as the control. By assigning a domain to a column, you ensure consistent data types and UI controls across your entire application. Change a domain once, and every column using it updates accordingly.

### 6.3 Base Models

Base models are reusable foundation models that your application can inherit from — like template/base classes in programming. Thinkwise provides standard base models (e.g., for verification, system configuration) and you can create your own. When a base model is updated, all models that inherit from it benefit from the changes after regeneration.

### 6.4 The Role of SQL

Even though Thinkwise is a low-code platform, SQL is everywhere under the hood. All business logic beyond what can be modeled is written in T-SQL (or the equivalent for DB2/Oracle). Stored procedures, views, functions, and triggers are the backbone of every Thinkwise application.

Business logic in the SF follows a template-based approach. You define templates containing SQL code with placeholders, then assign those templates to program objects (e.g., "after insert on table X"). During the Creation process, the SF assembles these templates into complete stored procedures.

### 6.5 Conditional Layouts & Screen Types

Screen types define the visual layout of a subject (how tables, forms, tabs, and grids are arranged). In the Universal GUI, what were previously form "tabs" now appear as collapsible sections. Conditional layouts allow you to dynamically change the appearance of grids, forms, tasks, and reports based on data conditions — for example, highlighting overdue orders in red.

### 6.6 Custom Components

When standard Thinkwise UI controls aren't enough, you can embed custom web components into your application. These are mini web applications (HTML/JS/CSS) that run inside the Universal GUI and communicate with the Thinkwise application through a defined API. Perfect for specialized visualizations, embedded third-party tools, or unique interaction patterns.

---

## Part 7: Quick Reference

### 7.1 Component-to-Technology Mapping

| Component | Technology | Deployment |
|---|---|---|
| Software Factory | Thinkwise application on SQL Server | SQL Server + Indicium + GUI |
| IAM | Thinkwise application on SQL Server | SQL Server + Indicium + GUI |
| Indicium | ASP.NET Core | IIS (Windows), Docker/K8s possible |
| Universal GUI | React PWA | IIS (static web app), modern browser |
| Windows GUI (legacy) | .NET Framework desktop client | Direct install or RDS/Citrix/VDI |
| Application DB | SQL Server, DB2 for IBM i, or Oracle | Depends on customer infrastructure |
| Deployment Center | .NET application | GUI wizard or CLI for automated deployment |

### 7.2 URL Patterns

- Universal GUI: `https://<server>/<indicium-alias>/<iam-alias>/<app-alias>`
- Indicium API: `https://<server>/<indicium-alias>/iam/<app-alias>/<entity>`
- SF in Universal GUI (2026.1+): `https://<server>/indicium/iam/sf`

### 7.3 Key Database Objects

| In the SF Database | In the Application Database | In IAM |
|---|---|---|
| `tab` (tables) | Your modeled tables | `usr` (users) |
| `col` (columns) | Your stored procedures | `role_tab` (role permissions) |
| `ref` (references) | Views | `appl` (applications) |
| `dom` (domains) | Functions | `model` (models) |
| `cntrl_proc` (control procedures) | Triggers | `branch` (branches) |
| `proc_flow` (process flows) | Indexes | `appl_lang` (languages) |
| `model_vrs` (model versions) | User-defined types | `usr_pref` (user preferences) |

### 7.4 Where to Go From Here

- [Thinkwise Documentation](https://docs.thinkwisesoftware.com) — the authoritative reference
- [Thinkwise Community](https://community.thinkwisesoftware.com) — forums, blogs, release notes, feature requests
- [Release Notes](https://docs.thinkwisesoftware.com/blog) — essential reading for staying current
- ThinkStore — browse available solutions to understand common patterns
