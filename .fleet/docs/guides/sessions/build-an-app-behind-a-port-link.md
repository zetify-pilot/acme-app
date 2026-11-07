# Build an app that runs behind a port link

When you are done, your app builds every address the browser sees (a sign-in redirect, an OIDC issuer, a link in an email) from its real public address, both behind **Open ↗** and in your own end-to-end tests.

**Open ↗** on a session's **Ports** tab opens a web port in a new tab, at an address of its own such as `https://p5173-0b9c6f5e-1111-4222-8333-944445555666.fleet.example.com`. We call that the *port link*. The browser talks to Fleet, and Fleet carries each request to the port on the session's machine. On the way it changes some headers, so that a dev server that only accepts `localhost` still works. Your app sees `localhost`, but the browser is somewhere else. An app that builds absolute addresses has to use the headers below, or the address in the session's environment, or it sends the browser to its own computer.

**Contract version: 1**

This page is the contract between Fleet and your app. Fleet's tests check every header named here, and the fixture at the end of this page is built from the same code as Fleet's proxy. When the contract changes, its version goes up and the change is listed under **Changes**.

## What your app receives

For a request the browser sends to `https://p5173-<session>.fleet.example.com/login`:

| Header | Value | What it means |
|---|---|---|
| `Host` | `localhost:5173` | Always the app's own port on `localhost`, so a dev server's host check (Vite's `allowedHosts`) passes. Do not build a public address from it. |
| `X-Forwarded-Host` | `p5173-<session>.fleet.example.com` | The host the browser used, with its port if it named one (`…fleet.example.com:8443`). |
| `X-Forwarded-Proto` | `https` | The scheme the browser used. |
| `X-Forwarded-Port` | `443` | The port the browser used: the one in `X-Forwarded-Host`, or the scheme's default when it names none. It always agrees with `X-Forwarded-Host`. |
| `Forwarded` | `host="p5173-<session>.fleet.example.com";proto=https` | The same address in the standard form (RFC 7239). The host is always quoted. There is no `for=`: Fleet does not tell the app who the client is. |
| `Origin` | `http://localhost:5173` | Sent only when the browser's `Origin` is the port link itself, rewritten to the app's own. A different origin is not passed on. |
| `Referer` | `http://localhost:5173/…` | Sent only when it is a page of the port link, rewritten the same way. |
| `Cookie` | your app's cookies | Fleet's own sign-in cookies are removed. |
| `Authorization` | the browser's own | Passed on unchanged, so a `Bearer` token your page sends to its own API arrives. |
| `Connection` | `close` | Every request is its own connection to the app. |

Every other header the browser sends is passed on. A `X-Forwarded-*`, `Forwarded` or `X-Real-IP` header from the client is **never** passed on: the forwarded headers above are written by Fleet alone. There is no `X-Forwarded-For` and no `X-Forwarded-Prefix`: the app is served at the root of its own address (`/`), never under a path, so it has no prefix to strip.

A websocket (Vite's hot reload, for example) is opened with the same `Host`, `Origin` and forwarded headers.

## What changes on the way back

- A redirect (`Location`) to the app's own `localhost`, `127.0.0.1` or `[::1]` on the same port is made relative, so `https://localhost:5173/after` becomes `/after` and stays on the port link.
- A `Set-Cookie`'s `Domain` is removed, so the cookie belongs to the port link only.
- `Strict-Transport-Security`, `Alt-Svc` and `Clear-Site-Data` are removed. They would reach past the app's own address.
- `X-Frame-Options: SAMEORIGIN`, `Cross-Origin-Resource-Policy: same-origin` and `Referrer-Policy: same-origin` are added when the app sets none.

## Your app's public address

Every session is given `FLEET_PORT_URL_TEMPLATE` in its environment: its ports' public address with `{port}` in place of the port number, and no slash at the end.

```
FLEET_PORT_URL_TEMPLATE=https://p{port}-0b9c6f5e-1111-4222-8333-944445555666.fleet.example.com
```

Fill in the port to get the address **Open ↗** opens:

- shell: `export PUBLIC_URL="${FLEET_PORT_URL_TEMPLATE/\{port\}/5173}"`
- Python: `os.environ["FLEET_PORT_URL_TEMPLATE"].format(port=5173)`
- Node: `process.env.FLEET_PORT_URL_TEMPLATE.replace("{port}", "5173")`

Set your app's public base URL from it, the way you would on any hosting platform. That is the most reliable choice: it does not depend on your framework trusting proxy headers. It is set only when your Fleet opens ports in the browser.

> **Tip:** **Signing in with OIDC.** Two addresses matter. The one the **browser** goes to (the redirect URI, and the issuer's authorize page when the sign-in server runs in the session too) must be a port link. The one your **server** calls (the token endpoint, the discovery document) should be `http://localhost:<port>` on the machine: a server-to-server call to a port link would have to sign in to Fleet first. A sign-in server that names its issuer from `X-Forwarded-Host` (mock-oauth2-server does) gives the port link as issuer; tell your app to accept that issuer while it fetches keys from `localhost`.

If you would rather read the headers, tell your framework that the hop in front of it is a proxy it can trust: Express `app.set("trust proxy", "loopback")`, Werkzeug `ProxyFix(app, x_proto=1, x_host=1, x_port=1)`, Spring `server.forward-headers-strategy=framework`, ASP.NET Core `UseForwardedHeaders` with `XForwardedHost` and `XForwardedProto`.

## Test sign-in in your own CI

`fleet-port-proxy-fixture` behaves like the port link on your own machine: HTTPS, the `Host` rewrite, the same headers and the same changes on the way back. Fleet's proxy imports its header code, so the two cannot drift apart. It leaves out Fleet's own sign-in, which stands in front of your app rather than between your app and its headers.

1. [you] **Get the file.** While signed in to Fleet, open `/api/workstation/port-proxy/fixture` on your Fleet's address, or run `fleet-port-proxy-fixture --version` to see the contract an existing copy implements. It is one Python file that needs Python 3.8 or newer and nothing else. Commit it into your repository, for example as `tests/fleet-port-proxy-fixture`, so your CI does not need to reach Fleet.
2. [you] **Start it in front of your app.** For an app on port 5173 and its sign-in server on 8080:

   ```
   python3 tests/fleet-port-proxy-fixture --target 5173 --target 8080
   ```

   It prints each port's address, such as `https://p5173-00000000-0000-4000-8000-000000000000.localhost:8443`, and the `FLEET_PORT_URL_TEMPLATE` a session would be given. Give your app that value, as Fleet would.
3. [you] **Point your browser tests at it.** Browsers find every `*.localhost` address on the same machine without any setup. The certificate is one it makes for itself with `openssl`, so tell the test runner to accept it (Fleet's own value (set your own): `ignore_https_errors=True`), or pass your own with `--cert` and `--key`. For curl, add `--resolve` with the printed host and `127.0.0.1`.

`--listen` changes the port it answers on (8443), `--session` the session id in the address, and `--parent` the host the addresses sit under (`localhost`). A port not named with `--target` is refused.

## Changes

| Version | Change |
|---|---|
| 1 | First published contract. Adds `X-Forwarded-Port` and `Forwarded` beside `X-Forwarded-Host` and `X-Forwarded-Proto`, and `FLEET_PORT_URL_TEMPLATE` in the session's environment. |

Next: Review what a session did (guides/sessions/review-a-sessions-work) · Reach a session's port from your computer (guides/sessions/reach-a-port)
