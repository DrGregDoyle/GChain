'''
Testing transactions
'''

from transaction import Transaction, decode_raw_transaction
from utxo import UTXO_OUTPUT, UTXO_INPUT
import secrets
from hashlib import sha256
from wallet import Wallet


def test_raw_transaction():
    tx_id = sha256('Transaction'.encode()).hexdigest()
    tx_index = 0
    sig_script = hex(secrets.randbits(288))[2:]
    sequence = 0xffffffff
    input_utxo = UTXO_INPUT(tx_id, tx_index, sig_script, sequence)

    tx_index2 = 1
    sig_script2 = hex(secrets.randbits(140))[2:]
    input_utxo2 = UTXO_INPUT(tx_id, tx_index2, sig_script2, sequence)

    amount = secrets.randbelow(1000)
    unlock_script = Wallet().address
    output_utxo = UTXO_OUTPUT(amount, unlock_script)

    amount2 = secrets.randbelow(4000)
    unlock_script2 = Wallet().address
    output_utxo2 = UTXO_OUTPUT(amount2, unlock_script2)

    version = 1
    input_count = 2
    inputs = [input_utxo.raw_utxo, input_utxo2.raw_utxo]
    output_count = 2
    outputs = [output_utxo.raw_utxo, output_utxo2.raw_utxo]
    locktime = secrets.randbits(Transaction.LOCKTIME_BITS)

    t = Transaction(inputs=inputs, outputs=outputs, version=version, locktime=locktime)
    raw = t.raw_transaction
    new_t = decode_raw_transaction(raw)

    assert new_t.raw_transaction == raw
    assert new_t.id == t.id
