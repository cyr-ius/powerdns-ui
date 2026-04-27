---
name: development-standards
description: Normes de développement frontend et backend pour la mise en oeuvre de projet Angular/Fastapi
---

## When to Use This Skill

- Creation of new projects
- Code implementation
- Development of high-performance web services and microservices
- Creation of asynchronous applications
- Implementation of structured and tested API projects

# 🎓 Development Standards

## Framework Technologies

| Layer              | Technology      | Version     | Features                                    |
| ------------------ | --------------- | ----------- | ------------------------------------------- |
| **Frontend**       | Angular         | 21          | Signals, Signal Forms, Zoneless, Standalone |
| **Backend**        | FastAPI         | 0.136.0     | Async/Await, Pydantic v2                    |
| **UI Framework**   | Bootstrap       | 5.3.8       | Responsive, Accessible                      |
| **Icons**          | Bootstrap Icons | 1.13.1      | SVG Icons                                   |
| **Python Runtime** | Python          | 3.14        | Asynchronous                                |
| **Node Runtime**   | Node.js         | 18+         | ES2021                                      |
| **Deployment**     | Docker          | Multi-stage | Single Container SPA                        |

---

## 📘 ANGULAR 21 STANDARDS

Les SPA Angular 21 doivent suivre les normes suivantes pour garantir la maintenabilité, les performances et la scalabilité.

### 1. Principes Fondamentaux

**Angular 21 apporte des changements majeurs:**

- ✅ **Signaux** (réactivité granulaire)
- ✅ **Signal Forms** (formulaires réactifs simplifiés)
- ✅ **Zoneless** (sans NgZone, performances meilleures)
- ✅ **Standalone Components** (pas de modules)
- ❌ **Directives avec `*`** (dépréciées: `*ngIf`, `*ngFor`, `*ngSwitch`)
- ❌ **Two-way Binding avec `[(ngModel)]`** (déprécié, utiliser des signaux et événements)
- ❌ **Change Detection avec Zones** (déprécié, utiliser des signaux et computed)
- ❌ **Reactive Forms avec `FormGroup`** (déprécié, utiliser `form` et `FormField` de Signal Forms)
- ✅ **Control Flow** (syntaxe nouvelle: `@if`, `@for`, `@switch`)
- ✅ **HTML Format recommandé avec fichier séparé:**
- ✅ **CSS Format recommandé avec fichier séparé:**

### 2. Types de Composants

Tous les composants **doivent avoir des fichiers séparés** pour template et style:

```
app/features/user/
├── user-list/
│   ├── user-list.component.ts      ← Code TypeScript
│   ├── user-list.component.html    ← Template HTML
│   └── user-list.component.css     ← Styles CSS
```

### 3. Architecture des Dossiers

```
frontend/src/app/
├── core/                              # Singleton services, guards, interceptors
│   ├── services/
│   │   ├── auth.service.ts           # Authentication
│   │   ├── api.service.ts            # HTTP API calls
│   │   ├── theme.service.ts          # Theme management
│   │   └── ...
│   ├── guards/
│   │   └── auth.guard.ts             # Route protection
│   ├── interceptors/
│   │   └── auth.interceptor.ts       # Add JWT tokens
│   ├── models/
│   │   ├── auth.models.ts
│   │   ├── user.models.ts
│   │   └── ...
│   └── constants/
│       └── app.constants.ts
│
├── features/                          # Feature modules (lazy loaded)
│   ├── auth/
│   │   ├── login/
│   │   │   ├── login.component.ts
│   │   │   ├── login.component.html
│   │   │   └── login.component.css
│   │   └── ...
│   ├── dashboard/
│   │   ├── dashboard.component.ts
│   │   ├── dashboard.component.html
│   │   └── dashboard.component.css
│   └── ...
│
├── shared/                            # Reusable components, pipes, directives
│   ├── components/
│   │   ├── header/
│   │   ├── layout/
│   │   └── ...
│   ├── pipes/
│   │   └── custom.pipe.ts
│   └── directives/
│       └── custom.directive.ts
│
├── app.config.ts                     # Angular configuration
├── app.routes.ts                     # Route definitions
├── app.component.ts                  # Root component
└── main.ts                           # Application entry point
```

