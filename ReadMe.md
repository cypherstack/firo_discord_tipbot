## How to deploy Firo Tip bot

Update Ubuntu packages
<pre>sudo apt update</pre>
<pre>sudo apt upgrade</pre>
<pre>sudo apt-get install python3-dev python3-pip python3-virtualenv</pre>

Clone firo tip bot repo:
<pre>git clone https://repo_link</pre>
<pre>cd firo_tipbot</pre>

Install python requirement packages
<pre>pip3 install -r requirements.txt</pre>

To check if the bot works correct (after MangoDB, Firod, and the services.json are set up):
<pre>python3 tipbot.py</pre>
If there's not exceptions, use Ctrl+C to break the process.

### Configure TipBot
<pre>vim /etc/systemd/system/tipbot.service</pre>

Paste
<pre>
[Unit]
Description=firotipbot
After=network.target
After=mongodb.service


[Service]
Type=simple
WorkingDirectory=/root/firo_tipbot
ExecStart=/usr/bin/python3 tipbot.py
EnvironmentFile=/etc/environment
RestartSec=10
SyslogIdentifier=tipbot
TimeoutStopSec=120
TimeoutStartSec=2
StartLimitInterval=120
StartLimitBurst=5
KillMode=mixed
Restart=always
PrivateTmp=true


[Install]
WantedBy=multi-user.target
</pre>

Get your Discord bot token following these instructions.
1) Create your discord server.
2) https://discordapp.com/developers/applications/
3) Click "New Application".
4) Name the bot.
5) Go to "Bot" and click add a bot.
6) Click "Copy" and get the bot_token.
7) Go to "OAuth2" .
   1) Click "bot" in scopes.
   2) add the following bot permissions.
      1) Send Messages
      2) Public Threads
      3) Private Threads
      4) Manage Messages
      5) Attach Files
      6) Read Message History
      7) Use External Emojis
      8) Add Reactions
      9) View Channels.
   3) Copy the url given by the scopes, and enter it in the search bar.
      1) Approve adding the bot to the server of your choice.
8) Create a private channel in your server called tipbot_logs.

Configure the services.json with your relevant information. 
<pre>
... bot_token should be set to your Discord Bots token.
    "discord_bot":
    {
      "bot_token":"your_discord_bot_token_goes_here"
    },
... 
    "httpprovider": "http://username:password@localhost:8888",
    "log_ch": "tipbot_logs",
     "discord_server": "discord_server_name",
    "admins": {
      "yourdiscordname": true
    }
</pre>

Next run

<pre>systemctl daemon-reload</pre>

Run the following systemctl command to start the Tipbot service:
<pre>sudo systemctl start tipbot.service</pre>
 
Then check the service’s status.
<pre>sudo systemctl status tipbot.service</pre>

After confirming that the service is running as expected, enable the Tipbot service to start up at boot:
<pre>sudo systemctl enable tipbot.service</pre>

To stop the service
<pre>sudo systemctl stop tipbot.service</pre>

### Install Mongodb on ubuntu
#### Follow this manual:
https://www.digitalocean.com/community/tutorials/how-to-install-mongodb-on-ubuntu-18-04-source

<pre>curl -fsSL https://www.mongodb.org/static/pgp/server-4.4.asc | sudo apt-key add -</pre>
<pre>echo "deb [ arch=amd64,arm64 ] https://repo.mongodb.org/apt/ubuntu bionic/mongodb-org/4.4 multiverse" | sudo tee /etc/apt/sources.list.d/mongodb-org-4.4.list</pre>
<pre>sudo apt update</pre>
<pre>sudo apt install mongodb-org</pre>

Configure init script
<pre>vim /etc/systemd/system/mongod.service</pre>
<pre>
[Unit]
Description=High-performance, schema-free document-oriented database
After=network.target
Documentation=https://docs.mongodb.org/manual

[Service]
User=mongodb
Group=mongodb
ExecStart=/usr/bin/mongod --quiet --config /etc/mongod.conf
RestartSec=10
TimeoutStopSec=120
TimeoutStartSec=2
StartLimitInterval=120
StartLimitBurst=5
TasksMax=infinity
TasksAccounting=false
KillMode=mixed
Restart=always
PrivateTmp=true

