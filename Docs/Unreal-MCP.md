# Reading this Unreal project

This project uses the Unreal MCP and All Toolsets plugins bundled with UE 5.8.2.
The editor loads binary assets and exposes their structure through MCP.

## Connection

- Open `shite.uproject` in Unreal Editor and wait for startup to finish.
- The project defaults enable automatic MCP startup at `http://127.0.0.1:8000/mcp`.
- The project-scoped Codex connection is in `.codex/config.toml`.
- Restart/reconnect Codex after adding the connection if its tools are not visible.
- If the server is stopped, use `ModelContextProtocol.StartServer` in the Unreal console.
- Editor Preferences > General > Model Context Protocol can override the project defaults.

## Inspection workflow

1. Call `list_toolsets`, then `describe_toolset` for the relevant toolset.
2. Use `call_tool` with the exact names and argument schemas returned by discovery.
3. For Blueprints, discover `BlueprintTools`: list graphs, functions, events, and variables.
4. Read a graph with `read_graph_dsl` for compact logic, and inspect nodes and pins when full structural detail is needed.
5. Use the asset, object, scene, material, data-table, mesh, and UMG toolsets as appropriate. Available coverage depends on the loaded toolsets and asset type.

Issue editor tool calls sequentially. Read ordinary source/config/text files directly.
For inspection requests, use read operations; do not compile, save, or modify assets unless the task calls for it.
The connection also exposes editing operations; it is not a technically read-only server.

Project asset examples: `/Game/BP_GridManager`, `/Game/BP_BuildingBase`,
`/Game/PC_Cam`, `/Game/WBP_BuildingMenu`.

## Verified on this project

On 2026-09-29, the live UE 5.8.2 server successfully returned all six graphs in
`BP_GridManager`: UserConstructionScript, GridToWorld, WorldToGrid, DrawGridDebug,
CheckFootprint, and EventGraph. Both the compact logic and all 13 nodes of
CheckFootprint were read, including typed pins, values, connections, and positions.
Verification output is under `Saved/Codex/` and is not a live replacement for MCP.

## Limits

The editor must be running for live asset inspection. This reads editor asset data,
not arbitrary binary files or a universal bytecode decompilation. Raw mesh, texture,
and audio contents may need exports or previews beyond property inspection.
Epic labels the bundled MCP system experimental.

Official setup: https://dev.epicgames.com/documentation/unreal-engine/unreal-mcp-in-unreal-editor
