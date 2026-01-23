from fastapi import  APIRouter,HTTPException,Query
from app.crud import crud_player
from app.db.session import SessionDep
from app.models import Player, PlayerPublic, PlayerCreate

router = APIRouter()


@router.get("/")
async def get_players(session: SessionDep,
                      page: int = Query(0, ge=1),
                      page_size: int = Query(8, ge=1, le=100),
                      ):

    return crud_player.get_players_paginated(session=session, page=page, page_size=page_size)

@router.get("/{name}")
async def get_user_by_name(session: SessionDep, name: str):

    return crud_player.get_player_by_name(session=session, name=name)

@router.post("/", response_model=PlayerPublic)
async def register( session: SessionDep , player_in: PlayerCreate):
    player = crud_player.get_player_by_name(session=session, name=player_in.name)
    if player:
       raise HTTPException(status_code=400, detail="Player already exists")
    return crud_player.create_player(session, player_in)