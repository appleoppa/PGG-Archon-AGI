# Private GitHub Deploy Snapshot for Shallow/LFS External Repos

## Trigger

Use when the user wants a local external repo (for example PilotDeck) saved to the user's own private GitHub repository so it can be cloned/deployed on another machine, especially when the local repo is a shallow clone or has Git LFS media.

## Verified pattern from 2026-06-06

A direct push from a shallow local clone can fail with a remote unpack error such as:

```text
remote: fatal: did not receive expected object <sha>
remote rejected main -> main (failed)
```

This is not proof that GitHub is broken. Check:

```bash
git rev-parse --is-shallow-repository
git config --get-regexp 'remote\..*\.promisor|remote\..*\.partialclonefilter|extensions.partialclone|core.repositoryformatversion' || true
git fsck --connectivity-only --no-dangling || true
git rev-list --objects --missing=print HEAD | grep '^?' || true
```

If the repo is shallow and the user's goal is cross-machine deployment rather than preserving upstream history, prefer a clean snapshot mirror.

## Clean snapshot mirror workflow

1. Verify current remotes and status:

```bash
git remote -v
git status --short --branch
git log --oneline origin/main..HEAD --max-count=30 || true
```

2. Audit local deltas and staged candidates before committing/pushing:

```bash
git diff --stat
git diff -- <candidate-files>
git status --porcelain=v1
```

3. Secret-scan staged/snapshot files. Treat obvious placeholders such as `ghp_xx...xxxx` as placeholders only after reading the exact source lines. Never push `.env`, auth DBs, node_modules, runtime state, provider keys, telemetry queues, or session state.

4. Create a private GitHub repo if needed:

```bash
gh repo create <user>/<repo> --private --description "..." --disable-wiki --disable-issues
```

5. If direct push fails due to shallow/missing objects, create a clean snapshot from tracked working-tree files rather than `git archive` if Git LFS filters are unavailable:

```bash
SNAP=/path/to/private-snapshot
mkdir -p "$SNAP"
python3 - <<'PY'
import os, subprocess, shutil, pathlib
src=pathlib.Path('/path/to/source')
snap=pathlib.Path('/path/to/private-snapshot')
files=subprocess.check_output(['git','-C',str(src),'ls-files','-z'],text=False).split(b'\0')
skip_prefixes=(b'node_modules/', b'ui/node_modules/', b'.git/')
skip_exact={b'.env', b'home/.pilotdeck/.env', b'.pilotdeck/auth.db'}
for raw in files:
    if not raw or raw in skip_exact or any(raw.startswith(p) for p in skip_prefixes):
        continue
    rel=pathlib.Path(raw.decode('utf-8','surrogateescape'))
    s=src/rel; d=snap/rel
    if not s.exists() or not s.is_file():
        continue
    d.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(s,d)
PY
```

6. Initialize and add the snapshot. If `.gitattributes` declares LFS and `git add` triggers `git-lfs filter-process: git-lfs: command not found`, use command-level LFS filter overrides for `git add`:

```bash
git init -b main
git -c filter.lfs.process= -c filter.lfs.clean=cat -c filter.lfs.smudge=cat -c filter.lfs.required=false add -A
```

7. Commit and push:

```bash
git commit -m "Snapshot local <repo> sync"
git remote add origin https://github.com/<user>/<repo>.git
git push -u origin main
```

8. Read back remote state:

```bash
git ls-remote --heads origin main
gh repo view <user>/<repo> --json nameWithOwner,visibility,url,defaultBranchRef,pushedAt,isEmpty
gh api 'repos/<user>/<repo>/contents/docs/...?...' --jq '{path:.path,size:.size,sha:.sha}'
```

## LFS boundary handling

If `git lfs fetch` from upstream returns a budget error:

```text
This repository exceeded its LFS budget
```

do not claim a full media-complete mirror. Either stop with a blocker or convert the private repo into a code/deployment snapshot:

- neutralize LFS filter lines in the private snapshot `.gitattributes` only;
- document that media/icon/video files may remain LFS pointer text;
- state that source install/gateway/server smoke should still be possible, but visual/media assets may be missing;
- do not advise `git lfs pull` against the private mirror until real LFS objects have been uploaded.

Example `.gitattributes` neutralization line:

```text
# apple-sync private deploy mirror: LFS disabled because upstream LFS budget blocked object fetch; media may remain pointer placeholders: *.png filter=lfs diff=lfs merge=lfs -text
```

## Deployment note to include

Add `docs/<sync-name>/DEPLOY_FROM_PRIVATE_REPO.md` with:

- what is included;
- what is intentionally excluded;
- fresh-machine clone/install commands;
- env/key placement warning;
- LFS/media boundary if any;
- smoke checks (`curl /health`, protocol smoke if applicable);
- remote roles (`origin` upstream vs user private mirror) if both are kept locally.

## Boundary wording

A private deploy snapshot proves the user can clone the source/overlay from their own GitHub repo. It does not include credentials, auth DBs, local runtime state, provider accounts, or unavailable upstream LFS media objects. If LFS objects could not be fetched, call it a code/deployment snapshot, not a full asset mirror.
