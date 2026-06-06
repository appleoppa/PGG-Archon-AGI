# Hermes Desktop official-origin verification (2026-06-03)

## When to use

Use when a user asks whether a downloaded Hermes Desktop app is official, especially after they also have a local Hermes Agent CLI/source deployment.

## Key distinction

Separate three identities:

1. **CLI/source deployment** — local repo/CLI such as `~/.hermes/hermes-agent`, `hermes --version`, git remotes.
2. **Desktop app bundle** — macOS app such as `/Applications/Hermes.app` with `Info.plist`, bundle id, version, and code signature.
3. **Download origin** — URL/site/release asset the app came from.

Do not answer “official” from only one layer. A local CLI official repo does not prove a downloaded Desktop app is official; a bundle identifier does not prove download provenance; Apple Gatekeeper rejection does not automatically mean fake.

## Verified official Desktop URL pattern

For the checked session, the user-provided URL was:

```text
https://hermes-agent.nousresearch.com/desktop
```

Live inspection showed:

- page title: `Hermes Desktop | Nous Research`
- links to official repo/release:
  - `https://github.com/NousResearch/hermes-agent`
  - `https://github.com/NousResearch/hermes-agent/releases`
- macOS download asset:
  - `https://hermes-assets.nousresearch.com/Hermes-Setup.dmg`
- response hosted as a Next.js/Vercel site, matched path `/desktop`.

Treat this as the official NousResearch Hermes Desktop download page unless later official docs contradict it.

## macOS verification commands

```bash
APP='/Applications/Hermes.app'
/usr/libexec/PlistBuddy -c 'Print :CFBundleIdentifier' "$APP/Contents/Info.plist"
/usr/libexec/PlistBuddy -c 'Print :CFBundleName' "$APP/Contents/Info.plist"
/usr/libexec/PlistBuddy -c 'Print :CFBundleShortVersionString' "$APP/Contents/Info.plist"
codesign --verify --deep --strict --verbose=4 "$APP"
codesign -dv --verbose=4 "$APP" 2>&1 | egrep 'Authority=|TeamIdentifier=|Identifier=|Runtime Version|Timestamp|CDHash|Format='
spctl -a -vvv -t exec "$APP" 2>&1 || true
xattr -p com.apple.quarantine "$APP" 2>/dev/null || true
```

Typical observed Desktop bundle fields:

```text
CFBundleIdentifier: com.nousresearch.hermes
CFBundleName: Hermes
CFBundleDisplayName: Hermes
CFBundleShortVersionString: 0.15.1
CFBundleVersion: 0.15.1
```

Observed code-signing/Gatekeeper nuance:

```text
/Applications/Hermes.app: valid on disk
/Applications/Hermes.app: satisfies its Designated Requirement
Identifier=com.nousresearch.hermes
TeamIdentifier=not set
spctl: rejected
```

Meaning: the app bundle’s internal signature can be valid while still lacking an Apple Developer ID TeamIdentifier/notarization. Report this as “official-origin page, but not Apple-notarized/Developer-ID verified on this machine,” not as “fake.”

## Suggested answer shape

```text
status: 官方下载地址/来源可信度
checked_url:
app_bundle:
code_signing:
gatekeeper:
important_distinction:
```

Keep it concise for mobile. If the user gives an exact URL, check that URL directly before answering.
