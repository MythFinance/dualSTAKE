from pyteal import (
    And,
    Concat,
    ExtractUint64,
    Global,
    If,
    Int,
    Itob,
    ScratchVar,
    Seq,
    Subroutine,
    TealType,
    abi,
)
from lib.decorators import fee_admin_only
from lib.err import err_delta_platform_fees, err_delta_noderunner_fees, err_no_update
from lib.events import emit_event
from lib.storage import gget, gset
from lib.str import (
    bytes_empty,
    str_fee_update,
    str_noderunner_fee_bps,
    str_platform_fee_bps,
    str_fee_update_max_delta,
    str_fee_update_period,
)
from lib.utils import abs_diff, custom_assert
from router import router

## Time locked, delta constrained fee updates (node runner, platform)

# fee_update map:

# 0:  [8 bytes] timestamp_applicable uint64
# 8:  [8 bytes] next_noderunner_fee_bps uint64
# 16: [8 bytes] next_platform_fee_bps uint64

params_ts_offset = Int(0)  # uint64
params_noderunner_fee_bps_offset = Int(8)  # uint64
params_platform_fee_bps_offset = Int(16)  # uint64


def get_update_params_ts():
    """
    Returns stored timestamp of next fee update applicability
    """
    return ExtractUint64(gget(str_fee_update), params_ts_offset)


def get_update_params_noderunner_fee_bps():
    """
    Returns current fee update's noderunner fee rate value in bps
    """
    return ExtractUint64(gget(str_fee_update), params_noderunner_fee_bps_offset)


def get_update_params_platform_fee_bps():
    """
    Returns current fee update's platform fee rate value in bps
    """
    return ExtractUint64(gget(str_fee_update), params_platform_fee_bps_offset)


@Subroutine(TealType.none)
def maybe_apply_fee_update():
    """
    internal. applies a vested fee update, if there is any
    """
    # if latest timestamp is after stored applicability timestamp: apply update
    return If(gget(str_fee_update) != bytes_empty).Then(
        If(get_update_params_ts() < Global.latest_timestamp()).Then(
            # apply fees
            apply_fee_updates(
                get_update_params_noderunner_fee_bps(),
                get_update_params_platform_fee_bps(),
            ),
            # clear fee update field
            gset(str_fee_update, bytes_empty),
        )
    )


@Subroutine(TealType.none)
def apply_fee_updates(noderunner_fee_bps, platform_fee_bps):
    return Seq(
        # apply new noderunner fee
        gset(str_noderunner_fee_bps, noderunner_fee_bps),
        # apply new platform fee
        gset(str_platform_fee_bps, platform_fee_bps),
        # log event
        emit_event(
            "fee_update(uint64,uint64)",  # arc28: noderunner_fee_bps, platform_fee_bps
            Itob(noderunner_fee_bps),
            Itob(platform_fee_bps),
        ),
    )


@router.method
@fee_admin_only
def queue_update_fees(
    new_platform_fee_bps: abi.Uint64,
    new_noderunner_fee_bps: abi.Uint64,
    *,
    output: abi.Uint64
):
    """
    Fee admin method. Changes enforced to +/- 2.5% delta max
    If increasing fees, schedules an update of the node+platform fees in bps.
    Decreasing fees are applied immediately.
    Return timestamp of applicability as uint64
    """
    wen = ScratchVar(TealType.uint64)
    return Seq(
        # enforce noderunner fee delta restriction
        custom_assert(
            abs_diff(gget(str_noderunner_fee_bps), new_noderunner_fee_bps.get())
            <= gget(str_fee_update_max_delta),
            err_delta_noderunner_fees,
        ),
        # enforce platform fee delta restriction
        custom_assert(
            abs_diff(gget(str_platform_fee_bps), new_platform_fee_bps.get())
            <= gget(str_fee_update_max_delta),
            err_delta_platform_fees,
        ),
        # fee reductions can apply instantly
        If(
            And(
                new_noderunner_fee_bps.get() <= gget(str_noderunner_fee_bps),
                new_platform_fee_bps.get() <= gget(str_platform_fee_bps),
            )
        )
        .Then(
            apply_fee_updates(
                new_noderunner_fee_bps.get(),
                new_platform_fee_bps.get(),
            ),
            output.set(Int(0)),
        )
        .Else(
            # fee increases; applied with a time-delay of UPDATE_PERIOD
            wen.store(Global.latest_timestamp() + gget(str_fee_update_period)),
            # set update struct
            gset(
                str_fee_update,
                Concat(
                    Itob(wen.load()),
                    Itob(new_noderunner_fee_bps.get()),
                    Itob(new_platform_fee_bps.get()),
                ),
            ),
            emit_event(
                "queue_fee_update(uint64,uint64,uint64)",  # arc28: applicable_at, noderunner_fee_bps, platform_fee_bps
                Itob(wen.load()),
                Itob(new_noderunner_fee_bps.get()),
                Itob(new_platform_fee_bps.get()),
            ),
            # return timestamp of applicability
            output.set(wen.load()),
        ),
    )


@router.method
@fee_admin_only
def reset_update_fees():
    """
    Fee admin method. Cancel a scheudled params update
    """
    return Seq(
        custom_assert(gget(str_fee_update) != bytes_empty, err_no_update),
        gset(str_fee_update, bytes_empty),
    )