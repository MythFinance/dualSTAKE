from pyteal import Int, Seq, Txn, abi
from lib.decorators import fee_admin_only, fee_admin_or_node_runner_only
from lib.err import err_over, err_zero
from lib.storage import gget, global_decr
from lib.str import str_noderunner_addr, str_noderunner_fees, str_platform_fees
from lib.utils import custom_assert, send_algo
from router import router


@router.method
@fee_admin_or_node_runner_only
def withdraw_node_runner_fees(amount: abi.Uint64):
    """
    fee admin/node runner method. withdraw node runner fees. hard coded to send to node runner address.
    the fee admin may call this to pay out the current node runner before changing node runner address
    """
    return Seq(
        custom_assert(amount.get() > Int(0), err_zero),
        custom_assert(amount.get() <= gget(str_noderunner_fees), err_over),
        send_algo(gget(str_noderunner_addr), amount.get(), Int(0)),
        global_decr(str_noderunner_fees, amount.get()),
    )


@router.method
@fee_admin_only
def withdraw_platform_fees(amount: abi.Uint64):
    """
    fee admin method. withdraw platform fees
    """
    return Seq(
        custom_assert(amount.get() > Int(0), err_zero),
        custom_assert(amount.get() <= gget(str_platform_fees), err_over),
        send_algo(Txn.sender(), amount.get(), Int(0)),
        global_decr(str_platform_fees, amount.get()),
    )
