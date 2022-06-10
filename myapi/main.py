import uvicorn
from typing import Optional

import databases
from fastapi import FastAPI
from fastapi_users.authentication import AuthenticationBackend, CookieTransport, RedisStrategy
from fastapi import Depends, Request
from fastapi_users import BaseUserManager, FastAPIUsers

from fastapi_users.db import SQLAlchemyBaseUserTableUUID, SQLAlchemyUserDatabase
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.ext.declarative import DeclarativeMeta, declarative_base
from sqlalchemy.orm import sessionmaker

DATABASE_URL = "sqlite+aiosqlite:///./test.db"
Base: DeclarativeMeta = declarative_base()

class User(SQLAlchemyBaseUserTableUUID, Base):
    pass


engine = create_async_engine(DATABASE_URL)
async_session_maker = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def create_db_and_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        yield session


async def get_user_db(session: AsyncSession = Depends(get_async_session)):
    yield SQLAlchemyUserDatabase(session, User)

SECRET = 'SECRET'  # CHANGE THIS!!


class UserManager(UUIDIDMixin, BaseUserManager[User, uuid.UUID]):
    reset_password_token_secret = SECRET
    verification_token_secret = SECRET

    async def on_after_register(self, user: User, request: Optional[Request] = None):
        print(f"User {user.id} has registered.")

    async def on_after_forgot_password(
        self, user: User, token: str, request: Optional[Request] = None
    ):
        print(f"User {user.id} has forgot their password. Reset token: {token}")

    async def on_after_request_verify(
        self, user: User, token: str, request: Optional[Request] = None
    ):
        print(f"Verification requested for user {user.id}. Verification token: {token}")


async def get_user_manager(user_db=Depends(get_user_db)):
    yield UserManager(user_db)

import uuid

from fastapi_users import schemas


class UserRead(schemas.BaseUser[uuid.UUID]):
    pass


class UserCreate(schemas.BaseUserCreate):
    pass


class UserUpdate(schemas.BaseUserUpdate):
    pass

app = FastAPI()



import redis.asyncio

redis = redis.asyncio.from_url("redis://localhost:6379", decode_responses=True)

def get_redis_strategy() -> RedisStrategy:
    return RedisStrategy(redis, lifetime_seconds=3600)

cookie_transport = CookieTransport(cookie_max_age=3600)

auth_backend = AuthenticationBackend(
    name="redis",
    transport=cookie_transport,
    get_strategy=get_redis_strategy,
)



fastapi_users = FastAPIUsers(
    get_user_manager,
    [auth_backend],
)


@app.on_event('startup')
async def startup():
    await database.connect()


@app.on_event('shutdown')
async def shutdown():
    await database.disconnect()


app.include_router(
    fastapi_users.get_auth_router(cookie_authentication),
    prefix='/auth/redis',
    tags=['auth'],
)
# See https://fastapi-users.github.io/fastapi-users/configuration/routers/reset/
app.include_router(
    fastapi_users.get_register_router(), prefix='/auth', tags=['auth']
)
# OLD: app.include_router(
#     fastapi_users.get_reset_password_router(SECRET), prefix='/auth', tags=['auth'],
# )
app.include_router(
    fastapi_users.get_reset_password_router(), prefix='/auth', tags=['auth'],
)
app.include_router(fastapi_users.get_users_router(), prefix='/users', tags=['users'])

# ADDED:
if __name__ == '__main__':
    uvicorn.run(app, host='0.0.0.0', port=8000)
