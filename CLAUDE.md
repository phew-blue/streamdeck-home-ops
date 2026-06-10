# streamdeck-home-ops

Stream Deck XL profile + plugin for the [home-ops](https://github.com/phew-blue/home-ops) Kubernetes cluster. Two halves:

1. **Python profile generator** (`generate.py` + `builder/`) — reads `config.yaml` and produces `profile/home-ops.streamDeckProfile` (a ZIP of page manifests, navigable as landing page → Talos nodes / K8s namespace grid → per-namespace status+action layers).
2. **TypeScript Stream Deck plugin** (`plugin/`, UUID `com.phew.blue.homeops`) — Node 20 plugin built with esbuild on the `@elgato/streamdeck` SDK (v2). Provides three live-updating actions: **App Status**, **Cluster Metric**, **Node Status**.

The deck runs on a Windows host; PowerShell helper scripts in `scripts/` are copied to `C:\StreamDeck-HomeOps` by `scripts/install.ps1` and invoked by buttons (logs, restart-pod, force-reconcile, update-profile, app launchers).

## Build & Test Commands

```bash
# Python deps (mise pins python 3.12)
pip install -r requirements.txt

# Regenerate the profile from config.yaml
python generate.py
# Also embed pages into the committed "Default Profile.streamDeckProfile"
python generate.py --embed

# Run tests
python -m pytest tests/ -v

# Build the plugin bundle (plugin/dist/plugin.js)
cd plugin && npm ci && npm run build
# Package into dist-plugin/com.phew.blue.homeops.sdPlugin
cd plugin && bash build-plugin.sh
# On the Windows host: build + install into Stream Deck
powershell -ExecutionPolicy Bypass -File plugin\build-plugin.ps1 -Install
```

## How It Talks to the Cluster

- **App Status / Node Status actions** shell out to `kubectl` and `flux` on the host (must be on PATH, kubeconfig at `~/.kube/config`): `kubectl get deployment/pods`, `kubectl top pod --sum`, `flux get hr`. Polls every 30s; commands time out after 10s and fail silently to `""` (see `plugin/src/kubectl.ts`).
- **Cluster Metric action** hits kromgo over HTTPS (`kromgo_url` in config, default `https://kromgo.phew.blue`), polls every 5 min.
- **Action-layer buttons** run the PowerShell scripts (`kubectl logs -f`, `kubectl rollout restart`, `flux reconcile helmrelease`).

## config.yaml Conventions

Single source of truth for the generated profile: `nodes`, `pinned` quick-launch apps, and `namespaces[].apps[]` with `name`, `deployment`, `url`. Per-namespace `color` themes the page.

- `deployment` must match the actual k8s Deployment name **and** is also used as the pod label selector `app.kubernetes.io/name=<deployment>` — verify both against the live cluster.
- Apps without a web UI use `https://phew.blue` as a placeholder URL.
- App icons are downloaded from `walkxcode/dashboard-icons`; if the icon filename differs from the app name, add a mapping to `ICON_NAME_OVERRIDES` in `builder/icons.py`.

## Release Flow

`.github/workflows/generate-profile.yml`: pushes to `main` touching `config.yaml`, `builder/`, `generate.py`, or plugin sources trigger CI, which rebuilds the plugin, runs `python generate.py`, force-adds and commits `profile/home-ops.streamDeckProfile` (`[skip ci]`), and publishes it to the rolling `latest` release. The deck's **Update Profile** button downloads from that release (`scripts/update-profile.ps1`).

## Gotchas

- `profile/home-ops.streamDeckProfile` is in `.gitignore` but committed by CI with `git add -f` — don't commit it manually.
- `Default Profile.streamDeckProfile` and `usethisone.streamDeckProfile` are committed binary ZIPs (the user's full deck profile). `generate.py --embed` rewrites pages into the Default Profile, converting the home-ops 1.0 flat-key manifest format to the Default Profile 3.0 `col,row` format (`builder/embed.py`).
- The plugin manifest (`plugin/manifest.json`) is Windows-only and requires Stream Deck software 6.4+. Action UUIDs (`com.phew.blue.homeops.{status,cluster,node}`) are referenced by both `builder/` page generation and `builder/embed.py` — keep all three in sync if renaming.
- `plugin/package.json` builds with esbuild only (no tsc typecheck step); `npm run build` is the whole build.
- Generated artifacts are gitignored: `plugin/dist/`, `dist-plugin/`, `icons/apps/`, `scripts/launchers/`.
