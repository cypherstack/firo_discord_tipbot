import json

import requests


class FiroWalletAPI:

    def __init__(self, httpprovider):
        self.httpprovider = httpprovider

    """
        Create new wallet for new bot member
    """
    def create_user_wallet(self):
        response = requests.post(
            self.httpprovider,
            data=json.dumps(
                {"jsonrpc": "1.0", "id": 1, "method": "getsparkdefaultaddress"}
            )).json()
        print(response)
        return response['result']

    """
        Fetch list of txs
    """
    def get_txs_list(self):
        response = requests.post(
            self.httpprovider,
            data=json.dumps(
                {"jsonrpc": "1.0", "id": 2, "method": "listtransactions", "params": ["*", 100]}
            )).json()

        return response

    def listlelantusmints(self):
        response = requests.post(
            self.httpprovider,
            data=json.dumps(
                {"jsonrpc": "1.0", "id": 2, "method": "listsparkmints"}
            )).json()

        return response

    """
        Get wallet status
    """
    def get_wallet_status(self):
        try:
            response = requests.post(
                self.httpprovider,
                data=json.dumps(
                    {
                        "jsonrpc": "1.0",
                        "id": 6,
                        "method": "getinfo",
                    })).json()

            print(response)
            return response
        except Exception as exc:
            print(exc)

    """
        Get transaction status
    """
    def get_tx_status(self, tx_id):
        response = requests.post(
            self.httpprovider,
            data=json.dumps(
                {
                    "jsonrpc": "1.0",
                    "id": 4,
                    "method": "tx_status",
                    "params":
                        {
                            "txId": "%s" % tx_id
                        }
                })).json()

        print(response)
        return response

    """ 
    """
    def automintunspent(self):
        response = requests.post(
            self.httpprovider,
            data=json.dumps(
                {
                    "jsonrpc": "1.0",
                    "id": 4,
                    "method": "autoMintlelantus",
                })).json()

        print(response)
        return response

    """
        Send Transaction 
    """
    def joinsplit(self, address, value, memo):
        response = requests.post(
            self.httpprovider,
            data=json.dumps(
                {
                    "jsonrpc": "1.0",
                    "id": 4,
                    "method": "spendspark",
                    "params": [{address: {value, memo, False}}]
                })).json()

        print(response)
        return response

    """ 
    """
    def listlelantusjoinsplits(self):
        response = requests.post(
            self.httpprovider,
            data=json.dumps(
                {
                    "jsonrpc": "1.0",
                    "id": 4,
                    "method": "listlelantusjoinsplits",
                    "params": [100]
                })).json()
        print(response)
        return response

    """
        Validate address
    """
    def validate_address(self, address):
        response = requests.post(
            self.httpprovider,
            data=json.dumps(
                {
                    "jsonrpc": "1.0",
                    "id": 1,
                    "method": "validateaddress",
                    "params":
                        {
                            "address": address
                        }
                })).json()
        return response
