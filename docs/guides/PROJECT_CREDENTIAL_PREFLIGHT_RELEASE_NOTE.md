# Project credential preflight — release note

Issue #116 добавляет read-only диагностический этап перед Project lifecycle write. Диагностика отделена от proven sync-кода #117/#119 и не меняет контракт `mtd`, auto-merge или PromotionStore.
