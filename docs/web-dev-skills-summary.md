# Web-Entwicklung – Vollständige Skill-Übersicht

---

## 1. Frontend

### HTML
- Semantische Elemente: `<header>`, `<main>`, `<section>`, `<article>`, `<nav>`, `<footer>`
- Formulare & Eingaben: `<form>`, `<input>`, `<select>`, `<textarea>`, Validierungsattribute
- Barrierefreiheit (Accessibility / a11y): ARIA-Rollen, `alt`-Texte, Tab-Reihenfolge, `role`, `aria-label`
- SEO-Grundlagen: Meta-Tags, Open Graph, strukturierte Daten (Schema.org)
- HTML5 APIs: `<canvas>`, `<video>`, `<audio>`, `<dialog>`, `<details>`

### CSS
- Box-Modell: `margin`, `padding`, `border`, `box-sizing: border-box`
- Layout: Flexbox (Haupt- und Querachse), CSS Grid (Tracks, Areas, `fr`-Einheit)
- Position: `static`, `relative`, `absolute`, `fixed`, `sticky`
- Responsive Design: Mobile-First, Media Queries, `clamp()`, fluid typography, `container queries`
- CSS-Variablen (`--custom-properties`), Animationen (`@keyframes`), Transitions
- Methodologien: BEM, SMACSS, CSS Modules, Tailwind CSS, Utility-First
- Moderne Features: `:has()`, `@layer`, `subgrid`, `aspect-ratio`

### JavaScript (ES6+)
- Kernkonzepte: Closures, Hoisting, Scope (var/let/const), Prototypen, Event Loop, Call Stack
- Asynchron: Promises, `async/await`, `fetch()`, `AbortController`, Error Handling
- DOM-Manipulation: `querySelector`, `querySelectorAll`, Event-Listener, Event Delegation
- Template Literals, Destructuring, Spread/Rest, Optional Chaining (`?.`), Nullish Coalescing (`??`)
- Module: `import/export`, Dynamic Imports (`import()`), Tree Shaking
- Wichtige APIs: LocalStorage, SessionStorage, IntersectionObserver, ResizeObserver, Web Workers, IndexedDB
- Funktionale Konzepte: `map`, `filter`, `reduce`, `flatMap`, Immutabilität

### TypeScript
- Typen: `string`, `number`, `boolean`, `any`, `unknown`, `never`, `void`
- Interfaces vs. Types, `extends`, `implements`
- Generics: `<T>`, generische Funktionen und Klassen
- Utility Types: `Partial<T>`, `Required<T>`, `Pick<T,K>`, `Omit<T,K>`, `Record<K,V>`, `Readonly<T>`
- Type Guards: `typeof`, `instanceof`, Custom Guards (`is`-Syntax)
- `strictMode`, `tsconfig.json`, Declaration Files (`.d.ts`)
- Integration mit React (`FC`, `ReactNode`, Event-Typen) und Node.js

### Web-Grundlagen
- HTTP/HTTPS: Methoden (GET, POST, PUT, PATCH, DELETE, HEAD, OPTIONS), Status-Codes (1xx–5xx)
- HTTP/2 & HTTP/3: Multiplexing, Header Compression, QUIC-Protokoll
- Browser-Rendering: Critical Rendering Path, Reflow vs. Repaint, Compositing
- Performance: Lazy Loading, Code Splitting, Tree Shaking, `preload`/`prefetch`, Caching (Cache-Control, ETags)
- Web-Sicherheit: CORS, Content Security Policy (CSP), HTTPS/TLS, XSS, CSRF, Clickjacking
- Browser DevTools: Performance-Profiling, Memory-Leaks finden, Network-Tab, Lighthouse-Audit, React/Vue DevTools

### UI/Design
- Design-Tokens: Farben (Palette, semantische Farben), Typografie, Abstände, Border-Radien, Schatten
- Figma: Komponenten, Auto Layout, Prototyping, Variants, Design-Tokens Export
- Design-Systeme: Atomic Design (Atoms → Organisms → Pages), Storybook, Style-Guides
- UX-Prinzipien: Affordance, Feedback, Konsistenz, Progressive Disclosure, Fehlertoleranz
- Accessibility Design: Kontrastverhältnisse (WCAG AA/AAA), Tastaturnavigation, Screenreader-Tests

### Components
- Komponentenarchitektur: Props, State, Events, Slots, Composition
- **React**: `useState`, `useEffect`, `useContext`, `useMemo`, `useCallback`, `useRef`, Custom Hooks
- **Vue 3**: Composition API (`setup`, `ref`, `reactive`, `computed`, `watch`), Pinia, Teleport
- Patterns: HOC (Higher-Order Components), Render Props, Compound Components, Headless Components
- State Management: Redux Toolkit, Zustand, Jotai, Pinia, TanStack Query (Server State)
- Meta-Frameworks: **Next.js** (SSR, SSG, ISR, App Router), **Nuxt 3**, **SvelteKit**

---

## 2. Backend

### Server
- **Node.js**: Event-driven Architektur, Non-blocking I/O, `EventEmitter`, Streams, Buffer
- **Express.js**: Middleware-Konzept, Request/Response-Zyklus, Error Middleware
- **Fastify**: Schema-basierte Validierung, performance-optimiert, Plugin-System
- **NestJS**: TypeScript-first, Module/Controller/Service-Muster, Decorators, Guards, Interceptors
- **Hono**: ultraleichter Framework für Edge/Bun/Deno
- Moderne Laufzeiten: **Bun** (schneller npm-Ersatz), **Deno** (sicher, eingebaut TypeScript)

### Routing
- RESTful Routing: Ressourcen-basierte URL-Struktur (`/users/:id/posts`)
- Router-Middleware: Gruppen, Guards, Parameter-Validierung (zod, joi, yup)
- Wildcard- & Nested-Routen, Route Guards, Middleware-Reihenfolge
- GraphQL-Routing: Resolver-basiert, kein URL-Routing

