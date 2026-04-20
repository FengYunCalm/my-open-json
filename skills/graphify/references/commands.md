# Graphify Command Patterns

## Build / Update

- Build current directory: `/graphify`
- Build a specific path: `/graphify <path>`
- Incremental update: `/graphify <path> --update`
- Deep extraction: `/graphify <path> --mode deep`
- Re-cluster existing output: `/graphify <path> --cluster-only`

## Querying

- Broad graph query: `/graphify query "<question>"`
- DFS-style trace: `/graphify query "<question>" --dfs`
- Path between nodes: `/graphify path "NodeA" "NodeB"`
- Explain a node: `/graphify explain "NodeName"`

## Corpus Growth

- Add URL to corpus: `/graphify add <url>`
- Watch for code changes: `/graphify <path> --watch`

Use these as entry patterns. Choose only the mode the user actually asked for.
