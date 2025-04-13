from pyteal import (
    Global,
    If,
    Int,
    Seq,
    Txn,
)
from lib.decorators import admin_only
from lib.err import err_stake_exists, err_noderunner_fees_exists
from lib.storage import gget
from lib.str import str_asa_id, str_noderunner_fees, str_staked
from lib.utils import closeout_algo, closeout_asa, custom_assert, delete_lst_asset, is_opted_in


@admin_only
def delete_app():
    return Seq(
        # no staked, no fees
        custom_assert(gget(str_staked) == Int(0), err_stake_exists),
        # no uncollected noderunner fees
        custom_assert(gget(str_noderunner_fees) == Int(0), err_noderunner_fees_exists),
        # LST balance should always be == staked, but if not this will fail
        delete_lst_asset(),
        # Close out any remaining ASA dust to caller
        If(is_opted_in(Global.current_application_address(), gget(str_asa_id))).Then(
            closeout_asa(Txn.sender(), gget(str_asa_id)),
        ),
        # Close out remaining ALGO to caller
        closeout_algo(Txn.sender()),
    )