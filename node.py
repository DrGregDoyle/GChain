'''
The Node class

'''

'''
IMPORTS
'''
import socket
import threading
from collections import Counter

from block import Block, decode_raw_block
from blockchain import Blockchain
from helpers import utc_to_seconds, list_to_node, verify_checksum
from miner import Miner
from network import get_ip, get_local_ip, close_socket, create_socket, send_to_client, send_to_server, \
    receive_event_data, receive_client_message
from transaction import Transaction, decode_raw_transaction
from utxo import UTXO_OUTPUT, UTXO_INPUT
from wallet import Wallet
import json
from hashlib import sha256

'''
CLASS
'''


class Node:
    '''
    We have two notions of node: there is the Node class, and there is the node socket, which is an ip address and
    port. We will refer to the Node class object explicitly using the uppercase N and the node socket using the
    lowercase n.

    NOTE: All ip addresses must be given in SINGLE QUOTES as a string

    NOTE: The node_list will be a list of all connected Nodes. And the server node of each Node is what's saved in
    the node_list.

    '''
    '''
    MESSAGE TYPES
    '''
    DATATYPES = [
        "PING",
        "NODE CONNECT",
        "NETWORK CONNECT",
        "DISCONNECT",
        "TRANSACTION",
        "TRANSACTION REQUEST",
        "NEW BLOCK",
        "INDEXED BLOCK",
        "STATUS",
        "HASH MATCH",
        "ADDRESS",
        "CONFIRM",
        "CHECKSUM ERROR",
        "NODE LIST"
    ]

    '''
    NETWORKING CONSTANTS
    '''
    DEFAULT_PORT = 41000
    DEFAULT_FORMAT = 'utf-8'
    LISTENER_TIMEOUT = 10
    MESSAGE_RETRIES = 5

    '''
    CONSENSUS CONSTANTS
    '''
    HASHINDEX_BITS = 32

    def __init__(self, wallet=None):
        '''

        '''
        # Logging
        print('Instantiating Blockchain and calculating hash_rate. This may take a moment.')

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

        # Create UTXO tracking dictionary
        self.consumed_utxos = {}

        # Create Mining stats dict from genesis block
        self.mining_stats = self.blockchain.genesis_mining_stats

        # Setup server
        self.listening_address = '0.0.0.0'
        self.server_address = get_ip()
        self.local_address = get_local_ip()

        # Setup node list
        self.node_list = []

        # Setup consensus variables (Start w genesis block vals)
        self.consensus_height = 0
        self.consensus_hash = '0000008f9a191320f71990f02c5b5abd40e4d9f17cd0cb7cc911a91e29f5fb49'
        self.consensus_timestamp = 1651769733

        # Setup consensus dict for nodes and their status
        self.consensus_dict = {}

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

    @property
    def status(self):
        last_block = decode_raw_block(self.last_block)
        height = self.height
        hash = last_block.id
        timestamp = int(last_block.timestamp, 16)
        status_dict = {
            "HEIGHT": height,  # int
            "HASH": hash,  # str
            "TIMESTAMP": timestamp  # int
        }
        return status_dict

    @property
    def consensus(self):
        consensus_dict = {
            "Consensus Height": self.consensus_height,
            "Consensus Hash": self.consensus_hash,
            "Consensus Timestamp": self.consensus_timestamp
        }
        return consensus_dict

    @property
    def consensus_nodes(self):
        consensus_node_list = []
        for node in self.consensus_dict:
            status_dict = self.consensus_dict.get(node)
            temp_height = status_dict.get("HEIGHT")
            temp_hash = status_dict.get("HASH")
            temp_time = status_dict.get("TIMESTAMP")
            if temp_height == self.consensus_height and temp_hash == self.consensus_hash and temp_time == self.consensus_timestamp:
                consensus_node_list.append(node)
        return consensus_node_list

    @property
    def hashlist(self):
        hashlist = []
        for raw_block in self.blockchain.chain:
            hashlist.append(decode_raw_block(raw_block).id)
        return hashlist

    '''
    STATUS
    '''

    def update_status(self):
        self.consensus_dict.update({self.server_node: self.status})

    '''
    CONSENSUS
    '''

    def gather_consensus(self):
        '''
        Consensus Algorithm:
        1) From the list of consensus nodes, find all nodes who have the greatest height

        2) From the list of nodes who have greatest height, find the id with the greatest frequency. If two id's have
        the same frequency, we choose the block with the least timestamp.

        3) Update consensus variables
        '''

        # 1) Get list of nodes with greatest height
        greatest_height = 0
        node_list = []
        for node in self.consensus_dict:
            status = self.consensus_dict.get(node)
            height = status.get("HEIGHT")
            if height > greatest_height:
                greatest_height = height
                node_list = [node]
            elif height == greatest_height:
                node_list.append(node)

        # 2) Find the maximum number of common hash values (AKA: the hash_freq)
        hashtime_list = []
        for h_node in node_list:
            h_status = self.consensus_dict.get(h_node)
            hashtime_list.append((h_status.get("HASH"), h_status.get("TIMESTAMP")))
        hash_freq_dict = Counter(hashtime_list)
        hash_freq = max(hash_freq_dict.values())

        # 3) Get all IDs with this hash frequency
        hashtime_candidate_list = [k for k, v in hash_freq_dict.items() if v == hash_freq]

        # 4) Sort by timestamp
        (temp_hash, temp_time) = ("", pow(2, 32) - 1)
        for t in hashtime_candidate_list:
            (hash, timestamp) = t
            if timestamp < temp_time:
                temp_hash = hash
                temp_time = timestamp

        # 5) Modify consensus variables
        self.consensus_hash = temp_hash
        self.consensus_timestamp = temp_time
        self.consensus_height = greatest_height

    def achieve_consensus(self):
        '''
        Will interrupt mining to achieve consensus
        TODO: Disable new block events during achieve consensus
        '''
        resume_mining = self.is_mining

        if resume_mining:
            self.stop_miner()
            while self.is_mining:
                pass

        self.match_to_consensus_chain()
        self.get_missing_blocks()
        self.send_status_to_network()

        if resume_mining:
            self.start_miner()

    def match_to_consensus_chain(self):
        '''
        Will modify the chain to match up to greatest height.
        '''

        matching_height = self.get_greatest_matching_height()

        while self.height > matching_height:
            self.blockchain.pop_block()

    def get_missing_blocks(self):
        '''
        We iterate over all consensus nodes and get an indexed block from each in turn
        '''

        node_modulus = len(self.consensus_nodes)
        node_count = 0
        c_nodes = self.consensus_nodes.copy()
        while self.height < self.consensus_height:
            get_node = c_nodes[node_count]
            next_block = self.get_indexed_block_from_node(get_node, self.height + 1)
            if self.add_block(next_block):
                self.update_status()
            else:
                # Logging
                print(f'Unable to add block at height {self.height + 1}')
            node_count = (node_count + 1) % node_modulus

    '''
    Hashlist Exchange
    '''

    def get_greatest_matching_height(self):
        '''
        We iterate over every consensus node until we connect.
        Then from a consensus node we find the greatest index for which the two hashlist's match
        Return the greatest index value. Will always be a non-negative value
        '''

        '''First get consensus to update the consensus nodes'''
        self.gather_consensus()

        match_index = 0
        index_found = False
        node_count = 0
        while not index_found and node_count < len(self.consensus_nodes):
            node = self.consensus_nodes[node_count]
            if node != self.server_node:
                try:
                    client = create_socket()
                    client.connect(node)
                    send_to_server(client, 9, json.dumps(self.hashlist))
                    message = receive_client_message(client)
                    if message == '01':
                        type, data, checksum = receive_event_data(client)
                        if type == '0a' and verify_checksum(data, checksum):
                            match_index = int(data, 16)
                            index_found = True
                        else:
                            node_count += 1
                    close_socket(client)

                except ConnectionRefusedError:
                    # Logging
                    node_count += 1
            else:
                # Logging
                node_count += 1

        return match_index

    '''
    MINER
    '''

    def start_miner(self):
        if not self.is_mining:
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
            self.is_mining = False
            while self.mining_thread.is_alive():
                pass
            # Logging
            print('Miner turned off.')
        else:
            # Logging
            print('Miner already turned off.')

    def mine_block(self):
        interrupted = False
        while not interrupted:
            # Create Mining Transaction
            mining_amount = self.get_mining_amount()
            mining_output = UTXO_OUTPUT(mining_amount, self.wallet.address)
            mining_transaction = Transaction(inputs=[], outputs=[mining_output.raw_utxo],
                                             min_height=self.blockchain.height + 1)
            self.validated_transactions.insert(0, mining_transaction.raw_tx)

            # Create candidate block
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
                    hash_rate = int(mined_block.nonce, 16) // mining_time
                    self.mining_stats.update({"mining_time": mining_time})
                    self.mining_stats.update({"hash_rate": hash_rate})
                    self.send_block_to_network(mined_raw_block)
                    self.check_for_parents()
                else:
                    # Logging
                    print(f'Error when trying to add Block. Ending mining.')
                    interrupted = True
            else:
                # Remove mining transaction
                self.validated_transactions.pop(0)
                # Logging
                print('Interrupt received by Node')
                interrupted = True
        # Stop mining if the thread is interrupted
        self.is_mining = False
        # Logging
        print('Mining turned off from interrupt')

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
                tx_index = int(i.tx_index, 16)
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
            # TODO: Run over tx in block and remove from validated_transactions and consumed_utxos
            self.validated_transactions = []
            self.consumed_utxos = {}
            self.update_status()
        return added

    '''
    TRANSACTIONS
    '''

    # SIEVE AND SORT CAN BE MOVED TO HELPERS
    def sieve_transactions(self, sieve_list: list, filter_list: list) -> list:
        sieve_index = sieve_list.copy()
        for s in sieve_index:
            if s in filter_list:
                sieve_list.remove(s)
        return sieve_list

    def sort_transactions(self, transaction_list: list) -> list:
        unique_list = []
        for x in transaction_list:
            if x not in unique_list:
                unique_list.append(x)
        return sorted(unique_list, key=lambda k: k['Timestamp'])

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

        # Return false if already validated or orphaned
        if new_tx in self.validated_transactions or new_tx in self.orphaned_transactions:
            # Logging
            print('Transaction already in node tx pools.')
            return False

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
                # Logging
                print(f'Unable to find utxo with id {tx_id} and index {tx_index}')
                all_inputs = False

            # If the row exists, validate the input with the output and add the amount
            else:
                # Validate the signature
                address = self.utxos.loc[input_index]['address'].values[0]
                if not self.blockchain.validate_signature(i.signature, address, tx_id):
                    # Logging
                    print(f'Signature error')
                    return False

                # Check input not already scheduled for consumption
                consumed = self.consumed_utxos.get(tx_id)
                if consumed is None or consumed != tx_index:
                    self.consumed_utxos.update({tx_id: tx_index})
                else:
                    # Logging
                    print(f'Utxo already consumed by this node')
                    return False

                # Increase total_input_amount
                amount = int(self.utxos.loc[input_index]['amount'].values[0], 16)
                total_input_amount += amount

        # If not flagged for orphaned
        if all_inputs:
            # Get the total output amount
            total_output_amount = 0
            for t in new_tx.outputs:
                total_output_amount += int(t.amount, 16)

            # Verify the total output amount
            if total_output_amount > total_input_amount:
                # Logging
                print('Input/Output amount error in tx')
                return False

            # Add tx to validated tx pool
            self.validated_transactions.append(raw_tx)

            # Send tx to network
            self.send_transaction_to_network(raw_tx)

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
    SERVER
    '''

    def create_nodes(self):
        '''
        The server will listen on address 0.0.0.0 - this allows it to listen to requests from multiple ip addresses (
        i.e., both internal and external.) To receive messages from external machines, the machine running the Node
        must port-forward the ports 41000--42000 to their internal IP address.
        '''
        port_found = False
        temp_port = self.DEFAULT_PORT
        while not port_found:
            try:
                temp_socket = create_socket()
                temp_socket.bind((socket.gethostname(), temp_port))
                port_found = True
            except OSError:
                # Logging
                print(f'Port {temp_port} unavailable.')
                temp_port += 1
        self.port = temp_port
        self.listening_node = (self.listening_address, self.port)
        self.server_node = (self.server_address, self.port)
        self.local_node = (self.local_address, self.port)

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
            # Stop all mining
            if self.is_mining:
                self.stop_miner()

            # Disconnnect from network
            self.__disconnect_from_network()

            # Set listening to False
            self.is_listening = False

            # Logging
            print(f'Shutting down listener within {self.LISTENER_TIMEOUT} seconds.', end='\r\n')

            # Wait for thread to Die
            while self.listening_thread.is_alive():
                pass

            # Clear port
            self.port = None

        # Logging
        print('Event listener turned off.')

    def event_listener(self):
        '''
        '''

        # Create nodes
        self.create_nodes()

        # Logging
        print(f'Listening node: {self.listening_node}')
        print(f'Server node: {self.server_node}')
        print(f'Local node: {self.local_node}')

        # Add server node to node_list
        self.node_list.append(self.server_node)

        # Add status to consensus dict
        self.update_status()

        # Listen on that port
        listening_socket = create_socket()
        listening_socket.settimeout(self.LISTENER_TIMEOUT)
        listening_socket.bind(self.listening_node)
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
        # Receive event data
        type, data, checksum = receive_event_data(event)

        # Verify checksum
        if not verify_checksum(data, checksum):
            send_to_client(event, 2)

        # TESTING#
        print(f'Type: {type}')
        print(f'Data: {data}')
        print(f'Checksum: {checksum}')
        #########

        if type == '01':
            self.node_connect_event(event, data)
        elif type == '02':
            self.network_connect_event(event, data)
        elif type == '03':
            self.disconnect_from_network_event(event, data)
        elif type == '04':
            self.new_transaction_event(event, data)
        elif type == '05':
            self.get_transaction_event(event, data)
        elif type == '06':
            self.new_block_event(event, data)
        elif type == '07':
            self.indexed_block_event(event, data)
        elif type == '08':
            self.status_event(event, data)
        elif type == '09':
            self.hash_match_event(event, data)

    '''
    SERVER EVENTS
    '''

    def node_connect_event(self, client: socket, node: str):
        '''
        The node will be a json string of a list with the host and port. We can retrieve the list with json.loads -
        and then the tuple with the list_to_node function.
        '''
        new_node = list_to_node(json.loads(node))
        if new_node not in self.node_list:
            # Logging
            print(f'Node connection established with {new_node}')
            self.node_list.append(new_node)
        send_to_client(client, 1)

    def network_connect_event(self, client: socket, node: str):
        '''
        The Node will confirm the network request and send the node list.
        It will then run the node_connect_event to add the new node received
        '''
        send_to_client(client, 1)
        send_to_server(client, 2, json.dumps(self.node_list))
        self.node_connect_event(client, node)

    def disconnect_from_network_event(self, client: socket, node: str):
        '''
        We remove the node from the node_list.
        '''
        new_node = list_to_node(json.loads(node))
        if new_node in self.node_list:
            self.node_list.remove(new_node)
        # CONSENSUS DICT
        send_to_client(client, 1)

    def new_transaction_event(self, client: socket, raw_tx: str):
        '''

        '''

        if raw_tx not in self.validated_transactions:
            # Logging
            print('Received new transaction')
            self.add_transaction(raw_tx)
        send_to_client(client, 1)

    def get_transaction_event(self, client: socket, node: str):
        '''

        '''
        new_node = list_to_node(json.loads(node))
        send_to_client(client, 1)
        for t in self.validated_transactions:
            self.send_transaction_to_node(new_node, t)

    def new_block_event(self, client: socket, raw_block: str):
        '''
        TODO: Change it so that mining stops only if the block is added. Otherwise Miners could be effectively
        stopped using a fake 'new block' attack
        '''
        # Stop mining
        resume_mining = self.is_mining
        if resume_mining:
            self.stop_miner()

        # Try and Add Block
        added = self.add_block(raw_block)
        if added:
            send_to_client(client, 1)
        else:
            send_to_client(client, 3)

        # Resume Mining
        if resume_mining:
            self.start_miner()

    def indexed_block_event(self, client: socket, index: str):
        '''
        The index will be a 1-byte hex string
        '''
        index_num = int(index, 16)
        try:
            raw_indexed_block = self.blockchain.chain[index_num]
            send_to_client(client, 1)
            send_to_server(client, 6, raw_indexed_block)
        except IndexError:
            send_to_client(client, 2)

    def status_event(self, client: socket, status_list: str):
        '''
        The status list will be a json string which we recover using json.loads. It will have the node as first entry
        and the corresponding status as second entry.
        '''
        node_list, status_dict = json.loads(status_list)
        node = list_to_node(node_list)
        self.consensus_dict.update({node: status_dict})
        send_to_client(client, 1)
        send_to_server(client, 8, json.dumps(self.status))

        # Make sure we're still at consensus
        self.gather_consensus()
        if self.server_node not in self.consensus_nodes:
            self.achieve_consensus()

    def hash_match_event(self, client: socket, hash_list: str):
        '''
        The hash_list will be a json string we recover with json.loads
        '''
        id_list = json.loads(hash_list)
        min_length = min(len(id_list), len(self.hashlist))
        match_index = 0
        for x in range(1, min_length):
            if id_list[x] == self.hashlist[x]:
                match_index += 1
        send_to_client(client, 1)
        send_to_server(client, 10, format(match_index, f'0{self.HASHINDEX_BITS // 4}x'))

    '''
    CLIENT EVENTS
    '''

    def connect_to_node(self, node: tuple) -> bool:
        '''
        We attempt to connect to the node (socket) given. Will retry if we get such a message up to MESSAGE_RETRIES
        times.
        '''
        if node not in [self.listening_node, self.server_node, self.local_node]:
            connected = False
            retry_count = 0
            while not connected and retry_count < self.MESSAGE_RETRIES:
                try:
                    node_socket = create_socket()
                    node_socket.connect(node)
                    send_to_server(node_socket, 1, json.dumps(self.server_node))
                    confirm_message = receive_client_message(node_socket)
                    if confirm_message == '01':
                        connected = True
                        if node not in self.node_list:
                            self.node_list.append(node)
                    elif confirm_message == '02':
                        retry_count += 1
                    close_socket(node_socket)

                    # TESTING
                    print(f'Confirm message: {confirm_message}')

                except ConnectionRefusedError:
                    # Logging
                    print(f'Unable to connect to node {node}')
                    retry_count += 1

                except TimeoutError:
                    # Logging
                    print(f'Timeout error connecting to {node}')
                    retry_count += 1
            return connected

        else:
            # Logging
            print(f'Cannot connect to own address: {node}')
            return False

    def connect_to_network(self, node: tuple):
        '''
        We send a network request to a node - which means we will receive a node_list.
        For all the new nodes in the node_list, we will run connect_to_node
        '''
        # Track new nodes
        new_nodes = []

        # If the node isn't ours and we're listening
        if node not in [self.listening_node, self.local_node, self.server_node] and self.is_listening:
            node_list_received = False
            retry_count = 0
            while not node_list_received and retry_count < self.MESSAGE_RETRIES:
                try:
                    network_socket = create_socket()
                    network_socket.connect(node)
                    send_to_server(network_socket, 2, json.dumps(self.server_node))
                    message = receive_client_message(network_socket)

                    # If confirm message, get the node list
                    if message == '01':
                        # Get node list
                        type, data, checksum = receive_event_data(network_socket)

                        # Get confirm message that server added node
                        node_added = receive_client_message(network_socket)

                        # If all data valid, proceed
                        if verify_checksum(data, checksum) and type == '02' and node_added == '01':
                            # Node list will be a list of "nodes as list"
                            node_list = json.loads(data)

                            # Add all the new nodes to node_list
                            for L in node_list:
                                new_node = list_to_node(L)
                                if new_node not in self.node_list:
                                    self.node_list.append(new_node)
                                    if new_node != node:
                                        new_nodes.append(new_node)
                            node_list_received = True
                            # Logging
                            print(f'Successfully received node list from {node}')

                        # If checksum fails, retry
                        else:
                            retry_count += 1
                    else:
                        retry_count += 1
                    close_socket(network_socket)

                except ConnectionRefusedError:
                    # Logging
                    print(f'Unable to connect to node {node}')
                    retry_count += 1
        elif node in [self.listening_node, self.local_node, self.server_node]:
            # Logging
            print(f'Cannot connect to own node: {node}')
        elif not self.is_listening:
            # Logging
            print('Event listener not running')

        # Now connect to all new_nodes
        for n in new_nodes:
            self.connect_to_node(n)

        # Send existing transactions
        for tx in self.validated_transactions:
            self.send_transaction_to_network(tx)

        # Get transactions from node
        self.get_transactions_from_node(node)

        # Exchange statuses
        self.send_status_to_network()

        # Achieve consensus
        self.achieve_consensus()

    def __disconnect_from_network(self):
        '''
        Send disconnect message to all nodes in node_list.
        Set to private as we only want this called when we stop event listener
        '''
        # Remove our own port first
        self.node_list.remove(self.server_node)

        # Get iterable list
        node_list = self.node_list.copy()

        # Iterate over all nodes in node_list
        for node in node_list:
            # Allow for retries
            disconnected = False
            retries = 0
            while not disconnected and retries < self.MESSAGE_RETRIES:
                try:
                    client = create_socket()
                    client.connect(node)
                    send_to_server(client, 3, json.dumps(self.server_node))
                    message = receive_client_message(client)
                    if message == '01':
                        # Logging
                        print(f'Disconnect message sent successfully to {node}')
                        self.node_list.remove(node)
                        disconnected = True
                    else:
                        retries += 1
                    close_socket(client)
                except ConnectionRefusedError:
                    # Logging
                    print(f'Unable to send disconnect message to {node}')
                    retries += 1

        # Logging
        print(f'After disconnecting the node_list is {self.node_list}')

    def send_transaction_to_node(self, node: tuple, raw_tx: str):
        '''
        We send a raw_tx to the node
        '''
        if node not in [self.listening_node, self.server_node, self.local_node]:
            connected = False
            retries = 0
            while not connected and retries < self.MESSAGE_RETRIES:
                try:
                    client = create_socket()
                    client.connect(node)
                    send_to_server(client, 4, raw_tx)
                    message = receive_client_message(client)
                    if message == '01':
                        # Logging
                        print(f'Successfully sent transaction to {node}')
                        connected = True
                    else:
                        retries += 1
                    close_socket(client)
                except ConnectionRefusedError:
                    # Logging
                    print(f'Error connecting to {node} for transaction')
                    retries += 1

            if not connected:
                # Logging
                print(f'Failed to send transaction {decode_raw_transaction(raw_tx).id}')
        else:
            # Logging
            print('Cannot send transaction to own node.')

    def send_transaction_to_network(self, raw_tx: str):
        for node in self.node_list:
            if node != self.server_node:
                self.send_transaction_to_node(node, raw_tx)

    def get_transactions_from_node(self, node: tuple):
        '''
        We request the validated transactions from a node
        '''
        if node not in [self.listening_node, self.server_node, self.local_node]:
            connected = False
            retries = 0
            while not connected and retries < self.MESSAGE_RETRIES:
                try:
                    client = create_socket()
                    client.connect(node)
                    send_to_server(client, 5, json.dumps(self.server_node))
                    message = receive_client_message(client)
                    if message == '01':
                        # Logging
                        print(f'Successfully requested transaction from {node}')
                        connected = True
                    else:
                        retries += 1
                    close_socket(client)
                except ConnectionRefusedError:
                    # Logging
                    print(f'Error connecting to {node} for transaction requests')
                    retries += 1

            if not connected:
                # Logging
                print(f'Failed to request transactions from {node}')
        else:
            # Logging
            print('Cannot send transaction to own node.')

    def send_block_to_node(self, node: tuple, raw_block: str):
        '''
        We send a raw block to the node
        '''
        if node not in [self.listening_node, self.server_node, self.local_node]:
            connected = False
            retries = 0
            while not connected and retries < self.MESSAGE_RETRIES:
                try:
                    client = create_socket()
                    client.connect(node)
                    send_to_server(client, 6, raw_block)
                    message = receive_client_message(client)
                    if message == '01':
                        # Logging
                        print(f'Successfully sent block to {node}')
                        connected = True
                    elif message == '03':
                        # Logging
                        print(f'Node at {node} failed to add block. Gain consensus')
                        retries += 1
                        # Gain consensus
                    else:
                        retries += 1
                    close_socket(client)
                except ConnectionRefusedError:
                    # Logging
                    print(f'Error connecting to {node} for transaction')
                    retries += 1

            if not connected:
                # Logging
                print(f'Failed to send block {decode_raw_transaction(raw_block).id}')
        else:
            # Logging
            print('Cannot send block to own node.')

    def send_block_to_network(self, raw_block: str):
        for node in self.node_list:
            if node != self.server_node:
                self.send_block_to_node(node, raw_block)

    def get_indexed_block_from_node(self, node: tuple, index: int):
        '''

        '''
        raw_block = None
        # Allow retries
        block_received = False
        retries = 0
        while not block_received and retries < self.MESSAGE_RETRIES:
            try:
                client = create_socket()
                client.connect(node)
                send_to_server(client, 7, hex(index)[2:])
                message = receive_client_message(client)
                if message == '01':
                    type, data, checksum = receive_event_data(client)
                    if type == '06' and verify_checksum(data, checksum):
                        raw_block = data
                        block_received = True
                    else:
                        # Logging
                        print(f'DataType or checksum error requesting block at index {index} from node {node}')
                        retries += 1
                else:
                    # Logging
                    print(f'Index error received when requesting block at index {index} from node {node}')
                    retries += 1
                close_socket(client)
            except ConnectionRefusedError:
                # Logging
                print(f'Failed to connect to {node} for block at index {index}')
                retries += 1

        return raw_block

    def send_status_to_node(self, node: tuple):
        '''

        '''
        if node not in [self.listening_node, self.server_node, self.local_node]:
            connected = False
            retries = 0
            while not connected and retries < self.MESSAGE_RETRIES:
                try:
                    client = create_socket()
                    client.connect(node)
                    send_to_server(client, 8, json.dumps([self.server_node, self.status]))
                    message = receive_client_message(client)
                    if message == '01':
                        # Logging
                        print(f'Successfully exchanged statuses with {node}')
                        type, data, checksum = receive_event_data(client)
                        if type == '08' and verify_checksum(data, checksum):
                            status = json.loads(data)
                            self.consensus_dict.update({node: status})
                        connected = True
                    else:
                        retries += 1
                    close_socket(client)
                except ConnectionRefusedError:
                    # Logging
                    print(f'Error connecting to {node} for transaction')
                    retries += 1

            if not connected:
                # Logging
                print(f'Failed to send status')
        else:
            # Logging
            print('Cannot send status to own node.')

    def send_status_to_network(self):
        '''

        '''
        for node in self.node_list:
            if node != self.server_node:
                self.send_status_to_node(node)

    # TESTING
    def generate_function(self):
        '''
        We generate a function and add it to the validated_transactions node
        '''
        utxo_list = self.utxos.iloc[0].values
        tx_id = utxo_list[0]
        tx_index = utxo_list[1]
        amount = int(utxo_list[2], 16)
        address = utxo_list[3]

        # Genesis signature
        sig = '420213e322dc11b4f3778896bd72ca96fa79a0bd0a6c986e5057236ecb2bffd54b4c40279202d872ea89f0cbdbbfa3448031d9cb99a4b4efe913b61d8f313070e9badf407deca985023bcfb9634aaf088b8c095e3799d1b31f340c7b0a82b0d90c1d5a36'
        utxo_input = UTXO_INPUT(tx_id, tx_index, sig)
        output1 = UTXO_OUTPUT(amount // 2, self.wallet.address)
        output2 = UTXO_OUTPUT(amount // 2, address)
        new_tx = Transaction(inputs=[utxo_input.raw_utxo], outputs=[output1.raw_utxo, output2.raw_utxo])
        self.add_transaction(new_tx.raw_tx)

    def mine_one_block(self):
        starting_height = self.height
        self.start_miner()
        while self.height == starting_height:
            pass
        self.stop_miner()
