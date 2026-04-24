import { HttpClient } from "@angular/common/http";
import { Injectable, inject } from "@angular/core";
import { firstValueFrom } from "rxjs";
import {
  Account,
  AccountCreate,
  AdminUser,
  OidcSettings,
  RecordType,
  RecordTypeCreate,
} from "../../shared/models/admin.model";

@Injectable({ providedIn: "root" })
export class AdminService {
  private readonly http = inject(HttpClient);

  // ── Users ────────────────────────────────────────────────────────────────

  listUsers(): Promise<AdminUser[]> {
    return firstValueFrom(this.http.get<AdminUser[]>("/api/admin/users"));
  }

  createUser(data: {
    username: string;
    password: string;
    email?: string | null;
    is_admin: boolean;
  }): Promise<AdminUser> {
    return firstValueFrom(this.http.post<AdminUser>("/api/admin/users", data));
  }

  updateUser(id: number, data: { email?: string | null; is_admin?: boolean; is_active?: boolean }): Promise<AdminUser> {
    return firstValueFrom(this.http.patch<AdminUser>(`/api/admin/users/${id}`, data));
  }

  resetPassword(id: number, newPassword: string): Promise<void> {
    return firstValueFrom(this.http.post<void>(`/api/admin/users/${id}/reset-password`, { new_password: newPassword }));
  }

  deleteUser(id: number): Promise<void> {
    return firstValueFrom(this.http.delete<void>(`/api/admin/users/${id}`));
  }

  // ── Accounts ─────────────────────────────────────────────────────────────

  listAccounts(): Promise<Account[]> {
    return firstValueFrom(this.http.get<Account[]>("/api/admin/accounts"));
  }

  createAccount(data: AccountCreate): Promise<Account> {
    return firstValueFrom(this.http.post<Account>("/api/admin/accounts", data));
  }

  updateAccount(id: number, data: { name?: string; description?: string | null }): Promise<Account> {
    return firstValueFrom(this.http.patch<Account>(`/api/admin/accounts/${id}`, data));
  }

  setAccountUsers(id: number, userIds: number[]): Promise<void> {
    return firstValueFrom(this.http.put<void>(`/api/admin/accounts/${id}/users`, { user_ids: userIds }));
  }

  deleteAccount(id: number): Promise<void> {
    return firstValueFrom(this.http.delete<void>(`/api/admin/accounts/${id}`));
  }

  // ── OIDC ─────────────────────────────────────────────────────────────────

  getOidcSettings(): Promise<OidcSettings> {
    return firstValueFrom(this.http.get<OidcSettings>("/api/admin/oidc"));
  }

  updateOidcSettings(data: OidcSettings): Promise<OidcSettings> {
    return firstValueFrom(this.http.put<OidcSettings>("/api/admin/oidc", data));
  }

  // ── Record Types ──────────────────────────────────────────────────────────

  listRecordTypes(): Promise<RecordType[]> {
    return firstValueFrom(this.http.get<RecordType[]>("/api/admin/record-types"));
  }

  createRecordType(data: RecordTypeCreate): Promise<RecordType> {
    return firstValueFrom(this.http.post<RecordType>("/api/admin/record-types", data));
  }

  updateRecordType(id: number, data: { enabled?: boolean; applicable_to?: string }): Promise<RecordType> {
    return firstValueFrom(this.http.patch<RecordType>(`/api/admin/record-types/${id}`, data));
  }

  deleteRecordType(id: number): Promise<void> {
    return firstValueFrom(this.http.delete<void>(`/api/admin/record-types/${id}`));
  }
}
