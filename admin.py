from pyteal import (
    AppParamObject,
    Bytes,
    Concat,
    Global,
    Or,
    Gtxn,
    If,
    ImportScratchValue,
    InnerTxnBuilder,
    Int,
    Itob,
    MethodSignature,
    Not,
    OnComplete,
    Pop,
    ScratchVar,
    Seq,
    TealType,
    Txn,
    TxnField,
    TxnType,
    abi,
)
from lib.decorators import (
    admin_only,
    admin_or_fee_admin_only,
    fee_admin_or_node_runner_only,
    fee_admin_only,
)
from lib.err import (
    err_configured,
    err_unauthorized,
    err_max_stake_exceeded,
    err_noderunner_fees_not_zero,
    err_chadm_txn_type,
    err_chadm_app_id,
    err_chadm_app_arg,
    err_chadm_oc,
    err_chadm_not_called_by_new_admin,
)
from lib.rate import pre_mint_or_redeem
from lib.storage import gget, gset
from lib.str import (
    str_admin_addr,
    str_arc59_app_id,
    str_asa_id,
    str_delay_optin,
    str_fee_addr,
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
    str_rate_precision,
    str_tm2_app_id,
    str_upgrade_period,
)
from lib.utils import create_lst_asset, custom_assert, send_asa
from router import router


@router.method
@admin_or_fee_admin_only
def configure(
    asa_id: abi.Uint64,
    lp_type: abi.DynamicBytes,
    lp_id: abi.DynamicBytes,
    platform_fee_bps: abi.Uint64,
    noderunner_fee_bps: abi.Uint64,
    admin_addr: abi.Address,
    fee_admin_addr: abi.Address,
    noderunner_addr: abi.Address,
    delay_optin: abi.Bool,
    max_balance: abi.Uint64,
    upgrade_period: abi.Uint64,
    fee_update_period: abi.Uint64,
    fee_update_max_delta: abi.Uint64,
    rate_precision: abi.Uint64,
    tm2_app_id: abi.Uint64,
    arc59_app_id: abi.Uint64,
):
    """
    Admin or fee admin method. Bootstrap; configure global storage except LST ID.
    """
    return Seq(
        custom_assert(gget(str_lst_id) == Int(0), err_configured),
        gset(str_asa_id, asa_id.get()),
        gset(str_lp_type, lp_type.get()),
        gset(str_lp_id, lp_id.get()),
        gset(str_platform_fee_bps, platform_fee_bps.get()),
        gset(str_noderunner_fee_bps, noderunner_fee_bps.get()),
        gset(str_admin_addr, admin_addr.get()),
        gset(str_fee_addr, fee_admin_addr.get()),
        gset(str_noderunner_addr, noderunner_addr.get()),
        gset(str_delay_optin, delay_optin.get()),
        gset(str_upgrade_period, upgrade_period.get()),
        gset(str_fee_update_period, fee_update_period.get()),
        gset(str_fee_update_max_delta, fee_update_max_delta.get()),
        gset(str_max_balance, max_balance.get()),
        gset(str_rate_precision, rate_precision.get()),
        gset(str_tm2_app_id, tm2_app_id.get()),
        gset(str_arc59_app_id, arc59_app_id.get()),
        # opt in to ASA ID if not deferring
        If(Not(delay_optin.get())).Then(
            send_asa(
                Global.current_application_address(),
                asa_id.get(),
                Int(0),
                Global.min_txn_fee(),
            ),
        ),
    )

@router.method
def configure2(
    lst_asa_name: abi.DynamicBytes,
    lst_unit_name: abi.DynamicBytes,
    lst_url: abi.DynamicBytes,
):
    caller_creator = AppParamObject(Global.caller_app_id()).creator_address()
    """
    Admin method. Also callable by applications created by admin.
    Create LST and implicitly mark contract as ready
    """
    return Seq(
        custom_assert(gget(str_lst_id) == Int(0), err_configured),
        custom_assert(Or(
            Txn.sender() == gget(str_admin_addr),
            Seq(
                caller_creator,
                caller_creator.value() == gget(str_admin_addr),
            )
        ), err_unauthorized),
        # create LST asset
        gset(
            str_lst_id,
            create_lst_asset(lst_asa_name.get(), lst_unit_name.get(), lst_url.get()),
        ),
    )

@router.method
@admin_only
def change_admin_1(new_admin: abi.Address):
    """
    admin method. first of 2-step admin change process.
    """
    admin = ScratchVar(TealType.bytes, 13)
    return admin.store(new_admin.get())


@router.method
def change_admin_2():
    """
    public method. second of 2-step admin change process. called by new admin in atomic group after change_admin_1
    """
    prev_txn = Gtxn[Txn.group_index() - Int(1)]
    # Load new admin stored in scratch var 13 by change_admin_1
    new_admin = ImportScratchValue(0, 13)
    return Seq(
        custom_assert(
            prev_txn.type_enum() == TxnType.ApplicationCall, err_chadm_txn_type
        ),
        custom_assert(prev_txn.on_completion() == OnComplete.NoOp, err_chadm_oc),
        custom_assert(
            prev_txn.application_id() == Global.current_application_id(),
            err_chadm_app_id,
        ),
        custom_assert(
            prev_txn.application_args[0]
            == MethodSignature("change_admin_1(address)void"),
            err_chadm_app_arg,
        ),
        custom_assert(Txn.sender() == new_admin, err_chadm_not_called_by_new_admin),
        gset(str_admin_addr, new_admin),
    )


@router.method
@fee_admin_or_node_runner_only
def change_noderunner(new_noderunner: abi.Address):
    """
    fee admin/node runner method. change node runner address.
    node runner fees must be withdrawn before this, otherwise fee admin could steal node runner fees.
    """
    return Seq(
        Pop(pre_mint_or_redeem()),
        custom_assert(
            gget(str_noderunner_fees) == Int(0), err_noderunner_fees_not_zero
        ),
        gset(str_noderunner_addr, new_noderunner.get()),
    )


@router.method
@admin_or_fee_admin_only
def change_feeaddr(new_feeaddr: abi.Address):
    """
    admin/fee admin method. change fee admin address
    """
    return gset(str_fee_addr, new_feeaddr.get())


@router.method
@fee_admin_only
def update_max_balance(new_max_balance: abi.Uint64):
    """
    Fee admin method. Updates max algo stake
    """
    return Seq(
        custom_assert(new_max_balance.get() <= Int(65432100000000), err_max_stake_exceeded), # 65M ALGO max
        gset(str_max_balance, new_max_balance.get()),
    )


@router.method
@fee_admin_only
def verify_nfdomains(registry_app_id: abi.Uint64, nfd_app_id: abi.Uint64, name: abi.DynamicBytes):
    return InnerTxnBuilder.Execute({
        TxnField.type_enum: TxnType.ApplicationCall,
        TxnField.on_completion: OnComplete.NoOp,
        TxnField.application_id: registry_app_id.get(),
        TxnField.application_args: [
            Bytes("verify_nfd_addr"),
            Concat(name.get(), Bytes(".dualstake.algo")),
            Itob(nfd_app_id.get()),
            Global.current_application_address(),
        ],
        TxnField.applications: [nfd_app_id.get()],
        TxnField.fee: Int(0),
    })
