'''
UTXO Testing
'''

from hashlib import sha256
from utxo import UTXO_INPUT, UTXO_OUTPUT, decode_raw_input_utxo, decode_raw_output_utxo
import secrets


def test_raw_utxo():
    random_bits = secrets.randbelow(1024)
    tx_id = sha256('Transaction'.encode()).hexdigest()
    tx_index = 0
    sig_script = hex(secrets.randbits(random_bits))[2:]
    sequence = pow(2, 32) - 1
    utxo = UTXO_INPUT(tx_id, tx_index, sig_script, sequence)
    raw1 = utxo.raw_utxo
    utxo2 = decode_raw_input_utxo(raw1)

    assert utxo2.raw_utxo == raw1


def test_raw_output():
    random_bits = secrets.randbelow(1024)
    amount = secrets.randbelow(1000)
    locking_script = hex(secrets.randbits(random_bits))[2:]
    output1 = UTXO_OUTPUT(amount, locking_script)
    raw1 = output1.raw_utxo
    output2 = decode_raw_output_utxo(raw1)

    assert output2.raw_utxo == raw1