### Authentication & Authorization
- Session-basiert: serverseitige Sessions + Cookies (HttpOnly, Secure, SameSite=Strict)
- Token-basiert: **JWT** (Header.Payload.Signature), Refresh Token Rotation, Token Blacklisting
- **OAuth 2.0 / OpenID Connect**: Authorization Code Flow, PKCE, Implicit Flow (veraltet)
- Passwort-Sicherheit: bcrypt (10–12 Runden), argon2, Salt, Pepper
- **MFA**: TOTP (Google Authenticator), WebAuthn/Passkeys, SMS (unsicher, fallback only)
- RBAC (Role-Based Access Control) & ABAC (Attribute-Based)
- Bibliotheken: Passport.js, Auth.js/NextAuth, Lucia, Clerk, Supabase Auth

### APIs
- **REST**: Status-Codes, HATEOAS, Versionierung (`/api/v1/`), Pagination (Cursor, Offset)
- **GraphQL**: SDL, Queries, Mutations, Subscriptions, DataLoader (N+1-Lösung), Persisted Queries
- **gRPC**: Protocol Buffers (`.proto`), Unary/Streaming, hohe Performance für interne Services
- **WebSockets**: bidirektionale Kommunikation, `socket.io`, Heartbeat/Reconnect-Logik
- **Server-Sent Events (SSE)**: One-Way-Streams, einfacher als WebSockets
- **tRPC**: End-to-End-Typsicherheit zwischen Next.js Frontend und Backend
- Rate Limiting, API-Keys, Throttling, Circuit Breaker

### API-Dokumentation
- **OpenAPI 3.x / Swagger**: Schema-Definition, automatische Docs (Swagger UI, Redoc)
- **Postman / Insomnia**: API Testing, Collections, Environments, Mock Servers
- **Zod**: Schema-Validierung + automatische TypeScript-Typen

---

## 3. Datenbanken

### SQL
- Grundlagen: DDL (`CREATE`, `ALTER`, `DROP`), DML (`SELECT`, `INSERT`, `UPDATE`, `DELETE`)
- Joins: `INNER`, `LEFT`, `RIGHT`, `FULL OUTER`, `CROSS JOIN`, `SELF JOIN`
- Aggregatfunktionen: `COUNT`, `SUM`, `AVG`, `MIN`, `MAX`, `GROUP BY`, `HAVING`
- Fensterfunktionen: `ROW_NUMBER()`, `RANK()`, `LAG()`, `LEAD()`, `OVER (PARTITION BY ...)`
- Transaktionen: ACID (Atomicity, Consistency, Isolation, Durability), `BEGIN`, `COMMIT`, `ROLLBACK`
- Indizes: B-Tree, Hash, GIN/GiST (PostgreSQL), Composite Indexes, Partial Indexes, Index-Only Scans
- **PostgreSQL**: JSONB, Arrays, Full-Text Search, Row-Level Security, Extensions (pgvector)
- **MySQL/MariaDB**: Storage Engines (InnoDB), Replikation
- **SQLite**: serverlos, ideal für lokale Entwicklung und mobile Apps

### NoSQL
- **Dokumentenorientiert – MongoDB**: Dokumente, Collections, Aggregation Pipeline, `$match`, `$group`, `$lookup`, `$unwind`
- **Key-Value – Redis**: Strings, Hashes, Lists, Sets, Sorted Sets; Caching, Pub/Sub, Rate Limiting, Sessions
- **Column-Family – Cassandra**: CQL, Partitionierungsschlüssel, write-optimiert, horizontale Skalierung
- **Graph – Neo4j**: Nodes, Relationships, Properties; Cypher Query Language
- **Zeitreihendatenbanken**: InfluxDB, TimescaleDB — für Metriken, IoT-Daten
- **Supabase**: PostgreSQL + Realtime + Auth + Storage als Backend-as-a-Service

### ORM / Datenbankabstraktion
- **Prisma**: Schema-First, Migrationen, typsicherer Client, Middleware (empfohlen für Node.js + TypeScript)
- **Drizzle ORM**: leichtgewichtig, SQL-nah, sehr performant
- **TypeORM**: Decorator-basiert, gut für NestJS
- **Mongoose**: ODM für MongoDB, Schema-Validierung, Middleware (pre/post hooks)
- **Kysely**: SQL Query Builder mit vollständiger TypeScript-Unterstützung
- Migrations-Konzepte: up/down Migrationen, Schema-Versionierung

### Optimierte Queries
- Query-Analyse: `EXPLAIN ANALYZE` (PostgreSQL), Execution Plans lesen und interpretieren
- Index-Optimierung: fehlende Indizes identifizieren, Covering Indexes, Partial Indexes
- **N+1 Problem**: erkennen (zu viele DB-Anfragen in Schleifen) und lösen mit JOINs oder DataLoader
- Connection Pooling: pgBouncer, `pg.Pool`, Prisma Connection Pool, maximale Verbindungen
- Caching-Schichten: Redis vor der Datenbank, Query-Result-Caching, Materialized Views
- Denormalisierung: wann Performance über Normalform-Reinheit geht

---

## 4. Software-Engineering

### Design Patterns
- **Kreationsmuster**: Factory, Abstract Factory, Singleton, Builder, Prototype
- **Strukturmuster**: Adapter, Decorator, Facade, Proxy, Composite
- **Verhaltensmuster**: Observer, Strategy, Command, Iterator, Mediator, Chain of Responsibility
- **Architekturmuster**: MVC, MVVM, MVP, Repository Pattern, Unit of Work
- **SOLID-Prinzipien**: Single Responsibility, Open/Closed, Liskov Substitution, Interface Segregation, Dependency Inversion
- **DRY** (Don't Repeat Yourself), **KISS** (Keep It Simple), **YAGNI** (You Aren't Gonna Need It)

### System Design
- Skalierungsstrategien: Vertical (bessere Hardware) vs. Horizontal Scaling (mehr Instanzen)
- Load Balancing: Round Robin, Least Connections, IP Hashing; Nginx, HAProxy
- Architektur-Patterns: Monolith, Modularer Monolith, Microservices, Event-Driven Architecture
- **Message Queues**: RabbitMQ (AMQP), Kafka (Streams, hoher Durchsatz), Bull/BullMQ (Redis-basiert)
- CDN & Edge: statische Assets global verteilen, Edge Functions, Origin Shield
- **CAP-Theorem**: Consistency, Availability, Partition Tolerance — nur 2 von 3 gleichzeitig
- **PACELC**: Erweiterung des CAP-Theorems (Latenz-Kompromisse)
- Caching-Strategien: Cache-Aside, Write-Through, Write-Behind, Read-Through
- Datenbank-Sharding, Replikation (Primary/Replica), Read Replicas

