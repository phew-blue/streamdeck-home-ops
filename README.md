# streamdeck-home-ops

Stream Deck XL profile for the [home-ops](https://github.com/phew-blue/home-ops) Kubernetes cluster. Shows live pod status, CPU/RAM usage, and provides one-press restart/reconcile/logs actions for every deployed app.

## Features

- **Landing page** — live cluster stats (age, uptime, node count, pod count, CPU, memory, alerts) via [kromgo](https://github.com/kashalls/kromgo)
- **Talos nodes page** — per-node status (Ready, pod count, CPU%, RAM%)
- **K8s namespace grid** — one folder per namespace, pinned quick-launch apps
- **Per-namespace pages** — two layers per namespace:
  - Layer 1 (status): app icon -> web UI, live pod/restart count, CPU, RAM
  - Layer 2 (actions): logs, restart pod, force-reconcile
- **Auto-update** — press the Update Profile button to download and import the latest release

## Prerequisites (Windows)

- [kubectl](https://kubernetes.io/docs/tasks/tools/install-kubectl-windows/) with your kubeconfig at `~/.kube/config`
- [flux CLI](https://fluxcd.io/flux/installation/)
- [Elgato Stream Deck software](https://www.elgato.com/downloads) v6.4+
- Node.js v20+ (for plugin build)

## Installation

### 1. Install scripts

```powershell
git clone https://github.com/phew-blue/streamdeck-home-ops
cd streamdeck-home-ops
powershell -ExecutionPolicy Bypass -File scripts\install.ps1
```

### 2. Install the plugin

```powershell
cd plugin
powershell -ExecutionPolicy Bypass -File build-plugin.ps1 -Install
```

Restart the Elgato Stream Deck software after installing the plugin.

### 3. Import the profile

Download `home-ops.streamDeckProfile` from the [latest release](https://github.com/phew-blue/streamdeck-home-ops/releases/latest) and double-click it.

Or press **Update Profile** (bottom-right of the landing page) to download and import automatically.

## Layout

### Landing page

| Col | R1 | R2 | R3 |
|-----|----|----|-----|
| 1 | Back | | |
| 2 | Talos | Age | CPU |
| 3 | K8s | Uptime | Memory |
| 4 | Flux | Nodes | Alerts |
| 5 | (future) | Pods | |
| 7 | | | Update Profile |

### Talos nodes page

One column per node (cols 2-6). Each column: name+role (R1), pods running/capacity (R2), CPU% (R3), RAM% (R4). Press a node button to open `kubectl describe node` in a terminal.

### Namespace pages - Layer 1 (status)

- **R1**: App icon - click to open web UI
- **R2**: Live pod count + restart count (`1/1 * 0`)
- **R3**: Live CPU usage
- **R4**: Live RAM usage
- **Col 8 down**: Switch to actions layer
- **Col 1 home**: Back to K8s grid

### Namespace pages - Layer 2 (actions)

- **R1**: View logs (`kubectl logs -f`)
- **R2**: Restart pod (`kubectl rollout restart`)
- **R3**: Force reconcile (`flux reconcile helmrelease`)
- **Col 8 up**: Back to status layer
- **Col 1 home**: Back to landing page

## Updating the profile

When apps are added or URLs change:

1. Edit `config.yaml`
2. Push to `main`
3. GitHub Actions regenerates the profile and publishes a new release
4. Press **Update Profile** on the deck -> click Import

## Development

```bash
# Regenerate profile after config changes
python generate.py

# Run tests
python -m pytest tests/ -v

# Build plugin
cd plugin && npm run build
```
