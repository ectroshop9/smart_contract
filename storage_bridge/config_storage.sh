#!/bin/bash
# تهيئة مسارات التخزين الدائم لضمان عدم ضياع البيانات
STORAGE_PATH="/data/smart_contract_vault"

if [ ! -d "$STORAGE_PATH" ]; then
  mkdir -p "$STORAGE_PATH/backups"
  mkdir -p "$STORAGE_PATH/logs"
  echo "Storage Bridge: Directories created at $STORAGE_PATH"
else
  echo "Storage Bridge: Persistent storage already exists."
fi
