from dataclasses import dataclass


@dataclass
class BaseUser:
    id: int
    email: str
    role: str = "user"
    is_active: bool = True

    def __post_init__(self) -> None:
        if not self.email or "@" not in self.email.strip():
            raise ValueError("Valid email address is required")
        self.email = self.email.strip().lower()

    def can_audit_all_tenants(self) -> bool:
        return False


@dataclass
class StandardUser(BaseUser):
    role: str = "user"


@dataclass
class AdminUser(BaseUser):
    role: str = "admin"

    def can_audit_all_tenants(self) -> bool:
        return True