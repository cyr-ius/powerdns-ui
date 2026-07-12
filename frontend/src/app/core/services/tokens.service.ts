import { HttpClient } from "@angular/common/http";
import { Injectable, inject } from "@angular/core";
import { firstValueFrom } from "rxjs";

export interface PersonalAccessToken {
  id: number;
  name: string;
  token_prefix: string;
  comment: string | null;
  created_at: string;
  username?: string;
  user_id?: number;
}

export interface PersonalAccessTokenCreated extends PersonalAccessToken {
  token: string;
}

@Injectable({ providedIn: "root" })
export class TokensService {
  private readonly http = inject(HttpClient);

  /** Liste les jetons d'accès personnels de l'utilisateur courant. */
  listTokens(): Promise<PersonalAccessToken[]> {
    return firstValueFrom(this.http.get<PersonalAccessToken[]>("/api/tokens"));
  }

  /** Liste tous les jetons, tous utilisateurs confondus (admin uniquement). */
  listAllTokens(): Promise<PersonalAccessToken[]> {
    return firstValueFrom(this.http.get<PersonalAccessToken[]>("/api/tokens/all"));
  }

  /** Crée un jeton d'accès personnel pour l'utilisateur courant. */
  createToken(name: string, token?: string, comment?: string): Promise<PersonalAccessTokenCreated> {
    return firstValueFrom(
      this.http.post<PersonalAccessTokenCreated>("/api/tokens", {
        name,
        token: token || undefined,
        comment: comment || undefined,
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