[Install]
WantedBy=multi-user.target
</pre>


<pre>systemctl daemon-reload</pre>

Run the following systemctl command to start the MongoDB service:
<pre>sudo systemctl start mongod.service</pre>
 
Then check the service’s status.
<pre>sudo systemctl status mongod.service</pre>

After confirming that the service is running as expected, enable the MongoDB service to start up at boot:
<pre>sudo systemctl enable mongod.service</pre>

To stop the service
<pre>sudo systemctl stop mongod.service</pre>

## Install Firewall
#### To install Firewall follow instructoins
https://firo.org/guide/masternode-setup.html

We are installing UFW (uncomplicated firewall) to further secure your VPS server. This is optional but highly recommended.

While still in root user on your VPS (or alternatively you can sudo within your newly created user).

<pre>apt install ufw</pre>

(press Y and Enter to confirm)

<pre>ufw allow ssh/tcp</pre>

<pre>ufw limit ssh/tcp</pre>

<pre>ufw logging on</pre>

<pre>ufw enable</pre> 

## How to install Firo Wallet/Node on Ubuntu

#### Download and unzip last release 

<code>wget https://github.com/firoorg/firo/releases/download/v0.14.6.0/firo-0.14.6.0-linux64.tar.gz | tar -xvf</code>

#### Send files to binary folder