---

## 🐍 FASTAPI STANDARDS

Les projets FastAPI doivent suivre les normes suivantes pour garantir la maintenabilité, les performances et la scalabilité.

### 1. Principes Fondamentaux

- ✅ **Async/Await** (toutes les fonctions de route sont asynchrones)
- ✅ **Pydantic v2** (validation des données avec les nouveaux modèles)
- ✅ **Gestion d'erreurs avec HTTPException**
- ✅ **Logging structuré** (pas de print())
- ✅ **Type hints complets** (sur toutes les fonctions)
- ✅ **Docstrings complètes** (format Google style)
- ✅ **Configuration via variables d'environnement** (pas de secrets hardcodés)
- ✅ **Structure de projet modulaire** (services, modèles, routes séparés)

---

## 📋 CONVENTIONS COMMUNES

### 1. Noms de Fichiers

```
# Angular
my-component.component.ts       # Composant
my-component.component.html     # Template
my-component.component.css      # Styles
my.service.ts                   # Service
my.pipe.ts                      # Pipe
my.directive.ts                 # Directive
my.guard.ts                     # Guard

# FastAPI
user_service.py                 # Service
user_models.py                  # Modèles Pydantic
user_routes.py                  # Routes
config.py                       # Configuration
exceptions.py                   # Exceptions personnalisées
```

### 2. Conventions de Nommage

```typescript
// Angular/TypeScript
const MAX_RETRY = 3;                    // Constantes
let currentUser: User | null;           // Variables
function getUserById(id: number): User; // Fonctions
class UserService { }                   // Classes
interface IUser { }                     // Interfaces
type AuthResponse = { ... };            // Types
enum Status { ACTIVE, INACTIVE }        // Énumérations

// HTML templates
data-testid="user-form"                 // Tests
aria-label="Close modal"                // Accessibilité
(click)="handleClick()"                 // Événements
(keydown.enter)="submitForm()"          // Événements clavier
[attr.aria-expanded]="isOpen()"         // Attributs dynamiques
```

```python
# Python/FastAPI
MAX_RETRIES = 3                         # Constantes
current_user = None                     # Variables
def get_user_by_id(user_id: int):      # Fonctions
class UserService:                      # Classes
async def fetch_data():                 # Fonctions asynchrones
```

### 3. Gestion d'Erreurs

```typescript
// Angular - Error handling
try {
  const user = await this.userService.getUser(id).toPromise();
  this.selectedUser.set(user);
} catch (error) {
  logger.error("Failed to load user", error);
  this.errorMessage.set("Failed to load user. Please try again.");
}
```

```python
# FastAPI - Error handling
try:
    user = await self.db.get_user(user_id)
    if not user:
        raise NotFoundException("User", user_id)
    return user
except Exception as exc:
    logger.error(f"Error fetching user {user_id}: {exc}")
    raise HTTPException(
        status_code=500,
        detail="Internal server error"
    )
```

---

## 🔧 PRE-COMMIT CONFIGURATION & LINTING

Tous les changements doivent respecter la configuration définie dans `.pre-commit-config.yaml`.

### Hooks Disponibles

Le fichier `.pre-commit-config.yaml` configure les outils suivants:

#### 1. **Ruff** - Python Linting & Formatting

Ruff remplace Black, Flake8, isort et autres (outils Python).

```bash
# Run all ruff checks/formatting
ruff check backend/ --fix        # Auto-fix linting issues
ruff format backend/             # Format code

# Configuration (pyproject.toml)
[tool.ruff]
line-length = 100
target-version = "py314"

[tool.ruff.lint]
select = ["E", "F", "W", "I", "B", "C4", "UP"]
ignore = ["E501"]  # Line too long is handled by formatter
```

**Utilisé pour:**

- Vérification PEP 8
- Formatage du code Python
- Tri des imports
- Réduction de la complexité

