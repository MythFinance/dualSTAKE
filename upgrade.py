from pyteal import (
    Concat,
    Int,
    Len,
    Mod,
    Seq,
    abi,
)
from lib.decorators import admin_only, admin_or_fee_admin_only
from lib.err import err_hash_len, err_no_contract_upgrade
from lib.storage import gget, gset
from lib.str import bytes_empty, str_contract_upgrade, str_upgrade_period
from lib.utils import custom_assert, latest_timestamp_plus_uint32
from router import router

## Upgrading with time-block to a pre-declared version only
#
# Methodology
#
# The global state contract_upgrade field will include a number of hashes that mush correspond to the future approval program pages
#
# A timelock of 1 week must also be satisfied
#
# The code handling application updates verify that the SHA512_256 hash of each program page is equal to the stored hashes
#
# The update lifecycle starts with a queue_upgrade call that accepts the concatenated hashes and stores them in struct along with the timestamp of update applicability
#
# There must also not be any protesting stake in the contract
#
# TODO validate clear state program as well?
#   will do in v2. Need to ship before 2027. Current program does not allow optin. 
#   WARNING for auditors of v2+: If approval code is changed to allows optins, then the clear program is not validated and can be trojan-horsed to do <whatever>

@router.method
@admin_only
def queue_upgrade(hashes: abi.DynamicBytes):
    """
    admin method only.
    stage a contract upgrade. time applicability 1 week from current timestamp. hashes are variable length, 32b each, corresponding to SHA512_256 of approval program pages
    """
    return Seq(
        custom_assert(Mod(Len(hashes.get()), Int(32)) == Int(0), err_hash_len),
        gset(str_contract_upgrade,
            Concat(
                latest_timestamp_plus_uint32(gget(str_upgrade_period)),
                hashes.get()
            )
        )
    )

@router.method
@admin_or_fee_admin_only
def reset_upgrade():
    """
    admin or fee admin only.
    clear a staged contract upgrade
    """
    return Seq(
        custom_assert(gget(str_contract_upgrade) != bytes_empty, err_no_contract_upgrade),
        gset(str_contract_upgrade, bytes_empty),
    )
