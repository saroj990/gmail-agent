# Future Architecture

Once the MVP works:

```text
                       Gmail
                         │
                         ▼
                    Gmail API
                         │
                         ▼
                ┌─────────────────┐
                │   AI Agent      │
                └────────┬────────┘
                         │
          ┌──────────────┼──────────────┐
          ▼              ▼              ▼
       Gmail Tool     Classifier     Memory
          │              │              │
          └──────────────┼──────────────┘
                         ▼
                   Decision Engine
                         │
                 ┌───────┴────────┐
                 ▼                ▼
             Automatic        Human Review
                 │                │
                 └───────┬────────┘
                         ▼
                      Gmail
```

## Possible later technologies

```text
LangGraph
FastAPI
React
PostgreSQL
Redis
MCP
```

Do not add these until the basic Python implementation works.
