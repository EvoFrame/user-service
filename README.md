# user-service

> **Phase 3** · User profiles and preferences

`user-service` owns user-facing profile data (`display_name`, `bio`, avatar metadata, locale, timezone, notification preferences).  
Authentication credentials stay in `auth-service`.

## API surface

All endpoints are mounted under `/api/v1` internally and are expected to be exposed as `/users/**` by gateway rewrite rules.

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/v1/users/me` | Get authenticated user profile |
| `PATCH` | `/api/v1/users/me` | Update authenticated user profile |
| `DELETE` | `/api/v1/users/me` | Soft-delete authenticated user account |
| `GET` | `/api/v1/users/{id}` | Get public profile projection |
| `POST` | `/api/v1/users/me/avatar` | Delegate avatar upload flow to file-service |
| `GET` | `/api/v1/users/me/preferences` | Read preferences |
| `PATCH` | `/api/v1/users/me/preferences` | Update preferences |

## Event contracts

- Consumes: `auth.user.registered`
- Publishes: `user.profile.updated`, `user.account.deleted`

All events include the envelope fields:

- `source_service`
- `timestamp`

## Development

```bash
task init-env
devbox shell
task dev
```

## Common tasks

```bash
task test
task lint
task format
task migrate
task up
task down
```
