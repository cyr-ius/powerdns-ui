import { HttpInterceptorFn } from "@angular/common/http";
import { inject } from "@angular/core";
import { catchError, throwError } from "rxjs";
import { AuthService } from "../services/auth.service";

const isOwnApi = (url: string): boolean => url.startsWith("/api/") || url.startsWith("/api");

export const authInterceptor: HttpInterceptorFn = (req, next) => {
  const auth = inject(AuthService);

  if (!isOwnApi(req.url)) {
    return next(req);
  }

  // Auth travels in an HttpOnly cookie; ensure it is sent with API calls.
  const authReq = req.clone({ withCredentials: true });

  return next(authReq).pipe(
    catchError((error) => {
      // A 401 on the auth endpoints is expected when simply not logged in
      // (e.g. the startup /me probe) and must not surface as "session expired".
      const isAuthEndpoint = req.url.includes("/api/auth/");
      if (error.status === 401 && !isAuthEndpoint && !auth.sessionExpired()) {
        auth.markSessionExpired();
      }
      return throwError(() => error);
    }),
  );
};
