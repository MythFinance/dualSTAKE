#!/usr/bin/env python
import base64
import os
import shutil
from pathlib import Path
from algosdk.v2client import algod
from src import get_contracts
from json import dumps

algod_server = os.getenv("ALGOD_SERVER", "https://mainnet-api.4160.nodely.dev")
algod_port = os.getenv("ALGOD_PORT", "443")
algod_token = os.getenv("ALGOD_TOKEN", "")
algod_client = algod.AlgodClient(algod_token, f"{algod_server}:{algod_port}")

# Change working directory to the script's location
script_dir = Path(__file__).parent.resolve()
os.chdir(script_dir)

# Create "artifacts" directory if it doesn't exist, otherwise delete its contents
artifacts_dir = script_dir / "artifacts"
if artifacts_dir.exists():
    shutil.rmtree(artifacts_dir)
artifacts_dir.mkdir(exist_ok=True)

def compile_teal():
    approval_program, clear_program, contract = get_contracts()

    # Create directories if they don't exist
    artifacts_dir = os.path.abspath("artifacts")

    # compile program to TEAL assembly
    approval_path = os.path.join(artifacts_dir, "approval.teal")
    with open(approval_path, "w") as f:
        f.write(approval_program)
        print(f"Wrote approval teal to {approval_path}")

    # compile program to TEAL assembly
    clear_path = os.path.join(artifacts_dir, "clear.teal")
    with open(clear_path, "w") as f:
        f.write(clear_program)
        print(f"Wrote clear teal to {clear_path}")

    contract_path = os.path.join(artifacts_dir, "contract.arc32.json")
    with open(contract_path, "w") as f:
        f.write(dumps(contract.dictify()))
        print(f"Wrote ARC32 to {contract_path}")

    return [approval_program, clear_program, contract]

# helper function to compile program source
def _compile_program(client, source_code):
    compile_response = client.compile(source_code)
    return base64.b64decode(compile_response['result'])

def compile_binary():
    [approval_program, clear_program, _contract] = compile_teal()
    approval_binary = _compile_program(algod_client, approval_program)
    
    approval_tok_path = os.path.join(artifacts_dir, "approval.teal.tok")
    with open(approval_tok_path, "wb") as f:
        f.write(approval_binary)
        print(f"Wrote approval binary to {approval_tok_path}")

    # Split approval binary into 4096-byte chunks
    page_size = 4096
    approval_page1 = approval_binary[:page_size]
    approval_page2 = approval_binary[page_size:page_size*2]
    
    approval_page1_path = os.path.join(artifacts_dir, "approval.teal.tok.page1")
    with open(approval_page1_path, "wb") as f:
        f.write(approval_page1)
        print(f"Wrote approval binary page 1 ({len(approval_page1)} bytes) to {approval_page1_path}")
    
    if approval_page2:
        approval_page2_path = os.path.join(artifacts_dir, "approval.teal.tok.page2")
        with open(approval_page2_path, "wb") as f:
            f.write(approval_page2)
            print(f"Wrote approval binary page 2 ({len(approval_page2)} bytes) to {approval_page2_path}")
    
    # compile program to TEAL assembly
    clear_binary = _compile_program(algod_client, clear_program)

    clear_tok_path = os.path.join(artifacts_dir, "clear.teal.tok")
    with open(clear_tok_path, "wb") as f:
        f.write(clear_binary)
        print(f"Wrote clear binary to {clear_tok_path}")

compile_binary()