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
