from pyteal import Int, Seq, Subroutine, TealType, Txn
from lib.err import err_inited
from lib.storage import gget, gset
from lib.str import (
    bytes_empty,
    str_admin_addr,
    str_arc59_app_id,
    str_asa_id,
    str_contract_upgrade,
    str_delay_optin,
    str_fee_addr,
    str_fee_update,
    str_fee_update_max_delta,
    str_fee_update_period,
    str_lp_id,
    str_lp_type,
    str_lst_id,
    str_max_balance,
    str_noderunner_addr,
    str_noderunner_fee_bps,
    str_noderunner_fees,
    str_platform_fee_bps,
    str_platform_fees,
    str_protest_count,
    str_protest_sum,
    str_rate_precision,
    str_staked,
    str_tm2_app_id,
    str_upgrade_period,
    str_version,
)
from lib.utils import custom_assert


@Subroutine(TealType.none)
def create_storage():
    """
    Runs on app creation; Initializes global state
    """
    return Seq(
        custom_assert(gget(str_asa_id) == Int(0), err_inited),
        gset(str_version, Int(1)),
        gset(str_asa_id, Int(0)),
        gset(str_lst_id, Int(0)),
        gset(str_delay_optin, Int(0)),
        gset(str_staked, Int(0)),
        gset(str_platform_fees, Int(0)),
        gset(str_noderunner_fees, Int(0)),
        gset(str_platform_fee_bps, Int(0)),
        gset(str_noderunner_fee_bps, Int(0)),
        gset(str_admin_addr, Txn.sender()),
        gset(str_fee_addr, Txn.sender()),
        gset(str_noderunner_addr, Txn.sender()),
        gset(str_lp_type, bytes_empty),
        gset(str_lp_id, bytes_empty),
        gset(str_fee_update, bytes_empty),
        gset(str_contract_upgrade, bytes_empty),
        gset(str_protest_count, Int(0)),
        gset(str_protest_sum, Int(0)),
        gset(str_upgrade_period, Int(0)),
        gset(str_fee_update_period, Int(0)),
        gset(str_fee_update_max_delta, Int(0)),
        gset(str_max_balance, Int(0)),
        gset(str_rate_precision, Int(0)),
        gset(str_tm2_app_id, Int(0)),
        gset(str_arc59_app_id, Int(0)),
    )