# Web-Entwicklung – Komplette Skill-Übersicht

---

## 1. Frontend

### HTML
- Semantische Elemente: `<header>`, `<main>`, `<section>`, `<article>`, `<nav>`, `<footer>`
- Formulare & Eingaben: `<form>`, `<input>`, `<select>`, `<textarea>`, Validierungsattribute
- Barrierefreiheit (Accessibility): ARIA-Rollen, `alt`-Texte, Tab-Reihenfolge
- SEO-Grundlagen: Meta-Tags, Open Graph, strukturierte Daten

### CSS
- Box-Modell: `margin`, `padding`, `border`, `box-sizing`
- Layout: Flexbox, CSS Grid, Position (`static`, `relative`, `absolute`, `fixed`, `sticky`)
- Responsive Design: Media Queries, `clamp()`, fluid typography, mobile-first
- CSS-Variablen (`--custom-properties`), Animationen, Transitions
- Methodologien: BEM, SMACSS, CSS Modules, Tailwind CSS

### JavaScript (ES6+)
- Kernkonzepte: Closures, Hoisting, Scope, Prototypen, Event Loop
- Asynchron: Promises, `async/await`, `fetch()`, Error Handling
- DOM-Manipulation: `querySelector`, Event-Listener, Template Literals
- Module: `import/export`, Dynamic Imports
- Wichtige APIs: LocalStorage, SessionStorage, IntersectionObserver, Web Workers

### Web-Grundlagen
- HTTP/HTTPS: Methoden (GET, POST, PUT, DELETE, PATCH), Status-Codes (2xx, 3xx, 4xx, 5xx)
- Browser-Rendering: Critical Rendering Path, Reflow vs. Repaint
- Performance: Lazy Loading, Code Splitting, Tree Shaking, Caching (Cache-Control, ETags)
- Web-Sicherheit: CORS, Content Security Policy (CSP), HTTPS, XSS, CSRF

### UI/Design
- Design-Tokens: Farben, Typografie, Abstände, Border-Radien
- Figma-Grundlagen: Komponenten, Auto Layout, Prototyping
- Design-Systeme: Atomic Design, Storybook, Style-Guides
- UX-Prinzipien: Affordance, Feedback, Konsistenz, Progressive Disclosure

### Components
- Komponentenarchitektur: Props, State, Events, Slots
- React: `useState`, `useEffect`, `useContext`, `useMemo`, `useCallback`, Custom Hooks
- Vue 3: Composition API, `ref`, `reactive`, `computed`, Pinia
- Wiederverwendbarkeit: HOC, Render Props, Compound Components
- State Management: Redux Toolkit, Zustand, Pinia, Jotai

---

## 2. Backend

### Server
- Node.js: Event-driven, Non-blocking I/O, `EventEmitter`, Streams
- Express.js: Middleware-Konzept, Request/Response-Zyklus
- Alternativen: Fastify (performance-optimiert), NestJS (strukturiert, TypeScript-first)
- Deno & Bun: moderne Laufzeiten mit eingebautem TypeScript-Support

### Routing
- RESTful Routing: Ressourcen-basierte URL-Struktur (`/users/:id`)
- Router-Middleware: Gruppen, Guards, Parameter-Validierung
- Wildcard- & Nested-Routen
- GraphQL-Routing: Resolver-basiert (kein URL-Routing)

### Authentication
- Session-basiert: serverseitige Sessions + Cookies (HttpOnly, Secure, SameSite)
- Token-basiert: JWT (Header.Payload.Signature), Refresh-Token-Rotation
- OAuth 2.0 / OpenID Connect: Authorization Code Flow, PKCE
- Passwort-Sicherheit: bcrypt/argon2 Hashing, Salt-Runden
- MFA: TOTP (Authenticator-Apps), WebAuthn/Passkeys

### APIs
- REST: Statuscode-Konventionen, HATEOAS, Versionierung (`/api/v1/`)
- GraphQL: Schema Definition Language, Queries, Mutations, Subscriptions, DataLoader
- gRPC: Protocol Buffers, Streaming, hohe Performance für Microservices
- WebSockets: bidirektionale Kommunikation, `socket.io`
- API-Design: Pagination (Cursor vs. Offset), Rate Limiting, Error Responses

---

## 3. Datenbanken

### SQL
- Grundlagen: DDL (`CREATE`, `ALTER`, `DROP`), DML (`SELECT`, `INSERT`, `UPDATE`, `DELETE`)
- Joins: `INNER`, `LEFT`, `RIGHT`, `FULL OUTER`, `CROSS JOIN`
- Transaktionen: ACID-Eigenschaften, `BEGIN`, `COMMIT`, `ROLLBACK`
- Indizes: B-Tree, Hash-Indizes, Composite Indexes, Index-Strategie
- Populäre Systeme: PostgreSQL (empfohlen), MySQL, SQLite

### NoSQL
- Dokumentenorientiert: MongoDB – Dokumente, Collections, `$match`, `$group`, `$lookup`
- Key-Value: Redis – Caching, Pub/Sub, Sessions, Rate Limiting
- Column-Family: Cassandra – skalierbar, write-optimiert
- Graph-Datenbanken: Neo4j – Nodes & Relationships, Cypher Query Language
- Wann NoSQL? Flexible Schemas, horizontale Skalierung, spezifische Zugriffspattern

