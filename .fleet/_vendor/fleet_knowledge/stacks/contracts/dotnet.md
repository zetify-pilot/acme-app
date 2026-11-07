---
type: spec
---

# .NET (C#) implementation contract — read before writing any C# code

The coding and lint contract for the **.NET lane**. The `languages` slot points here; an
implementing agent reads it in full before touching a `.cs` file. Code that breaks it fails
`make lint`, `make typecheck` or review, and the rework costs more than reading this did.

Written by `fleet init` from the `dotnet` stack profile. It is this repository's file: change a
rule here when the team changes its mind, and the next agent follows the new rule.

---

## The gate: warnings are errors, and nothing is baselined

- `make lint` runs `dotnet format --verify-no-changes`; `make typecheck` builds with
  `-warnaserror`. Both run in `make preflight`, before every push, and in CI.
- The analyzers are configured in `Directory.Build.props`: `<Nullable>enable</Nullable>`,
  `<AnalysisLevel>latest-recommended</AnalysisLevel>`, `<EnforceCodeStyleInBuild>true</EnforceCodeStyleInBuild>`,
  `<TreatWarningsAsErrors>true</TreatWarningsAsErrors>`. Style lives in `.editorconfig`.
- **Never suppress to get green.** No `#pragma warning disable`, no `[SuppressMessage]`, no
  `<NoWarn>` and no `!` (null-forgiving) added to make a warning go away. Fix the cause. A
  suppression that is genuinely right carries a one-line justification naming why the analyzer
  is wrong *here*, and is the exception a reviewer asks about.
- Package versions live in `Directory.Packages.props` (central package management). A
  `PackageReference` carries no `Version`. Restore is locked (`packages.lock.json`, committed).

## Coding conventions

- **Names.** `PascalCase` for types, members, constants and public fields; `camelCase` for
  locals and parameters; `_camelCase` for private fields; `I` prefix for interfaces; `Async`
  suffix for every method returning `Task`/`ValueTask`. One public type per file, file named
  after it, file-scoped `namespace` matching the folder.
- **Nullability is the contract.** A reference type that can be absent is `T?`; one that
  cannot, is checked at the boundary (`ArgumentNullException.ThrowIfNull`) and trusted inside.
- **Immutability by default.** `record` / `readonly record struct` for values and messages,
  `init` setters, `IReadOnlyList<T>` in signatures. Mutable state is private and owned.
- **Async all the way.** No `.Result`, `.Wait()` or `async void` (event handlers excepted).
  Every async method that does I/O takes a `CancellationToken` and passes it on.
- **Dependency injection through constructors** (primary constructors are fine). No service
  locator, no static mutable state, no `new HttpClient()` — use `IHttpClientFactory`.
- **Time and randomness are injected** (`TimeProvider`), so a test controls them.
- **Logging is structured**: `ILogger<T>` with message templates (`"Fault {FaultId} closed"`),
  never string interpolation into the message; prefer `[LoggerMessage]` source-generated
  methods on hot paths. Never log a secret, a token or personal data.
- **Configuration is typed**: options classes bound with `IOptions<T>` and validated at start
  (`ValidateDataAnnotations().ValidateOnStart()`), never `IConfiguration["key"]` scattered.
- **Data access**: EF Core with migrations, owned by the project that owns the schema. No raw
  SQL string concatenation, ever; `FromSql` with interpolated parameters when SQL is needed.
- Keep a method small enough to read on one screen; extract a well-named private method
  before adding a comment that explains a block.

## Error handling

- **Exceptions are for the exceptional.** An expected outcome a caller must handle (not found,
  validation failed, conflict) is a return value — a result type or a discriminated record —
  not an exception used for control flow.
- **Validate at the boundary** (request DTOs, message handlers, configuration) and fail with a
  precise message naming the field. Inside the domain, invariants are guaranteed by types.
- **Never swallow.** No empty `catch`, no `catch (Exception)` that logs and continues. Catch
  only what you can handle, at the layer that can handle it; otherwise let it propagate to the
  host's single handler.
- **Rethrow with `throw;`**, never `throw ex;` (it loses the stack). Wrap only to add meaning,
  with the original as `innerException`.
- **One translation point to the wire.** HTTP APIs answer errors as RFC 9457 problem details
  (`AddProblemDetails`, an `IExceptionHandler`); gRPC services map to a `Status` code in one
  interceptor. No stack trace or internal message reaches a client.
- `OperationCanceledException` from a cancelled token is not an error: let it propagate and do
  not log it as one.

## Tests — levels and naming

Three levels, told apart by an xUnit trait, because the `make` targets filter on it:

| Level | Trait | Runs in | What it may touch |
|---|---|---|---|
| unit | none | `make test-unit` | nothing outside the process: no database, network, clock or file system |
| integration | `[Trait("Category", "Integration")]` | `make test-db` | real dependencies in containers (Testcontainers: PostgreSQL, brokers), `WebApplicationFactory` |
| end-to-end | `[Trait("Category", "E2E")]` | `make test-e2e` | the built artifact, started as it ships |

- **Projects.** Tests live in `tests/<Project>.Tests` (unit) and `tests/<Project>.IntegrationTests`
  beside the `src/<Project>` they test, mirroring its folders.
- **Names.** Class `<TypeUnderTest>Tests`; method `<Method>_<Scenario>_<ExpectedResult>`, e.g.
  `Close_WhenFaultAlreadyClosed_ReturnsConflict`. The name states the behaviour, so a failure
  reads as a sentence.
- **Shape.** Arrange / act / assert, one behaviour per test, `[Theory]` + `[InlineData]` for
  the same behaviour over several inputs. No logic (loops, branches) in a test body.
- **Doubles.** Fake what you own at a seam; never mock a type you do not own (wrap it first).
  Never mock the database in an integration test — that is what the container is for.
- **Determinism.** No `Thread.Sleep`, no wall clock (`FakeTimeProvider`), no order dependence
  between tests; await the event, not a delay. A flaky test is a bug, fixed at its cause.
- **A bug fix starts with a failing test** that reproduces it, then the fix.
- Prefer xUnit's own `Assert`, or a library whose licence the project accepts; check the
  licence of any assertion or mocking package before adding it.

## Generated code stays separate

- Generated sources (gRPC/protobuf stubs, EF Core compiled models, OpenAPI clients) are produced
  by `make generate` or the build from a source of truth (`.proto`, a schema, the model), and
  are **never edited by hand** — change the source and regenerate.
- Build-time generators (`Grpc.Tools`, source generators) write under `obj/` and are never
  committed. Generated files that must be committed live in a folder or project of their own
  (`Generated/`, `*.Contracts`), carry the `// <auto-generated/>` header so analyzers skip them,
  and are excluded from `dotnet format` through `.editorconfig` (`generated_code = true`).
- EF Core migrations are generated (`dotnet ef migrations add <Name>`) and then reviewed; edit
  one only to fix what the generator cannot express, and never edit an applied migration — add
  a new one.
- Hand-written code never lives in a generated file. Extend a generated type through a
  `partial` class in a separate file.

## Verification you run yourself (FAST only — never the slow gates)

- `dotnet build <project> --nologo` for the project you changed.
- One targeted test: `make test-one T=<TestName>` (filters on the fully qualified name).
- `dotnet format <project> --verify-no-changes` for the project you changed.

Do **not** run `make test`, `make test-db`, `make test-e2e` or `make generate` from an
implementation task: the coordinator runs those once per wave.
