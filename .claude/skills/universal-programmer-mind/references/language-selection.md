# Language and Stack Selection

## First rule

For an existing project, prefer its current language, framework, runtime, package manager, testing stack, and conventions unless there is evidence they cannot meet the requirement.

## Selection criteria

Evaluate:
- Required platforms and deployment environment
- Existing team and codebase
- Performance, latency, memory, startup, and concurrency needs
- Safety and type-system requirements
- Libraries, drivers, standards, and vendor support
- Build, test, debug, observability, and packaging tools
- Security maintenance and support horizon
- Hiring and long-term maintenance
- Interoperability and migration cost

## Typical fits, not automatic answers

- Python: automation, data work, scripting, backend services, ML ecosystems; assess packaging, runtime performance, and type discipline.
- TypeScript/JavaScript: browser applications, Node.js services, shared web types; assess runtime validation and dependency footprint.
- Java/Kotlin: mature enterprise services and Android; assess JVM footprint and project complexity.
- C#: .NET services, Windows integration, cross-platform enterprise applications, Unity; assess target runtime and deployment.
- Go: simple deployable services, networking, concurrency, tooling; assess domain/library fit and abstraction needs.
- Rust: memory safety with systems-level control, performance-sensitive components, secure tooling; assess development complexity and ecosystem fit.
- C/C++: hardware, embedded, operating systems, real-time, legacy/native ecosystems; apply strict memory-safety tooling and review.
- Swift: Apple platform applications.
- Kotlin: Android and JVM services.
- Dart/Flutter: cross-platform UI where Flutter is an accepted product choice.
- PHP: web backends in PHP ecosystems and existing CMS/framework deployments.
- Ruby: productive web/application work in established Ruby ecosystems.
- SQL: declarative data access and transformation; not a substitute for application control flow.
- Shell/PowerShell: bounded operating-system automation; avoid for complex data models or security-sensitive parsing.

## Framework choice

Choose a framework only after confirming:
- It supports the target runtime and deployment.
- It is actively maintained and documented.
- Required integrations are mature.
- The team can operate it.
- Its complexity is justified.

## Database choice

- Relational database by default for transactional business data and strong constraints.
- Document/key-value/time-series/search/graph systems only for demonstrated access patterns or operational requirements.
- Avoid polyglot persistence without a clear ownership and operations plan.

## Decision output

For material choices provide:
1. Requirements
2. Options
3. Decision matrix or concise comparison
4. Selected option
5. Trade-offs
6. Revisit trigger

Never invent benchmarks. Measure the actual workload when performance determines the choice.
