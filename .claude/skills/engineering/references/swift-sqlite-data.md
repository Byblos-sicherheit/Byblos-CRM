# SQLiteData — Swift Persistence (SwiftData Replacement)

Fast, lightweight replacement for SwiftData, powered by SQLite and GRDB, with built-in CloudKit sync.

Source: `pointfreeco/sqlite-data` (MIT) · Swift 6 · iOS 16+ / macOS 13+ / tvOS 16+ / watchOS 9+  
Docs: swiftpackageindex.com/pointfreeco/sqlite-data

---

## When to Use vs. SwiftData

| Situation | Use SQLiteData | Use SwiftData |
|---|---|---|
| Need direct SQL access | ✅ | ❌ |
| UIKit / @Observable outside SwiftUI | ✅ | ❌ (SwiftUI-centric) |
| Performance-critical bulk reads | ✅ | ❌ |
| CloudKit sync with sharing | ✅ | ⚠ limited |
| Simple SwiftUI-only app | ⚠ overkill | ✅ |
| Xcode visual schema editor | ❌ | ✅ |

Performance note: SQLiteData's raw fetch speed ≈ C SQLite API. SwiftData/GRDB-Codable is 6-7× slower.

---

## Core API

### 1. Define a Table (like SwiftData's `@Model`)

```swift
import SQLiteData

@Table
struct Item {
  let id: UUID
  var title = ""
  var isInStock = true
  var notes = ""
}
```

`@Table` is a Swift macro from `StructuredQueries` that generates type-safe column accessors and
table metadata. Use `struct`, not `class` (unlike SwiftData's `@Model`).

### 2. Bootstrap the Database

```swift
@main
struct MyApp: App {
  init() {
    prepareDependencies {
      $0.defaultDatabase = try! appDatabase()
    }
  }
}

func appDatabase() throws -> DatabaseQueue {
  let db = try DatabaseQueue(path: /* ... */)
  var migrator = DatabaseMigrator()
  migrator.registerMigration("v1") { db in
    try db.create(table: Item.tableName) { t in
      t.primaryKey("id", .text)
      t.column("title", .text).notNull().defaults(to: "")
      t.column("isInStock", .boolean).notNull().defaults(to: true)
      t.column("notes", .text).notNull().defaults(to: "")
    }
  }
  try migrator.migrate(db)
  return db
}
```

### 3. Fetch in SwiftUI (`@FetchAll` / `@FetchOne`)

```swift
struct ItemListView: View {
  @FetchAll var items: [Item]                              // all rows
  @FetchAll(Item.order(by: \.title)) var sorted: [Item]   // sorted
  @FetchAll(Item.where(\.isInStock)) var inStock: [Item]  // filtered
  @FetchOne(Item.count()) var count = 0                   // aggregate

  var body: some View {
    List(items, id: \.id) { item in
      Text(item.title)
    }
  }
}
```

Views update automatically when the database changes (like SwiftData `@Query`).

### 4. Fetch in @Observable / UIKit

```swift
@Observable
class ItemModel {
  var items: [Item] = []
  private var cancellable: AnyDatabaseCancellable?

  func start() {
    cancellable = Item.fetchAll()
      .observeInBackground { [weak self] result in
        self?.items = (try? result.get()) ?? []
      }
  }
}
```

### 5. Write (Insert / Update / Delete)

```swift
@Dependency(\.defaultDatabase) var database

// Insert
try database.write { db in
  try Item.insert { Item(id: UUID(), title: "Buy milk") }.execute(db)
}

// Update
try database.write { db in
  try Item.update { $0.isInStock = false }
    .where { $0.id == item.id }
    .execute(db)
}

// Delete
try database.write { db in
  try Item.delete().where { $0.id == item.id }.execute(db)
}
```

### 6. Associations (Joins)

```swift
@Table struct Tag { let id: UUID; var name = "" }
@Table struct ItemTag { let itemId: UUID; let tagId: UUID }

// Fetch items with their tags
let itemsWithTags = try database.read { db in
  try Item
    .join(ItemTag.self, on: \.id == \.itemId)
    .join(Tag.self, on: ItemTag.Columns.tagId == \.id)
    .fetchAll(db)
}
```

### 7. Dynamic Queries

```swift
struct SearchView: View {
  @State var searchText = ""

  var query: some QueryExpression {
    if searchText.isEmpty {
      Item.fetchAll()
    } else {
      Item.where { $0.title.like("%\(searchText)%") }
    }
  }

  @FetchAll(query) var results: [Item]
}
```

---

## CloudKit Sync

```swift
@main
struct MyApp: App {
  init() {
    prepareDependencies {
      $0.defaultDatabase = try! appDatabase()
      $0.defaultSyncEngine = SyncEngine(
        for: $0.defaultDatabase,
        tables: Item.self, Tag.self
      )
    }
  }
}
```

- Uses `CKSyncEngine` under the hood (requires CloudKit entitlement)
- Handles conflict resolution automatically (last-write-wins by default)
- CloudKit sharing (share a specific record with another iCloud user) documented in `CloudKitSharing.md`

---

## Migrations

```swift
migrator.registerMigration("v2") { db in
  try db.alter(table: Item.tableName) { t in
    t.add(column: "priority", .integer).notNull().defaults(to: 0)
  }
}
// migrator.eraseDatabaseOnSchemaChange = true  // dev-only: reset DB on mismatch
```

SQLiteData uses GRDB's `DatabaseMigrator` — migrations are numbered strings, run in order, never re-run.

---

## Installation

```swift
// Package.swift
.package(url: "https://github.com/pointfreeco/sqlite-data", from: "1.0.0")

// Target dependency
.product(name: "SQLiteData", package: "sqlite-data")
```

Or via Xcode: File → Add Package Dependencies → paste GitHub URL.

---

## Dependencies (auto-installed via SPM)

| Package | Purpose |
|---|---|
| `groue/GRDB.swift` | SQLite access, migrations, observation |
| `pointfreeco/swift-structured-queries` | Type-safe query building, `@Table` macro |
| `pointfreeco/swift-dependencies` | DI for `defaultDatabase` and `defaultSyncEngine` |
| `pointfreeco/swift-sharing` | `@FetchAll` / `@FetchOne` property wrappers |
| `apple/swift-collections` | `OrderedDictionary` for sectioned queries |

---

## Key Differences from SwiftData

| | SQLiteData | SwiftData |
|---|---|---|
| Schema type | `struct` + `@Table` | `class` + `@Model` |
| Fetch in view | `@FetchAll` / `@FetchOne` | `@Query` |
| Fetch outside view | `.observeInBackground` | No native support |
| Write | `database.write { try ... }` | `modelContext.insert/save` |
| Migrations | Manual GRDB migrator | Automatic (opaque) |
| SQL access | Direct via GRDB | ❌ hidden |
| CloudKit sharing | ✅ built in | ⚠ limited |
| Xcode preview support | ✅ (in-memory DB) | ✅ |
