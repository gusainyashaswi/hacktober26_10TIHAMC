const STORAGE_KEYS = {
  SELECTED_REPO_ID: 'nobluff:selected_repo_id',
  DEV_MODE_ENABLED: 'nobluff:dev_adapter_enabled',
};

// UI preference only: remembers which repository ID was active in the UI
export function getSelectedRepoId(): number | null {
  try {
    const raw = localStorage.getItem(STORAGE_KEYS.SELECTED_REPO_ID);
    if (!raw) return null;
    const num = Number(raw);
    return isNaN(num) ? null : num;
  } catch {
    return null;
  }
}

export function saveSelectedRepoId(id: number | null): void {
  try {
    if (id !== null && id !== undefined) {
      localStorage.setItem(STORAGE_KEYS.SELECTED_REPO_ID, String(id));
    } else {
      localStorage.removeItem(STORAGE_KEYS.SELECTED_REPO_ID);
    }
  } catch {
    // Ignore storage issues
  }
}

// Development adapter is DISABLED by default. Only enabled when explicitly turned on in Settings.
export function isDevAdapterEnabled(): boolean {
  try {
    const val = localStorage.getItem(STORAGE_KEYS.DEV_MODE_ENABLED);
    return val === 'true'; // strictly false by default!
  } catch {
    return false;
  }
}

export function setDevAdapterEnabled(enabled: boolean): void {
  try {
    localStorage.setItem(
      STORAGE_KEYS.DEV_MODE_ENABLED,
      enabled ? 'true' : 'false',
    );
  } catch {
    // Ignore
  }
}
