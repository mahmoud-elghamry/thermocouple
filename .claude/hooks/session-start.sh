#!/usr/bin/env bash
# SessionStart hook: make a Claude Code *cloud* session able to check this
# project the way the Windows workstation does.
#
# Runs only when CLAUDE_CODE_REMOTE=true (the cloud container). On the Windows
# workstation, or any local Linux box, it exits at once and changes nothing.
#
# What a cloud session gets:
#   avr-gcc + host cc      make -C firmware all test   (build.ps1 needs MSVC)
#   kicad-cli (KiCad 10)   ERC / DRC / netlist, via kicad-tool
#   kicad-tool             uv tool, from mash/kicad-skills (never pip kiutils)
#   pwsh                   hardware/8ch/validate.ps1 / run_all.ps1
#   Konnect                the KiCad MCP, same version as the workstation
#
# Not available in the cloud: -Regenerate (needs KiCad's pcbnew Python and
# Freerouting) and anything needing the KiCad GUI. docs/TOOLS.md has the list.
#
# Every step is idempotent and fails soft: one missing tool must not stop the
# session from starting. The summary at the end says what is and is not there.

set -u

[ "${CLAUDE_CODE_REMOTE:-}" = "true" ] || exit 0
[ "$(uname -s)" = "Linux" ] || exit 0

KONNECT_VERSION="0.11.1"   # keep equal to the workstation: konnect.exe --version
PWSH_VERSION="7.6.6"
KICAD_PPA="ppa:kicad/kicad-10.0-releases"

LOCAL="$HOME/.local"
BIN="$LOCAL/bin"
mkdir -p "$BIN"
export PATH="$BIN:$PATH"
LOG="$HOME/.cache/thermo-session-start.log"
mkdir -p "$(dirname "$LOG")"
: >"$LOG"

SUDO=""
if [ "$(id -u)" -ne 0 ]; then SUDO="sudo -n"; fi

step() { echo "== $*" >>"$LOG"; }
have() { command -v "$1" >/dev/null 2>&1; }

# --- apt: firmware toolchain, python, KiCad -----------------------------------
apt_pkgs=""
have avr-gcc      || apt_pkgs="$apt_pkgs gcc-avr binutils-avr avr-libc"
have cc           || apt_pkgs="$apt_pkgs gcc"
have make         || apt_pkgs="$apt_pkgs make"
have python3      || apt_pkgs="$apt_pkgs python3"
have python       || apt_pkgs="$apt_pkgs python-is-python3"
have unzip        || apt_pkgs="$apt_pkgs unzip"
have curl         || apt_pkgs="$apt_pkgs curl ca-certificates"
if [ -n "$apt_pkgs" ]; then
  step "apt:$apt_pkgs"
  $SUDO apt-get update -qq >>"$LOG" 2>&1
  DEBIAN_FRONTEND=noninteractive $SUDO apt-get install -y -qq --no-install-recommends $apt_pkgs >>"$LOG" 2>&1
fi

# Only KiCad 10 counts: Ubuntu's own `kicad` is 7.0, which cannot open this
# project's files. If the PPA is not added, apt would silently install that.
kicad10() { kicad-cli version 2>/dev/null | grep -q '^10\.'; }

if ! kicad10; then
  step "KiCad 10 from $KICAD_PPA"
  have add-apt-repository || DEBIAN_FRONTEND=noninteractive $SUDO apt-get install -y -qq software-properties-common >>"$LOG" 2>&1
  if $SUDO add-apt-repository -y "$KICAD_PPA" >>"$LOG" 2>&1; then
    $SUDO apt-get update -qq >>"$LOG" 2>&1
    # No libraries: ERC/DRC/netlist read the project files, not the libraries.
    DEBIAN_FRONTEND=noninteractive $SUDO apt-get install -y -qq --no-install-recommends kicad >>"$LOG" 2>&1
  fi
fi

# Fallback, measured 2026-09-24: the cloud proxy answers 403 for
# ppa.launchpadcontent.net and add-apt-repository has no apt_pkg, so the PPA
# never installs. KiCad's own image on ghcr.io does (docker.io rate-limits).
# kicad-cli then runs in that container with host paths mounted in place.
KICAD_IMAGE="ghcr.io/kicad/kicad:10.0"
if ! kicad10 && have docker; then
  step "KiCad 10 from $KICAD_IMAGE"
  if ! docker info >/dev/null 2>&1; then
    (nohup dockerd >>"$LOG" 2>&1 &)
    for _ in $(seq 1 30); do docker info >/dev/null 2>&1 && break; sleep 1; done
  fi
  if docker pull -q "$KICAD_IMAGE" >>"$LOG" 2>&1; then
    cat >"$BIN/kicad-cli" <<EOF
