from pyteal import (
    And,
    App,
    Bytes,
    Global,
    If,
    InnerTxnBuilder,
    Int,
    Itob,
    Log,
    OnComplete,
    ScratchVar,
    Seq,
    TealType,
    TxnField,
    TxnType,
    WideRatio,
)
from lib.err import err_lp
from lib.events import emit_event
from lib.storage import gget
from lib.str import str_asa_id, str_lp_id, str_tm2_app_id
from lib.utils import custom_assert, get_asset_balance


def swap_tm2_algo_asa(swap_amt):
    price = ScratchVar(TealType.uint64)
    return Seq(
        price.store(get_price(gget(str_lp_id), swap_amt)),
        If(price.load() == Int(0))
        .Then(
            Int(0),
        )
        .Else(
            InnerTxnBuilder.Begin(),
            InnerTxnBuilder.SetFields(
                {
                    TxnField.type_enum: TxnType.Payment,
                    TxnField.receiver: gget(str_lp_id),
                    TxnField.amount: swap_amt,
                    TxnField.fee: Global.min_txn_fee(),
                }
            ),
            InnerTxnBuilder.Next(),
            InnerTxnBuilder.SetFields(
                {
                    TxnField.type_enum: TxnType.ApplicationCall,
                    TxnField.on_completion: OnComplete.NoOp,
                    TxnField.application_id: gget(str_tm2_app_id),
                    TxnField.application_args: [
                        Bytes("swap"),
                        Bytes("fixed-input"),
                        Itob(price.load()),
                    ],
                    TxnField.assets: [gget(str_asa_id)],
                    TxnField.accounts: [gget(str_lp_id)],
                    TxnField.fee: Int(2) * Global.min_txn_fee(),
                }
            ),
            InnerTxnBuilder.Submit(),
            emit_event(
                "swap(uint64,uint64)",  # arc28: algo_amount, asa_amount
                Itob(swap_amt),
                Itob(price.load()),
            ),
            emit_event(
                "asa_balance(uint64)",  # arc28: asa_balance
                Itob(get_asset_balance(gget(str_asa_id))),
            ),
            Int(1),
        ),
    )


def get_price(tm_account, amount):
    asset1_id = App.localGetEx(
        tm_account, gget(str_tm2_app_id), Bytes("asset_1_id")
    )
    asset1_reserves = App.localGetEx(
        tm_account, gget(str_tm2_app_id), Bytes("asset_1_reserves")
    )
    asset2_reserves = App.localGetEx(
        tm_account, gget(str_tm2_app_id), Bytes("asset_2_reserves")
    )
    return Seq(
        asset1_id,
        asset1_reserves,
        asset2_reserves,
        custom_assert(
            And(
                asset1_id.hasValue(),
                asset2_reserves.hasValue(),
                asset1_reserves.hasValue(),
            ),
            err_lp,
        ),
        If(asset1_id.value() == Int(0))
        .Then(
            asset2_reserves.value()
            - Int(1)
            - WideRatio(
                [asset1_reserves.value(), asset2_reserves.value()],
                [asset1_reserves.value() + get_tm2_net_amt(amount)],
            )
        )
        .Else(
            asset1_reserves.value()
            - Int(1)
            - WideRatio(
                [asset2_reserves.value(), asset1_reserves.value()],
                [asset2_reserves.value() + get_tm2_net_amt(amount)],
            )
        ),
    )


def get_tm2_net_amt(amt):
    return amt - (Int(30) * amt / Int(10000))
