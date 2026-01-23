
from datetime import datetime
from typing import Optional, List, Sequence
from sqlmodel import Session, select, func, and_
from datetime import datetime
from typing import Optional, List, Sequence
from sqlmodel import Session, select, func, and_
from app.models import Asset, PlayerAsset  # Import PlayerAsset model
from app.db.session import SessionDep


def create_asset(db: SessionDep, asset: Asset) -> Asset:
    db.add(asset)
    db.commit()
    db.refresh(asset)
    return asset


def create_player_asset(db: SessionDep, player_asset: PlayerAsset) -> PlayerAsset:
    db.add(player_asset)
    db.commit()
    db.refresh(player_asset)
    return player_asset


def get_asset_by_id(db: SessionDep, asset_id: int) -> Optional[Asset]:
    return db.get(Asset, asset_id)


def get_player_asset_by_id(db: SessionDep, player_asset_id: int) -> Optional[PlayerAsset]:
    return db.get(PlayerAsset, player_asset_id)


def get_all_assets(db: SessionDep) -> List[Asset]:
    return db.exec(select(Asset)).all()


def get_all_player_assets(db: SessionDep) -> List[PlayerAsset]:
    return db.exec(select(PlayerAsset)).all()


def update_asset(db: SessionDep, asset_id: int, updated_asset: Asset) -> Optional[Asset]:
    existing_asset = db.get(Asset, asset_id)
    if existing_asset:
        for key, value in updated_asset.dict(exclude_unset=True).items():
            setattr(existing_asset, key, value)
        db.add(existing_asset)
        db.commit()
        db.refresh(existing_asset)
        return existing_asset
    return None


def update_player_asset(db: SessionDep, player_asset_id: int, updated_player_asset: PlayerAsset) -> Optional[
    PlayerAsset]:
    existing_player_asset = db.get(PlayerAsset, player_asset_id)
    if existing_player_asset:
        for key, value in updated_player_asset.dict(exclude_unset=True).items():
            setattr(existing_player_asset, key, value)
        db.add(existing_player_asset)
        db.commit()
        db.refresh(existing_player_asset)
        return existing_player_asset
    return None


def delete_asset(db: SessionDep, asset_id: int) -> bool:
    asset = db.get(Asset, asset_id)
    if asset:
        db.delete(asset)
        db.commit()
        return True
    return False


def delete_player_asset(db: SessionDep, player_asset_id: int) -> bool:
    player_asset = db.get(PlayerAsset, player_asset_id)
    if player_asset:
        db.delete(player_asset)
        db.commit()
        return True
    return False
