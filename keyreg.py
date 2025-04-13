from pyteal import (
    AccountParamObject,
    Global,
    If,
    InnerTxnBuilder,
    Int,
    Seq,
    TxnField,
    TxnType,
    abi,
)
from lib.decorators import fee_admin_or_node_runner_only
from lib.err import err_ie, err_not_ie, err_payment_amount_failed
from lib.events import emit_event
from lib.str import byte_zero, byte_one
from lib.utils import custom_assert
from lib.validate import validate_algo_payment_after
from router import router


@router.method
@fee_admin_or_node_runner_only
def keyreg_online(
    selection_key: abi.DynamicBytes,
    voting_key: abi.DynamicBytes,
    sp_key: abi.DynamicBytes,
    first_round: abi.Uint64,
    last_round: abi.Uint64,
    key_dilution: abi.Uint64,
    fee: abi.Uint64,
):
    """
    Fee admin or node runner only. Send keyreg online.
    Required payment if fee is not zero. Fee must be 2A if escrow is not account eligible, otherwise zero (paid by outer)
    Fee amount is validated against Global eligibility fee parameter
    """
    eligible = AccountParamObject(
        Global.current_application_address()
    ).incentive_eligible()
    return Seq(
        eligible,
        # if fee required, next txn must be payment
        If(fee.get() > Int(0)).Then(
            custom_assert(
                validate_algo_payment_after(Int(1)) == fee.get(),
                err_payment_amount_failed,
            )
        ),
        # if aligible already, enforce zero fees. inner fee must be paid by caller
        If(eligible.value() == Int(1))
        .Then(
            emit_event(
                "keyreg_online(uint8)",  # arc28: incentive_eligible
                byte_zero,
            ),
            custom_assert(fee.get() == Int(0), err_ie),
        )
        .Else(
            # if not eligible, enforce fee equal to proto payouts_go_online_fee, currently 2A
            custom_assert(fee.get() == Global.payouts_go_online_fee(), err_not_ie),
            emit_event(
                "keyreg_online(uint8)",  # arc28: incentive_eligible
                byte_one,
            ),
        ),
        # send keyreg
        InnerTxnBuilder.Execute(
            {
                TxnField.type_enum: TxnType.KeyRegistration,
                TxnField.selection_pk: selection_key.get(),
                TxnField.vote_pk: voting_key.get(),
                TxnField.state_proof_pk: sp_key.get(),
                TxnField.vote_first: first_round.get(),
                TxnField.vote_last: last_round.get(),
                TxnField.vote_key_dilution: key_dilution.get(),
                TxnField.fee: fee.get(),
            }
        ),
    )


@router.method
@fee_admin_or_node_runner_only
def keyreg_offline():
    """
    Fee admin or noderunner only. Send keyreg offline for an escrow account
    """
    return Seq(
        emit_event(
            "keyreg_offline()",  # arc28
        ),
        InnerTxnBuilder.Execute(
            {
                TxnField.type_enum: TxnType.KeyRegistration,
                TxnField.fee: Int(0),
            }
        ),
    )
