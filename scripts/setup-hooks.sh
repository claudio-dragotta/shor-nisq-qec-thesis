#!/bin/sh
# Configura i git hook del progetto. Eseguire UNA volta dopo il clone:
#     sh scripts/setup-hooks.sh
git config core.hooksPath .githooks
git config tesi.autopublish true
chmod +x .githooks/* scripts/*.sh 2>/dev/null || true
echo "Hook attivati."
echo "  post-commit -> auto-pubblica il mirror ripulito su repo pubblico quando cambi file pubblici."
echo "  Disattiva con:  git config tesi.autopublish false"
echo "  URL pubblico:   git config tesi.publicurl <url>   (default: shor-nisq-qec-thesis)"
