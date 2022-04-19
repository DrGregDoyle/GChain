'''
UTXO Testing
'''

from hashlib import sha256
from utxo import UTXO, OUTPUT_UTXO, decode_raw_utxo, decode_raw_output
import secrets


def test_raw_utxo():
    tx_id = sha256('Transaction'.encode()).hexdigest()
    tx_index = 0
    sig_script = hex(secrets.randbits(288))[2:]
    utxo = UTXO(tx_id, tx_index, sig_script)
    raw1 = utxo.get_raw_utxo()
    utxo2 = decode_raw_utxo(raw1)

    assert utxo2.get_raw_utxo() == raw1


def test_raw_output():
    amount = secrets.randbelow(1000)
    unlock_script = hex(secrets.randbits(360))[2:]
    output1 = OUTPUT_UTXO(amount, unlock_script)
    raw1 = output1.get_raw_output()
    output2 = decode_raw_output(raw1)

    assert output2.get_raw_output() == raw1