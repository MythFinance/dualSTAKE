from pyteal import Router, Reject, OnCompleteAction, BareCallActions
from lib.create import create_storage
from lib.upgrade_apply import process_upgrade
from delete import delete_app

# Main router class
router = Router(
    # Name of the contract
    "dualSTAKE Contract",
    # What to do for each on-complete type when no arguments are passed (bare call)
    BareCallActions(
        no_op=OnCompleteAction.create_only(create_storage()),
        update_application=OnCompleteAction.call_only(process_upgrade()),
        delete_application=OnCompleteAction.call_only(delete_app()),
        # WARNING this should not be changed without moving future clearstate program into hash validation when upgrading
        opt_in=OnCompleteAction.always(Reject()),
        close_out=OnCompleteAction.always(Reject()),
    ),
    clear_state=Reject(),
)