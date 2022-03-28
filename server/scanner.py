import os
import requests

from dotenv import load_dotenv
from tqdm import tqdm
from web3 import Web3
from web3.providers.rpc import HTTPProvider
from web3._utils.filters import construct_event_filter_params
from web3._utils.events import get_event_data

from abi import ERC721_ABI
from db import Database

class Scanner:
    def __init__(self, rpc_url: str, db: Database) -> None:
        provider = HTTPProvider(rpc_url)
        self.web3 = Web3(provider)
        self.ERC721 = self.web3.eth.contract(abi=ERC721_ABI)
        self.db = db

        self.transfer_event = self.ERC721.events.Transfer
        self.event_abi = self.transfer_event._get_event_abi()
        self.codec = self.web3.codec

        self.previous_block_num = self.web3.eth.block_number - 1

    def _is_erc721_log(self, log: dict) -> bool:
        """
            Note: for ERC721 tokens, there should be 1 signature + 3 indexed arguments
                = 4 topics
        """
        return len(log['topics']) == 4

    def _get_event_metadata(self, event):
        args = event['args']
        metadata = {}
        metadata['sender'] = args['from']
        metadata['receiver'] = args['to']
        metadata['token_id'] = args['tokenId']
        metadata['contract_address'] = event['address']
        metadata['tx_hash'] = event['transactionHash'].hex()
        return metadata

    def _get_nft_metadata(self, nft_contract, token_id):
        metadata = {}
        metadata['name'] = nft_contract.functions.name().call()
        metadata['token_uri'] = nft_contract.functions.tokenURI(
            token_id).call()
        return metadata

    def _fetch_nft_metadata(self, token_uri):
        if token_uri.startswith('ipfs://'):
            token_uri = token_uri.replace('ipfs://', 'https://ipfs.io/ipfs/')
        response = requests.get(token_uri)
        # print(f'[{response.status_code}] GET {token_uri}')
        nft_metadata = response.json()
        return nft_metadata

    def scan(self, limit: int = 50):
        
        latest_block_num = self.web3.eth.block_number
        if latest_block_num <= self.previous_block_num:
            return

        _, event_filter_params = construct_event_filter_params(
            self.event_abi,
            self.codec,
            fromBlock='latest'
        )
        self.previous_block_num = latest_block_num

        logs = self.web3.eth.get_logs(event_filter_params)
        result_cnt = 0
        print(f'Got {len(logs)} token transfer events')

        for log in tqdm(logs):
            if not self._is_erc721_log(log):
                continue
            if result_cnt >= limit:
                break
            try:
                event = get_event_data(self.codec, self.event_abi, log)
                event_metadata = self._get_event_metadata(event)

                nft_contract = self.web3.eth.contract(
                    abi=ERC721_ABI, address=event_metadata['contract_address'])

                event_metadata['nft_name'] = nft_contract.functions.name().call()
                event_metadata['token_uri'] = nft_contract.functions.tokenURI(
                    event_metadata['token_id']).call()

                nft_metadata = self._fetch_nft_metadata(
                    event_metadata['token_uri'])
                if 'image' in nft_metadata:
                    nft_metadata['image'] = nft_metadata['image'].replace('ipfs://', 'https://ipfs.io/ipfs/')
                    event_metadata['nft_metadata'] = nft_metadata
                    self.db.insert(event_metadata)
                    result_cnt += 1
            except Exception as err:
                # print(err)
                continue
        print(f'Got {result_cnt} NFT transfer events')


if __name__ == '__main__':
    load_dotenv()
    rpc_url = os.environ['ETH_RPC_URL']
    scanner = Scanner(rpc_url)
    print(scanner.scan())
