'''
UTXO Testing
'''

from hashlib import sha256
from utxo import UTXO, decode_raw_utxo


def test_raw_utxo():
    tx_id = sha256('Transaction'.encode()).hexdigest()
    tx_index = 0
    sig_script = sha256('SignatureScript'.encode()).hexdigest()
    utxo = UTXO(tx_id, tx_index, sig_script)
    raw1 = utxo.get_raw_utxo()
    utxo2 = decode_raw_utxo(raw1)

    assert utxo2.get_raw_utxo() == utxo.get_raw_utxo()
