from fastapi import APIRouter, Depends, HTTPException

from app.core.error import GameError
from app.dependencies import get_current_user
from app.models import SpotContract, SpotContractCreate, PlayerPublic, TransactionActionType, ContractStatus
from app.db.session import SessionDep
from datetime import datetime
from sqlmodel import select, or_
from app.crud import crud_inventory
from app.service.accounting import AccountingService
from app.service.inventory import InventoryService
import logging

router = APIRouter()


@router.post("/create")
async def create_contract(session: SessionDep,
                          contract_create: SpotContractCreate,
                          player_in: PlayerPublic = Depends(get_current_user)):
    if contract_create.receiver_id == player_in.id:
        raise HTTPException(status_code=400, detail="Cannot create contract to yourself")
    new_contract = SpotContract(
        **contract_create.model_dump()
    )
    new_contract.sender_id = player_in.id
    session.add(new_contract)
    session.flush()

    # 2. 根据生成的 ID 补全 contract_no
    date_str = datetime.now().strftime("%Y%m%d")
    new_contract.contract_no = f"SPOT-{date_str}-{new_contract.id:05d}"


    session.commit()
    session.refresh(new_contract)
    return new_contract


@router.get("/")
async def get_pending_contracts(session: SessionDep,
                                player_in: PlayerPublic = Depends(get_current_user)):
    statement = select(SpotContract).where(
        SpotContract.status == "pending",
        or_(
            SpotContract.receiver_id == player_in.id,
            SpotContract.sender_id == player_in.id
        )
    )

    return session.exec(statement).all()


@router.post("/{contract_id}/accept")
async def accept_contract(contract_id: int, session: SessionDep,
                          player_in: PlayerPublic = Depends(get_current_user)):
    # --- 核心经济逻辑：原子化交易 ---
    # 1. 检查买家（当前用户）余额
    # 2. 检查卖家库存（如果发起合同时没扣除的话）
    # 3. 执行转账：buyer.money -= total; seller.money += total
    # 4. 执行转货：buyer.stock += qty; seller.stock -= qty
    try:
        contract = session.get(SpotContract, contract_id)
        # 接收方是卖方，价钱，扣除库存
        AccountingService.change_cash(session, contract.receiver_id, contract.total_amount,
                                      TransactionActionType.CONTRACT_REVENUE, contract_id)
        InventoryService.change_resource(session, contract.receiver_id,
                                         contract.resource_id, -contract.quantity)

        # 发起方是买房， 扣钱，增加库存
        AccountingService.change_cash(session, contract.sender_id, -contract.total_amount,
                                      TransactionActionType.CONTRACT_COST, contract_id)
        InventoryService.change_resource(session, contract.sender_id,
                                         contract.resource_id, contract.quantity)


        contract.status = ContractStatus.SIGNED
        contract.signed_at = datetime.now()
        session.commit()
        session.refresh(contract)
    except GameError as e:
        raise HTTPException(status_code=400, detail=e.message)
    except Exception as e:
        logging.error(e)
        raise HTTPException(status_code=400, detail=str(e))

    return contract


@router.post("/{contract_id}/reject")
async def reject_contract(contract_id: int, session: SessionDep,
                          player_in: PlayerPublic = Depends(get_current_user)):
    contract = session.exec(
        select(SpotContract).where(
            SpotContract.id == contract_id,
            SpotContract.receiver_id == player_in.id
        )
    ).first()
    contract.status = ContractStatus.REJECTED
    session.add(contract)
    session.commit()
    session.refresh(contract)
    return contract

@router.post("/{contract_id}/cancel")
async def cancel_contract(contract_id: int, session: SessionDep,
                          player_in: PlayerPublic = Depends(get_current_user)):
    contract = session.exec(
        select(SpotContract).where(
            SpotContract.id == contract_id,
            SpotContract.sender_id == player_in.id
        )
    ).first()
    contract.status = ContractStatus.CANCELLED
    session.add(contract)
    session.commit()
    session.refresh(contract)
    return contract