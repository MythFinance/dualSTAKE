err_unauthorized = "ERR UNAUTH"
err_not_ready = "ERR !RDY"
err_payment_validation_failed = "ERR PAY"
err_payment_amount_failed = "ERR PAY AMT"
err_min_payment = "ERR MIN AMT"
err_invalid_asset_id = "ERR AID"
err_max_stake_exceeded = "ERR MAX"

err_ie = "ERR IE" # Incentive eligibility fee found but not required
err_not_ie = "ERR !IE"  # Incentive eligibility fee not found but required

err_early = "ERR EARLY" # Contract upgrade timestamp has not elapsed yet
err_protest = "ERR PRTST" # Contract has protesting stake; can not upgrade
err_size = "ERR SIZE" # Approval page count does not match expected hash count 
err_hash = "ERR HASH" # Program page hash does not match

err_fees = "ERR FEES" # internal error; send arc59 called with fees=0. This should not happen
err_not_implemented = "ERR !IMPL" # feature not implemented; swapping only supported via tinyman currently
err_no_pre = "ERR NP" # internal guard against getting the DS:ASA rate before calling pre_mint_or_redeem, which may swap if needed
err_lp = "ERR LP" # Error reading tinyman LP Asset ID or reserve values

err_zero = "ERR ZERO" # redeeming or withdrawing zero amount
err_over = "ERR OVER" # Over-budget withdrawal was requested
err_inited = "ERR I" # internal error: storage was already initialized

err_stake_exists = "ERR STK" # Error deleting: staked amount not zero
err_noderunner_fees_exists = "ERR NF" # Error deleting: node runner fees not zero

err_delta_noderunner_fees = "ERR DELTA N" # requested noderunner fee update was over the allowed delta
err_delta_platform_fees = "ERR DELTA P" # requested platform fee update was over the allowed delta 
err_no_update = "ERR NOU" # reset update fees was called but without a fee update scheduled

err_no_swap = "ERR NO SWP" # swap called but no swap is due
err_swap_fail = "ERR SWP" # swap was attempted but price was calculated to be zero

err_asa_rate = "ERR RATE" # minting with incorrect amount of the paired ASA provided
err_box_del = "ERR BOX DEL" # error deleting box

err_no_upgrade = "ERR NO UPG" # protesting stake without upgrade scheduled
err_min_protest = "ERR MIN PRTST" # protesting under the minimum amount
err_upgrade = "ERR UPG" # admin tried to unprotest stake but an upgrade is still scheduled
err_no_protest = "ERR NO PRTST" # user protesting stake was requested but not found

err_hash_len = "ERR HASH LEN" # Queued hashes length was not a multiple of 32
err_no_contract_upgrade = "ERR NO C UPGR" # A scheduled contract upgrade was attempted to be clear, but there was none

err_chadm_txn_type  = "ERR TXT" # Changing admin: call 1 failed txn type validation
err_chadm_oc  = "ERR OC" # Changing admin: call 1 failed on complete validation
err_chadm_app_id  = "ERR APID" # Changing admin: call 1 failed app id validation
err_chadm_app_arg  = "ERR ARG" # Changing admin: call 1 failed app argument validation
err_chadm_not_called_by_new_admin = "ERR NA" # Changing admin: call 2 failed next-admin-sender validation

err_noderunner_fees_not_zero = "ERR FEE" # Changing noderunner but previous noderunner has fees to be paid out
err_configured = "ERR CFGD" # Configure called but the contract is configured already