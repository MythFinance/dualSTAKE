from pyteal import (
    And,
    Balance,
    Bytes,
    Global,
    If,
    Int,
    MinBalance,
    Or,
    Return,
    ScratchVar,
    Seq,
    Subroutine,
    TealType,
    WideRatio,
)
from fee_update import maybe_apply_fee_update
from lib.err import err_not_implemented, err_no_pre
from lib.storage import gget, global_incr, gset
from lib.str import (
    str_asa_id,
    str_delay_optin,
    str_lp_type,
    str_noderunner_fee_bps,
    str_noderunner_fees,
    str_platform_fee_bps,
    str_platform_fees,
    str_rate_precision,
    str_staked,
)
from lib.swap import swap_tm2_algo_asa
from lib.utils import custom_assert, fail, get_asset_balance, send_asa

swap_enforced = ScratchVar(TealType.uint64, 255)
swap_enforced_magic_value = Int(255255255)


@Subroutine(TealType.uint64)
def pre_mint_or_redeem():
    """
    Pre mint or redeem: Apply any pending fee updates & swap if needed
    Must be called before any operation that calculates the rate
    Returns 1 if a swap was performed
    """
    return Seq(
        # Using scratch for runtime enforcement of must-swap-before-rate
        swap_enforced.store(swap_enforced_magic_value),
        # apply any pending fee updates
        maybe_apply_fee_update(),
        # if rewards have been paid out, swap them
        If(need_swap())
        .Then(
            # opt in if we are delaying optin
            maybe_optin(),
            Return(swap()),
        )
        .Else(
            Return(Int(0)),
        ),
    )


@Subroutine(TealType.uint64)
def swap():
    total_rewards_amt = ScratchVar(TealType.uint64)
    plat_fee_amt = ScratchVar(TealType.uint64)
    node_fee_amt = ScratchVar(TealType.uint64)
    swap_amt = ScratchVar(TealType.uint64)
    return Seq(
        # surplus = actual balance - expected balance
        # we subtract 3x min fees needed to swap
        total_rewards_amt.store(
            get_actual_expected_balance_delta() - Int(3) * Global.min_txn_fee(),
        ),
        # platform fees
        plat_fee_amt.store(
            gget(str_platform_fee_bps) * total_rewards_amt.load() / Int(10000)
        ),
        global_incr(str_platform_fees, plat_fee_amt.load()),
        # node runner fees
        node_fee_amt.store(
            gget(str_noderunner_fee_bps) * total_rewards_amt.load() / Int(10000)
        ),
        global_incr(str_noderunner_fees, node_fee_amt.load()),
        # swap amount: subtract fees
        swap_amt.store(
            total_rewards_amt.load() - node_fee_amt.load() - plat_fee_amt.load()
        ),
        If(gget(str_lp_type) == Bytes("tm2"))
        .Then(swap_tm2_algo_asa(swap_amt.load()))
        .Else(
            fail(err_not_implemented),
            Int(0),
        ),
    )


@Subroutine(TealType.none)
def maybe_optin():
    return If(gget(str_delay_optin)).Then(
        send_asa(
            Global.current_application_address(),
            gget(str_asa_id),
            Int(0),
            Global.min_txn_fee(),
        ),
        gset(str_delay_optin, Int(0)),
    )


@Subroutine(TealType.uint64)
def get_expected_balance():
    """
    The "equilibrium" balance of the contract. Staked ALGO + fees + minimum balance
    Used as baseline to determine "need to swap"
    """
    return (
        gget(str_staked)
        + gget(str_platform_fees)
        + gget(str_noderunner_fees)
        + get_min_balance()
    )


def get_min_balance():
    """
    Get minimum balance, factoring in delayed optin fee of 0.1A + 1 txn fee
    """
    return MinBalance(Global.current_application_address()) + If(
        gget(str_delay_optin)
    ).Then(Global.asset_opt_in_min_balance() + Global.min_txn_fee()).Else(Int(0))



@Subroutine(TealType.uint64)
def get_actual_expected_balance_delta():
    """
    Returns balance surplus, or zero if <= expected
    """
    actual = ScratchVar(TealType.uint64)
    expected = ScratchVar(TealType.uint64)
    return Seq(
        actual.store(get_actual_balance()),
        expected.store(get_expected_balance()),
        If(actual.load() > expected.load())
        .Then(actual.load() - expected.load())
        .Else(Int(0)),
    )


def need_swap():
    """
    Calculate if we need to swap - if escrow balance surplus exceeds 1000x min fees - 1 ALGO currently
    """
    return And(
        Or(
            # here we are guarding against forcing an early optin despite delay_optin
            # if delay_optin is 1: only swap when we are over the payouts_min_balance
            gget(str_delay_optin) == Int(0),
            get_actual_balance() > Global.payouts_min_balance(),
        ),
        gget(str_staked) > Int(0),
        get_actual_expected_balance_delta() > Global.min_txn_fee() * Int(1000),  # 1 ALGO at 0.001 min fee
    )


def _get_rate():
    """
    internal method to get rate of ASA to ALGO. Default 1e8 = 1.0 (disregarding decimals)
    """
    return Seq(
        # This is a runtime enforcement that the pre_mint_or_redeem method is always called upstream
        # before calculating this rate
        custom_assert(swap_enforced.load() == swap_enforced_magic_value, err_no_pre),
        If(gget(str_staked) == Int(0))
        .Then(
            Int(0),
        )
        .Else(
            WideRatio(
                [gget(str_rate_precision), get_paired_asa_balance()],
                [gget(str_staked)],
            ),
        ),
    )


def get_actual_balance():
    return Balance(Global.current_application_address())


def get_paired_asa_balance():
    return get_asset_balance(gget(str_asa_id))