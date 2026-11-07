---
title: "Reach a session's port from your computer"
kind: guide
for: [developer]
summary: "Point psql, DBeaver or pgAdmin on your own Windows, Mac or Linux computer at a database a session runs, signed in as you, with nothing opened on the machine."
sources:
  - packages/fleet-service/src/fleet_service/api/portforward.py
  - packages/fleet-service/src/fleet_service/laptop/fleet_port_forward.py
  - packages/fleet-service/src/fleet_service/api/static/cockpit-portsfiles.js
minutes: 6
---

:::lede
When you are done, a database a session started, such as the Postgres from `make up`, answers on your own computer's `localhost`, and `psql -h localhost -p 5432`, DBeaver or pgAdmin reaches it.
:::

Fleet's machines take no connections from the internet. `fleet-port-forward` runs on your computer, listens on `localhost`, and carries each connection over HTTPS through Fleet to the port on the session's machine, using the link that machine already keeps to Fleet. Nothing is opened on the machine, and you need no VPN and no SSH access. It works the same on Windows, macOS and Linux.

:::callout{kind="careful"}
Only a port served on the machine itself can be reached. A database that lives only inside a container network is not on the machine. Publish it first, for example in compose: `ports: ["127.0.0.1:5432:5432"]`. The session's **Ports** tab lists exactly what can be reached.
:::

## What you need

- **Python 3.8 or newer.** macOS and most Linux computers already have it: `python3 --version` says which. On Windows, install it from [python.org](https://www.python.org/downloads/windows/) and keep the **py launcher** option ticked, or run `winget install Python.Python.3.12`. Then `py --version` works in PowerShell or Command Prompt. Nothing else is installed: the command is one file that uses only what comes with Python.
- **Your own personal key** for this Fleet, saved on your computer. The next steps show how.
- **The id of a session you opened.** The **Ports** tab gives you the whole line, id included.

## Set it up once

:::steps
- [you] **Make and save your key.** In Fleet, open **Settings › Connect your tools**, make a key (or pick one you have), and run the save command shown under it. Paste the key when it waits (nothing is shown) and press :kbd[Enter]. On macOS and Linux run the first command in a terminal; on Windows run the one marked **On Windows, in PowerShell**. The key is saved in a file only you can read, one file for each Fleet you use, in the `.config\fleet` folder of your user folder (`~/.config/fleet` on macOS and Linux). If you already connected your AI tool to Fleet, the key is already saved.
- [you] **Download the command.** In the session's **Ports** tab, press **download fleet-port-forward**. The file already knows your Fleet's address.
- [you] **Put it somewhere handy.** On macOS and Linux, make it runnable and put it on your `PATH`: `chmod +x fleet-port-forward && mv fleet-port-forward ~/.local/bin/` (or any folder on your `PATH`). On Windows, leave it in a folder you will remember, for example `Downloads`, and open PowerShell in that folder.
:::

## Use it

:::steps
- [you] **Start it.** In the session's **Ports** tab, press **Copy** beside the port and run the line on your computer. On Windows, put `py` in front of it.

  macOS and Linux:

  ```
  fleet-port-forward 0b9c6f5e-1111-4222-8333-944445555666 5432
  ```

  Windows, in PowerShell, in the folder you saved it to:

  ```
  py .\fleet-port-forward 0b9c6f5e-1111-4222-8333-944445555666 5432
  ```

  It checks that you may reach the port, then prints a line starting `Forwarding localhost:5432`. Leave the window open while you work.
- [you] **Connect your client.** Point it at `localhost` and that port, with the database's own user and password (the session's project sets those, Fleet does not):
  - **psql:** `psql -h localhost -p 5432 -U postgres`
  - **DBeaver:** **Database › New Database Connection › PostgreSQL**, Host `localhost`, Port `5432`, then the database, user and password.
  - **pgAdmin:** **Object › Register › Server**, and on the **Connection** tab Host name `localhost`, Port `5432`, then the user and password.
  - **A web server** on the port: open `http://localhost:8765` in your browser.
- [you] **Stop it.** Press :kbd[Ctrl+C] in its window, or close the window. It says `stopped`. Your client's connections end with it.
- [fleet] **Every connection is recorded** against you, the session and the port.
:::

**The port is already taken on your computer?** That happens when you run a database of your own. Add `--local-port 15432` to the line and connect to port `15432` instead: `psql -h localhost -p 15432 -U postgres`.

