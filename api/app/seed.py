import logging
import re

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import hash_password
from app.config import settings
from app.models.core import Tenant, User

logger = logging.getLogger("quizbee")


def _slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


async def seed_admin(db: AsyncSession) -> None:
    result = await db.execute(select(User).where(User.email == settings.admin_email))
    if result.scalar_one_or_none():
        return

    # Create default tenant
    slug = _slugify(settings.admin_email.split("@")[0])
    tenant = Tenant(name="Default", slug=slug or "default")
    db.add(tenant)
    await db.flush()

    admin = User(
        tenant_id=tenant.id,
        email=settings.admin_email,
        password_hash=hash_password(settings.admin_password),
        role="admin",
        force_password_reset=True,
    )
    db.add(admin)
    await db.commit()
    logger.info("Admin user seeded: %s", settings.admin_email)
