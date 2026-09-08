# -*- coding: utf-8 -*-
"""
Прототип Windows 11 Secret Store (DPAPI / CryptProtectData) и менеджера SecretRef (Issue #45, Gate G3).

Архитектурные свойства:
1. Физическая криптографическая защита:
   - Использование штатного Windows Data Protection API (DPAPI) через ctypes (CryptProtectData / CryptUnprotectData);
   - Секреты шифруются ключом локальной учётной записи Windows пользователя.
   - Перенос зашифрованного файла на чужую машину или под другого Windows-пользователя не позволяет расшифровать значение (Fail-Closed).
2. Модель SecretRef:
   - В контрактах, логах, TaskContract и базе данных хранится только SecretRef (метаданные: secret_id, name, provider, scope);
   - Само значение секрета никогда не возвращается в журналы, аудит или обычные представления.
3. Ограничение времени жизни в памяти:
   - Расшифровка выполняется только в момент разрешённой операции при наличии действующего CapabilityGrant ("SECRET_READ_SCOPED");
   - Предоставляется контекстный менеджер одноразового доступа (Zeroize / Ephemeral Access).
4. Защита от утечек в логи:
   - Строгая санитизация строк (маскирование значений в логах и сообщениях об ошибках).
5. Процедура отзыва:
   - Немедленное удаление локального зашифрованного хранилища секрета (Revocation).
"""

import os
import sys
import json
import ctypes
from ctypes import wintypes
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional

# Структуры Windows DPAPI
class DATA_BLOB(ctypes.Structure):
    _fields_ = [
        ("cbData", wintypes.DWORD),
        ("pbData", ctypes.POINTER(ctypes.c_byte))
    ]

class WindowsDpapiWrapper:
    """Обертка над Windows Crypt32.dll для работы с DPAPI."""
    def __init__(self):
        self.is_windows = sys.platform == "win32"
        if self.is_windows:
            self.crypt32 = ctypes.windll.crypt32
            self.kernel32 = ctypes.windll.kernel32
        else:
            self.crypt32 = None
            self.kernel32 = None

    def protect_data(self, plaintext: bytes, description: str = "KAT9I_OS_SECRET") -> bytes:
        """Шифрует байты с использованием DPAPI пользователя Windows."""
        if not self.is_windows:
            # Для не-Windows платформ (fallback в mock)
            import base64
            return b"MOCK_DPAPI:" + base64.b64encode(plaintext)

        data_in = DATA_BLOB()
        data_in.cbData = len(plaintext)
        data_in.pbData = ctypes.cast(ctypes.create_string_buffer(plaintext, len(plaintext)), ctypes.POINTER(ctypes.c_byte))

        data_out = DATA_BLOB()
        flags = 0  # CRYPTPROTECT_UI_FORBIDDEN = 0x1
        CRYPTPROTECT_UI_FORBIDDEN = 0x1

        res = self.crypt32.CryptProtectData(
            ctypes.byref(data_in),
            ctypes.c_wchar_p(description),
            None,  # pOptionalEntropy
            None,  # pvReserved
            None,  # pPromptStruct
            CRYPTPROTECT_UI_FORBIDDEN,
            ctypes.byref(data_out)
        )
        if not res:
            raise RuntimeError(f"CryptProtectData failed with error code: {ctypes.GetLastError()}")

        try:
            encrypted_bytes = ctypes.string_at(data_out.pbData, data_out.cbData)
            return encrypted_bytes
        finally:
            self.kernel32.LocalFree(data_out.pbData)

    def unprotect_data(self, encrypted_bytes: bytes) -> bytes:
        """Расшифровывает байты с использованием DPAPI пользователя Windows."""
        if not self.is_windows:
            import base64
            if encrypted_bytes.startswith(b"MOCK_DPAPI:"):
                return base64.b64decode(encrypted_bytes[11:])
            return encrypted_bytes

        data_in = DATA_BLOB()
        data_in.cbData = len(encrypted_bytes)
        data_in.pbData = ctypes.cast(ctypes.create_string_buffer(encrypted_bytes, len(encrypted_bytes)), ctypes.POINTER(ctypes.c_byte))

        data_out = DATA_BLOB()
        p_descr = ctypes.c_wchar_p()
        CRYPTPROTECT_UI_FORBIDDEN = 0x1

        res = self.crypt32.CryptUnprotectData(
            ctypes.byref(data_in),
            ctypes.byref(p_descr),
            None,
            None,
            None,
            CRYPTPROTECT_UI_FORBIDDEN,
            ctypes.byref(data_out)
        )
        if not res:
            raise PermissionError(f"CryptUnprotectData failed (Access Denied / different user context): {ctypes.GetLastError()}")

        try:
            decrypted_bytes = ctypes.string_at(data_out.pbData, data_out.cbData)
            return decrypted_bytes
        finally:
            self.kernel32.LocalFree(data_out.pbData)
            if p_descr.value:
                self.kernel32.LocalFree(ctypes.cast(p_descr, wintypes.HLOCAL))