#### 2. **Python Typing Update** - Type Hints Modernization

Met à jour la syntaxe des type hints Python aux standards modernes.

```bash
# Manual run (not automatic)
pre-commit run --hook-stage manual python-typing-update --all-files

# Configuration
# Python 3.14+ syntax: `str | None` au lieu de `Optional[str]`
# `list[int]` au lieu de `List[int]`
```

**Exemples de mise à jour:**

```python
# Before (old syntax)
from typing import Optional, List
def get_users() -> Optional[List[str]]:
    pass

# After (Python 3.14 syntax)
def get_users() -> list[str] | None:
    pass
```

#### 3. **Prettier** - Frontend Formatting

Formate HTML, JSON, YAML, et Markdown.

```bash
# Format frontend files
npm run prettier
cd frontend && npx prettier --write "src/**/*.{ts,html,scss}"

# Configuration (.prettierrc)
{
  "printWidth": 100,
  "tabWidth": 2,
  "useTabs": false,
  "semi": true,
  "singleQuote": true,
  "trailingComma": "es5",
  "arrowParens": "avoid"
}
```

#### 4. **Codespell** - Spell Checking

Vérifie l'orthographe et détecte les erreurs courantes.

```bash
# Check spelling in all files
codespell

# Auto-fix spelling errors
codespell --write-changes

# Configuration (.codespellrc)
skip = ./.git,*.json,*.csv,.devcontainer,.vscode
ignore-words-list = te
```

#### 5. **Standard Pre-commit Hooks**

Hooks fournis par pre-commit pour validations basiques:

```bash
# Standard validations applied automatically
check-json           # Validate JSON files
check-yaml          # Validate YAML files (with --unsafe)
check-toml          # Validate TOML files
check-added-large-files  # Prevent committing large files
end-of-file-fixer   # Ensure files end with newline
trailing-whitespace # Remove trailing spaces
mixed-line-ending   # Normalize line endings
```

Assurez-vous que les fichiers se terminent par un saut de ligne.
Supprimez les espaces de fin de ligne.
Normalisez les fins de ligne.

#### 6. **yamllint** - YAML Validation

Valide la structure YAML selon les standards.

```bash
# Check YAML files
yamllint .

# Configuration (.yamllint)
extends: default
rules:
  line-length: disable
  indentation:
    spaces: 2
```

### Exécution Manuelle des Hooks

```bash
# Run all hooks on all files
prek run --all-files

# Run specific hook
prek run ruff-format --all-files
prek run prettier --all-files

# Install pre-commit hook (auto-run on git commit)
prek install

# Update hooks to latest versions
prek autoupdate

# Disable hooks for single commit (not recommended!)
git commit --no-verify
```

### Workflow Recommandé

**Avant chaque commit:**

```bash
# 1. Format all code
cd backend && ruff format . && cd ..
cd frontend && npm run prettier && cd ..

# 2. Run all pre-commit hooks
prek run --all-files

# 3. Fix any remaining issues manually
# (ruff might have unfixable errors)

# 4. Verify no errors remain
prek run --all-files  # Should pass without changes

# 5. Run tests
cd backend && python -m pytest && cd ..
cd frontend && npm run test && cd ..

# 6. Commit changes
git add .
git commit -m "feat(scope): description"
```

### Configuration IDE pour Auto-Format

**VS Code - `.vscode/settings.json`:**

```json
{
  "[python]": {
    "editor.formatOnSave": true,
    "editor.defaultFormatter": "charliermarsh.ruff",
    "editor.codeActionsOnSave": {
      "source.fixAll": "explicit",
      "source.organizeImports": "explicit"
    }
  },
  "[typescript]": {
    "editor.formatOnSave": true,
    "editor.defaultFormatter": "esbenp.prettier-vscode"
  },
  "[html]": {
    "editor.formatOnSave": true,
    "editor.defaultFormatter": "esbenp.prettier-vscode"
  },
  "[json]": {
    "editor.formatOnSave": true,
    "editor.defaultFormatter": "esbenp.prettier-vscode"
  },
  "[yaml]": {
    "editor.formatOnSave": true,
    "editor.defaultFormatter": "esbenp.prettier-vscode"
  }
}
```

