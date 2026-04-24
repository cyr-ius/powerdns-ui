import { inject } from "@angular/core";
import { CanActivateFn, Router } from "@angular/router";
import { ServerService } from "../services/server.service";

export const lmdbGuard: CanActivateFn = () => {
  const server = inject(ServerService);
  const router = inject(Router);
  if (server.supportsViewsAndNetworks()) {
    return true;
  }
  return router.createUrlTree(["/zones"]);
};
