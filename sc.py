from pyteal import (
    AccountParamObject,
    Approve,
    AssetParam,
    Balance,
    Global,
    If,
    Int,
    Itob,
    Pop,
    ScratchVar,
    Seq,
    TealType,
    Txn,
    VoterParamObject,
    WideRatio,
    abi,
)
from admin import (
    change_admin_1,
    change_admin_2,
    change_feeaddr,
    change_noderunner,
    configure,
)
from fee_update import maybe_apply_fee_update, queue_update_fees, reset_update_fees
from fees import withdraw_node_runner_fees, withdraw_platform_fees
from keyreg import keyreg_offline, keyreg_online
from lib.decorators import ready
from lib.events import emit_event
from lib.err import err_max_stake_exceeded, err_asa_rate, err_no_swap, err_swap_fail
from lib.rate import (
    _get_rate,
    get_asset_balance,
    maybe_optin,
    need_swap,
    pre_mint_or_redeem,
    swap,
)
from lib.storage import gget, global_incr
from lib.str import str_asa_id, str_lst_id, str_max_balance, str_rate_precision, str_staked
from lib.utils import custom_assert, send_asa
from lib.validate import (
    validate_algo_payment_after,
    validate_asa_payment_after,
    validate_asa_payment_before,
)
from redeem_protest import (
    admin_unprotest_stake,
    dissolve_protesting_stake,
    internal_redeem,
    protest_stake,
    unprotest_stake,
)
from router import router
from upgrade import queue_upgrade, reset_upgrade

# Listing ABI methods here so they are not marked as unused variables...
withdraw_node_runner_fees
withdraw_platform_fees
queue_update_fees
reset_update_fees
configure
change_admin_1
change_admin_2
change_feeaddr
change_noderunner
protest_stake
unprotest_stake
admin_unprotest_stake
dissolve_protesting_stake
queue_upgrade
reset_upgrade
keyreg_offline
keyreg_online


@router.method
@ready
def mint():
    """
    Public method. Mint dualSTAKE lst
    NEXT transaction in group must be payment in ALGO
    if rate != 0, 2 txns after must be payment in ASA
    will swap and apply fee updates if needed
    sends dualSTAKE tokens to caller
    """
    amount = ScratchVar(TealType.uint64)
    rate = ScratchVar(TealType.uint64)
    pay_txn_offset = Int(1)
    asa_txn_offset = Int(2)
    asa_amount_required = ScratchVar(TealType.uint64)
    asa_amount_received = ScratchVar(TealType.uint64)
    return Seq(
        Pop(pre_mint_or_redeem()),
        amount.store(validate_algo_payment_after(pay_txn_offset)),
        # check that deposit will not put us over balance
        custom_assert(
            Balance(Global.current_application_address()) + amount.load()
            <= gget(str_max_balance),
            err_max_stake_exceeded,
        ),
        rate.store(_get_rate()),
        emit_event(
            "rate(uint64)",  # arc28: rate
            Itob(rate.load()),
        ),
        If(rate.load() > Int(0))
        .Then(
            asa_amount_required.store(
                WideRatio(
                    [amount.load(), rate.load()],
                    [gget(str_rate_precision)],
                )
            ),
            # WARNING Intentionally using after-positioning for the asa payment
            # Currently nothing else expects an ASA payments at (previous position)
            # If this changes then we introduced a vulnerability
            # As the ASA payment could double for this call and the future call that validates at position-1
            asa_amount_received.store(
                validate_asa_payment_after(asa_txn_offset, gget(str_asa_id))
            ),
            custom_assert(
                asa_amount_required.load() <= asa_amount_received.load(),
                err_asa_rate,
            ),
        )
        .Else(
            asa_amount_received.store(Int(0)),
            asa_amount_required.store(Int(0)),
        ),
        emit_event(
            "mint(uint64,uint64,uint64)",  # arc28: algo_amount, asa_amount_required, asa_amount_received
            Itob(amount.load()),
            Itob(asa_amount_required.load()),
            Itob(asa_amount_received.load()),
        ),
        emit_event(
            "asa_balance(uint64)",  # arc28: asa_balance
            Itob(get_asset_balance(gget(str_asa_id))+asa_amount_received.load()),
        ),
        global_incr(str_staked, amount.load()),
        send_asa(Txn.sender(), gget(str_lst_id), amount.load(), Int(0)),
    )


@router.method
@ready
def redeem():
    """
    Public method. Redeem dualSTAKE tokens back to ALGO+ASA.
    dualSTAKE:ALGO is always 1:1
    dualSTAKE:ASA is (ASA balance):(global staked)
    will swap and apply fee updates if needed
    """
    return Seq(
        # swap if needed, update fees if needed
        Pop(pre_mint_or_redeem()),
        internal_redeem(
            Txn.sender(),
            validate_asa_payment_before(Int(1), gget(str_lst_id)),
            Int(0),
        ),
    )


@router.method
@ready
def get_rate(*, output: abi.Uint64):
    """
    Public method. Returns the current rate as ABI uint64:
        1e8 * (ASA Balance) / (global staked)
    Returns zero if staked == 0
    will swap and apply fee updates if needed
    """
    return Seq(
        Pop(pre_mint_or_redeem()),
        output.set(_get_rate()),
    )