### Erreurs Courantes et Fixes

**Erreur: "Line too long"**

```python
# ❌ WRONG - Line > 100 chars
user_data = UserService.get_all_active_users_with_pending_transactions_and_notifications()

# ✅ CORRECT - Break into multiple lines
user_data = UserService.get_all_active_users_with_pending_transactions_and_notifications()
```

**Erreur: "Import sorting"**

```python
# ❌ WRONG - Wrong import order
import os
from typing import List
import sys
from app.models import User

# ✅ CORRECT - Group: stdlib, third-party, local
import os
import sys
from typing import List

from app.models import User
```

**Erreur: "Type hints missing"**

```python
# ❌ WRONG - No type hints
def process_data(data):
    return data.strip()

# ✅ CORRECT - Complete type hints
def process_data(data: str) -> str:
    """Process user input.

    Args:
        data: Input string to process.

    Returns:
        str: Processed string.
    """
    return data.strip()
```

---

## ⚠️ ERREURS COURANTES À ÉVITER

### Frontend - Angular

**❌ Ne pas utiliiser zone.js:**

```typescript// WRONG - Using NgZone
export const appConfig: ApplicationConfig = {
  providers: [
    provideZoneChangeDetection({ eventCoalescing: true }),
  ]
};
```

**✅ Utiliser Angular en mode zoneless:**

```typescript// CORRECT - Zoneless with signals
export const appConfig: ApplicationConfig = {
  providers: [
    provideZonelessChangeDetection()
  ]
};
```

**❌ Utiliser les anciennes directives:**

```typescript
// WRONG - Deprecated directives
<div *ngIf="isVisible">Content</div>
<div *ngFor="let item of items">{{ item }}</div>
```

**✅ Utiliser le nouveau control flow:**

```typescript
// CORRECT - Use control flow
@if (isVisible) {
  <div>Content</div>
}

@for (item of items; track item.id) {
  <div>{{ item }}</div>
}
```

**❌ Ne pas utiliser les signaux:**

```typescript
// WRONG - Old way with property
export class MyComponent {
  isLoading = false; // Not reactive
  items: Item[] = []; // Not tracked
}
```

**✅ Utiliser les signaux:**

```typescript
// CORRECT - Reactive with signals
export class MyComponent {
  isLoading = signal(false); // Reactive state
  items = signal<Item[]>([]); // Tracked changes
  itemCount = computed(
    () =>
      // Derived state
      this.items().length,
  );
}
```

**❌ Inliner trop de code HTML/CSS:**

```typescript
// WRONG - 200 lignes de HTML inlinées
@Component({
  selector: 'app-complex',
  template: `<div>... 150 lignes ...</div>`,
  styles: [`... 100 lignes CSS ...`]
})
```

**✅ Utiliser des fichiers séparés:**

```typescript
// CORRECT - External files
@Component({
  selector: 'app-complex',
  templateUrl: './complex.component.html',
  styleUrls: ['./complex.component.scss']
})
```

**❌ Utiliser `any` type:**

```typescript
// WRONG - Lose type safety
function processData(data: any): any {
  return data.transform();
}
```

**✅ Utiliser des types spécifiques:**

```typescript
// CORRECT - Strong typing
interface DataModel {
  id: number;
  name: string;
}

function processData(data: DataModel): string {
  return data.name.toUpperCase();
}
```

**❌ Oublier de se désabonner (RxJS):**

```typescript
// WRONG - Memory leak
export class MyComponent implements OnInit {
  ngOnInit() {
    this.service.data$.subscribe((data) => {
      this.items = data;
    });
  }
}
```

**✅ Utiliser takeUntilDestroyed ou signaux:**