<code>cd firo-0.14.6; cp bin/* /usr/local/bin</code>

#### Create config file
nano /root/.firo/firo.config

<pre>
#----
rpcuser=user
rpcpassword=password
rpcallowip=127.0.0.1
rpcport=8332
#----
listen=1
server=1
daemon=1
logtimestamps=1
txindex=1
</pre>

#### Run node as daemon with systemctl
https://github.com/firoorg/firo/wiki/Configuring-masternode-with-systemd

# Firo CLI HELP

<pre>
== Addressindex ==
getaddressbalance
getaddressdeltas
getaddressmempool
getaddresstxids
getaddressutxos
gettotalsupply

== Blockchain ==
clearmempool
getbestblockhash
getblock "blockhash" ( verbose )
getblockchaininfo
getblockcount
getblockhash height
getblockhashes timestamp
getblockheader "hash" ( verbose )
getchaintips
getdifficulty
getmempoolancestors txid (verbose)
getmempooldescendants txid (verbose)
getmempoolentry txid
getmempoolinfo
getrawmempool ( verbose )
getspecialtxes "blockhash" ( type count skip verbosity )
gettxout "txid" n ( include_mempool )
gettxoutproof ["txid",...] ( blockhash )
gettxoutsetinfo
preciousblock "blockhash"
pruneblockchain
verifychain ( checklevel nblocks )
verifytxoutproof "proof"

== Control ==
getinfo
getmemoryinfo
help ( "command" )
stop

== Evo ==
bls "command" ...
protx "command" ...
quorum "command" ...
spork list

== Firo ==
evoznode "command"...
evoznode list ( "mode" "filter" )
evoznsync [status|next|reset]

== Generating ==
generate nblocks ( maxtries )
generatetoaddress nblocks address (maxtries)
setgenerate generate ( genproclimit )

== Mining ==
getblocktemplate ( TemplateRequest )
getmininginfo
getnetworkhashps ( nblocks height )
prioritisetransaction txid priority delta fee delta
submitblock "hexdata" ( "jsonparametersobject" )

== Mobile ==
getanonymityset
getlatestcoinids
getmintmetadata
getusedcoinserials

== Network ==
addnode "node" "add|remove|onetry"
clearbanned
disconnectnode "address"
getaddednodeinfo ( "node" )
getconnectioncount
getnettotals
getnetworkinfo
getpeerinfo
listbanned
ping
setban "subnet" "add|remove" (bantime) (absolute)
setnetworkactive true|false

== Rawtransactions ==
createrawtransaction [{"txid":"id","vout":n},...] {"address":amount,"data":"hex",...} ( locktime )
decoderawtransaction "hexstring"
decodescript "hexstring"
fundrawtransaction "hexstring" ( options )
getrawtransaction "txid" ( verbose )
sendrawtransaction "hexstring" ( allowhighfees )
signrawtransaction "hexstring" ( [{"txid":"id","vout":n,"scriptPubKey":"hex","redeemScript":"hex"},...] ["privatekey1",...] sighashtype )

== Util ==
createmultisig nrequired ["key",...]
estimatefee nblocks
estimatepriority nblocks
estimatesmartfee nblocks
estimatesmartpriority nblocks
signmessagewithprivkey "privkey" "message"
validateaddress "address"
verifymessage "address" "signature" "message"

== Wallet ==
abandontransaction "txid"
addmultisigaddress nrequired ["key",...] ( "account" )
addwitnessaddress "address"
This function automatically mints all unspent transparent funds
backupwallet "destination"
bumpfee "txid" ( options )
dumpprivkey "firoaddress"
dumpwallet "filename"
encryptwallet "passphrase"
getaccount "firoaddress"
getaccountaddress "account"
getaddressesbyaccount "account"
getbalance ( "account" minconf include_watchonly )
getnewaddress ( "account" )
getrawchangeaddress
getreceivedbyaccount "account" ( minconf )
getreceivedbyaddress "firoaddress" ( minconf )
gettransaction "txid" ( include_watchonly )
getunconfirmedbalance
getwalletinfo
importaddress "address" ( "label" rescan p2sh )
importmulti "requests" "options"
importprivkey "firoprivkey" ( "label" ) ( rescan )
importprunedfunds
importpubkey "pubkey" ( "label" rescan )
importwallet "filename"
joinsplit {"address":amount,...} (["address",...] )
keypoolrefill ( newsize )
listaccounts ( minconf include_watchonly)
listaddressbalances ( minamount )
listaddressgroupings
listlelantusjoinsplits
listlelantusmints all(false/true)
listlockunspent
listmintzerocoins all(false/true)
listpubcoins all(1/10/25/50/100)
listreceivedbyaccount ( minconf include_empty include_watchonly)
listreceivedbyaddress ( minconf include_empty include_watchonly)
listsigmamints all(false/true)
listsigmapubcoins all(0.05/0.1/0.5/1/10/25/100)
listsigmaspends
listsinceblock ( "blockhash" target_confirmations include_watchonly)
listspendzerocoins
listtransactions ( "account" count skip include_watchonly)
listunspent ( minconf maxconf  ["addresses",...] [include_unsafe] )
listunspentsigmamints [minconf=1] [maxconf=9999999]
listunspentmintzerocoins [minconf=1] [maxconf=9999999]
resetlelantusmint
resetmintzerocoin
resetsigmamint
sendfrom "fromaccount" "toaddress" amount ( minconf "comment" "comment_to" )
sendmany "fromaccount" {"address":amount,...} ( minconf "comment" ["address",...] )
sendtoaddress "firoaddress" amount ( "comment" "comment-to" subtractfeefromamount )
setaccount "firoaddress" "account"
setlelantusmintstatus "coinserial" isused(true/false)
setmininput amount
setmintzerocoinstatus "coinserial" isused(true/false)
setsigmamintstatus "coinserial" isused(true/false)
settxfee amount
signmessage "firoaddress" "message"
spendmany "fromaccount" {"address":amount,...} ( minconf "comment" ["address",...] )
spendmanyzerocoin "{"address":"third party address or blank for internal", "denominations": [{"value":(1,10,25,50,100), "amount":}, {"value":(1,10,25,50,100), "amount":},...]}"
spendzerocoin amount(1,10,25,50,100) ("firoaddress")
</pre>


#### Curl Request 

<code>curl --data-binary '{"jsonrpc": "1.0", "id":"curltest", "method": "getbalance"}' http://user:password@127.0.0.1:8332</code>

<code> curl --data-binary '{"jsonrpc": "1.0", "id":"curltest", "method": "getaddressbalance", "params": [{"addresses": ["XwnLY9Tf7Zsef8gMGL2fhWA9ZmMjt4KPwg"]}] }' -H 'content-type: text/plain;' http://user:password@127.0.0.1:8332</code>
