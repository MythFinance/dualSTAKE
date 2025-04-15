from pyteal import (
    Extract,
    For,
    Global,
    Int,
    Itob,
    Len,
    ScratchVar,
    Seq,
    Sha512_256,
    Suffix,
    TealType,
    Txn,
)
from lib.decorators import admin_or_fee_admin_only
from lib.events import emit_event
from lib.storage import gget, gset
from lib.str import bytes_empty, str_contract_upgrade, str_protest_sum
from lib.utils import custom_assert, get_upgrade_maturity_ts
from lib.err import err_early, err_hash, err_no_upgrade, err_size, err_protest


@admin_or_fee_admin_only
def process_upgrade():
    expected_page_hashes = ScratchVar(TealType.bytes)
    expected_hash = ScratchVar(TealType.bytes)
    pg_idx = ScratchVar(TealType.uint64)
    return Seq(
        custom_assert(gget(str_contract_upgrade) != bytes_empty, err_no_upgrade),
        # timestamp has elapsed
        custom_assert(get_upgrade_maturity_ts() < Global.latest_timestamp(), err_early),
        # any protesting stake has been dissolved
        custom_assert(gget(str_protest_sum) == Int(0), err_protest),
        # chop uint32 timestamp, save in expected_page_hashes
        expected_page_hashes.store(Suffix(gget(str_contract_upgrade), Int(4))),
        emit_event(
            "count_expected_actual_pages(uint64,uint64)",  # arc28: expected_page_count, actual_page_count
            Itob(Len(expected_page_hashes.load()) / Int(32)),
            Itob(Txn.approval_program_pages.length()),
        ),
        # Validate approval page count == expected hashes count
        custom_assert(
            Txn.approval_program_pages.length()
            == Len(expected_page_hashes.load()) / Int(32),
            err_size,
        ),
        # walk through pages. compare hash of page with expected hash
        For(
            pg_idx.store(Int(0)),
            pg_idx.load() < Txn.approval_program_pages.length(),
            pg_idx.store(pg_idx.load() + Int(1)),
        ).Do(
            # Store the expected hash in scratch to compare
            expected_hash.store(
                Extract(expected_page_hashes.load(), Int(32) * pg_idx.load(), Int(32))
            ),
            # hash the program page and compare to the expected hash
            custom_assert(
                expected_hash.load()
                == Sha512_256(Txn.approval_program_pages[pg_idx.load()]),
                err_hash,
            ),
            emit_event(
                "validate_page(uint64)",  # arc28: page index
                Itob(pg_idx.load()),
            ),
        ),
        gset(str_contract_upgrade, bytes_empty),
    )