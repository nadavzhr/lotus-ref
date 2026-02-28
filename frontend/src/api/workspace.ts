/**
 * Workspace-level API calls (WARD / CELL resolution, etc.).
 * Currently a stub — will be populated when Electron IPC is available.
 */

export async function getWorkspaceInfo(): Promise<{
  ward: string;
  cell: string;
}> {
  // In Electron, this would call ipcRenderer.invoke("get-workspace-info").
  // For now, read from environment or return defaults.
  return {
    ward: import.meta.env.VITE_WARD ?? "",
    cell: import.meta.env.VITE_CELL ?? "",
  };
}
