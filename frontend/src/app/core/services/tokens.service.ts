import { HttpClient } from "@angular/common/http";
import { Injectable, inject } from "@angular/core";
import { firstValueFrom } from "rxjs";

export interface PersonalAccessToken {
  id: number;
  name: string;
  token_prefix: string;
  comment: string | null;
  created_at: string;
  expires_at: string | null;
  is_expired: boolean;
  username?: string;
  user_id?: number;
}

export interface PersonalAccessTokenCreated extends PersonalAccessToken {
  token: string;
}

@Injectable({ providedIn: "root" })
export class TokensService {
  private readonly http = inject(HttpClient);

  /** Lists the current user's personal access tokens. */
  listTokens(): Promise<PersonalAccessToken[]> {
    return firstValueFrom(this.http.get<PersonalAccessToken[]>("/api/tokens"));
  }

  /** Lists all tokens, across all users (admin only). */
  listAllTokens(): Promise<PersonalAccessToken[]> {
    return firstValueFrom(this.http.get<PersonalAccessToken[]>("/api/tokens/all"));
  }

  /** Creates a personal access token for the current user. */
  createToken(
    name: string,
    token?: string,
    comment?: string,
    durationDays?: number | null,
  ): Promise<PersonalAccessTokenCreated> {
    return firstValueFrom(
      this.http.post<PersonalAccessTokenCreated>("/api/tokens", {
        name,
        token: token || undefined,
        comment: comment || undefined,
        duration_days: durationDays ?? null,
      }),
    );
  }

  updateToken(tokenId: number, comment: string | null): Promise<PersonalAccessToken> {
    return firstValueFrom(this.http.patch<PersonalAccessToken>(`/api/tokens/${tokenId}`, { comment }));
  }

  deleteToken(tokenId: number): Promise<unknown> {
    return firstValueFrom(this.http.delete(`/api/tokens/${tokenId}`));
  }
}