## Who may reach a port

Only the person who opened the session, with a personal key of their own. A key made for an agent, or a colleague's key, is refused. A connection ends when your key is revoked or expires, when the session closes, and after a working day at most.

## When it says no

| It says | What it means, and what to do |
|---|---|
| `no key at …` | No key is saved for this Fleet on this computer. Save one, step 1 of the setup. |
| `… can be read by other users. Run: chmod 600 …` | On macOS or Linux the key file must be yours alone. Run that command. |
| `… nothing this box's user runs is listening on port 5432` | The port is not published on the machine. The server is not running, or it lives only inside a container network: publish its port on the machine, then press **Refresh** on the **Ports** tab. |
| `no workstation session …` | The session is not yours, it is closed, or the id is wrong. Copy the line from the **Ports** tab of a session you opened. |
| `this API key has expired` / `was revoked` | Make a new key under **Settings › Connect your tools** and save it again. |
| `port 5432 is already in use on this computer` | Something on your computer already uses that port. Add the `--local-port` the message names and connect to that port. |
| `this computer does not allow listening on port …` | Windows keeps some ports for itself. Add the `--local-port` the message names. |
| `the proxy may be blocking websocket connections` | Your company's network sends web traffic through a proxy that does not let this kind of connection through. Ask your IT team to allow websocket connections to your Fleet's address. |
| `the proxy at … asks for a sign-in` | Your company's proxy wants a user name and password. Put them in the proxy setting, as in **Behind a company proxy** below. |
| `the proxy at … turned down the user name and password` | The proxy did not accept them. Check them, or ask your IT team. |
| `the proxy at … does not allow connections to …` | The proxy blocks your Fleet's address. Ask your IT team to allow it, websocket connections included. |
| `could not reach the proxy at …` | The proxy setting names a proxy this computer cannot reach. Check the setting, or ask your IT team for the right one. |
| `could not reach …` | Your computer cannot reach Fleet at all. Check that you are online and can open your Fleet in a browser. If your company sends web traffic through a proxy, see **Behind a company proxy** below. |
| `does not trust …'s certificate` | On macOS with Python from python.org, run its **Install Certificates** command once. On Windows and Linux, your company may check web traffic with a certificate of its own: ask your IT team to add it to the computer's trusted certificates. |
| `'py' is not recognized` (Windows) | Python is not installed, or was installed without the py launcher. Install it as in **What you need**. |

## Behind a company proxy

If your company's network sends web traffic through a proxy, the command goes through it the same way `curl`, `pip` and `git` do. Nothing changes in how you run it.

- **On Windows**, it uses the proxy set in Windows' own settings (**Settings › Network & internet › Proxy**, **Manual proxy setup**), unless one of the variables below is set.
- **On any computer**, it uses the `HTTPS_PROXY` variable, or `ALL_PROXY` if that is not set. `NO_PROXY` lists addresses to reach directly, separated by commas.
- **If the proxy wants a user name and password**, put them in the variable: `http://user:password@proxy.example.com:8080`. Characters such as `@` or `:` in them are written `%40` and `%3A`. The command sends them only to the proxy and never prints them.

To set the variable for one PowerShell window on Windows:

```
$env:HTTPS_PROXY = "http://proxy.example.com:8080"
py .\fleet-port-forward 0b9c6f5e-1111-4222-8333-944445555666 5432
```

On macOS and Linux: `export HTTPS_PROXY=http://proxy.example.com:8080`.

When it uses a proxy, its first line ends with `through the proxy at proxy.example.com:8080`. It does not read an automatic proxy script (a "PAC" address in your settings): ask your IT team which proxy that script names, and set `HTTPS_PROXY` to it. Only ordinary web proxies (`http://…`) work, not SOCKS proxies.

## Where the key is read from

In this order: the `FLEET_API_KEY` environment variable; the file the `FLEET_HEADERS_FILE` environment variable names; this Fleet's own key file, `.config/fleet/<Fleet address>.headers.json` in your user folder; and last `.config/fleet/headers.json`, the single file older versions of the save command wrote, so a key saved before still works. `FLEET_URL` overrides the Fleet address written into the command. The key is never taken from the command line, where other programs could read it.

::cards{links="guides/sessions/review-a-sessions-work, guides/your-tools/connect-your-terminal, guides/your-tools/api-keys"}