# Enough results to show an index entry/listing page
class ContractListing(abi.NamedTuple):
    rate: abi.Field[abi.Uint64]
    algo_balance: abi.Field[abi.Uint64]
    asa_balance: abi.Field[abi.Uint64]

    staked: abi.Field[abi.Uint64]

    lst_id: abi.Field[abi.Uint64]
    lst_name: abi.Field[abi.String]

    asa_id: abi.Field[abi.Uint64]
    asa_name: abi.Field[abi.String]
    asa_unit_name: abi.Field[abi.String]
    asa_decimals: abi.Field[abi.Uint16]

    need_swap: abi.Field[abi.Bool]
    incentive_eligible: abi.Field[abi.Bool]
    is_online: abi.Field[abi.Bool]


@router.method
@ready
def get_contract_listing(*, output: ContractListing):
    """
    Public method. Returns ABI struct ContractListing:
        rate (see get_rate)
        escrow algo balance
        escrow asa balance
        staked balance
        dualstake token ID
        dualstake asset name
        asa asset ID
        asa asset name
        asa unit name
        asa decimals
        need_swap
        incentive_eligible
        is_online
    will swap and apply fee updates if needed
    """
    rate = abi.Uint64()
    algo_balance = abi.Uint64()
    asa_balance = abi.Uint64()

    staked = abi.Uint64()

    dualstake_id = abi.Uint64()
    dualstake_name = abi.String()

    asa_id = abi.Uint64()
    asa_name = abi.String()
    asa_unit_name = abi.String()
    asa_decimals = abi.Uint16()

    will_swap = abi.Bool()
    ie = abi.Bool()
    is_online = abi.Bool()

    lst_asset_param_name = AssetParam.name(gget(str_lst_id))
    asa_asset_param_name = AssetParam.name(gget(str_asa_id))
    asa_asset_param_unit_name = AssetParam.unitName(gget(str_asa_id))
    asa_asset_decimal_param = AssetParam.decimals(gget(str_asa_id))

    acct_param_eligible = AccountParamObject(
        Global.current_application_address()
    ).incentive_eligible()
    # Using this as a proxy for online-ness; 320-round lag.
    voter_param_eligible = VoterParamObject(
        Global.current_application_address()
    ).incentive_eligible()
    return Seq(
        lst_asset_param_name,
        asa_asset_param_name,
        asa_asset_param_unit_name,
        asa_asset_decimal_param,
        acct_param_eligible,
        voter_param_eligible,
        algo_balance.set(Balance(Global.current_application_address())),
        asa_balance.set(get_asset_balance(gget(str_asa_id))),
        staked.set(gget(str_staked)),
        dualstake_id.set(gget(str_lst_id)),
        dualstake_name.set(lst_asset_param_name.value()),
        asa_id.set(gget(str_asa_id)),
        asa_name.set(asa_asset_param_name.value()),
        asa_unit_name.set(asa_asset_param_unit_name.value()),
        asa_decimals.set(asa_asset_decimal_param.value()),
        will_swap.set(pre_mint_or_redeem()),
        rate.set(_get_rate()),
        ie.set(acct_param_eligible.value()),
        is_online.set(voter_param_eligible.hasValue()),
        output.set(
            rate,
            algo_balance,
            asa_balance,
            staked,
            dualstake_id,
            dualstake_name,
            asa_id,
            asa_name,
            asa_unit_name,
            asa_decimals,
            will_swap,
            ie,
            is_online,
        ),
    )


class StateResult(abi.NamedTuple):
    rate: abi.Field[abi.Uint64]
    algo_balance: abi.Field[abi.Uint64]
    asa_balance: abi.Field[abi.Uint64]

@router.method
@ready
def get_rate_and_balances(*, output: StateResult):
    """
    Public method. Returns ABI tuple[3]:
        rate (see get_rate)
        escrow algo balance
        escrow asa balance
    will swap and apply fee updates if needed
    """
    rate = abi.Uint64()
    algo_balance = abi.Uint64()
    asa_balance = abi.Uint64()
    return Seq(
        Pop(pre_mint_or_redeem()),
        rate.set(_get_rate()),
        algo_balance.set(Balance(Global.current_application_address())),
        asa_balance.set(get_asset_balance(gget(str_asa_id))),
        output.set(rate, algo_balance, asa_balance),
    )


@router.method
@ready
def get_need_swap(*, output: abi.Bool):
    """
    Public method. Returns whether the contract thinks it needs to swap
    """
    return Seq(output.set(need_swap()))


@router.method
@ready
def swap_or_fail():
    """
    Public method. Perform swap or fail
    """
    return Seq(
        maybe_apply_fee_update(),
        maybe_optin(),
        custom_assert(need_swap(), err_no_swap),
        custom_assert(swap(), err_swap_fail),
    )


@router.method
def nullun():
    """
    Public empty method for opcode budget increase
    """
    return Approve()


def get_contracts():
    return router.compile_program(version=11)
