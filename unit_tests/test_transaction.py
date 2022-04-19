'''
Testing transactions
'''

from transaction import Transaction, decode_raw_transaction
from utxo import UTXO, OUTPUT_UTXO
import secrets
from hashlib import sha256


def test_raw_transaction():
    tx_id = sha256('Transaction'.encode()).hexdigest()
    tx_index = 0
    sig_script = hex(secrets.randbits(288))[2:]
    sequence = 0xffffffff
    input_utxo = UTXO(tx_id, tx_index, sig_script, sequence)

    tx_index2 = 1
    sig_script2 = hex(secrets.randbits(140))[2:]
    input_utxo2 = UTXO(tx_id, tx_index2, sig_script2, sequence)

    amount = secrets.randbelow(1000)
    unlock_script = hex(secrets.randbits(360))[2:]
    output_utxo = OUTPUT_UTXO(amount, unlock_script)

    amount2 = secrets.randbelow(4000)
    unlock_script2 = hex(secrets.randbits(155))[2:]
    output_utxo2 = OUTPUT_UTXO(amount2, unlock_script2)

    version = 1
    input_count = 2
    inputs = [input_utxo.get_raw_utxo(), input_utxo2.get_raw_utxo()]
    output_count = 2
    outputs = [output_utxo.get_raw_output(), output_utxo2.get_raw_output()]

    t = Transaction(version, input_count, inputs, output_count, outputs)
    raw = t.get_raw_transaction()
    t_new = decode_raw_transaction(raw)

    assert raw == t_new.get_raw_transaction()