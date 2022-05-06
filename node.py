'''
The Node class

'''

'''
IMPORTS
'''
import socket
import threading

from block import Block, decode_raw_block
from blockchain import Blockchain
from helpers import utc_to_seconds, list_to_node, verify_checksum
from miner import Miner
from network import close_socket, create_socket, package_and_send_data, receive_data
from transaction import Transaction, decode_raw_transaction
from utxo import UTXO_OUTPUT
from wallet import Wallet
import json
from hashlib import sha256

'''
CLASS
'''


class Node:
    '''

    '''
    DEFAULT_PORT = 41000
    DEFAULT_FORMAT = 'utf-8'
    LISTENER_TIMEOUT = 10
    MESSAGE_RETRIES = 5

    def __init__(self, wallet=None):
        '''

        '''
        # Instantiate the Blockchain
        self.blockchain = Blockchain()

        # Create Miner
        self.miner = Miner()

        # Create local wallet if none used during instantiation
        if wallet is None:
            self.wallet = Wallet()
        else:
            self.wallet = wallet

        # Create Mining and Listening flags
        self.is_mining = False
        self.is_listening = False

        # Create transaction lists
        self.incoming_transactions = []
        self.validated_transactions = []
        self.orphaned_transactions = []

        # Create Mining stats dict
        self.mining_stats = {}

        # Setup server
        self.local_host = "0.0.0.0"
        self.port = self.DEFAULT_PORT
        self.local_node = (self.local_host, self.port)

        # Setup node list
        self.node_list = []

        # Start Event Listener
        self.start_event_listener()

    '''
    PROPERTIES
    '''

    @property
    def last_block(self):
        return self.blockchain.last_block

    @property
    def utxos(self):
        return self.blockchain.utxos

    @property
    def curve(self):
        return self.blockchain.curve

    @property
    def height(self):
        return self.blockchain.height

    '''
    MINER
    '''

    def start_miner(self):
        if not self.is_mining:
            # Get hash rate before beginning
            # Logging
            print('Calculating hashrate')
            self.mining_stats.update({'hashrate': self.miner.get_hashrate()})

            # Start mining Block in new thread
            self.is_mining = True
            self.mining_thread = threading.Thread(target=self.mine_block)
            self.mining_thread.start()
        else:
            # Logging
            print('Miner already running')

    def stop_miner(self):
        if self.is_mining:
            self.miner.stop_mining()
            while self.mining_thread.is_alive():
                pass
            self.is_mining = False
        else:
            # Logging
            print('Miner already stopped')

    def mine_block(self):
        interrupted = False
        while not interrupted:
            # Create Mining Transaction
            mining_amount = self.get_mining_amount()
            mining_output = UTXO_OUTPUT(mining_amount, self.wallet.address)
            current_height = self.blockchain.height
            mining_transaction = Transaction(inputs=[], outputs=[mining_output.raw_utxo], min_height=current_height + 1)
            self.validated_transactions.insert(0, mining_transaction.raw_tx)

            # Create candidate block
            if self.last_block == []:
                new_block = Block('', self.get_mining_target(), 0, self.validated_transactions)
            else:
                last_block = decode_raw_block(self.last_block)
                new_block = Block(last_block.id, self.get_mining_target(), 0, self.validated_transactions)

            # Mine block
            start_time = utc_to_seconds()
            mined_raw_block = self.miner.mine_block(new_block.raw_block)

            # Add block or interrupt miner
            if mined_raw_block != '':
                end_time = utc_to_seconds()
                mining_time = end_time - start_time
                mined_block = decode_raw_block(mined_raw_block)
                added = self.add_block(mined_block.raw_block)
                if added:
                    self.validated_transactions = []
                    self.mining_stats.update({"mining_time": mining_time})
            else:
                # Remove mining transaction
                self.validated_transactions.pop(0)
                interrupted = True
        # Stop mining if the thread is interrupted
        self.is_mining = False

    def get_mining_amount(self):
        '''
        The mining reward will be the difference between the sum of all input amounts and the sum of all output
        amounts, plus the reward variable. We also verify that the total_input_amount >= total_output_amount and that
        the referenced output utxos for each input utxo exists.
        '''

        total_input_amount = 0
        total_output_amount = 0
        reward = self.get_mining_reward()

        for t in self.validated_transactions:
            # Recover tx
            temp_tx = decode_raw_transaction(t)

            # Add total input amount for tx
            for i in temp_tx.inputs:
                tx_id = i.tx_id
                tx_index = i.tx_index
                input_index = self.utxos.index[(self.utxos['tx_id'] == tx_id) & (self.utxos['tx_index'] == tx_index)]
                assert not input_index.empty
                total_input_amount += int(self.utxos.loc[input_index]['amount'].values[0], 16)

            # Add total output amount for tx
            for t in temp_tx.outputs:
                total_output_amount += int(t.amount, 16)

        assert total_input_amount >= total_output_amount
        return reward + (total_input_amount - total_output_amount)

    def get_mining_reward(self):
        return self.blockchain.determine_reward()

    def get_mining_target(self):
        '''
        Algorithm for determining mining target goes here
        '''
        return self.blockchain.determine_target()

    '''
    ADD BLOCK
    '''

    def add_block(self, raw_block: str):
        '''

        '''
        added = self.blockchain.add_block(raw_block)
        if added:
            self.check_for_parents()
        return added

    '''
    TRANSACTIONS
    '''

    def add_transaction(self, raw_tx: str) -> bool:
        '''
        When a Node receives a new transaction (tx), one of three things may happen: either the tx gets validated,
        in which case it's added to the validated transactions pool; or the tx has an invalid signature and locking
        script, in which case the tx is rejected; or the tx contains inputs which reference outputs which don't exist
        in the db, in which case this tx gets put in the orphaned transactions pool.

        We recover a Transaction object from the raw_tx string. We then iterate over all inputs. For each input,
        we first check that the referenced utxo output is stored in the blockchain. If the reference output does not
        exist, the Transaction gets flagged as orphaned. For the inputs whose reference utxo exists, we validate the
        input signature with the output locking script (compressed public key). If the signature fails validation,
        we reject the tx, otherwise we continue. As well, as we are validating each input tx, we are adding the value
        of the amount of the corresponding output utxo.

        Finally, if the transaction is not flagged as orphaned, we verify that the total input amount available in
        the output utxos stored in the blockchain is greater than or equal to the total output amount of the
        Transaction outputs. If the total input amount is smaller than the total output amount, we reject the tx.

        With the final check complete, either the tx is added to the validated tx pool or the orphaned tx pool,
        depending on the orphan flag.
        '''

        # Recover the transaction object
        new_tx = decode_raw_transaction(raw_tx)

        # Set orphaned transaction Flag
        all_inputs = True

        # Validate inputs
        total_input_amount = 0
        for i in new_tx.inputs:  # Looping over utxo_input objects

            # Get the row index for the output utxo
            tx_id = i.tx_id
            tx_index = int(i.tx_index, 16)
            input_index = self.utxos.index[(self.utxos['tx_id'] == tx_id) & (self.utxos['tx_index'] == tx_index)]

            # If the row doesn't exist, mark for orphan
            if input_index.empty:
                all_inputs = False

            # If the row exists, validate the input with the output and add the amount
            else:
                # Increase total_input_amount
                amount = int(self.utxos.loc[input_index]['amount'].values[0], 16)
                total_input_amount += amount

                # Validate the signature
                address = self.utxos.loc[input_index]['address'].values[0]
                if not self.blockchain.validate_signature(i.signature, address, tx_id):
                    return False

        # If not flagged for orphaned
        if all_inputs:
            # Get the total output amount
            total_output_amount = 0
            for t in new_tx.outputs:
                total_output_amount += int(t.amount, 16)

            # Verify the total output amount
            if total_output_amount > total_input_amount:
                return False

            # Add tx to validated tx pool
            self.validated_transactions.append(raw_tx)

        # Flagged for orphaned. Add to orphan pool
        else:
            self.orphaned_transactions.append(raw_tx)

        return True

    def check_for_parents(self):
        '''
        For every orphaned transaction, we see if its parents have arrived yet. If not, they will either be placed
        back in the orphaned tx pool, or invalidated.
        '''
        orphan_copies = self.orphaned_transactions.copy()
        self.orphaned_transactions = []
        for r in orphan_copies:
            self.add_transaction(r)

    '''
    EVENT LISTENER
    '''

    def start_event_listener(self):
        if not self.is_listening:
            self.is_listening = True
            self.listening_thread = threading.Thread(target=self.event_listener)
            self.listening_thread.start()

    def stop_event_listener(self):
        if self.is_listening:
            if self.is_mining:
                self.stop_miner()
            self.is_listening = False
            # Logging
            print(f'Shutting down listener within {self.LISTENER_TIMEOUT} seconds.', end='\r\n')
            while self.listening_thread.is_alive():
                pass
            self.local_node = None
        # Logging
        print('Event listener turned off.')

    def event_listener(self):
        '''
        '''

        # Find an available port
        port_assigned = False
        while not port_assigned:
            try:
                temp_socket = create_socket()
                temp_socket.bind(self.local_node)
                port_assigned = True
            except OSError:
                # Logging
                print(f'Socket at port {self.port} is in use')
                self.port += 1
                self.local_node = (self.local_host, self.port)

        print(f'Local node: {self.local_node}')
        self.node_list.append(self.local_node)

        # Listen on that port
        listening_socket = create_socket()
        listening_socket.settimeout(self.LISTENER_TIMEOUT)
        listening_socket.bind(self.local_node)
        listening_socket.listen()

        # Create new thread for events
        while self.is_listening:
            try:
                event, addr = listening_socket.accept()
                event_thread = threading.Thread(target=self.handle_event, args=(event, addr,))
                event_thread.start()
            except socket.timeout:
                pass
        close_socket(listening_socket)

    def handle_event(self, event, addr):
        '''

        '''
        type, data, checksum = receive_data(event)

        # package_and_send_data(event, 11, json.dumps(self.local_node))

        if type == '01':
            self.node_connect_event(event, data, checksum)
        else:
            package_and_send_data(event, 0, '')

    '''
    EVENTS
    '''
    '''
    Connect/Disconnect Events
    '''

    def node_connect_event(self, client: socket, data: str, checksum: str):

        new_node = list_to_node(json.loads(data))
        if not verify_checksum(json.dumps(new_node), checksum):
            package_and_send_data(client, 12, '')

        # Logging
        print(f'Node connection received from {new_node}.')

        if new_node not in self.node_list:
            self.node_list.append(new_node)
        package_and_send_data(client, 11, json.dumps(self.local_node))

    '''
    Connect and Disconnect
    '''

    def connect_to_node(self, node: tuple) -> bool:
        '''
        Connect to a specific node and exchange addresses.
        Needs to be only called when Node is_listening, otherwise we wont have a self.local_node
        '''
        # Verify the node is external
        if node != self.local_node:
            # Handle connection errors
            try:
                # Create a client socket
                client = create_socket()
                client.connect(node)

                # Send local node - datatype == 01
                package_and_send_data(client, 1, json.dumps(self.local_node))

                # Receive data from node
                type, data, checksum = receive_data(client)
                print(f'Type: {type}')
                print(f'Data: {data}')
                print(f'Checksum: {checksum}')

                # Verify checksum
                if not verify_checksum(data, checksum):
                    return False

                # Add node to node_list
                if type == '0b':
                    new_node = list_to_node(json.loads(data))
                    if new_node not in self.node_list:
                        self.node_list.append(new_node)
                else:
                    return False

                # Logging
                print(f'Successfully connected to {new_node}')
                close_socket(client)

            # Connection errors
            except ConnectionError:
                return False

        # Local node is node
        else:
            # Logging
            print(f'Cannot connect to own address: {self.local_node}')
            return False
