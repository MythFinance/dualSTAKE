from pyteal import (
    AppParam,
    Balance,
    Global,
    If,
    InnerTxn,
    InnerTxnBuilder,
    Int,
    Itob,
    Len,
    Not,
    ScratchVar,
    Seq,
    Subroutine,
    Substring,
    TealType,
    TxnField,
    TxnType,
    abi,
)
from lib.storage import gget
from lib.str import str_arc59_app_id
from lib.utils import custom_assert, is_opted_in, send_algo, send_asa
from lib.err import err_fees

# extra_fields{} for different fee structures
double_fee_extra_fields={}
double_fee_extra_fields[TxnField.fee]=Int(2) * Global.min_txn_fee()

triple_fee_extra_fields={}
triple_fee_extra_fields[TxnField.fee]=Int(3) * Global.min_txn_fee()

quadruple_fee_extra_fields={}
quadruple_fee_extra_fields[TxnField.fee]=Int(4) * Global.min_txn_fee()

t = abi.Tuple3[abi.Uint64, abi.Uint64, abi.Bool]

@Subroutine(TealType.none)
def arc59_send_asa_and_algo(receiver, algo_amount, asa_id, asa_amount):
    """
    Send ALGO+ASA via ARC59 inbox; ARC59 MBR+fees are subtracted from algo amount.
    """
    return_val = abi.make(t)
    itxns = abi.Uint64()
    mbr = abi.Uint64()
    router_opted_in = abi.Bool()
    arc59Address = AppParam.address(gget(str_arc59_app_id))
    algo_diff = ScratchVar(TealType.uint64)
    receiver_inbox_address = abi.Address()
    amount = ScratchVar(TealType.uint64)
    return Seq(
        amount.store(Int(1)),
        # store initial balance, convert into a diff after done
        algo_diff.store(Balance(Global.current_application_address())),

        InnerTxnBuilder.ExecuteMethodCall(
            app_id=gget(str_arc59_app_id),
            method_signature="arc59_getSendAssetInfo(address,uint64)(uint64,uint64,bool,bool,uint64,uint64)",
            args=[receiver, Itob(asa_id)],
        ),
        return_val.decode(Substring(InnerTxn.last_log(), Int(4), Len(InnerTxn.last_log()))),
        return_val[0].store_into(itxns),
        return_val[1].store_into(mbr),
        return_val[2].store_into(router_opted_in),

        arc59Address,
        If(mbr.get() > Int(0)).Then(
            send_algo(arc59Address.value(), mbr.get(), Global.min_txn_fee()),
        ),

        If(Not(router_opted_in.get())).Then(
            InnerTxnBuilder.ExecuteMethodCall(
                app_id=gget(str_arc59_app_id),
                method_signature="arc59_optRouterIn(uint64)void",
                args=[Itob(asa_id)],
                extra_fields=double_fee_extra_fields,
            ),
        ),

        # hacky way to figure out if inbox requires creation
        If(itxns.get() >= Int(5)).Then(
            # calculate escrow address
            InnerTxnBuilder.ExecuteMethodCall(
                app_id=gget(str_arc59_app_id),
                method_signature="arc59_getOrCreateInbox(address)address",
                args=[receiver],
                extra_fields=quadruple_fee_extra_fields,
            ),
            receiver_inbox_address.decode(Substring(InnerTxn.last_log(), Int(4), Len(InnerTxn.last_log()))),
            send_algo(receiver_inbox_address.get(), Global.min_balance(), Global.min_txn_fee()),
        ).Else(
            InnerTxnBuilder.ExecuteMethodCall(
                app_id=gget(str_arc59_app_id),
                method_signature="arc59_getOrCreateInbox(address)address",
                args=[receiver],
            ),
            receiver_inbox_address.decode(Substring(InnerTxn.last_log(), Int(4), Len(InnerTxn.last_log()))),
        ),

        InnerTxnBuilder.ExecuteMethodCall(
            app_id=gget(str_arc59_app_id),
            method_signature="arc59_sendAsset(axfer,address,uint64)address",
            args=[
                {
                    TxnField.type_enum: TxnType.AssetTransfer,
                    TxnField.asset_receiver: arc59Address.value(),
                    TxnField.xfer_asset: asa_id,
                    TxnField.asset_amount: amount.load(),
                    TxnField.fee: Global.min_txn_fee(),
                },
                receiver,
                Itob(Int(0)),
            ],
            extra_fields={
                TxnField.fee: If(is_opted_in(receiver_inbox_address.get(), asa_id))
                    .Then(Int(2) * Global.min_txn_fee())
                    .Else(Int(4) * Global.min_txn_fee()),
            }
        ),

        algo_diff.store(algo_diff.load() - Balance(Global.current_application_address())),

        send_algo(receiver, algo_amount - algo_diff.load() - Global.min_txn_fee(), Global.min_txn_fee()),
    )

def send_algo_and_asa(receiver, algo_amount, asa_id, asa_amount, txn_fee):
    """
    Send ALGO+ASA. if txn_fee is set to Global.min_txn_fee, fees subtracted from algo amount
    If receiver is opted in, ALGO amount is -= by 2 min txn fees and ASA is sent directly.
    If receiver is not opted in, ARC59 inbox is used to send, and txn fees are subtracted from the ALGO amount
    """
    return Seq(
        If(is_opted_in(receiver, asa_id)).Then(
            # send asset, paying min fee
            send_asa(receiver, asa_id, asa_amount, txn_fee),
            # send algo, paying min fee, subtract 2 min fees from amount for the txns
            send_algo(receiver, algo_amount - Int(2) * txn_fee, txn_fee),
        ).Else(
            custom_assert(txn_fee > Int(0), err_fees),
            arc59_send_asa_and_algo(receiver, algo_amount, asa_id, asa_amount),
        )
    )