### Security (Erweitert)
- **OWASP Top 10**: Injection, Broken Auth, XSS, Insecure Direct Object Reference (IDOR), SSRF, Misconfiguration
- Input Sanitization: immer auf dem Server validieren, niemals nur auf dem Client
- Abhängigkeiten: `npm audit`, Snyk, Dependabot — regelmäßige Sicherheits-Updates
- Headers: `Helmet.js` für Express (HSTS, X-Frame-Options, X-Content-Type-Options)
- Rate Limiting, IP-Blocking, Captcha gegen Brute-Force
- Secrets-Management: nie Secrets im Code, `.env` für lokal, Vault/AWS Secrets Manager für Production
- HTTPS/TLS: Zertifikate (Let's Encrypt), TLS 1.3, HSTS
- Penetration Testing Grundlagen: OWASP ZAP, Burp Suite

### Testing
- **Unit Tests**: isolierte Funktion/Modul-Tests — **Jest**, **Vitest**
- **Integrationstests**: mehrere Einheiten zusammen, Datenbank-Integration — **Supertest**
- **End-to-End Tests**: vollständiger User Flow im Browser — **Cypress**, **Playwright**
- **Component Tests**: Komponenten isoliert rendern — React Testing Library, Vue Test Utils
- **Snapshot Tests**: UI-Regressions-Erkennung (mit Bedacht einsetzen)
- Test-Strategien: AAA-Pattern (Arrange, Act, Assert), Mocking (`jest.mock()`), Stubbing, Spying
- **TDD** (Test-Driven Development): Red → Green → Refactor
- Code Coverage: kritische Pfade priorisieren, nicht 100% als Ziel
- **Playwright**: schneller als Cypress, Multi-Browser, nativer fetch-Intercept

### Cypress (Vertiefung)
- Setup: `cypress open` (interaktiv, GUI) vs. `cypress run` (CI/CD, headless)
- Selektoren: `cy.get('[data-cy="submit"]')` — niemals CSS-Klassen oder IDs die sich ändern
- Kernbefehle: `cy.visit()`, `cy.get()`, `cy.find()`, `cy.click()`, `cy.type()`, `cy.check()`, `cy.select()`
- Assertions: `should('be.visible')`, `should('contain.text', '...')`, `should('have.length', n)`
- **API-Mocking**: `cy.intercept('POST', '/api/login', { fixture: 'user.json' })`
- Fixtures: `cy.fixture('data.json')` für Testdaten
- Custom Commands: eigene Befehle in `commands.ts` (z.B. `cy.login()`)
- Component Testing: Komponenten isoliert in Cypress mounten
- CI-Integration: GitHub Actions mit `cypress-io/github-action`
- Best Practices: keine `cy.wait(1000)`, stattdessen `cy.intercept` + Aliase; `data-cy` Attribute

### Git (Vertiefung)
- Grundbefehle: `clone`, `init`, `add`, `commit`, `push`, `pull`, `fetch`, `stash`
- Branching: Feature Branches, Release Branches, Hotfix Branches
- **Git Flow**: `main` → `develop` → `feature/*` → `release/*` → `hotfix/*`
- **Trunk-Based Development**: kurze Feature Branches, häufige Merges zu `main`, Feature Flags
- Merge vs. Rebase: `merge` erhält History, `rebase` bereinigt History; `--interactive` für Squashing
- **Conventional Commits**: `feat(auth): add OAuth login`, `fix(api): handle 404 responses`
- `.gitignore`, `.gitattributes` (Zeilenenden), Submodules
- Code Review: Pull Requests, Review-Checklist, LGTM-Kultur, Draft PRs
- Git Hooks: pre-commit (lint), commit-msg (conventional commits), pre-push (tests) via **Husky**
- Monorepo: `git worktree`, Turborepo, Nx

### Zusammenhänge zwischen Komponenten
- Datenfluss: unidirektionaler Datenfluss (React), Props-Down / Events-Up (Vue)
- **Dependency Injection**: NestJS-Provider, Angular-DI-Container, Inversify
- Event-Bus: `EventEmitter` (Node.js), `mitt`, Pub/Sub-Pattern
- Shared State: globale Stores (Redux Toolkit, Pinia, Zustand), React Context (für einfache Fälle)
- **Micro-Frontends**: Module Federation (Webpack 5), iframes, Single-SPA, Qiankun
- **Monorepo-Werkzeuge**: Turborepo (Caching, Pipelines), Nx (Generators, Affected-Commands)

---

## 5. Progressive Web Apps (PWA)

- **Service Workers**: Lifecycle (install, activate, fetch), Background Sync, Push Notifications
- **Caching-Strategien**: Cache First, Network First, Stale-While-Revalidate
- **Web App Manifest**: `manifest.json`, Icons, `display: standalone`, Theme-Color
- **Offline-Unterstützung**: IndexedDB für lokale Datenspeicherung, Workbox-Bibliothek
- **Installierbarkeit**: Add-to-Home-Screen, Installation-Prompt
- Performance: App Shell Pattern, Skeleton Screens, Pre-Caching kritischer Assets
- Push API + Notifications API für Re-Engagement

---

## 6. Echtzeit & WebRTC

### WebSockets
- Bidirektionale Kommunikation, persistent connection
- `socket.io`: Rooms, Namespaces, Auto-Reconnect, Binary Data
- Anwendungsfälle: Chat, Live-Dashboards, kollaborative Editoren, Gaming

### Server-Sent Events (SSE)
- Einfacher One-Way-Stream vom Server zum Client
- Automatisches Reconnect eingebaut, nur HTTP nötig
- Besser als WebSockets wenn nur Server → Client Daten nötig

### WebRTC
- Peer-to-Peer Verbindungen direkt zwischen Browsern
- Komponenten: RTCPeerConnection, RTCDataChannel, MediaStream API
- Signaling-Server nötig (WebSockets), STUN/TURN-Server für NAT-Traversal
- Anwendungsfälle: Video-/Audio-Calls, Screen Sharing, P2P File Transfer

---

## 7. Serverless & Edge Computing

### Serverless Functions
- **AWS Lambda**: Event-triggered, Pay-per-Invocation, Cold Starts vermeiden
- **Vercel Functions / Netlify Functions**: Next.js API Routes, automatisches Deployment
- **Cloudflare Workers**: V8-Isolate, kein Cold Start, globale Edge-Verteilung
- **Supabase Edge Functions**: Deno-basiert, Datenbanknahe Ausführung

### Edge Computing
- Ausführung am Netzwerk-Rand (nahe beim Nutzer), niedrigste Latenz
- Middleware an der Edge: A/B-Testing, Geo-Routing, Auth-Checks
- **Edge Databases**: Turso (SQLite am Edge), PlanetScale, Neon

### Wann Serverless?
- Unregelmäßiger Traffic, keine permanenten Prozesse, schnelles Deployment
- Nicht geeignet für: Long-Running Tasks, WebSockets, komplexes State-Management

---

## 8. Internationalisierung (i18n) & Lokalisierung (l10n)

- Bibliotheken: **i18next** / **react-i18next**, **vue-i18n**, `next-intl`, `@formatjs/intl`
- Übersetzungsdateien: JSON-Format (`en.json`, `de.json`), Namespace-Trennung
- Interpolation, Pluralisierung, Datumsformate (`Intl.DateTimeFormat`)
- Währungen & Zahlen (`Intl.NumberFormat`)
- **RTL-Unterstützung** (Arabisch, Hebräisch): `dir="rtl"`, CSS Logical Properties (`margin-inline-start`)
- Lazy Loading von Übersetzungen, Namespace-Splitting für Performance

---

## 9. Deployment / Betrieb

### Production
- Umgebungsvariablen: `.env`-Dateien (lokal), Secrets-Management (HashiCorp Vault, AWS Secrets Manager, Doppler)
- **Strukturiertes Logging**: JSON-Format, Log-Level (debug/info/warn/error), Korrelations-IDs
- Logging-Bibliotheken: `winston` (Express), `pino` (Fastify/Koa), `Bunyan`
- **Monitoring**: Prometheus (Metriken sammeln) + Grafana (Dashboards)
- **Distributed Tracing**: OpenTelemetry, Jaeger, Zipkin
- **Error Tracking**: **Sentry** — Fehler, Stacktraces, Performance-Monitoring in Production
- **Uptime Monitoring**: UptimeRobot, Better Uptime, PagerDuty (Alerting)
- **Web Vitals**: LCP (Largest Contentful Paint < 2.5s), FID / INP (< 200ms), CLS (< 0.1)
- Lighthouse, PageSpeed Insights, Web.dev/measure

### Docker
- Grundkonzepte: Image (unveränderlich), Container (laufende Instanz), Layer (Cache), Registry
- **Dockerfile**: `FROM`, `RUN`, `COPY`, `WORKDIR`, `EXPOSE`, `ENV`, `CMD` vs. `ENTRYPOINT`
- **Multi-Stage Builds**: Builder-Image → minimales Production-Image (spart 80%+ Größe)
- `.dockerignore`: `node_modules`, `.env`, `.git` ausschließen
- **docker-compose**: Service-Dependencies (`depends_on`), Networks, Volumes, Health Checks
- Best Practices: non-root User, Alpine Base Images, Layer-Caching optimieren
- Image Registry: Docker Hub, GitHub Container Registry (GHCR), AWS ECR

### Kubernetes (K8s)
- Kernkonzepte: **Pod** (kleinste Einheit), **Deployment** (gewünschter Zustand), **Service** (Netzwerk-Exposure)
- **Ingress**: HTTP-Routing, SSL-Terminierung (cert-manager + Let's Encrypt)
- ConfigMaps & Secrets, Namespace-Isolation
- **Horizontal Pod Autoscaler (HPA)**: automatische Skalierung bei Last
- Helm: Package Manager für Kubernetes (Charts)
- Managed Kubernetes: AWS EKS, GCP GKE, Azure AKS

### CI/CD
- **GitHub Actions**: Workflows (`.github/workflows/*.yml`), Jobs, Steps, Secrets, Artifacts
- Pipeline-Phasen: Lint → Test → Build → Security Scan → Deploy
- **GitLab CI/CD**: `.gitlab-ci.yml`, Stages, Runners, Environments
- Deployment-Strategien: Blue/Green, Canary Deployment, Rolling Update
- **Trunk-Based CI**: bei jedem Commit zu `main` automatisch deployen (mit Feature Flags)

### Weitere Werkzeuge
- **Package Manager**: npm, **pnpm** (disk-effizient, schnell, Workspaces), yarn
- **Bundler**: **Vite** (Dev + Build, blitzschnell), esbuild, Rollup, Webpack (Legacy)
- **Linting**: ESLint (JS/TS), Stylelint (CSS), markdownlint
- **Formatting**: Prettier — einheitlicher Code-Stil im Team
- **Git Hooks**: Husky + lint-staged (nur geänderte Dateien linting/formatieren)
- **IaC (Infrastructure as Code)**: Terraform, Pulumi — Infrastruktur versioniert und reproduzierbar
- **Hosting Frontend**: Vercel, Netlify, Cloudflare Pages
- **Hosting Backend**: Railway, Render, Fly.io, AWS ECS/Lambda, GCP Cloud Run
- **Datenbank-Hosting**: Supabase, PlanetScale, Neon (serverless Postgres), MongoDB Atlas

---

## 10. Datenstrukturen & Algorithmen (für Web-Entwickler)

### Wichtige Datenstrukturen
- **Array**: O(1) Zugriff, O(n) Suche, JavaScript-Arrays sind dynamisch
- **Map/HashMap**: O(1) Lesen/Schreiben, `Map` vs. Plain Object in JS
- **Set**: keine Duplikate, O(1) Membership-Check
- **Stack**: LIFO — `push`/`pop`, Undo-Funktionalität, Browserhistorie
- **Queue**: FIFO — Message Queues, Aufgabenverarbeitung
- **Linked List**: O(n) Zugriff, O(1) Insert/Delete am Anfang/Ende
- **Baum**: DOM ist ein Baum, JSON-Struktur, Binärer Suchbaum
- **Graph**: soziale Netzwerke, Routing-Algorithmen

### Wichtige Algorithmen
- **Big-O-Notation**: O(1), O(log n), O(n), O(n log n), O(n²) — Worst-Case verstehen
- Suche: Lineare Suche O(n), Binäre Suche O(log n) (nur sortierte Arrays)
- Sortierung: Bubble Sort (Konzept), Merge Sort, Quick Sort, eingebautes `Array.sort()`
- **Rekursion**: Basisfall + rekursiver Fall, Stack Overflow vermeiden, Memoization
- **Dynamic Programming**: Unterprobleme cachen, Fibonacci-Beispiel
- String-Manipulation: Palindrom-Check, Anagramm-Detection, Sliding Window

---

## Lernpfad & Zusammenfassung

### Empfohlener Lernpfad

```
HTML → CSS → JavaScript → TypeScript → Git → React/Vue → Node.js →
SQL (PostgreSQL) → Testing (Jest + Cypress) → Docker → CI/CD → System Design
```

### Skill-Matrix

| Bereich | Einstieg | Vertiefung | Expert |
|---|---|---|---|
| Frontend | HTML, CSS, Vanilla JS | React/Vue, TypeScript, PWA | Micro-Frontends, Web Performance |
| Backend | Node + Express | NestJS, GraphQL, gRPC | Microservices, Event-Driven |
| Datenbank | SQL (PostgreSQL) | Redis, ORM (Prisma), Indizes | Sharding, CQRS, Event Sourcing |
| Testing | Jest Unit Tests | React Testing Library, Supertest | Cypress E2E, TDD, Contract Tests |
| Security | HTTPS, Input Validation | OWASP Top 10, JWT best practices | Penetration Testing, Threat Modeling |
| Deployment | Docker | Kubernetes, GitHub Actions | Terraform, Multi-Region, Observability |
| Design | Grundlagen Figma | Design Systems, Storybook | Design Tokens, Accessibility Audit |

### Technologie-Empfehlungen 2024/2025

| Kategorie | Empfehlung | Alternative |
|---|---|---|
| Frontend Framework | React + Next.js | Vue 3 + Nuxt |
| Styling | Tailwind CSS | CSS Modules |
| State Management | TanStack Query + Zustand | Redux Toolkit |
| Backend | Node.js + NestJS | Bun + Hono |
| Datenbank | PostgreSQL + Prisma | SQLite + Drizzle |
| Cache | Redis | Memcached |
| Testing | Vitest + Playwright | Jest + Cypress |
| Deployment | Docker + GitHub Actions | Vercel/Railway |
| Monitoring | Grafana + Sentry | Datadog |

---

## 11. KI / LLM-Integration

### Grundlagen
- **Large Language Models (LLMs)**: Sprachmodelle, die Text verstehen und generieren
- **Tokens**: Einheit der Verarbeitung (~4 Zeichen = 1 Token), direkt verknüpft mit Kosten
- **Context Window**: maximale Anzahl Tokens pro Anfrage (z.B. 200k bei Claude)
- **Temperature**: 0 = deterministisch, 1 = kreativ/zufällig
- **System Prompt**: Anweisung an das Modell, die das Verhalten definiert

### Claude API / Anthropic SDK
- **Messages API**: `messages.create({ model, max_tokens, messages: [{role, content}] })`
- **Streaming**: `stream: true` für token-by-token Ausgabe (`stream.on('text', ...)`)
- **Tool Use (Function Calling)**: Modell ruft definierte Funktionen auf, strukturierte Ausgabe
- **Prompt Caching**: wiederholte System Prompts cachen → 90% Kostenreduktion
- **Modelle**: Claude Haiku (schnell/günstig), Sonnet (ausgewogen), Opus (leistungsstark)

### Prompt Engineering
- **Zero-Shot**: direkte Aufgabe ohne Beispiele
- **Few-Shot**: 2–5 Beispiele im Prompt für konsistenteres Verhalten
- **Chain-of-Thought (CoT)**: "Denke Schritt für Schritt" → bessere Reasoning-Qualität
- **Structured Output**: JSON-Format erzwingen via Tool Use oder `response_format`
- **System + User + Assistant**: korrekte Rollenstruktur für Multi-Turn-Dialoge
- Anti-Patterns: zu langer Prompt ohne Struktur, widersprüchliche Anweisungen

### RAG (Retrieval-Augmented Generation)
- **Embeddings**: Text → Vektor (numerische Darstellung der Bedeutung)
- **Vektordatenbanken**: pgvector (PostgreSQL), Pinecone, Weaviate, Qdrant
- RAG-Pipeline: Dokument → Chunks → Embeddings → DB → Query → relevante Chunks → LLM
- **Chunking-Strategien**: Fixed-Size, Sentence-Splitting, Semantic Chunking
- **Reranking**: zweite Stufe zur Relevanz-Verbesserung (Cohere Rerank)
- Anwendungsfälle: Chatbots auf eigenen Daten, Dokumentensuche, Q&A über PDFs

### AI SDK & Frameworks
- **Vercel AI SDK**: `useChat`, `useCompletion` für React/Next.js, Streaming out-of-the-box
- **LangChain.js**: Chains, Agents, Memory, Tool-Integration
- **LlamaIndex**: spezialisiert auf Dokumenten-Indexierung und RAG
- **Mastra**: TypeScript-natives AI-Agent-Framework (Workflows, Memory, Tools)

### AI-Agents
- **Tool-Calling Loop**: LLM → Tool ausführen → Ergebnis zurück → LLM → ...
- **Multi-Agent-Systeme**: Orchestrator-Agent delegiert an Spezialist-Agenten
- **Memory-Typen**: In-Context (Conversation History), External (DB), Semantic (Embeddings)
- **Human-in-the-Loop**: Checkpoints wo Menschen bestätigen müssen

---

## 12. Payment-Integration

### Stripe (Standard)
- **Payment Intent**: serverseitig erstellen, clientseitig bestätigen (PCI-sicher)
- **Stripe Elements / Stripe.js**: vorgefertigte UI-Komponenten für Karteneingabe
- **Webhooks**: `payment_intent.succeeded`, `invoice.payment_failed` → eigene DB aktualisieren
- **Subscriptions**: `stripe.subscriptions.create()`, Billing Cycles, Proration
- **Refunds**: `stripe.refunds.create({ payment_intent: '...' })`
- **Stripe Checkout**: hosted Payment Page ohne eigene UI
- **Stripe Connect**: Marketplace-Zahlungen, Split Payments

### Sicherheit & Compliance
- **PCI-DSS**: Kartendaten NIE selbst speichern oder loggen
- Stripe übernimmt PCI-Compliance wenn Stripe.js korrekt verwendet
- Webhook-Signaturen verifizieren: `stripe.webhooks.constructEvent()`
- **Idempotency Keys**: doppelte Zahlungsversuche sicher abfangen

### Europäische Besonderheiten
- **SEPA-Lastschrift**: für DE/AT/CH-Kunden
- **Mollie / PayPal**: Alternativen mit lokalen Zahlungsmethoden (iDEAL, Sofort)
- **3D Secure (3DS2)**: EU-Pflicht (SCA), Stripe handhabt das automatisch

---

## 13. E-Mail

### Transaktions-E-Mails
- **Resend**: moderne API, React Email Unterstützung, einfache Integration
- **SendGrid**: Marktführer, starkes Analytics-Dashboard
- **Nodemailer**: direkt via SMTP, gut für self-hosted
- **Mailgun / Postmark**: zuverlässige Zustellung, gute Logs

### E-Mail-Templates
- **React Email**: E-Mails als React-Komponenten schreiben, dann rendern
- **MJML**: responsives E-Mail-Markup, kompiliert zu HTML
- Inline-CSS ist Pflicht (E-Mail-Clients ignorieren externe Stylesheets)
- Dark Mode in E-Mails: `@media (prefers-color-scheme: dark)` (nur teils unterstützt)

### Zustellbarkeit (Deliverability)
- **SPF**: autorisierte Mail-Server im DNS definieren
- **DKIM**: kryptografische Signatur jeder E-Mail
- **DMARC**: Policy was bei SPF/DKIM-Fehlschlag passiert (reject/quarantine/none)
- Eigene Domain verwenden, niemals `@gmail.com` für transaktionale Mails
- Bounce-Handling und Unsubscribe-Links sind Pflicht (CAN-SPAM, DSGVO)

---

## 14. Suche (Search)

### Volltextsuche
- **PostgreSQL Full-Text Search**: `tsvector`, `tsquery`, `@@`-Operator, `ts_rank`
- **Elasticsearch**: mächtig, horizontale Skalierung, komplexe Aggregationen
- **OpenSearch**: AWS-Variante von Elasticsearch (open source)

### SaaS-Suchlösungen
- **Algolia**: sehr schnell (< 100ms), InstantSearch UI-Bibliothek, einfach zu integrieren
- **Typesense**: open source, selbst gehostet, einfacher als Elasticsearch
- **Meilisearch**: open source, typo-tolerant, Deutsch-Unterstützung

### Suchmuster
- **Fuzzy Search**: Tippfehler tolerieren (`"helo" → "hello"`)
- **Faceted Search**: Filterkategorien (Preis, Kategorie, Bewertung)
- **Autovervollständigung**: Prefix-Search, Suggest-API
- **Semantic Search**: Embeddings-basiert, findet Bedeutung statt Stichwörter
- **Hybrid Search**: Keyword + Semantic kombinieren für beste Ergebnisse

---

## 15. File Upload & Medien

### Objekt-Speicher
- **AWS S3**: Standard, günstig, nahezu unbegrenzt
- **Cloudflare R2**: S3-kompatibel, kein Egress-Preis (günstiger für Downloads)
- **Supabase Storage**: S3 dahinter, einfache SDK-Integration
- **Uploadthing**: Next.js-optimiert, typsicher, einfach

### Upload-Strategie
- **Presigned URLs**: Browser lädt direkt zu S3, Server nie als Zwischenspeicher
- Dateivalidierung: MIME-Type, Dateigröße, Magic Bytes (echten Typ prüfen)
- Virus-Scanning: ClamAV oder SaaS (z.B. Cloudmersive) nach Upload
- Multipart Upload für große Dateien (> 100 MB)

### Bild-Optimierung
- **Formate**: WebP (80% kleiner als JPEG), AVIF (noch kleiner, breite Unterstützung 2024)
- `<picture>` + `srcset` für responsive Bilder
- **Next.js `<Image>`**: automatische Optimierung, Lazy Loading, Blur Placeholder
- **Sharp**: serverseitige Bildbearbeitung (Resize, Crop, Compress)
- CDN mit Image Transformation: Cloudflare Images, Imgix, Cloudinary

---

## 16. Background Jobs & Scheduling

### Job Queues
- **BullMQ** (Redis-basiert): zuverlässig, Retry-Logik, Prioritäten, Rate Limiting, Cron
- **pg-boss** (PostgreSQL-basiert): kein Redis nötig, ACID-Garantien
- **Inngest**: cloud-native Event-driven Jobs, einfach lokal zu testen
- **Trigger.dev**: TypeScript-native, Background Jobs als Code

### Wann Jobs statt HTTP?
- E-Mail versenden, PDF generieren, externe API aufrufen
- Alles was > 30 Sekunden dauert (HTTP Timeout-Grenze)
- Retry bei Fehlern ist Pflicht (idempotente Jobs schreiben)

### Cron Jobs
- Syntax: `* * * * *` (Minute Stunde Tag Monat Wochentag)
- Beispiele: `0 8 * * 1-5` (Mo–Fr 8 Uhr), `0 0 1 * *` (Monatserster)
- Monitoring: Dead Man's Snitch, Healthchecks.io — Alarm wenn Cron nicht läuft

---

## 17. Headless CMS

| CMS | Hosting | Besonderheit |
|-----|---------|--------------|
| **Strapi** | Self-hosted | flexibel, REST + GraphQL, Plugin-Ökosystem |
| **Payload CMS** | Self-hosted | TypeScript-nativ, DB direkt in App |
| **Directus** | Self-hosted | wirkt wie Admin-UI über jede DB |
| **Sanity** | Cloud | Real-time, GROQ-Abfragesprache, strukturiert |
| **Contentful** | Cloud | Enterprise, stark typisiert, viele Integrationen |
| **Storyblok** | Cloud | Visual Editor, gut für Marketing-Teams |

- **Content Delivery API** vs. **Management API**: lesen vs. schreiben
- **Webhooks**: bei Content-Änderung Rebuild triggern (ISR in Next.js)
- **Preview Mode**: unveröffentlichten Content im Frontend anzeigen

---

## 18. Analytics & Feature Flags

### Web Analytics
- **PostHog**: open source, Session Recordings, Funnels, Feature Flags, self-hostbar
- **Plausible**: DSGVO-konform, kein Cookie-Banner nötig, leichtgewichtig
- **Mixpanel**: Event-basiert, starke Nutzer-Journey-Analyse
- **Google Analytics 4**: kostenlos, DSGVO-kritisch ohne Consent-Management

### Feature Flags
- Deployment von Feature-Aktivierung entkoppeln
- **LaunchDarkly**: Enterprise, SDK für alle Sprachen
- **GrowthBook**: open source, A/B Testing integriert
- **Unleash**: open source, self-hostbar
- Patterns: `if (featureFlag('new-checkout')) { ... }`, Rollout-Prozentsätze

### A/B Testing
- Kontrollgruppe (A) vs. Variante (B), statistisch signifikante Ergebnisse abwarten
- Server-side vs. Client-side Testing (Server verhindert Layout Shifts)
- Metriken definieren bevor Test startet (Conversion Rate, Klickrate)

---

## 19. Barrierefreiheit (a11y) – Vertiefung

### Standards & Gesetze
- **WCAG 2.2**: Web Content Accessibility Guidelines
  - Level A: Mindestanforderungen
  - Level AA: gesetzliche Pflicht (EU Web Accessibility Directive, BFSG in DE ab 2025)
  - Level AAA: optimal, nicht immer erreichbar
- **ARIA**: `role`, `aria-label`, `aria-describedby`, `aria-expanded`, `aria-live`

### Praktische Umsetzung
- **Tastaturnavigation**: alle interaktiven Elemente via Tab erreichbar, sichtbarer Focus-Ring
- **Focus Management**: bei Modals Focus sperren (`focus-trap`), bei Navigation Focus setzen
- **Skip Links**: "Zum Hauptinhalt springen" als erster Link
- **Semantisches HTML** schlägt ARIA: `<button>` > `<div role="button">`
- **Kontrastverhältnis**: min. 4.5:1 (Text), 3:1 (großer Text, UI-Komponenten)
- `prefers-reduced-motion`: Animationen für vestibulär sensible Nutzer deaktivieren

### Testing-Tools
- **axe-core** / **axe DevTools**: automatische a11y-Prüfung (findet ~30% der Probleme)
- **Lighthouse**: a11y-Score in Chrome DevTools
- **NVDA** (Windows) / **VoiceOver** (Mac/iOS): manuelle Screenreader-Tests
- **Colour Contrast Analyser**: Kontrast prüfen
- Automatisiert: `jest-axe`, `cypress-axe`

---

## 20. Observability – Die 3 Säulen (Vertiefung)

### Logs
- **Strukturiertes Logging**: JSON statt Freitext → maschinell auswertbar
- **Log-Level**: `debug` (Entwicklung), `info` (normal), `warn` (Achtung), `error` (Problem)
- **Korrelations-IDs**: Request-ID durch alle Services mitschleppen (`X-Correlation-ID`)
- **Log-Aggregation**: Loki + Grafana, Datadog Logs, AWS CloudWatch
- Was loggen? Wer, Was, Wann, Ergebnis — NIE Passwörter oder PII

### Metrics
- **Prometheus**: Pull-basiert, Zeitreihendaten, `Counter`, `Gauge`, `Histogram`
- **Grafana**: Dashboards für Prometheus-Daten
- **Wichtige Metriken**: Request Rate, Error Rate, Latenz (p50/p95/p99), CPU, Memory
- **RED-Methode**: Rate, Errors, Duration — für Services
- **USE-Methode**: Utilization, Saturation, Errors — für Ressourcen

### Traces
- **Distributed Tracing**: Anfrage durch mehrere Services verfolgen
- **OpenTelemetry**: offener Standard, Vendor-neutral (einmal instrumentieren, überall exportieren)
- **Jaeger / Zipkin**: open source Trace-Backends
- **Spans**: einzelne Operation innerhalb eines Traces, mit Start/End-Zeit
- Anwendungsfall: "Warum dauert diese API-Anfrage 800ms?" → Trace zeigt wo

---

## 21. Sicherheit – Vertiefung

### OWASP Top 10 (2021)
1. **Broken Access Control**: fehlende Autorisierungsprüfungen
2. **Cryptographic Failures**: schwache Verschlüsselung, HTTP statt HTTPS
3. **Injection**: SQL, NoSQL, Command Injection durch unsanitisierte Eingaben
4. **Insecure Design**: fehlende Sicherheitskonzepte in der Architektur
5. **Security Misconfiguration**: Default-Passwörter, offene Cloud-Buckets
6. **Vulnerable Components**: veraltete Dependencies mit bekannten CVEs
7. **Authentication Failures**: schwache Passwörter, fehlende MFA, Session-Probleme
8. **Software & Data Integrity**: CI/CD ohne Verifikation, unsichere Deserializierung
9. **Logging & Monitoring Failures**: Angriffe nicht erkennen
10. **SSRF**: Server macht Anfragen an interne Systeme durch Nutzer-Input

### Praktische Gegenmaßnahmen
- Input Validation: Whitelist statt Blacklist, auf dem Server validieren (nicht nur Client)
- Parameterized Queries (Prepared Statements): SQL Injection verhindern
- `helmet.js`: setzt wichtige HTTP-Security-Header automatisch
- Content Security Policy (CSP): erlaubte Script-Quellen definieren
- `npm audit --fix`, Dependabot, Snyk: automatische Dependency-Sicherheit
- Secrets niemals im Code oder Git: `.env`, Vault, GitHub Secrets
- **CSRF-Tokens**: bei State-ändernden Formularen (oder SameSite=Strict Cookies)
- **Rate Limiting**: Login-Versuche begrenzen (z.B. 5 pro Minute)

### Sicherheits-Tools
- **OWASP ZAP**: automatischer Vulnerability-Scanner
- **Burp Suite**: professionelles Pentesting-Tool
- **Trivy**: Container-Image auf Schwachstellen scannen
- **GitLeaks**: versehentliche Secrets in Git-History finden

---

## 22. Mobile & Cross-Platform

### React Native
- JavaScript/TypeScript → native iOS & Android Apps
- **Expo**: vereinfachtes Setup, OTA-Updates, `expo-router`
- Kernkomponenten: `View`, `Text`, `ScrollView`, `FlatList`, `TouchableOpacity`
- Navigation: React Navigation (Stack, Tab, Drawer)
- Native Module: Kamera, GPS, Push-Notifications, Biometrie

### Capacitor (Ionic)
- Web-App (HTML/CSS/JS) → native App über WebView
- Zugriff auf native APIs: Kamera, Dateisystem, Gerätesensoren
- Gut wenn man bestehende Web-App zur nativen App machen will

### Electron (Desktop)
- Web-Technologien → Desktop-App (Windows, Mac, Linux)
- Chromium + Node.js in einem Paket
- Beispiele: VS Code, Discord, Figma (Desktop), Slack
- Nachteil: große Bundle-Größe (~150MB)

### Tauri (Desktop — modern)
- Rust-basiert, nutzt System-WebView statt Chromium → viel kleiner (~10MB)
- Besser für Sicherheit und Performance als Electron

---

## 23. Web Scraping & Automatisierung

### Tools
- **Puppeteer**: Chrome-Steuerung via Node.js, Google-Projekt
- **Playwright**: moderner, multi-browser (Chrome, Firefox, Safari), Microsoft-Projekt
- **Cheerio**: HTML parsen wie jQuery — nur für statische Seiten
- **Axios + JSDOM**: leichtgewichtig für einfache Fälle

### Techniken
- **Headless Mode**: Browser ohne GUI (`--headless`)
- **Selektoren**: CSS-Selektoren, XPath, `data-*`-Attribute bevorzugen
- **Warten auf Elemente**: `waitForSelector`, `waitForNetworkIdle`
- **Anti-Bot-Umgehung**: User-Agent setzen, Delays, Proxies (mit Erlaubnis!)
- **Pagination**: nächste Seite klicken oder URL-Parameter erhöhen

### Rechtliches & Ethik
- `robots.txt` immer prüfen und respektieren
- Terms of Service beachten — Scraping kann verboten sein
- Rate Limiting: Server nicht überlasten (1 Request pro Sekunde als Faustregel)
- Persönliche Daten: DSGVO beachten beim Speichern gescrapeter Daten

---

## 24. Datenstrukturen & Algorithmen (Vertiefung)

### Wichtige Algorithmen für Web-Entwickler
- **Debounce & Throttle**: Sucheingabe-Optimierung, Scroll-Events
- **Memoization**: `useMemo`, `React.memo`, manuelle Cache-Maps
- **Binary Search**: O(log n) Suche in sortierten Arrays
- **Diff-Algorithmus**: wie React den Virtual DOM vergleicht (Myers-Diff)
- **Trie (Prefix-Tree)**: effiziente Autovervollständigung
- **LRU-Cache**: Least Recently Used — Cache-Verdrängungsstrategie

### Komplexitätsanalyse (Praxis)
```
O(1)      → HashMap lookup, Array-Zugriff per Index
O(log n)  → Binäre Suche, Balanced BST
O(n)      → Array durchlaufen, lineare Suche
O(n log n)→ Merge Sort, Quick Sort (avg)
O(n²)     → verschachtelte Schleifen (vermeiden bei großen Daten!)
```

### Häufige Interview-Aufgaben (Konzepte)
- Two Pointers: Array-Probleme in O(n) statt O(n²) lösen
- Sliding Window: maximale Teilfolge finden
- Rekursion + Memoization → Dynamic Programming
- Graph-Traversal: BFS (Level-Order) vs. DFS (Tiefe-zuerst)

---

## 25. Continuous Learning (Wie aktuell bleiben?)

### Ressourcen-Empfehlungen
- **Dokumentationen**: MDN (Web), Node.js Docs, React Docs (react.dev)
- **Newsletter**: JavaScript Weekly, Bytes.dev, Node Weekly, CSS-Tricks
- **Blogs**: Kent C. Dodds, Josh W. Comeau, Dan Abramov, Addy Osmani
- **YouTube**: Fireship, Theo (t3.gg), Jack Herrington, Traversy Media
- **Podcasts**: Syntax.fm, JS Party, The Changelog
- **Plattformen**: Frontend Masters, Egghead.io, Total TypeScript

### Lernstrategien
- **Learning by Doing**: echte Projekte bauen statt nur Tutorials konsumieren
- **Teach to Learn**: Blog-Posts schreiben, andere unterrichten
- **Code Reading**: Open-Source-Code lesen (React, Next.js, Prisma Sourcecode)
- **Spaced Repetition**: Anki-Karten für Konzepte die man vergisst
- Konferenzen: JSConf, VueConf, React Summit, NodeConf

---

## Gesamtübersicht aller Bereiche

| # | Bereich | Status |
|---|---------|--------|
| 1 | Frontend (HTML, CSS, JS, TS, Components) | ✅ |
| 2 | Backend (Server, Routing, Auth, APIs) | ✅ |
| 3 | Datenbanken (SQL, NoSQL, ORM, Queries) | ✅ |
| 4 | Software-Engineering (Patterns, Testing, Git) | ✅ |
| 5 | Progressive Web Apps (PWA) | ✅ |
| 6 | Echtzeit & WebRTC | ✅ |
| 7 | Serverless & Edge Computing | ✅ |
| 8 | Internationalisierung (i18n/l10n) | ✅ |
| 9 | Deployment (Docker, K8s, CI/CD) | ✅ |
| 10 | Datenstrukturen & Algorithmen | ✅ |
| 11 | KI / LLM-Integration | ✅ |
| 12 | Payment-Integration (Stripe) | ✅ |
| 13 | E-Mail (Transaktional, Deliverability) | ✅ |
| 14 | Suche (Elasticsearch, Algolia, Typesense) | ✅ |
| 15 | File Upload & Medien | ✅ |
| 16 | Background Jobs & Scheduling | ✅ |
| 17 | Headless CMS | ✅ |
| 18 | Analytics & Feature Flags | ✅ |
| 19 | Barrierefreiheit (a11y) | ✅ |
| 20 | Observability (Logs, Metrics, Traces) | ✅ |
| 21 | Sicherheit (OWASP Top 10) | ✅ |
| 22 | Mobile & Cross-Platform | ✅ |
| 23 | Web Scraping & Automatisierung | ✅ |
| 24 | Algorithmen (Vertiefung) | ✅ |
| 25 | Continuous Learning | ✅ |
