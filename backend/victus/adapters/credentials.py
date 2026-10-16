"""Windows Credential Manager only; credentials never use prompts or frontend storage."""


class WindowsCredentials:
    target = "VICTUS:cloud:openrouter"

    def read(self):
        try:
            import win32cred

            value = win32cred.CredRead(self.target, win32cred.CRED_TYPE_GENERIC)
            raw = value["CredentialBlob"]
            key = raw.decode("utf-16-le") if isinstance(raw, bytes) else raw
            if not key or len(key) > 4096 or any(c.isspace() for c in key):
                raise ValueError()
            return key
        except Exception:
            raise RuntimeError("CLOUD_CREDENTIAL_UNAVAILABLE") from None

    def store(self, key):
        if not isinstance(key, str) or not key or len(key) > 4096 or any(c.isspace() for c in key):
            raise ValueError("Invalid credential")
        try:
            import win32cred

            win32cred.CredWrite({
                "Type": win32cred.CRED_TYPE_GENERIC,
                "TargetName": self.target,
                "CredentialBlob": key.encode("utf-16-le"),
                "Persist": win32cred.CRED_PERSIST_LOCAL_MACHINE,
                "UserName": "VICTUS",
            }, 0)
        except Exception:
            raise RuntimeError("CLOUD_CREDENTIAL_UNAVAILABLE") from None