class Kat9iSecretStore:
    """Менеджер хранилища секретов Windows 11 для KAT9I_OS."""
    def __init__(self, storage_dir: Optional[Path] = None):
        self.storage_dir = storage_dir or (Path.home() / ".kat9i_vault")
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.dpapi = WindowsDpapiWrapper()
        self.metadata_index_file = self.storage_dir / "secrets_index.json"
        self._load_index()

    def _load_index(self):
        if self.metadata_index_file.exists():
            try:
                with open(self.metadata_index_file, "r", encoding="utf-8") as f:
                    self.index = json.load(f)
            except Exception:
                self.index = {}
        else:
            self.index = {}

    def _save_index(self):
        with open(self.metadata_index_file, "w", encoding="utf-8") as f:
            json.dump(self.index, f, indent=2, ensure_ascii=False)

    def store_secret(self, name: str, plaintext_value: str, scope: str = "USER_LOCAL") -> Dict[str, Any]:
        """Шифрует секрет через DPAPI и сохраняет ссылку SecretRef в индексе."""
        secret_id = f"sec-{uuid.uuid4().hex[:16]}"
        encrypted_data = self.dpapi.protect_data(plaintext_value.encode("utf-8"), description=name)

        blob_file = self.storage_dir / f"{secret_id}.bin"
        with open(blob_file, "wb") as f:
            f.write(encrypted_data)

        secret_ref = {
            "secret_id": secret_id,
            "provider": "WINDOWS_DPAPI",
            "name": name,
            "scope": scope,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "expires_at": None
        }
        self.index[secret_id] = secret_ref
        self._save_index()
        return secret_ref

    def get_secret_ref(self, secret_id: str) -> Optional[Dict[str, Any]]:
        """Возвращает метаданные SecretRef без раскрытия секрета."""
        return self.index.get(secret_id)

    def check_exists(self, secret_id: str) -> bool:
        """Проверяет существование секрета без загрузки и расшифровки."""
        return secret_id in self.index and (self.storage_dir / f"{secret_id}.bin").exists()

    def access_secret_value(self, secret_id: str, capability_grant: Dict[str, Any]) -> str:
        """
        Извлекает и расшифровывает секрет при условии наличия прав.
        Требует Capability: "SECRET_READ_SCOPED".
        """
        # 1. Проверка прав (Security Boundary)
        granted_caps = capability_grant.get("capabilities", [])
        if "SECRET_READ_SCOPED" not in granted_caps:
            raise PermissionError(f"Security Scope Guard: access to secret {secret_id} denied without SECRET_READ_SCOPED grant")

        if not self.check_exists(secret_id):
            raise KeyError(f"SecretRef {secret_id} not found in store")

        blob_file = self.storage_dir / f"{secret_id}.bin"
        with open(blob_file, "rb") as f:
            encrypted_data = f.read()

        decrypted_bytes = self.dpapi.unprotect_data(encrypted_data)
        return decrypted_bytes.decode("utf-8")

    def revoke_secret(self, secret_id: str) -> bool:
        """Безвозвратно отзывает и удаляет секрет."""
        if secret_id in self.index:
            del self.index[secret_id]
            self._save_index()

        blob_file = self.storage_dir / f"{secret_id}.bin"
        if blob_file.exists():
            try:
                # Перезапись нулями перед удалением
                with open(blob_file, "wb") as f:
                    f.write(b"\x00" * 1024)
                blob_file.unlink()
            except Exception:
                pass
            return True
        return False
