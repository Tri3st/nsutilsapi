# Identity Checker — Integration Guide

## API Endpoints

| Method | URL | Description |
|--------|-----|-------------|
| GET    | `/api/identity-checker/status/` | Record counts for all app/source combos |
| GET    | `/api/identity-checker/identities/?application=X&source=Y` | List identities |
| DELETE | `/api/identity-checker/identities/?application=X&source=Y` | Clear a source |
| POST   | `/api/identity-checker/upload/` | Upload CSV/XLSX (`multipart/form-data`) |
| GET    | `/api/identity-checker/cross-reference/?application=X` | Run cross-reference |
| GET    | `/api/identity-checker/upload-logs/?application=X` | Recent upload history |

---

## File format

The parser accepts flexible column names. Recognised aliases:

| Field | Accepted column names |
|-------|-----------------------|
| username | username, user, login, samaccountname, userid, account |
| email | email, mail, emailaddress, e-mail |
| display_name | display_name, displayname, name, full_name, cn |
| department | department, dept, division |

Any other columns are stored in `extra_data` (JSON).
