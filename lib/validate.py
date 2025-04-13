from pyteal import (
    Global,
    Gtxn,
    Int,
    Return,
    Seq,
    Subroutine,
    TealType,
    Txn,
    TxnType,
)
from lib.err import err_invalid_asset_id, err_min_payment, err_payment_validation_failed
from lib.utils import custom_assert


def _validate_asa_payment(transaction, asset_id):
    return Seq(
        custom_assert(
            transaction.type_enum() == TxnType.AssetTransfer,
            err_payment_validation_failed,
        ),
        custom_assert(
            transaction.asset_receiver() == Global.current_application_address(),
            err_payment_validation_failed,
        ),
        custom_assert(transaction.xfer_asset() == asset_id, err_invalid_asset_id),
        transaction.asset_amount(),
    )


@Subroutine(TealType.uint64)
def validate_asa_payment_after(txn_offset, asset_id):
    return _validate_asa_payment(Gtxn[Txn.group_index() + txn_offset], asset_id)


@Subroutine(TealType.uint64)
def validate_asa_payment_before(txn_offset, asset_id):
    return _validate_asa_payment(Gtxn[Txn.group_index() - txn_offset], asset_id)


@Subroutine(TealType.uint64)
def validate_algo_payment_after(txn_offset):
    transaction = Gtxn[Txn.group_index() + txn_offset]
    return Seq(
        custom_assert(
            transaction.type_enum() == TxnType.Payment, err_payment_validation_failed
        ),
        custom_assert(
            transaction.receiver() == Global.current_application_address(),
            err_payment_validation_failed,
        ),
        custom_assert(transaction.amount() >= Int(1000000), err_min_payment),
        Return(transaction.amount()),
    )
