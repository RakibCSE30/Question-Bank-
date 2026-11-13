export type UserRole = "ADMIN" | "REVIEWER" | "STUDENT";
export type Locale = "bn" | "en";

export interface User {
  id: string;
  email: string;
  full_name: string;
  role: UserRole;
  preferred_lang: Locale;
  is_active: boolean;
  created_at: string;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
  user: User;
}

export interface DashboardMetricCard {
  key: string;
  value: number | string;
}

export interface DashboardSummaryResponse {
  role: UserRole;
  phase: string;
  metrics: DashboardMetricCard[];
  notices: string[];
}

export interface UserListResponse {
  items: User[];
  total: number;
}
