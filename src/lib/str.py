from pyteal import Bytes

bytes_empty=Bytes('')
byte_zero=Bytes('base16', '00')
byte_one=Bytes('base16', '01')
bytes_numbers=Bytes("0123456789")

str_version=Bytes('v')

str_asa_id=Bytes('asa_id')
str_lst_id=Bytes('lst_id')
str_delay_optin=Bytes('delay_optin')

str_staked=Bytes('staked')
str_platform_fees=Bytes('platform_fees')
str_noderunner_fees=Bytes('noderunner_fees')

str_platform_fee_bps=Bytes('platform_fee_bps')
str_noderunner_fee_bps=Bytes('noderunner_fee_bps')

str_admin_addr=Bytes('admin_addr')
str_fee_addr=Bytes('fee_admin_addr')
str_noderunner_addr=Bytes('noderunner_addr')
str_lp_type=Bytes('lp_type')
str_lp_id=Bytes('lp_id')

str_fee_update=Bytes('fee_update')
str_contract_upgrade=Bytes('contract_upgrade')

str_protest_count=Bytes('protest_cnt')
str_protest_sum=Bytes('protest_sum')

str_upgrade_period=Bytes('upgrade_period')
str_fee_update_period=Bytes('fee_update_period')
str_fee_update_max_delta=Bytes('fee_update_max_delta')
str_max_balance=Bytes('max_balance')
str_rate_precision=Bytes('rate_precision')
str_tm2_app_id=Bytes('tm2_app_id')
str_arc59_app_id=Bytes('arc59_app_id')