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

  const token = auth.getToken();
  const authReq = token ? req.clone({ setHeaders: { Authorization: `Bearer ${token}` } }) : req;

  return next(authReq).pipe(
    catchError((error) => {
      if (error.status === 401 && !req.url.includes("/api/auth/login") && !auth.sessionExpired()) {
        auth.markSessionExpired();
      }
      return throwError(() => error);
    }),
  );
};