#!/bin/sh
exec docker run --rm -i --user root --network none -v /home:/home -v /tmp:/tmp -v "\$HOME:\$HOME" -e HOME="\$HOME" -w "\$PWD" $KICAD_IMAGE kicad-cli "\$@"
EOF
    chmod +x "$BIN/kicad-cli"
    # Stock library tables: without them ERC reports lib_symbol_issues on
    # every symbol. The container reads them from the mounted $HOME.
    kcfg="$HOME/.config/kicad/10.0"
    if [ ! -f "$kcfg/sym-lib-table" ]; then
      mkdir -p "$kcfg"
      docker run --rm --user root -v "$kcfg:/out" "$KICAD_IMAGE" sh -c \
        'cp /usr/share/kicad/template/sym-lib-table /usr/share/kicad/template/fp-lib-table /out/' >>"$LOG" 2>&1
    fi
  fi
fi

# --- pwsh ---------------------------------------------------------------------
if ! have pwsh; then
  step "pwsh $PWSH_VERSION"
  dir="$LOCAL/opt/pwsh-$PWSH_VERSION"
  mkdir -p "$dir"
  curl -fsSL "https://github.com/PowerShell/PowerShell/releases/download/v$PWSH_VERSION/powershell-$PWSH_VERSION-linux-x64.tar.gz" \
    | tar -xz -C "$dir" >>"$LOG" 2>&1 \
    && chmod +x "$dir/pwsh" && ln -sf "$dir/pwsh" "$BIN/pwsh"
fi

# --- uv + kicad-tool ------------------------------------------------------------
if ! have uv; then
  step "uv"
  curl -LsSf https://astral.sh/uv/install.sh | env UV_NO_MODIFY_PATH=1 sh >>"$LOG" 2>&1
  # astral.sh is 403 through the cloud proxy (2026-09-24); PyPI is allowed.
  have uv || python3 -m pip install -q uv >>"$LOG" 2>&1
fi
if ! have kicad-tool && have uv; then
  step "kicad-tool"
  uv tool install git+https://github.com/mash/kicad-skills.git >>"$LOG" 2>&1
fi

# --- Konnect --------------------------------------------------------------------
if ! have konnect || ! konnect --version 2>/dev/null | grep -q "$KONNECT_VERSION"; then
  step "Konnect $KONNECT_VERSION"
  curl -fsSL "https://github.com/mixelpixx/Konnect/releases/download/v$KONNECT_VERSION/konnect-v$KONNECT_VERSION-x86_64-unknown-linux-gnu.tar.gz" \
    | tar -xz -C "$BIN" konnect >>"$LOG" 2>&1 \
    && chmod +x "$BIN/konnect"
fi

# Local scope: lives in this container's ~/.claude.json only. The repo's
# .mcp.json stays empty on purpose (see its _comment). No KICAD_API_SOCKET:
# there is no KiCad GUI here, so Konnect runs on the files directly.
if have konnect && have claude && [ -n "${CLAUDE_PROJECT_DIR:-}" ]; then
  if ! (cd "$CLAUDE_PROJECT_DIR" && claude mcp get konnect >/dev/null 2>&1); then
    step "register Konnect"
    (cd "$CLAUDE_PROJECT_DIR" && claude mcp add --scope local konnect -- "$BIN/konnect") >>"$LOG" 2>&1
  fi
fi

# --- environment for the rest of the session ------------------------------------
if [ -n "${CLAUDE_ENV_FILE:-}" ]; then
  {
    echo "export PATH=\"$BIN:\$PATH\""
    kicad10         && echo "export KICAD_CLI=\"$(command -v kicad-cli)\""
    have kicad-tool && echo "export KICAD_TOOL=\"$(command -v kicad-tool)\""
  } >>"$CLAUDE_ENV_FILE"
fi

# --- summary: stdout becomes session context ---------------------------------------
missing=""
for t in avr-gcc cc make python pwsh kicad-cli kicad-tool konnect; do
  have "$t" || missing="$missing $t"
done
have kicad-cli && ! kicad10 && missing="$missing kicad-cli(not-10)"
echo "Thermo cloud setup (.claude/hooks/session-start.sh):"
echo "  firmware:  make -C firmware all test      (build.ps1 is Windows/MSVC only)"
echo "  hardware:  pwsh -File hardware/8ch/validate.ps1"
echo "  not here:  run_all.ps1 -Regenerate, KiCad GUI, Proteus"
if [ -n "$missing" ]; then
  echo "  MISSING:$missing  - see $LOG. Say so; do not claim a check you could not run."
else
  echo "  all tools present."
fi
exit 0