```typescript
// CORRECT - Proper cleanup
import { takeUntilDestroyed } from "@angular/core/rxjs-interop";

export class MyComponent {
  private destroyRef = inject(DestroyRef);

  constructor(private service: Service) {
    this.service.data$.pipe(takeUntilDestroyed(this.destroyRef)).subscribe((data) => {
      this.items = data;
    });
  }
}
```

### Backend - FastAPI

**❌ Typing manquant:**

```python# WRONG - No type hints
def get_user(user_id):
    return db.get_user(user_id)
```

**✅ Type hints complets:**

````python# CORRECT - Full type hints
async def get_user(
    user_id: int,
    db: AsyncSession = Depends(get_db)
) -> UserResponse:
    """Get user by ID.

**❌ Typing déprécié:**
```python# WRONG - Old typing syntax
from typing import List, Optional
````

**✅ Typing moderne:**

```python# CORRECT - Modern typing syntax
def get_users() -> list[UserResponse] | None:
    ...
```

**❌ Backtrace dans le retour client**

```python
# WRONG - Information leak
try:
  function()
except Exception as exc:
  return f"Error {exc}"
```

**❌ Endpoints non-asynchrones:**

```python
# WRONG - Block thread
@app.get("/users")
def get_users():  # Not async!
    users = db.query(User).all()
    return users
```

**✅ Endpoints asynchrones:**

```python
# CORRECT - Async all the way
@app.get("/users")
async def get_users(
    db: AsyncSession = Depends(get_db)
) -> List[UserResponse]:
    """Get all users."""
    users = await db.get_all_users()
    return users
```

**❌ Utiliser print() pour logs:**

```python
# WRONG - No log levels, hard to grep
@app.get("/data")
async def get_data():
    print("User requested data")  # Bad!
    return {"status": "ok"}
```

**✅ Utiliser logging:**

```python
# CORRECT - Proper logging
import logging

logger = logging.getLogger(__name__)

@app.get("/data")
async def get_data() -> dict:
    """Get data."""
    logger.info("User requested data")
    return {"status": "ok"}
```

**❌ Pas de type hints:**

```python
# WRONG - No type safety
def create_user(user_data):
    return UserService.create(user_data)
```

**✅ Type hints complets:**

```python
# CORRECT - Full type hints
async def create_user(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db)
) -> UserResponse:
    """Create new user.

    Args:
        user_data: User creation request.
        db: Database session.

    Returns:
        UserResponse: Created user.

    Raises:
        HTTPException: If user already exists.
    """
    user = await db.create_user(user_data)
    return user
```

**❌ Gestion d'erreurs manquante:**

```python
# WRONG - No error handling
@app.get("/items/{item_id}")
async def get_item(item_id: int):
    item = await db.get_item(item_id)
    return item  # Crashes if not found!
```

**✅ Gestion d'erreurs appropriée:**

```python
# CORRECT - Proper error handling
@app.get("/items/{item_id}", response_model=ItemResponse)
async def get_item(
    item_id: int,
    db: AsyncSession = Depends(get_db)
) -> ItemResponse:
    """Get item by ID.

    Args:
        item_id: Item unique ID.
        db: Database session.

    Returns:
        ItemResponse: Item data.

    Raises:
        HTTPException: If item not found.
    """
    item = await db.get_item(item_id)
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Item {item_id} not found"
        )
    return item
```

**❌ Hardcoder la configuration:**

```python
# WRONG - Secrets in code!
DATABASE_URL = "postgresql://user:password@localhost/db"
SECRET_KEY = "my-secret-key"
ADMIN_PASSWORD = "fixed-password"
```

**✅ Utiliser les variables d'environnement:**

```python
# CORRECT - Load from environment
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str  # From env
    secret_key: str    # From env
    admin_password: str  # From env

    class Config:
        env_file = ".env"

settings = Settings()
```

**❌ Pas de validation Pydantic:**

```python
# WRONG - No validation
@app.post("/users")
async def create_user(data: dict):
    # Anything goes!
    user = await db.create(data)
    return user
```

**✅ Validation avec Pydantic:**

```python
# CORRECT - Strong validation
from pydantic import BaseModel, EmailStr, Field

class UserCreate(BaseModel):
    username: str = Field(
        ...,
        min_length=3,
        max_length=50,
        description="Username 3-50 chars"
    )
    email: EmailStr  # Validates email format
    password: str = Field(
        ...,
        min_length=8,
        description="Password min 8 chars"
    )

@app.post("/users", response_model=UserResponse)
async def create_user(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db)
) -> UserResponse:
    """Create user with validation."""
    # Only valid data reaches here
    user = await db.create_user(user_data)
    return user
```

---

## 🔗 Ressources Complètes

### Frontend - Angular 21

- [Angular 21 Official Docs](https://angular.dev/overview) - Documentation complète
- [Angular Signals Guide](https://angular.dev/guide/signals) - API Signaux
- [Angular Forms](https://angular.dev/guide/forms) - Forms réactives
- [Angular HttpClient](https://angular.dev/guide/http) - HTTP API
- [Angular Routing](https://angular.dev/guide/routing) - Routage
- [Control Flow Syntax](https://angular.dev/guide/control-flow) - @if, @for, @switch
- [Dependency Injection](https://angular.dev/guide/di) - Injection de dépendances
- [TypeScript Handbook](https://www.typescriptlang.org/docs/) - Langage TypeScript

### UI & Styling

- [Bootstrap 5.3 Documentation](https://getbootstrap.com/docs/5.3/) - Framework CSS
- [Bootstrap Icons Library](https://icons.getbootstrap.com/) - Icônes SVG
- [SCSS Documentation](https://sass-lang.com/documentation) - CSS préprocesseur
- [CSS Grid & Flexbox](https://developer.mozilla.org/en-US/docs/Web/CSS) - Mise en page

### Backend - FastAPI

- [FastAPI Official Documentation](https://fastapi.tiangolo.com/) - Documentation complète
- [Pydantic v2 Docs](https://docs.pydantic.dev/latest/) - Validation des données
- [SQLAlchemy Async](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html) - ORM asynchrone
- [Uvicorn Documentation](https://www.uvicorn.org/) - Serveur ASGI
- [Python Type Hints](https://docs.python.org/3/library/typing.html) - Système de types
- [Python Async/Await](https://docs.python.org/3/library/asyncio.html) - Programmation asynchrone

### DevOps & Qualité

- [Pre-commit Framework](https://pre-commit.com/) - Git hooks
- [Ruff Documentation](https://docs.astral.sh/ruff/) - Linter Python rapide
- [Prettier Documentation](https://prettier.io/) - Code formatter
- [Docker Documentation](https://docs.docker.com/) - Containerization
- [Docker Compose](https://docs.docker.com/compose/) - Orchestration multi-conteneurs

### Development Tools

- [VS Code Extensions](https://marketplace.visualstudio.com/) - IDE extensions
- [Git Documentation](https://git-scm.com/doc) - Version control
- [npm Documentation](https://docs.npmjs.com/) - Package manager Node.js

---

## 📞 Support & Contribution

Pour toute question concernant les normes de développement:

1. Consulter ce fichier SKILL.md
2. Vérifier les exemples dans le code existant
3. Consulter la documentation officielle des frameworks
4. Demander aide à l'équipe senior

### Contributions aux normes

Pour proposer des modifications aux normes:

1. Créer une branche `docs/standards-update`
2. Mettre à jour le fichier SKILL.md
3. Créer une Pull Request avec justification
4. Attendre l'approbation de l'équipe

---

## 📝 Historique des versions

| Version | Date       | Changements                                  |
| ------- | ---------- | -------------------------------------------- |
| 1.2.0   | 2026-03-13 | Ajout section documentation                  |
| 1.1.0   | 2026-03-07 | Ajout section pre-commit & erreurs courantes |
| 1.0.0   | 2026-03-07 | Version initiale avec Angular 21 & FastAPI   |

---

**Dernière mise à jour:** 7 Mars 2026
**Statut:** Production Ready ✅
**Mainteneurs:** Development Team
