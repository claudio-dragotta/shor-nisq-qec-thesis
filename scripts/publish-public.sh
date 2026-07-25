#!/bin/sh
# Ripubblica un MIRROR RIPULITO di questo repo sul repository pubblico.
# Rimuove i file sensibili/privati dall'INTERA storia con git-filter-repo e poi
# fa force-push. Idempotente: si puo' eseguire quante volte si vuole.
#
# Requisiti: git-filter-repo  (pip install git-filter-repo)
# URL pubblico configurabile:  git config tesi.publicurl <url>
set -e

PUBLIC_URL=$(git config tesi.publicurl 2>/dev/null || true)
[ -z "$PUBLIC_URL" ] && PUBLIC_URL="https://github.com/claudio-dragotta/shor-nisq-qec-thesis.git"
REPO_ROOT=$(git rev-parse --show-toplevel)

if ! git filter-repo --version >/dev/null 2>&1; then
  echo "[publish-public] ERRORE: git-filter-repo non installato. Esegui 'pip install git-filter-repo'. Interrotto."
  exit 1
fi

TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT

# Percorsi da rimuovere da TUTTA la storia (glob per tipo + cartelle + PDF di terzi,
# inclusi i path "vecchi" pre-riordino). Tenere allineato al README.
cat > "$TMP/exclude.txt" <<'EOF'
glob:*.docx
glob:*.mp4
glob:*.mp3
glob:*.m4a
glob:*.wav
glob:*.mov
_archivio
diario_relatore.md
Extra/articoli
Extra/tesi_esterne
tesi_esterne
glob:*grover-Seminar.pdf
glob:*grover-art.1.pdf
glob:*Cescon_Matteo.pdf
glob:*martina_berarducci_tesi.pdf
glob:*Crittografia quantistica e algoritmo di Shor.pdf
EOF

git clone --no-local --quiet "$REPO_ROOT" "$TMP/mirror"
cd "$TMP/mirror"
git filter-repo --force --quiet --invert-paths --paths-from-file "$TMP/exclude.txt"
git remote add origin "$PUBLIC_URL"
git push --force --quiet origin HEAD:main
echo "[publish-public] OK $(date '+%Y-%m-%d %H:%M:%S') -> $PUBLIC_URL"
