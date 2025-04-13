from pyteal import (
    App,
    Btoi,
    Global,
    If,
    Int,
    Itob,
    Pop,
    ScratchVar,
    Seq,
    Subroutine,
    TealType,
    Txn,
    WideRatio,
    abi,
)
from lib.arc59 import send_algo_and_asa
from lib.decorators import fee_admin_only
from lib.err import (
    err_zero,
    err_early,
    err_box_del,
    err_no_upgrade,
    err_upgrade,
    err_min_protest,
    err_no_protest,
)
from lib.events import emit_event
from lib.rate import _get_rate, pre_mint_or_redeem
from lib.storage import gget, global_decr, global_incr
from lib.str import (
    bytes_empty,
    byte_zero,
    byte_one,
    str_asa_id,
    str_contract_upgrade,
    str_lst_id,
    str_protest_count,
    str_protest_sum,
    str_rate_precision,
    str_staked,
)
from lib.utils import custom_assert, get_asset_balance, get_upgrade_maturity_ts, send_algo, send_asa
from lib.validate import validate_asa_payment_before
from router import router


@router.method
def protest_stake():
    """
    public method. locks dualSTAKE LST stake on the contract as "upgrade protest".
    This blocks upgrading unless it is dissolved (redeemed & returned to user)
    The upgrade can also be cancelled, whereafter the dualSTAKE tokens can be returned to the user unchanged
    """
    amount = ScratchVar(TealType.uint64)
    return Seq(
        # reject if there is no upgrade proposed
        custom_assert(gget(str_contract_upgrade) != bytes_empty, err_no_upgrade),
        # validate received LST asset & get amount
        amount.store(validate_asa_payment_before(Int(1), gget(str_lst_id))),
        # assert min amount protesting
        custom_assert(
            amount.load() >= Int(1000000), err_min_protest # 1 ALGO equivalent minimum. to cover arc59 fees if necessary 
        ),
        If(is_user_protesting(Txn.sender()))
        .Then(
            # increase existing protesting stake
            set_user_protesting_stake(
                Txn.sender(), get_user_protesting_stake(Txn.sender()) + amount.load()
            ),
        )
        .Else(
            # new protest
            # increase the number of protesting accounts by one
            global_incr(str_protest_count, Int(1)),
            # set protesting stake on box
            set_user_protesting_stake(
                Txn.sender(),
                amount.load(),
            ),
        ),
        emit_event(
            "protest(uint64)",  # arc28: lst_amount
            Itob(amount.load()),
        ),
        # increase the sum of protesting stake (total amount)
        global_incr(str_protest_sum, amount.load()),
    )


@router.method
def unprotest_stake():
    """
    public method. revoke protesting stake for self. Returns dualSTAKE tokens to user who protested with them.
    """
    return internal_unprotest_stake(Txn.sender(), Int(1))


@router.method
@fee_admin_only
def admin_unprotest_stake(user: abi.Address):
    """
    fee admin method. callable when there is no upgrade scheduled. returns the protesting dualSTAKE tokens to user $user. If the user has opted out of the dualSTAKE asset, this fails and the user can undo the protest stake themselves.
    """
    return Seq(
        custom_assert(gget(str_contract_upgrade) == bytes_empty, err_upgrade),
        internal_unprotest_stake(user.get(), Int(0)),
    )


@router.method
@fee_admin_only
def dissolve_protesting_stake(user: abi.Address):
    """
    fee admin method. called before upgrading to dissolve protesting stake for user $user. Redeems & returns ALGO and ASA to user.
    If the user has opted out of the ASA: 1) ARC59 asset inbox is used to send the ASA and 2) the transaction and MBR fees for asset inbox are subtractd from the ALGO amount.
    """
    amount = ScratchVar(TealType.uint64)
    return Seq(
        # swap if needed
        Pop(pre_mint_or_redeem()),
        # ensure upgrade maturity is reached
        custom_assert(get_upgrade_maturity_ts() < Global.latest_timestamp(), err_early),
        # store protesting stake amount in scratch
        # fails if user is not protesting
        amount.store(get_user_protesting_stake(user.get())),
        # redeem method: sends algo+asa back to user
        internal_redeem(user.get(), amount.load(), Global.min_txn_fee()),
        # adjust state
        internal_unprotest_adjust_state(user.get(), amount.load()),
    )


@Subroutine(TealType.none)
def internal_unprotest_stake(user, user_initiated):
    """
    Internal function undo protesting stake
    """
    amount = ScratchVar(TealType.uint64)
    return Seq(
        # return protesting LST tokens to caller. does full amount. get_user_protesting_stake does validation
        amount.store(get_user_protesting_stake(user)),
        # If user has opted out, this will fail
        # This is fine as we would have to dissolve the ALGO part to send via ARC59
        # User can cancel themselves and pay for fees
        send_asa(user, gget(str_lst_id), amount.load(), Int(0)),
        # adjust state
        internal_unprotest_adjust_state(user, amount.load()),
        emit_event(
            "unprotest(uint64, uint8)",  # arc28: lst_amount, user_initiated
            Itob(amount.load()),
            If(user_initiated).Then(byte_one).Else(byte_zero)
        ),
    )


@Subroutine(TealType.none)
def internal_unprotest_adjust_state(user, amount):
    """
    Internal function adjust state after unprotesting
    """
    return Seq(
        # adjust global
        global_decr(str_protest_count, Int(1)),
        global_decr(str_protest_sum, amount),
        # delete user protest box
        custom_assert(App.box_delete(user), err_box_del),
    )


@Subroutine(TealType.none)
def internal_redeem(user, amount, fees):
    """
    Internal function performing LST->(ALGO+ASA) redemptions. Used when users redeem or admins dissolve protesting stake
    """
    rate = ScratchVar(TealType.uint64)
    asa_amount = ScratchVar(TealType.uint64)
    return Seq(
        custom_assert(amount, err_zero),
        rate.store(_get_rate()),
        emit_event(
            "rate(uint64)",  # arc28: rate
            Itob(rate.load()),
        ),
        If(rate.load() > Int(0))
        .Then(
            asa_amount.store(
                WideRatio([amount, rate.load()], [gget(str_rate_precision)])
            ),
            send_algo_and_asa(
                user,
                amount,
                gget(str_asa_id),
                asa_amount.load(),
                fees,
            ),
        )
        .Else(
            asa_amount.store(Int(0)),
                send_algo(user, amount - fees, fees),
        ),
        emit_event(
            "redeem(uint64,uint64)",  # arc28: algo_amount, asa_amount
            Itob(amount),
            Itob(asa_amount.load()),
        ),
        emit_event(
            "asa_balance(uint64)",  # arc28: asa_balance
            Itob(get_asset_balance(gget(str_asa_id))),
        ),
        # mark removed algo stake
        global_decr(str_staked, amount),
    )


@Subroutine(TealType.uint64)
def get_user_protesting_stake(user):
    return Seq(
        box := App.box_get(user),
        custom_assert(box.hasValue(), err_no_protest),
        Btoi(box.value()),
    )

# Following functions are too small to bother doing as subroutines
def set_user_protesting_stake(user, stake):
    return App.box_put(user, Itob(stake))


def is_user_protesting(user):
    return Seq(box := App.box_length(user), box.hasValue())
