# Windows setup with PostgreSQL installed directly

This route uses Python, Node.js and PostgreSQL on your Windows computer.
Docker Desktop is not required. The cloud development environment is separate
from your computer; these installation steps must be completed on Windows.

## 1. Install the prerequisites

- [Python 3.12](https://www.python.org/downloads/windows/). Enable the option to
  add Python to PATH.
- [Node.js LTS](https://nodejs.org/). Use Node.js 22.12 or later.
- [PostgreSQL for Windows](https://www.postgresql.org/download/windows/).
  PostgreSQL 17 matches the version used in development. Include PostgreSQL
  Server, pgAdmin 4 and command-line tools.

During PostgreSQL installation:

1. Keep the proposed installation and data directories unless you need another location.
2. Choose a password for the administrator account named `postgres`.
   Keep it privately; do not send passwords in chat.
3. Use the default port `5432`, unless another PostgreSQL instance already uses it.
   Remember the port you select.
4. Complete installation. PostgreSQL runs as a Windows service.

Python and Node.js installation are one-time steps. Restart any terminal that
was already open so it can find the newly installed tools.

## 2. Create an application login and database in pgAdmin

1. Open **pgAdmin 4**.
2. Expand **Servers → PostgreSQL 17** and connect using the administrator
   password you chose during installation.
3. Right-click **Login/Group Roles → Create → Login/Group Role**.
4. Under **General**, enter `dataflow` as the name.
5. Under **Definition**, choose a separate password for this application login.
6. Under **Privileges**, set **Can login?** to **Yes**. Leave Superuser,
   Create roles and Create databases disabled.
7. Save the role.
8. Right-click **Databases → Create → Database**.
9. Enter `dataflow` as the database name and select `dataflow` as the owner.
10. Save the database.

The administrator login installs/manages PostgreSQL; the app uses the dedicated
`dataflow` login. The app creates its own tables on first launch.

## 3. Get the updated project

If you already cloned the project, stop the app, open Git Bash in the repository,
and run:

```sh
git switch feat/dataflow-postgresql
git pull --ff-only
```

Keep your existing changes if Git reports a conflict; do not reset or discard them.
For a first clone:

```sh
git clone --branch feat/dataflow-postgresql https://github.com/nrldalia/data-science-analytics-portfolio.git
```

Open the repository's `data-flow-hub` folder.

## 4. Run setup

Double-click **Setup_Windows.bat**.

Setup installs Python dependencies and prompts for database details if no existing
configuration is present:

| Prompt | Enter |
|---|---|
| Host | `127.0.0.1` |
| Port | `5432`, or your installation port |
| Database | `dataflow` |
| User | `dataflow` |
| Password | The application login password from step 2 |

Password input is hidden. Setup checks the connection before saving a private
`.env` file and building the frontend. Existing configuration is preserved.
Keep `.env` private; it is excluded from Git.

## 5. Optional: preserve existing SQLite history

Before the first launch or demo load, open Command Prompt in `data-flow-hub`:

```bat
.venv\Scripts\python.exe script\migrate_sqlite.py script\dataflow.db
```

This requires an empty PostgreSQL destination and never overwrites existing
application records. The original SQLite file remains unchanged.

## 6. Load the four demo retailers

In Command Prompt in `data-flow-hub`:

```bat
.venv\Scripts\python.exe script\load_store_demo.py --apply
```

This adds Aurora, Bayu, Cempaka and Damai with 300 synthetic stores each. A complete
unchanged rerun does not duplicate data. Conflicting existing demo records are
reported rather than replaced.

## 7. Start the app

1. Double-click **Start_DataFlow.bat**.
2. Open `http://localhost:5000` in your Windows browser.
3. Open **Client**, edit a demo retailer, and use **Store management**.
4. Keep the application terminal open. Stop the app with **Ctrl+C**.

The launcher checks PostgreSQL but does not start, stop or reconfigure Windows
services. PostgreSQL normally starts automatically with Windows.

## Updating the app

1. Stop the app.
2. Run `git pull --ff-only` on the feature branch.
3. Run **Setup_Windows.bat** to refresh dependencies and rebuild.
4. Run **Start_DataFlow.bat**.

You do not need to recreate the login/database or reload an unchanged demo.
Git updates do not replace your ignored `.env` or database records.

## Troubleshooting

- **Connection refused:** open Windows **Services**, find the PostgreSQL service,
  and check that it is running. Confirm your host and port.
- **Login/database not found or incorrect password:** verify the application role
  and database in pgAdmin. Do not use the administrator password for the
  `dataflow` role unless you deliberately assigned the same password.
- **Existing configuration points to Docker:** the old route usually uses port
  `55432`; a native installation usually uses `5432`. Stop the app and preserve
  the old `.env` by renaming it to `.env.docker.backup`, then rerun setup for the
  native server. An exported `DATABASE_URL` in your terminal also takes precedence;
  keep it aligned with the intended database.
- **Already have Docker database records:** changing connection details does not
  move the records. Back up that database and restore into the native server
  before launching the app there. Keep the old database until the restore is verified.
- **Missing Python/Node:** reopen the terminal after installation and check
  `py --version` and `node --version`.

## Native database backup

With Command Prompt in `data-flow-hub`, use the PostgreSQL installation's tools
(adjust the version/path/port if needed):

```bat
mkdir backups
"C:\Program Files\PostgreSQL\17\bin\pg_dump.exe" -h 127.0.0.1 -p 5432 -U dataflow -d dataflow -Fc -f backups\dataflow.dump
```

The tool prompts for the application password. Keep backups private; the
`backups/` directory is excluded from Git. Restore into an empty destination
database using `pg_restore`, then verify records before switching the app.
