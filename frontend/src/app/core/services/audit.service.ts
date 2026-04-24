import { HttpClient, HttpParams } from "@angular/common/http";
import { Injectable, inject } from "@angular/core";
import { firstValueFrom } from "rxjs";
import { AuditLog, PdnsLogEntry, SyslogSettings } from "../../shared/models/audit.model";

export interface AuditLogFilters {
  skip?: number;
  limit?: number;
  username?: string;
  action?: string;
  resource_type?: string;
  status?: string;
  date_from?: string;
  date_to?: string;
}

@Injectable({ providedIn: "root" })
export class AuditService {
  private readonly http = inject(HttpClient);

  listAuditLogs(filters: AuditLogFilters = {}): Promise<AuditLog[]> {
    let params = new HttpParams();
    Object.entries(filters).forEach(([key, val]) => {
      if (val !== undefined && val !== null && val !== "") {
        params = params.set(key, String(val));
      }
    });
    return firstValueFrom(this.http.get<AuditLog[]>("/api/admin/audit", { params }));
  }

  countAuditLogs(filters: Omit<AuditLogFilters, "skip" | "limit"> = {}): Promise<{ count: number }> {
    let params = new HttpParams();
    Object.entries(filters).forEach(([key, val]) => {
      if (val !== undefined && val !== null && val !== "") {
        params = params.set(key, String(val));
      }
    });
    return firstValueFrom(this.http.get<{ count: number }>("/api/admin/audit/count", { params }));
  }

  getPdnsLogs(): Promise<PdnsLogEntry[]> {
    return firstValueFrom(this.http.get<PdnsLogEntry[]>("/api/admin/audit/pdns-logs"));
  }

  getSyslogSettings(): Promise<SyslogSettings> {
    return firstValueFrom(this.http.get<SyslogSettings>("/api/admin/audit/syslog"));
  }

  updateSyslogSettings(data: SyslogSettings): Promise<SyslogSettings> {
    return firstValueFrom(this.http.put<SyslogSettings>("/api/admin/audit/syslog", data));
  }
}
