from pyteal import (
    App,
    AssetHolding,
    Btoi,
    Bytes,
    Concat,
    Extract,
    Err,
    Global,
    If,
    InnerTxn,
    InnerTxnBuilder,
    Int,
    Itob,
    Log,
    Not,
    OnComplete,
    Seq,
    Subroutine,
    TealType,
    TxnField,
    TxnType,
)
from lib.str import bytes_numbers, str_contract_upgrade, str_lst_id


# assert that fails with an error string attached
def custom_assert(cond, str):
    """
    assert with custom error message
    """
    return If(Not(cond)).Then(
        Log(Bytes(str)),
        Err(),
    )

# same as above, but inversed - skips a Not()
# not sure if it saves opcode costs
def fail_if(cond, str):
    """
    inverted assert with custom error message
    """
    return If(cond).Then(
        Log(Bytes(str)),
        Err()
    )


# as above but without condition
def fail(str):
    """
    fail with custom error message
    """
    return Seq(
        Log(Bytes(str)),
        Err()
    )


def abs_diff(a, b):
    return If(a > b).Then(a - b).Else(b - a)


# lifted from pyteal-utils
@Subroutine(TealType.bytes)
def int_to_ascii(arg):
    """
    int_to_ascii converts an integer to the ascii byte that represents it
    """
    return Extract(bytes_numbers, arg, Int(1))


@Subroutine(TealType.bytes)
def itoa(i):
    """
    itoa converts an integer to the ascii byte string it represents
    """
    return If(
        i == Int(0),
        Bytes("0"),
        Concat(
            If(i / Int(10) > Int(0), itoa(i / Int(10)), Bytes("")),
            int_to_ascii(i % Int(10)),
        ),
    )


def create_lst_asset(name, unit, url):
    return Seq(
        # find out current TC to figure out the future asset ID
        InnerTxnBuilder.Execute(
            {
                TxnField.type_enum: TxnType.ApplicationCall,
                TxnField.on_completion: OnComplete.DeleteApplication,
                TxnField.approval_program: Bytes("base64", "C4EBQw=="),
                TxnField.clear_state_program: Bytes("base64", "C4EBQw=="),
            }
        ),
        InnerTxnBuilder.Execute(
            {
                TxnField.type_enum: TxnType.AssetConfig,
                TxnField.config_asset_name: name,
                TxnField.config_asset_unit_name: unit,
                TxnField.config_asset_url: Concat(
                    url, itoa(InnerTxn.created_application_id() + Int(1))
                ),
                TxnField.config_asset_decimals: Int(6),
                TxnField.config_asset_total: Int(10000000000000000), # 10B at 1e6, like ALGO
                TxnField.config_asset_manager: Global.current_application_address(),
                TxnField.config_asset_reserve: Global.current_application_address(),
            }
        ),
        InnerTxn.created_asset_id(),
    )


def delete_lst_asset():
    return InnerTxnBuilder.Execute(
        {
            TxnField.type_enum: TxnType.AssetConfig,
            TxnField.config_asset: App.globalGet(str_lst_id),
        }
    )


@Subroutine(TealType.none)
def send_algo(receiver, amount, fee):
    return InnerTxnBuilder.Execute(
        {
            TxnField.type_enum: TxnType.Payment,
            TxnField.sender: Global.current_application_address(),
            TxnField.receiver: receiver,
            TxnField.amount: amount,
            TxnField.fee: fee,
        }
    )


def closeout_algo(receiver):
    return InnerTxnBuilder.Execute(
        {
            TxnField.type_enum: TxnType.Payment,
            TxnField.amount: Int(0),
            TxnField.close_remainder_to: receiver,
            TxnField.receiver: receiver,
        }
    )


@Subroutine(TealType.none)
def send_asa(receiver, aid, amount, fee):
    return InnerTxnBuilder.Execute(
        {
            TxnField.type_enum: TxnType.AssetTransfer,
            TxnField.xfer_asset: aid,
            TxnField.asset_receiver: receiver,
            TxnField.asset_amount: amount,
            TxnField.fee: fee,
        }
    )


def closeout_asa(receiver, asa_id):
    return InnerTxnBuilder.Execute(
        {
            TxnField.type_enum: TxnType.AssetTransfer,
            TxnField.xfer_asset: asa_id,
            TxnField.asset_receiver: receiver,
            TxnField.asset_close_to: receiver,
            TxnField.asset_amount: Int(0),
        }
    )


def is_opted_in(addr, aid):
    """
    Returns true if $addr is opted in to $aid
    """
    ab = AssetHolding.balance(addr, aid)
    return Seq(ab, ab.hasValue())


def get_asset_balance(aid):
    ab = AssetHolding.balance(Global.current_application_address(), aid)
    return Seq(ab, ab.value())


def latest_timestamp_plus_uint32(offset):
    return Extract(Itob(Global.latest_timestamp() + offset), Int(4), Int(4))


def get_upgrade_maturity_ts():
    return Btoi(Extract(str_contract_upgrade, Int(0), Int(4)))
