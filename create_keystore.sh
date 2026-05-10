#!/usr/bin/env bash
# create_keystore.sh – Android Keystore für Byblos CRM erstellen
# ============================================================
# Erstellt einen neuen Release-Keystore und gibt die lokalen
# Gradle-Properties aus, die für den Release-Build benötigt werden.
#
# Einmalig ausführen! Den Keystore sicher aufbewahren (niemals in Git!).

set -euo pipefail

KEYSTORE_NAME="byblos_crm_release.jks"
KEY_ALIAS="bybloscrm"
VALIDITY_DAYS=10000

echo ""
echo "====================================================="
echo "  Byblos CRM – Android Keystore Generator"
echo "====================================================="
echo ""
echo "Gib ein sicheres Passwort für den Keystore ein:"
read -s STORE_PASS
echo "Wiederhole das Passwort:"
read -s STORE_PASS2
if [ "$STORE_PASS" != "$STORE_PASS2" ]; then
    echo "[FEHLER] Passwörter stimmen nicht überein."
    exit 1
fi

echo ""
echo "[INFO] Erstelle Keystore: $KEYSTORE_NAME"

keytool -genkeypair \
    -alias "$KEY_ALIAS" \
    -keyalg RSA \
    -keysize 2048 \
    -validity $VALIDITY_DAYS \
    -keystore "$KEYSTORE_NAME" \
    -storepass "$STORE_PASS" \
    -keypass "$STORE_PASS" \
    -dname "CN=Byblos Sicherheitsdienst, OU=IT, O=Byblos, L=Tuelau, ST=Niedersachsen, C=DE"

echo ""
echo "[OK] Keystore erstellt: $(pwd)/$KEYSTORE_NAME"
echo ""
echo "Füge folgende Zeilen in deine ~/.gradle/gradle.properties ein:"
echo "(NICHT in das Projekt-Verzeichnis – niemals in Git!)"
echo ""
echo "---------------------------------------------------"
echo "KEYSTORE_FILE=$(pwd)/$KEYSTORE_NAME"
echo "KEYSTORE_PASS=$STORE_PASS"
echo "KEY_ALIAS=$KEY_ALIAS"
echo "KEY_PASS=$STORE_PASS"
echo "---------------------------------------------------"
echo ""
echo "Danach Release-Build:"
echo "  ./android/build_apk.sh release"
echo ""
