from datetime import timedelta

from fastapi import APIRouter, Body, Depends
from starlette.exceptions import HTTPException
from starlette.status import HTTP_201_CREATED, HTTP_400_BAD_REQUEST

from app.core.config import ACCESS_TOKEN_EXPIRE_MINUTES
from app.core.jwt import create_access_token
from app.crud.shortcuts import check_free_username_and_email
from app.crud.user import create_user, get_user_by_email
from app.db.database import DataBase, get_database
from app.models.user import User, UserInCreate, UserInLogin, UserInResponse

router = APIRouter()


@router.post("/users/login", response_model=UserInResponse, tags=["authentication"])
async def login(
    user: UserInLogin = Body(..., embed=True), db: DataBase = Depends(get_database)
):
    async with db.pool.acquire() as conn:
        dbuser = await get_user_by_email(conn, user.email)
        if not dbuser or not dbuser.check_password(user.password):
            raise HTTPException(
                status_code=HTTP_400_BAD_REQUEST, detail="Incorrect email or password"
            )

        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        token = create_access_token(
            data={"username": dbuser.username}, expires_delta=access_token_expires
        )
        return UserInResponse(user=User(**dbuser.dict(), token=token))


@router.post(
    "/users",
    response_model=UserInResponse,
    tags=["authentication"],
    status_code=HTTP_201_CREATED,
)
async def register(
    user: UserInCreate = Body(..., embed=True), db: DataBase = Depends(get_database)
):
    async with db.pool.acquire() as conn:
        await check_free_username_and_email(conn, user.username, user.email)

        async with conn.transaction():
            dbuser = await create_user(conn, user)
            access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
            token = create_access_token(
                data={"username": dbuser.username}, expires_delta=access_token_expires
            )

            return UserInResponse(user=User(**dbuser.dict(), token=token))
