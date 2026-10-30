# Changelog

## [2.6.0](https://github.com/cyr-ius/powerdns-ui/compare/2.5.0...2.6.0) (2026-10-30)


### Features

* **about:** show the PowerDNS connection, version and URL ([c14a484](https://github.com/cyr-ius/powerdns-ui/commit/c14a484c575b303d3e137c4ae2ff5b96ea14ebb5))
* **admin:** rename the OIDC menu and page to Connexions ([4c281fc](https://github.com/cyr-ius/powerdns-ui/commit/4c281fc28af25a1667a126de660d59b4fe03319f))
* **auth:** enforce the password policy ([471dec4](https://github.com/cyr-ius/powerdns-ui/commit/471dec4039d9d0813864fbab293b03af73250f7a))
* **catalogues:** explain what a producer catalog is when there is none ([5346fd2](https://github.com/cyr-ius/powerdns-ui/commit/5346fd20dd9329bd0d51dd931611dd9148bdb6e9))
* **search:** search the term anywhere by default ([eef481a](https://github.com/cyr-ius/powerdns-ui/commit/eef481a36486a98eb927e92773673561dd5515d6))
* **zones:** filter the records of a zone ([b874eeb](https://github.com/cyr-ius/powerdns-ui/commit/b874eebb600d158a788036f45f58c1fb9a840ae3))


### Bug Fixes

* **zones:** validate zone ids and bound the zone file import ([6c50d9b](https://github.com/cyr-ius/powerdns-ui/commit/6c50d9b041a3acbfed61741f34caae6fdfc15ca5))


### Documentation

* **accounts:** explain that an account groups zones like a tenant ([42fb26e](https://github.com/cyr-ius/powerdns-ui/commit/42fb26e6251967898a50fa0fe835c904befd06e0))

## [2.5.0](https://github.com/cyr-ius/powerdns-ui/compare/2.4.0...2.5.0) (2026-10-30)


### Features

* **acme:** allow reassigning the owner of an ACME key ([d33f132](https://github.com/cyr-ius/powerdns-ui/commit/d33f132d8ba95dfb56b4127b6cf2a40a1882137c))
* **acme:** allow renaming and editing zone ACME keys ([3375da4](https://github.com/cyr-ius/powerdns-ui/commit/3375da4ebe1a3d60b1e164377098c0f2160b7857))
* **acme:** track and display last-used date for ACME keys ([1131bd6](https://github.com/cyr-ius/powerdns-ui/commit/1131bd697bd366613533a84f2cdfe1d1bd549ff2))
* add ACME key management for zones and update UI ([0fdeffd](https://github.com/cyr-ius/powerdns-ui/commit/0fdeffd4dd75d0fedbd5af894b52cdbc11ce6d0c))
* add ACME Keys feature to README.md ([99b7237](https://github.com/cyr-ius/powerdns-ui/commit/99b7237a9c480d95140dde1c60b16a84bc044bf9))
* add icons to zone detail tabs for better UX ([765644e](https://github.com/cyr-ius/powerdns-ui/commit/765644e2cee3abfcde73c28c563f7a3f6bf2ddc5))
* add orphan key handling and translations ([b694e6c](https://github.com/cyr-ius/powerdns-ui/commit/b694e6ce7cd260ca3b1bfb579c53a00189598975))
* ajouter des fichiers de documentation et de politique de sécurité ([2987b3e](https://github.com/cyr-ius/powerdns-ui/commit/2987b3ef854027c50036421ea82204324ac5eb26))
* ajouter des variables d'environnement et nettoyer les dépendances Python ([e221553](https://github.com/cyr-ius/powerdns-ui/commit/e221553f3918bb89be6cef39f98e609f2062086c))
* ajouter la gestion des cookies HttpOnly pour les sessions et limiter les tentatives de connexion ([6aaf1ef](https://github.com/cyr-ius/powerdns-ui/commit/6aaf1eff9f1eb26b3baba2883ee83e8506063421))
* always auto-generate the admin password ([bf4fd35](https://github.com/cyr-ius/powerdns-ui/commit/bf4fd351f4948db1cacaec865b312f0175647aec))
* améliorer la gestion de l'authentification en utilisant des cookies HttpOnly et simplifier le processus de connexion ([3022196](https://github.com/cyr-ius/powerdns-ui/commit/30221963f1cd3978603044ed707681b8fb6d189d))
* améliorer la gestion des clés secrètes et des mots de passe administratifs ([2183690](https://github.com/cyr-ius/powerdns-ui/commit/21836905618776b2cc477dbf83fe5ec92f628acb))
* **audit:** add free-text search on PDNS logs tab ([76815ad](https://github.com/cyr-ius/powerdns-ui/commit/76815ad987620adb5be4c465e7c1e3cf4cd44dda))
* **audit:** parse structured PDNS logs ([5688f3d](https://github.com/cyr-ius/powerdns-ui/commit/5688f3df66a763d55c705aef0e222f4cc1d78747))
* **auth:** dedicated Personal Access Token model, split from ACME keys ([e93cc46](https://github.com/cyr-ius/powerdns-ui/commit/e93cc46e0d90dcb1a000c4b0cf4a782b17b00a3c))
* **auth:** OIDC RP-initiated logout and empty SECRET_KEY default ([fd1260e](https://github.com/cyr-ius/powerdns-ui/commit/fd1260efdf89a51d3aaa664cf382c2fcbbf01bfa))
* **backend:** manage the UI database schema with Alembic ([4aa5280](https://github.com/cyr-ius/powerdns-ui/commit/4aa52800e98b1b694c5ca3ad43a37022fa3174c8))
* **backend:** PAT bearer auth, env-pinned connectors, SMTP test ([16bd46e](https://github.com/cyr-ius/powerdns-ui/commit/16bd46ed7c304a3415b81cb9eeefbbeb9edc6363))
* detach PowerDNS zones when deleting an account to avoid invalid references ([87ca15c](https://github.com/cyr-ius/powerdns-ui/commit/87ca15c39afa6471e695f3ce596ed96020defbef))
* **devcontainer:** add docker CLI and pdns start/stop tasks ([4aae2ce](https://github.com/cyr-ius/powerdns-ui/commit/4aae2cea0062f4751b794e09dc52f5d401657899))
* **frontend:** dashboard, About page, collapsible sidebar ([d136940](https://github.com/cyr-ius/powerdns-ui/commit/d136940d8e491d64d8b660384c47f144eb9c22fc))
* **i18n:** add description for API keys in translations ([c731c75](https://github.com/cyr-ius/powerdns-ui/commit/c731c75ba70f01cbee5d837d76854d2965913c2e))
* mettre à jour la documentation pour la génération automatique des mots de passe et des clés secrètes ([21e20a1](https://github.com/cyr-ius/powerdns-ui/commit/21e20a1286584b7ab285600fe3faa332ffabaac1))
* **pdns:** bump PowerDNS Authoritative to 5.1.3 and adopt new API capabilities ([d728921](https://github.com/cyr-ius/powerdns-ui/commit/d728921199e9aa1534a8b291f80d341ca611aa66))
* permettre la génération automatique des mots de passe administratifs et des clés secrètes ([69b41fe](https://github.com/cyr-ius/powerdns-ui/commit/69b41fee7b78da5f83e7fc227990727ec8733864))
* prevent locking out the last OIDC admin in OIDC-only mode ([77dfec5](https://github.com/cyr-ius/powerdns-ui/commit/77dfec5af1fc88473b6b197b155cf7349abeb36e))
* **profile:** add ACME keys management to profile ([641dc0a](https://github.com/cyr-ius/powerdns-ui/commit/641dc0aefca881cc930507f13faa627e0138c052))
* **security:** add global rate-limiting middleware with trusted proxies ([c20e191](https://github.com/cyr-ius/powerdns-ui/commit/c20e1911cde9974ee8138f9568b151fe8cc91c47))
* **tokens:** add expiration to personal access tokens ([0c41140](https://github.com/cyr-ius/powerdns-ui/commit/0c4114047a490868149ca99c9b2749a0a20f6323))
* update Node.js version to 2.1.0 in container configuration files ([8ebb195](https://github.com/cyr-ius/powerdns-ui/commit/8ebb195fdea64c91d8436d7214aa84ab4b485f63))


### Bug Fixes

* **auth:** revoke session JWTs and harden the OIDC flow ([9c3a786](https://github.com/cyr-ius/powerdns-ui/commit/9c3a7865e58c9ecb9e053ebf5690fd6c27ce50d0))
* **backend:** avoid races between Uvicorn workers on first start ([5b82e5b](https://github.com/cyr-ius/powerdns-ui/commit/5b82e5b6f5139ad5ad1cb3427421d95ef4056ddf))
* **ci:** add .mcp.json file ([a5ae8c5](https://github.com/cyr-ius/powerdns-ui/commit/a5ae8c5c66052ed73dd6a77281aba0fff9c895ef))
* **ci:** update environment files ([a31e9c5](https://github.com/cyr-ius/powerdns-ui/commit/a31e9c54e8150d0dec8aafe97f14894625bffb5d))
* **ci:** update environment files ([405b52a](https://github.com/cyr-ius/powerdns-ui/commit/405b52add8141bd528fffe4f60855e271b770bea))
* **ci:** update environnment files ([0104165](https://github.com/cyr-ius/powerdns-ui/commit/0104165057d246c404eb6aff924619a8ac8721d0))
* **ci:** update environnment files ([59fc624](https://github.com/cyr-ius/powerdns-ui/commit/59fc624baecc4e11ce40b0a759bf98e3d15c6cd4))
* **ci:** update environnment files ([4f357d4](https://github.com/cyr-ius/powerdns-ui/commit/4f357d41967470104aaeeff5dba0f7af66950393))
* **ci:** update environnment files ([c0b296a](https://github.com/cyr-ius/powerdns-ui/commit/c0b296af04ac0bebd5465185d5b98f1b30700672))
* **ci:** update environnment files ([77c27ea](https://github.com/cyr-ius/powerdns-ui/commit/77c27ea7ccbf2e3836b7960794efcd67bef9ab43))
* **deps:** replace python-jose with PyJWT ([abd0785](https://github.com/cyr-ius/powerdns-ui/commit/abd07854187c1901ee41555d2e7e7e8b40349c5d))
* **dev:** Add pretask launcher to start pdns ([4405eb6](https://github.com/cyr-ius/powerdns-ui/commit/4405eb66ff679197eb2d55c5947263b035644421))
* **docker:** build from root pyproject and add a hardened test compose ([3f54f00](https://github.com/cyr-ius/powerdns-ui/commit/3f54f00e57a851f8865152fef444bafd54732770))
* **docker:** hand an existing data volume over to the non-root user ([fbab5dc](https://github.com/cyr-ius/powerdns-ui/commit/fbab5dc8efe1f257e75732d19213322b4be3b263))
* **docker:** run a single Uvicorn worker by default ([46ace85](https://github.com/cyr-ius/powerdns-ui/commit/46ace85e466cd67c00c6f7ed062c672475498165))
* **docker:** run as non-root and make the build reproducible ([fa28459](https://github.com/cyr-ius/powerdns-ui/commit/fa28459318021071821269a98f273bc277d44a40))
* **docs:** update agent ([aeb63b6](https://github.com/cyr-ius/powerdns-ui/commit/aeb63b63d32637c8979109153d91f57f32074d51))
* handle optional user fields in admin response ([0628a23](https://github.com/cyr-ius/powerdns-ui/commit/0628a238f8f9058c3e3990b03e301099405f9446))
* improve logging configuration format for better readability ([543a2f1](https://github.com/cyr-ius/powerdns-ui/commit/543a2f11abef75eb910976177a9182ddb1883019))
* make user_id nullable for ACME keys ([2475abd](https://github.com/cyr-ius/powerdns-ui/commit/2475abd37df76f9206d20b85c0c60f6a10e20e6a))
* prevent non-global-admins from changing the account field in zone updates ([a6c9e66](https://github.com/cyr-ius/powerdns-ui/commit/a6c9e667860bc255a20346dbebc431eaaeb5ea81))
* restore runtime dependencies dropped from pyproject ([9ee7879](https://github.com/cyr-ius/powerdns-ui/commit/9ee78798bece674b6c77af08a13c46680773b5a4))
* **security:** drop unsafe-inline scripts and send HSTS over HTTPS only ([0538a78](https://github.com/cyr-ius/powerdns-ui/commit/0538a7842781eae55eff0a7c9ccc748b6de7c958))
* update .gitignore to streamline ignored files and directories ([6e269bd](https://github.com/cyr-ius/powerdns-ui/commit/6e269bdd7851dbec33b3e461b8ea9348745f1119))
* update Angular version in README.md ([c1b743a](https://github.com/cyr-ius/powerdns-ui/commit/c1b743a11e1edb9d966c55b74b03088966c7fa74))
* update comment for ACME key migration logic ([a32a664](https://github.com/cyr-ius/powerdns-ui/commit/a32a664219eb0f4b0d0a028217781fdc1971f7b2))
* update FastAPI and SQLModel versions in dependency files ([83f74c4](https://github.com/cyr-ius/powerdns-ui/commit/83f74c471113055ce4d60f8c2ef7247d82fdd278))
* Update release-please-config.json ([8d29d46](https://github.com/cyr-ius/powerdns-ui/commit/8d29d460aa4a63a5d626cc8e8fc5da8bd288321b))
* Update release-please-config.json ([d88d9ca](https://github.com/cyr-ius/powerdns-ui/commit/d88d9ca48ae19d895632d0e2d6fdd0545e521f74))
* update translation module to use TranslatePipe ([eae9b2f](https://github.com/cyr-ius/powerdns-ui/commit/eae9b2fc2f290c30e49532eef6184ff0715e9043))
* Use mcp server ([ea201e9](https://github.com/cyr-ius/powerdns-ui/commit/ea201e9dca8bc40c5e7cb2c2dd5a97da70e1f0cf))


### Documentation

* add MkDocs site with GitHub Pages deployment workflow ([e4b0aac](https://github.com/cyr-ius/powerdns-ui/commit/e4b0aacb0f5fb3819bf07f48030be70f3e6404a2))
* **agents:** drop mypy from the backend verification commands ([80bd44c](https://github.com/cyr-ius/powerdns-ui/commit/80bd44c482229c75b9e0078f516b5fc4d7ce6243))
* document API_KEYS_ENABLED, OIDC/SMTP env vars and PAT usage ([89b9fe3](https://github.com/cyr-ius/powerdns-ui/commit/89b9fe3fe917f692604f688c89554f28c376249b))
* document structured PDNS logging configuration ([3f5e8cf](https://github.com/cyr-ius/powerdns-ui/commit/3f5e8cf035e5db8ace6192ed215f79c8f3f4ea21))
* document SWAGGER_ENABLED environment variable ([e3e7100](https://github.com/cyr-ius/powerdns-ui/commit/e3e710055202811d0ee38ce663fb7a69279ea1c2))
* **examples:** add docker-compose example with PostgreSQL backend ([5196aa8](https://github.com/cyr-ius/powerdns-ui/commit/5196aa8d4ffde8283fef20e2bf4a1d1eda5a62bf))
* **readme:** document rate limiting and trusted proxies ([3c60b75](https://github.com/cyr-ius/powerdns-ui/commit/3c60b7544535b2096f47b426575f6af8dc812f2d))
* synthesize README, defer details to mkdocs site ([d8216df](https://github.com/cyr-ius/powerdns-ui/commit/d8216dfedc7450f8bee54d2b6b10598d3886b015))
* translate remaining French docstrings and comments to English ([9ec3640](https://github.com/cyr-ius/powerdns-ui/commit/9ec36408a76ec669b681493abe6e7de0657a72c7))

## [2.4.0](https://github.com/cyr-ius/powerdns-ui/compare/powerdns-ui-2.3.3...powerdns-ui-2.4.0) (2026-10-30)


### Features

* **acme:** allow reassigning the owner of an ACME key ([d33f132](https://github.com/cyr-ius/powerdns-ui/commit/d33f132d8ba95dfb56b4127b6cf2a40a1882137c))
* **acme:** allow renaming and editing zone ACME keys ([3375da4](https://github.com/cyr-ius/powerdns-ui/commit/3375da4ebe1a3d60b1e164377098c0f2160b7857))
* **acme:** track and display last-used date for ACME keys ([1131bd6](https://github.com/cyr-ius/powerdns-ui/commit/1131bd697bd366613533a84f2cdfe1d1bd549ff2))
* add ACME key management for zones and update UI ([0fdeffd](https://github.com/cyr-ius/powerdns-ui/commit/0fdeffd4dd75d0fedbd5af894b52cdbc11ce6d0c))
* add ACME Keys feature to README.md ([99b7237](https://github.com/cyr-ius/powerdns-ui/commit/99b7237a9c480d95140dde1c60b16a84bc044bf9))
* add icons to zone detail tabs for better UX ([765644e](https://github.com/cyr-ius/powerdns-ui/commit/765644e2cee3abfcde73c28c563f7a3f6bf2ddc5))
* add orphan key handling and translations ([b694e6c](https://github.com/cyr-ius/powerdns-ui/commit/b694e6ce7cd260ca3b1bfb579c53a00189598975))
* ajouter des fichiers de documentation et de politique de sécurité ([2987b3e](https://github.com/cyr-ius/powerdns-ui/commit/2987b3ef854027c50036421ea82204324ac5eb26))
* ajouter des variables d'environnement et nettoyer les dépendances Python ([e221553](https://github.com/cyr-ius/powerdns-ui/commit/e221553f3918bb89be6cef39f98e609f2062086c))
* ajouter la gestion des cookies HttpOnly pour les sessions et limiter les tentatives de connexion ([6aaf1ef](https://github.com/cyr-ius/powerdns-ui/commit/6aaf1eff9f1eb26b3baba2883ee83e8506063421))
* always auto-generate the admin password ([bf4fd35](https://github.com/cyr-ius/powerdns-ui/commit/bf4fd351f4948db1cacaec865b312f0175647aec))
* améliorer la gestion de l'authentification en utilisant des cookies HttpOnly et simplifier le processus de connexion ([3022196](https://github.com/cyr-ius/powerdns-ui/commit/30221963f1cd3978603044ed707681b8fb6d189d))
* améliorer la gestion des clés secrètes et des mots de passe administratifs ([2183690](https://github.com/cyr-ius/powerdns-ui/commit/21836905618776b2cc477dbf83fe5ec92f628acb))
* **audit:** add free-text search on PDNS logs tab ([76815ad](https://github.com/cyr-ius/powerdns-ui/commit/76815ad987620adb5be4c465e7c1e3cf4cd44dda))
* **audit:** parse structured PDNS logs ([5688f3d](https://github.com/cyr-ius/powerdns-ui/commit/5688f3df66a763d55c705aef0e222f4cc1d78747))
* **auth:** dedicated Personal Access Token model, split from ACME keys ([e93cc46](https://github.com/cyr-ius/powerdns-ui/commit/e93cc46e0d90dcb1a000c4b0cf4a782b17b00a3c))
* **auth:** OIDC RP-initiated logout and empty SECRET_KEY default ([fd1260e](https://github.com/cyr-ius/powerdns-ui/commit/fd1260efdf89a51d3aaa664cf382c2fcbbf01bfa))
* **backend:** manage the UI database schema with Alembic ([4aa5280](https://github.com/cyr-ius/powerdns-ui/commit/4aa52800e98b1b694c5ca3ad43a37022fa3174c8))
* **backend:** PAT bearer auth, env-pinned connectors, SMTP test ([16bd46e](https://github.com/cyr-ius/powerdns-ui/commit/16bd46ed7c304a3415b81cb9eeefbbeb9edc6363))
* detach PowerDNS zones when deleting an account to avoid invalid references ([87ca15c](https://github.com/cyr-ius/powerdns-ui/commit/87ca15c39afa6471e695f3ce596ed96020defbef))
* **devcontainer:** add docker CLI and pdns start/stop tasks ([4aae2ce](https://github.com/cyr-ius/powerdns-ui/commit/4aae2cea0062f4751b794e09dc52f5d401657899))
* **frontend:** dashboard, About page, collapsible sidebar ([d136940](https://github.com/cyr-ius/powerdns-ui/commit/d136940d8e491d64d8b660384c47f144eb9c22fc))
* **i18n:** add description for API keys in translations ([c731c75](https://github.com/cyr-ius/powerdns-ui/commit/c731c75ba70f01cbee5d837d76854d2965913c2e))
* mettre à jour la documentation pour la génération automatique des mots de passe et des clés secrètes ([21e20a1](https://github.com/cyr-ius/powerdns-ui/commit/21e20a1286584b7ab285600fe3faa332ffabaac1))
* **pdns:** bump PowerDNS Authoritative to 5.1.3 and adopt new API capabilities ([d728921](https://github.com/cyr-ius/powerdns-ui/commit/d728921199e9aa1534a8b291f80d341ca611aa66))
* permettre la génération automatique des mots de passe administratifs et des clés secrètes ([69b41fe](https://github.com/cyr-ius/powerdns-ui/commit/69b41fee7b78da5f83e7fc227990727ec8733864))
* prevent locking out the last OIDC admin in OIDC-only mode ([77dfec5](https://github.com/cyr-ius/powerdns-ui/commit/77dfec5af1fc88473b6b197b155cf7349abeb36e))
* **profile:** add ACME keys management to profile ([641dc0a](https://github.com/cyr-ius/powerdns-ui/commit/641dc0aefca881cc930507f13faa627e0138c052))
* **security:** add global rate-limiting middleware with trusted proxies ([c20e191](https://github.com/cyr-ius/powerdns-ui/commit/c20e1911cde9974ee8138f9568b151fe8cc91c47))
* **tokens:** add expiration to personal access tokens ([0c41140](https://github.com/cyr-ius/powerdns-ui/commit/0c4114047a490868149ca99c9b2749a0a20f6323))
* update Node.js version to 2.1.0 in container configuration files ([8ebb195](https://github.com/cyr-ius/powerdns-ui/commit/8ebb195fdea64c91d8436d7214aa84ab4b485f63))


### Bug Fixes

* **auth:** revoke session JWTs and harden the OIDC flow ([9c3a786](https://github.com/cyr-ius/powerdns-ui/commit/9c3a7865e58c9ecb9e053ebf5690fd6c27ce50d0))
* **backend:** avoid races between Uvicorn workers on first start ([5b82e5b](https://github.com/cyr-ius/powerdns-ui/commit/5b82e5b6f5139ad5ad1cb3427421d95ef4056ddf))
* **ci:** add .mcp.json file ([a5ae8c5](https://github.com/cyr-ius/powerdns-ui/commit/a5ae8c5c66052ed73dd6a77281aba0fff9c895ef))
* **ci:** update environment files ([a31e9c5](https://github.com/cyr-ius/powerdns-ui/commit/a31e9c54e8150d0dec8aafe97f14894625bffb5d))
* **ci:** update environment files ([405b52a](https://github.com/cyr-ius/powerdns-ui/commit/405b52add8141bd528fffe4f60855e271b770bea))
* **ci:** update environnment files ([0104165](https://github.com/cyr-ius/powerdns-ui/commit/0104165057d246c404eb6aff924619a8ac8721d0))
* **ci:** update environnment files ([59fc624](https://github.com/cyr-ius/powerdns-ui/commit/59fc624baecc4e11ce40b0a759bf98e3d15c6cd4))
* **ci:** update environnment files ([4f357d4](https://github.com/cyr-ius/powerdns-ui/commit/4f357d41967470104aaeeff5dba0f7af66950393))
* **ci:** update environnment files ([c0b296a](https://github.com/cyr-ius/powerdns-ui/commit/c0b296af04ac0bebd5465185d5b98f1b30700672))
* **ci:** update environnment files ([77c27ea](https://github.com/cyr-ius/powerdns-ui/commit/77c27ea7ccbf2e3836b7960794efcd67bef9ab43))
* **deps:** replace python-jose with PyJWT ([abd0785](https://github.com/cyr-ius/powerdns-ui/commit/abd07854187c1901ee41555d2e7e7e8b40349c5d))
* **dev:** Add pretask launcher to start pdns ([4405eb6](https://github.com/cyr-ius/powerdns-ui/commit/4405eb66ff679197eb2d55c5947263b035644421))
* **docker:** build from root pyproject and add a hardened test compose ([3f54f00](https://github.com/cyr-ius/powerdns-ui/commit/3f54f00e57a851f8865152fef444bafd54732770))
* **docker:** hand an existing data volume over to the non-root user ([fbab5dc](https://github.com/cyr-ius/powerdns-ui/commit/fbab5dc8efe1f257e75732d19213322b4be3b263))
* **docker:** run a single Uvicorn worker by default ([46ace85](https://github.com/cyr-ius/powerdns-ui/commit/46ace85e466cd67c00c6f7ed062c672475498165))
* **docker:** run as non-root and make the build reproducible ([fa28459](https://github.com/cyr-ius/powerdns-ui/commit/fa28459318021071821269a98f273bc277d44a40))
* **docs:** update agent ([aeb63b6](https://github.com/cyr-ius/powerdns-ui/commit/aeb63b63d32637c8979109153d91f57f32074d51))
* handle optional user fields in admin response ([0628a23](https://github.com/cyr-ius/powerdns-ui/commit/0628a238f8f9058c3e3990b03e301099405f9446))
* improve logging configuration format for better readability ([543a2f1](https://github.com/cyr-ius/powerdns-ui/commit/543a2f11abef75eb910976177a9182ddb1883019))
* make user_id nullable for ACME keys ([2475abd](https://github.com/cyr-ius/powerdns-ui/commit/2475abd37df76f9206d20b85c0c60f6a10e20e6a))
* prevent non-global-admins from changing the account field in zone updates ([a6c9e66](https://github.com/cyr-ius/powerdns-ui/commit/a6c9e667860bc255a20346dbebc431eaaeb5ea81))
* restore runtime dependencies dropped from pyproject ([9ee7879](https://github.com/cyr-ius/powerdns-ui/commit/9ee78798bece674b6c77af08a13c46680773b5a4))
* **security:** drop unsafe-inline scripts and send HSTS over HTTPS only ([0538a78](https://github.com/cyr-ius/powerdns-ui/commit/0538a7842781eae55eff0a7c9ccc748b6de7c958))
* update .gitignore to streamline ignored files and directories ([6e269bd](https://github.com/cyr-ius/powerdns-ui/commit/6e269bdd7851dbec33b3e461b8ea9348745f1119))
* update Angular version in README.md ([c1b743a](https://github.com/cyr-ius/powerdns-ui/commit/c1b743a11e1edb9d966c55b74b03088966c7fa74))
* update comment for ACME key migration logic ([a32a664](https://github.com/cyr-ius/powerdns-ui/commit/a32a664219eb0f4b0d0a028217781fdc1971f7b2))
* update FastAPI and SQLModel versions in dependency files ([83f74c4](https://github.com/cyr-ius/powerdns-ui/commit/83f74c471113055ce4d60f8c2ef7247d82fdd278))
* update translation module to use TranslatePipe ([eae9b2f](https://github.com/cyr-ius/powerdns-ui/commit/eae9b2fc2f290c30e49532eef6184ff0715e9043))
* Use mcp server ([ea201e9](https://github.com/cyr-ius/powerdns-ui/commit/ea201e9dca8bc40c5e7cb2c2dd5a97da70e1f0cf))


### Documentation

* add MkDocs site with GitHub Pages deployment workflow ([e4b0aac](https://github.com/cyr-ius/powerdns-ui/commit/e4b0aacb0f5fb3819bf07f48030be70f3e6404a2))
* **agents:** drop mypy from the backend verification commands ([80bd44c](https://github.com/cyr-ius/powerdns-ui/commit/80bd44c482229c75b9e0078f516b5fc4d7ce6243))
* document API_KEYS_ENABLED, OIDC/SMTP env vars and PAT usage ([89b9fe3](https://github.com/cyr-ius/powerdns-ui/commit/89b9fe3fe917f692604f688c89554f28c376249b))
* document structured PDNS logging configuration ([3f5e8cf](https://github.com/cyr-ius/powerdns-ui/commit/3f5e8cf035e5db8ace6192ed215f79c8f3f4ea21))
* document SWAGGER_ENABLED environment variable ([e3e7100](https://github.com/cyr-ius/powerdns-ui/commit/e3e710055202811d0ee38ce663fb7a69279ea1c2))
* **examples:** add docker-compose example with PostgreSQL backend ([5196aa8](https://github.com/cyr-ius/powerdns-ui/commit/5196aa8d4ffde8283fef20e2bf4a1d1eda5a62bf))
* **readme:** document rate limiting and trusted proxies ([3c60b75](https://github.com/cyr-ius/powerdns-ui/commit/3c60b7544535b2096f47b426575f6af8dc812f2d))
* synthesize README, defer details to mkdocs site ([d8216df](https://github.com/cyr-ius/powerdns-ui/commit/d8216dfedc7450f8bee54d2b6b10598d3886b015))
* translate remaining French docstrings and comments to English ([9ec3640](https://github.com/cyr-ius/powerdns-ui/commit/9ec36408a76ec669b681493abe6e7de0657a72c7))
