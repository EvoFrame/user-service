# user-service

> **Phase 3** · User profiles and preferences

`user-service` owns user-facing profile data (`display_name`, `bio`, avatar metadata, locale,
timezone, and notification preferences). Authentication credentials stay in `auth-service`.

---

## Tech stack

| Concern          | Technology                              |
| ---------------- | --------------------------------------- |
| Framework        | FastAPI (Python 3.13)                   |
| Database         | PostgreSQL (own instance)               |
| Cache / Events   | Redis                                   |
| ORM / models     | SQLModel (SQLAlchemy async)             |
| Token validation | PyJWT (RS256 public key only)           |
| Settings         | pydantic-settings                       |
| Logging          | structlog (structured JSON)             |
| Metrics          | prometheus-fastapi-instrumentator       |

---

## API endpoints

All endpoints are mounted under `/api/v1` internally and exposed as `/users/**`
by gateway rewrite rules.

| Method   | Path                        | Description                              |
| -------- | --------------------------- | ---------------------------------------- |
| `GET`    | `/api/v1/users/me`          | Get authenticated user profile           |
| `PATCH`  | `/api/v1/users/me`          | Update authenticated user profile        |
| `DELETE` | `/api/v1/users/me`          | Soft-delete authenticated user account   |
| `GET`    | `/api/v1/users/{user_id}`   | Get public profile projection            |
| `GET`    | `/api/v1/users/me/preferences` | Read preferences                      |
| `PATCH`  | `/api/v1/users/me/preferences` | Update preferences                    |
| `POST`   | `/api/v1/users/me/avatar`   | Delegate avatar upload to file-service   |

---

## Events consumed (Redis Streams)

| Stream                 | Action                                                                 |
| ---------------------- | ---------------------------------------------------------------------- |
| `auth.user.registered` | Creates a `UserProfile` + default `UserPreference` row (idempotent)    |

## Events published (Redis Streams)

| Stream                  | Trigger                                              |
| ----------------------- | ---------------------------------------------------- |
| `user.profile.updated`  | Profile fields or preferences changed                |
| `user.account.deleted`  | User account soft-deleted                            |

All events carry `source_service` and `timestamp` envelope fields.

---

## Local development

### First-time setup

```bash
mise run setup      # copies *.env.*example files + generates a local RSA public key
mise run dev        # starts db + redis, runs migrations, starts dev server
```

> **Note:** The generated key pair under `.docker/keys/` is for local development only.
> In production, obtain `RS256_PUBLIC_KEY` from `auth-service`.

---

## Related docs

- [EvoFrame roadmap](https://github.com/EvoFrame/roadmap/blob/main/README.md)
- [service-blueprint.md](https://github.com/EvoFrame/roadmap/blob/main/architecture/service-blueprint.md) — internal structure every service follows
