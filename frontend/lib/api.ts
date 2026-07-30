export type UserRole = "Admin" | "Custodian" | "Employee";

export type Permissions = Record<string, boolean>;

export interface AuthSession {
  access_token: string;
  role: UserRole;
  user_id: number;
  name: string;
  permissions: Permissions;
}

const API_BASE =
  typeof window !== "undefined"
    ? process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"
    : process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export function getApiBase(): string {
  return API_BASE.replace(/\/$/, "");
}

export async function apiFetch<T>(
  path: string,
  options: RequestInit = {},
  token?: string | null
): Promise<T> {
  const headers: HeadersInit = {
    "Content-Type": "application/json",
    ...(options.headers || {}),
  };
  if (token) {
    (headers as Record<string, string>)["Authorization"] = `Bearer ${token}`;
  }
  const res = await fetch(`${getApiBase()}${path}`, { ...options, headers });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail || JSON.stringify(body);
    } catch {
      /* ignore */
    }
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
  }
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

export interface Asset {
  id: number;
  asset_code: string;
  name: string;
  type: "DEVICE" | "SPACE" | "FACILITY";
  status: string;
  lifecycle_warning: boolean;
  custodian_id: number | null;
  metadata_json?: Record<string, any> | null;
  expiration_date?: string | null;
  remaining_years?: number | null;
}

export interface CalendarReservation {
  id: number;
  start_time: string;
  end_time: string;
  borrower_name: string | null;
  borrower_email: string | null;
  approval_status: string;
  purpose: string;
}

export interface Reservation {
  id: number;
  asset_id: number;
  borrower_id: number;
  start_time: string;
  end_time: string;
  purpose: string;
  approval_status: string;
  asset_name?: string;
  borrower_name?: string;
}

export interface PermissionMatrixResponse {
  matrix: Record<string, Record<string, boolean>>;
  current_role: UserRole;
  current_permissions: Permissions;
}
