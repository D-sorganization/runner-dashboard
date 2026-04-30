import { z, type ZodType } from "zod";

export const STORAGE_KEYS = {
  issuesSourceFilter: "issuesSourceFilter",
  issuesFilterRepo: "issues:filter_repo",
  issuesFilterComplexity: "issues:filter_complexity",
  issuesFilterJudgement: "issues:filter_judgement",
  issuesFilterPickable: "issues:filter_pickable",
  remediationSubtab: "remediation-subtab",
  workflowsMobileFilters: "workflowsMobileFilters",
  maxwellMobileChatHistory: "maxwellMobileChatHistory",
  maxwellMobileChatHistoryDisabled: "maxwellMobileChatHistoryDisabled",
  assistantOpen: "assistant:open",
  assistantPosition: "assistant:position",
  assistantWidth: "assistant:width",
  assistantTranscript: "assistant:transcript",
  assistantTranscriptTimestamp: "assistant:transcript:ts",
  assistantOpenByDefault: "assistant:openByDefault",
  assistantIncludeContext: "assistant:includeContext",
  assistantSaveHistory: "assistant:saveHistory",
} as const;

export type StorageKey = (typeof STORAGE_KEYS)[keyof typeof STORAGE_KEYS];
export type StorageArea = "local" | "session";

type StoredEnvelope = {
  version: number;
  value: unknown;
};

type StorageOptions<T> = {
  area?: StorageArea;
  version?: number;
  migrations?: Record<number, (value: unknown) => unknown>;
  onQuotaExceeded?: (key: StorageKey, value: T) => void;
};

const memoryStorage = new Map<string, string>();

export const booleanSchema = z.boolean();
export const stringSchema = z.string();
export const numberSchema = z.number();
export const stringRecordSchema = z.record(z.string());

export const maxwellChatMessageSchema = z
  .object({
    id: z.union([z.number(), z.string()]),
    role: z.string(),
    content: z.string(),
    streaming: z.boolean().optional(),
    error: z.boolean().optional(),
    detail: z.string().optional(),
  })
  .passthrough();

export const maxwellChatMessagesSchema = z.array(maxwellChatMessageSchema);

export const storageMigrations: Partial<
  Record<StorageKey, Record<number, (value: unknown) => unknown>>
> = {
  [STORAGE_KEYS.maxwellMobileChatHistory]: {
    1: (value: unknown) => value,
  },
};

function storageFor(area: StorageArea): Storage | null {
  if (typeof window === "undefined") return null;
  return area === "session" ? window.sessionStorage : window.localStorage;
}

function isQuotaExceeded(error: unknown): boolean {
  return (
    error instanceof DOMException &&
    (error.name === "QuotaExceededError" ||
      error.name === "NS_ERROR_DOM_QUOTA_REACHED" ||
      error.code === 22 ||
      error.code === 1014)
  );
}

function toastStorageWarning(key: StorageKey): void {
  try {
    const toaster = (window as unknown as { __toaster?: { showToast?: Function } }).__toaster;
    toaster?.showToast?.("Storage is full; using memory until reload.", {
      variant: "warning",
      title: "Preferences not saved",
      detail: key,
    });
  } catch {
    // Toasting must never break storage reads or writes.
  }
}

function decodeStored(raw: string): unknown {
  const parsed = JSON.parse(raw);
  if (
    parsed &&
    typeof parsed === "object" &&
    "version" in parsed &&
    "value" in parsed
  ) {
    return parsed as StoredEnvelope;
  }
  return parsed;
}

function migrateValue<T>(
  key: StorageKey,
  decoded: unknown,
  options: StorageOptions<T>,
): unknown {
  if (!decoded || typeof decoded !== "object" || !("version" in decoded)) {
    return decoded;
  }

  const envelope = decoded as StoredEnvelope;
  const targetVersion = options.version ?? 1;
  let value = envelope.value;
  let version = envelope.version;
  const migrations = options.migrations ?? storageMigrations[key] ?? {};

  while (version < targetVersion) {
    const migrate = migrations[version];
    if (!migrate) break;
    value = migrate(value);
    version += 1;
  }

  return value;
}

export function getItem<T>(
  key: StorageKey,
  schema: ZodType<T>,
  fallback: T,
  options: StorageOptions<T> = {},
): T {
  const area = options.area ?? "local";
  const storage = storageFor(area);
  const memoryKey = `${area}:${key}`;
  const raw = storage?.getItem(key) ?? memoryStorage.get(memoryKey);
  if (raw == null) return fallback;

  try {
    const value = migrateValue(key, decodeStored(raw), options);
    const parsed = schema.safeParse(value);
    return parsed.success ? parsed.data : fallback;
  } catch {
    return fallback;
  }
}

export function setItem<T>(
  key: StorageKey,
  value: T,
  schema: ZodType<T>,
  options: StorageOptions<T> = {},
): boolean {
  const parsed = schema.safeParse(value);
  if (!parsed.success) return false;

  const area = options.area ?? "local";
  const version = options.version ?? 1;
  const memoryKey = `${area}:${key}`;
  const raw = JSON.stringify({ version, value: parsed.data });
  const storage = storageFor(area);

  try {
    storage?.setItem(key, raw);
    memoryStorage.delete(memoryKey);
    return true;
  } catch (error) {
    if (isQuotaExceeded(error) || !storage) {
      memoryStorage.set(memoryKey, raw);
      options.onQuotaExceeded?.(key, parsed.data);
      toastStorageWarning(key);
      return false;
    }
    return false;
  }
}

export function removeItem(
  key: StorageKey,
  options: Pick<StorageOptions<unknown>, "area"> = {},
): void {
  const area = options.area ?? "local";
  const memoryKey = `${area}:${key}`;
  memoryStorage.delete(memoryKey);
  try {
    storageFor(area)?.removeItem(key);
  } catch {
    // Ignore unavailable storage, matching browser private-mode behavior.
  }
}

export function clearMemoryFallbacks(): void {
  memoryStorage.clear();
}