### Optimierte Queries
- Query-Analyse: `EXPLAIN ANALYZE` (PostgreSQL), Execution Plans lesen
- Index-Optimierung: fehlende Indizes identifizieren, Index-Only Scans
- N+1 Problem: erkennen und mit JOINs oder DataLoader lösen
- Connection Pooling: pgBouncer, `pg.Pool`, Prisma Connection Pool
- Caching-Schichten: Redis vor der Datenbank, Query-Result-Caching

---

## 4. Software-Engineering

### System Design
- Skalierungsstrategien: Vertical vs. Horizontal Scaling, Load Balancing
- Architektur-Patterns: Monolith, Microservices, Modular Monolith, Event-Driven
- Message Queues: RabbitMQ, Kafka – entkoppelte Kommunikation, Retry-Logik
- CDN & Edge: statische Assets global verteilen, Edge Functions
- CAP-Theorem: Consistency, Availability, Partition Tolerance – Kompromisse verstehen

### Testing
- Einheitstests (Unit Tests): isolierte Funktions-/Modul-Tests, Jest, Vitest
- Integrationstests: mehrere Einheiten zusammen, Supertest (API-Tests)
- End-to-End Tests: vollständiger User Flow, Cypress, Playwright
- Test-Strategien: AAA-Pattern (Arrange, Act, Assert), Mocking, Stubbing
- Code Coverage: nicht Ziel, sondern Hinweis – kritische Pfade priorisieren

### Cypress
- Setup: `cypress open` (interaktiv) vs. `cypress run` (CI)
- Befehle: `cy.visit()`, `cy.get()`, `cy.click()`, `cy.type()`, `cy.intercept()`
- Best Practices: `data-cy`-Attribute für Selektoren, keine Implementierungsdetails testen
- Fixtures & Mocking: `cy.fixture()`, `cy.intercept()` für API-Mocking
- Component Testing: Komponenten isoliert in Cypress testen (ohne Browser-Umgebung)

### Git
- Grundbefehle: `clone`, `add`, `commit`, `push`, `pull`, `fetch`
- Branching-Strategien: Git Flow, Trunk-Based Development, Feature Branches
- Merge vs. Rebase: Vor- und Nachteile, `squash merge` für saubere History
- Conventional Commits: `feat:`, `fix:`, `chore:`, `docs:`, `refactor:`
- Code Review: Pull Requests, Review-Feedback, geschützte Branches

### Zusammenhänge zwischen Komponenten
- Datenfluss: unidirektionaler Datenfluss (React), Props-Down / Events-Up (Vue)
- Dependency Injection: NestJS-Provider, Angular-DI-Container
- Event-Bus: `EventEmitter`, `mitt`, Pub/Sub-Pattern
- Shared State: globale Stores (Redux, Pinia), React Context vs. State-Management-Libraries
- Micro-Frontends: Module Federation, iframes, Single-SPA

---

## 5. Deployment / Betrieb

### Production
- Umgebungsvariablen: `.env`-Dateien, Secrets-Management (Vault, AWS Secrets Manager)
- Logging: strukturiertes Logging (JSON), Log-Level, `winston`, `pino`
- Monitoring: Metriken (Prometheus, Grafana), Traces (OpenTelemetry), Alerts
- Error Tracking: Sentry – Fehler in Production erfassen und analysieren
- Performance: Web Vitals (LCP, FID, CLS), Lighthouse, PageSpeed Insights

### Docker
- Grundkonzepte: Image, Container, Layer, Registry (Docker Hub, GHCR)
- `Dockerfile`: `FROM`, `RUN`, `COPY`, `EXPOSE`, `CMD`, Multi-Stage Builds
- `docker-compose`: Multi-Container-Setups lokal, Service-Dependencies, Volumes
- Best Practices: non-root User, `.dockerignore`, schlanke Base-Images (alpine)
- Orchestrierung: Kubernetes (k8s) – Pods, Deployments, Services, Ingress

### Weitere Werkzeuge
- CI/CD: GitHub Actions, GitLab CI – automatisierte Tests, Lint, Build & Deploy
- Package Manager: npm, pnpm (schneller, disk-effizienter), yarn
- Bundler: Vite (Entwicklung & Build), esbuild, Rollup, Webpack (Legacy)
- Linting & Formatting: ESLint, Prettier, Husky (Pre-Commit-Hooks), lint-staged
- IaC (Infrastructure as Code): Terraform, Pulumi – Infrastruktur versioniert verwalten
- Hosting-Plattformen: Vercel, Netlify (Frontends), Railway, Render, AWS, GCP, Azure

---

## Zusammenfassung: Lernpfad-Empfehlung

```
HTML → CSS → JavaScript → Git → React/Vue → Node.js → Datenbanken → Testing → Docker → CI/CD
```

| Bereich         | Einstieg              | Vertiefung                         |
|-----------------|-----------------------|------------------------------------|
| Frontend        | HTML, CSS, Vanilla JS | React/Vue, TypeScript, Performance |
| Backend         | Node + Express        | NestJS, GraphQL, Microservices     |
| Datenbank       | SQL (PostgreSQL)      | Redis, Query-Optimierung, ORM      |
| Testing         | Jest Unit Tests       | Cypress E2E, TDD-Methodik          |
| Deployment      | Docker                | Kubernetes, CI/CD, Monitoring      |
