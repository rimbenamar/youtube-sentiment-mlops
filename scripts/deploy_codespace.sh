#!/usr/bin/env bash
# Déploiement manuel dans GitHub Codespaces (équivalent de ce qui est lancé automatiquement
# au démarrage du Codespace) :   bash scripts/deploy_codespace.sh
exec bash "$(dirname "$0")/start_api.sh"
