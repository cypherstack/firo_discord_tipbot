"""
    Developed by @vsnation(t.me/vsnation)
    Email: vsnation.v@gmail.com
    If you'll need the support use the contacts ^(above)!
"""
import json
import logging
import threading
import traceback
import random
import pyqrcode
import schedule
import re
from PIL import Image, ImageFont, ImageDraw
import matplotlib.pyplot as plt
import datetime
import time
import discord
from discord.ext import tasks
import asyncio
from pymongo import MongoClient
import uuid
import png
from api.firo_wallet_api import FiroWalletAPI

plt.style.use('seaborn-whitegrid')

logger = logging.getLogger()
logger.setLevel(logging.ERROR)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

AV_FEE = 0.002

with open('services.json') as conf_file:
    conf = json.load(conf_file)
    connectionString = conf['mongo']['connectionString']
    bot_token = conf['discord_bot']['bot_token']
    httpprovider = conf['httpprovider']
    dictionary = conf['dictionary']
    LOG_CHANNEL = conf['log_ch']
    SERVER = conf['discord_server']
    admins = conf['admins']

SATS_IN_BTC = 1e8

wallet_api = FiroWalletAPI(httpprovider)

point_to_pixels = 1.33
bold = ImageFont.truetype(font="fonts/ProximaNova-Bold.ttf", size=int(18 * point_to_pixels))
regular = ImageFont.truetype(font="fonts/ProximaNova-Regular.ttf", size=int(18 * point_to_pixels))
bold_high = ImageFont.truetype(font="fonts/ProximaNova-Bold.ttf", size=int(26 * point_to_pixels))

WELCOME_MESSAGE = """
**Welcome to the Firo telegram tip bot!** 
"""

# Firo Butler Initialization
client = MongoClient(connectionString)
db = client.get_default_database()
col_captcha = db['captcha']
col_commands_history = db['commands_history']
col_users = db['users']
col_senders = db['senders']
col_tip_logs = db['tip_logs']
col_envelopes = db['envelopes']
col_txs = db['txs']

bot = discord.Client(intents=discord.Intents.default())

last_channel = 0
last_user = ""
admin_channel = None


async def send_to_logs(text):
    try:
        guild = discord.utils.get(bot.guilds, name=SERVER)
        if guild is not None:
            ch = discord.utils.get(guild.text_channels, name=LOG_CHANNEL)
            print("GETTING LOGS CHANNEL")
            print(text)
            await ch.send(text)
        else:
            print("Error: Cannot find logs server, please check the services.json file to see if it is set correctly.")
            print(text)
    except Exception as exc:
        print(exc)


async def get_wallet_balance():
    try:
        r = wallet_api.listlelantusmints()
        result = sum([_x['amount'] for _x in r['result'] if not _x['isUsed']])
        print("Current Balance", result / 1e8)
        return result
    except Exception as exc:
        await send_to_logs(exc)
        return 0


asyncio.run(get_wallet_balance())


async def clean_html(string_html_):
    clean_regex = re.compile('<.*?>')
    clean_text = re.sub(clean_regex, '', string_html_)
    return clean_text


async def send_message(target, text):
    try:
        response = ""
        await target.send(text)
        return response
    except Exception as exc:
        await send_to_logs(exc)


async def create_send_tips_image(user_id, amount, first_name, comment=""):
    try:
        im = Image.open("images/send_template.png")

        d = ImageDraw.Draw(im)
        location_f = (276, 21)
        location_s = (276, 45)
        location_t = (276, 67)
        d.text(location_f, "%s Firo" % "{0:.4f}".format(float(amount)), font=bold, fill='#000001')
        d.text(location_s, "tip was sent to", font=regular, fill='#000000')
        d.text(location_t, "%s" % first_name, font=bold, fill='#000000')
        send_img = 'send.png'
        im.save(send_img)
        target = await bot.fetch_user(user_id)
        if comment == "":
            await target.send(file=discord.File(send_img))
        else:
            com = await clean_html(comment)
            await target.send("**Comment:** *%s*" % com, file=discord.File(send_img))

    except Exception as exc:
        try:
            await send_to_logs(exc)
            group_channel = await bot.fetch_channel(last_channel)
            if '403' in str(exc):
                await group_channel.send(
                    "%s **needs to unblock the bot in order to check their balance!**" % user_id)
            traceback.print_exc()
        except Exception as exc:
            await send_to_logs(exc)


async def create_receive_tips_image(user_id, amount, first_name, comment=""):
    try:
        im = Image.open("images/receive_template.png")
        d = ImageDraw.Draw(im)

        location_f = (266, 21)
        location_s = (266, 45)
        location_t = (266, 67)
        if "Deposit" in first_name:
            d.text(location_f, "%s" % first_name, font=bold, fill='#000000')
            d.text(location_s, "has recharged", font=regular, fill='#000000')
            d.text(location_t, "%s Firo" % "{0:.4f}".format(float(amount)), font=bold, fill='#000000')

        else:
            d.text(location_f, "%s" % first_name, font=bold, fill='#000000')
            d.text(location_s, "sent you a tip of", font=regular, fill='#000000')
            d.text(location_t, "%s Firo" % "{0:.4f}".format(float(amount)), font=bold, fill='#000000')

        receive_img = 'receive.png'
        im.save(receive_img)
        target = await bot.fetch_user(user_id)
        if comment == "":
            await target.send(file=discord.File(receive_img))
        else:
            com = await clean_html(comment)
            await target.send("**Comment:** *%s*" % com, file=discord.File(receive_img))

    except Exception as exc:
        try:
            await send_to_logs(exc)
            group_channel = await bot.fetch_channel(last_channel)
            if '403' in str(exc):
                await group_channel.send(
                    "%s**needs to unblock the bot in order to check their balance!**" % user_id)
            traceback.print_exc()
        except Exception as exc:
            await send_to_logs(exc)


async def update_balance():
    """
        Update user's balance using transactions history
    """
    print("Handle TXs")

    response = wallet_api.get_txs_list()
    for _tx in response['result']:
        try:

            if not _tx.get('address'):
                continue

            """
                Check withdraw txs    
            """
            _user_receiver = col_users.find_one(
                {"Address": _tx['address']}
            )
            _is_tx_exist_deposit = col_txs.find_one(
                {"txId": _tx['txid'], "type": "deposit"}
            ) is not None

            if _user_receiver is not None and \
                    not _is_tx_exist_deposit and \
                    _tx['confirmations'] >= 2 and _tx['category'] == 'receive':
                value_in_coins = float(_tx['amount'])
                new_balance = _user_receiver['Balance'] + value_in_coins

                _id = str(uuid.uuid4())
                col_txs.insert_one({
                    '_id': _id,
                    'txId': _tx['txid'],
                    **_tx,
                    'type': "deposit",
                    'timestamp': datetime.datetime.now()
                })
                col_users.update_one(
                    _user_receiver,
                    {
                        "$set":
                            {
                                "Balance": float("{0:.8f}".format(float(new_balance)))
                            }
                    }
                )
                await create_receive_tips_image(
                    _user_receiver['_id'],
                    "{0:.8f}".format(value_in_coins),
                    "Deposit")

                print("*Deposit Success*\n"
                      "Balance of address %s has recharged on *%s* firos." % (
                          _tx['address'], value_in_coins
                      ))
                continue

            _is_tx_exist_withdraw = col_txs.find_one(
                {"txId": _tx['txid'], "type": "withdraw"}
            ) is not None

            pending_sender = col_senders.find_one(
                {"txId": _tx['txid'], "status": "pending"}
            )
            if not pending_sender:
                continue
            _user_sender = col_users.find_one({"_id": pending_sender['user_id']})
            if _user_sender is not None and not _is_tx_exist_withdraw and _tx['category'] == "spend":

                value_in_coins = float((abs(_tx['amount'])))

                #
                # if _tx['status'] == 4 or _tx['status'] == 2:
                #     await withdraw_failed_image(_user_sender['_id'])
                #     try:
                #         reason = _tx['failure_reason']
                #     except Exception:
                #         reason = "cancelled"
                #     col_txs.insert({
                #         "txId": _tx['txid'],
                #         'kernel': '000000000000000000',
                #         'receiver': _tx['receiver'],
                #         'sender': _tx['sender'],
                #         'status': _tx['status'],
                #         'fee': _tx['fee'],
                #         'reason': reason,
                #         'comment': _tx['comment'],
                #         'value': _tx['value'],
                #         'type': "withdraw",
                #         'timestamp': datetime.datetime.now()
                #     })
                #
                #     new_locked = float(_user_sender['Locked']) - value_in_coins
                #     new_balance = float(_user_sender['Balance']) + value_in_coins
                #
                #     col_users.update_one(
                #         {
                #             "_id": _user_sender['_id']
                #         },
                #         {
                #             "$set":
                #                 {
                #                     "IsWithdraw": False,
                #                     "Balance": float("{0:.8f}".format(float(new_balance))),
                #                     "Locked": float("{0:.8f}".format(float(new_locked)))
                #                 }
                #         }
                #     )

                if _tx['confirmations'] >= 2:
                    _id = str(uuid.uuid4())
                    col_txs.insert_one({
                        '_id': _id,
                        "txId": _tx['txid'],
                        **_tx,
                        'type': "withdraw",
                        'timestamp': datetime.datetime.now()
                    })
                    new_locked = float(_user_sender['Locked']) - value_in_coins
                    if new_locked >= 0:
                        col_users.update_one(
                            {
                                "_id": _user_sender['_id']
                            },
                            {
                                "$set":
                                    {
                                        "Locked": float("{0:.8f}".format(new_locked)),
                                        "IsWithdraw": False
                                    }
                            }
                        )
                    else:
                        new_balance = float(_user_sender['Balance']) - value_in_coins
                        col_users.update_one(
                            {
                                "_id": _user_sender['_id']
                            },
                            {
                                "$set":
                                    {
                                        "Balance": float("{0:.8f}".format(new_balance)),
                                        "IsWithdraw": False
                                    }
                            }
                        )

                    await create_send_tips_image(_user_sender['_id'],
                                                 "{0:.8f}".format(float(abs(_tx['amount']))),
                                                 "%s..." % _tx['address'][:8])

                    col_senders.update_one(
                        {"txId": _tx['txid'], "status": "pending", "user_id": _user_sender['_id']},
                        {"$set": {"status": "completed"}}
                    )
                    print("*Withdrawal Success*\n"
                          "Balance of address %s has recharged on *%s* firos." % (
                              _user_sender['Address'], value_in_coins
                          ))
                    continue

        except Exception as exc:
            await send_to_logs(exc)
            traceback.print_exc()


asyncio.run(update_balance())


class ImportantVariables:
    def __init__(self):
        self.message, self.text, self.is_video, self.message_text, self.first_name, self.username, self.user_id, self.firo_address, self.balance_in_firo, self.locked_in_firo, self.is_withdraw, self.balance_in_growth, self.is_verified, self.group_id, self.group_username, self.is_user_in_db, self.is_dm = \
            None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None


@tasks.loop(seconds=60)
async def loop_update_balance():
    await update_balance()


schedule.every(300).seconds.do(wallet_api.automintunspent)


def pending_tasks():
    while True:
        schedule.run_pending()
        time.sleep(5)


threading.Thread(target=pending_tasks).start()


async def get_user_data(user_id):
    """
        Get user data
    """
    try:
        _user = col_users.find_one({"_id": user_id})
        return _user['Address'], _user['Balance'], _user['Locked'], _user['IsWithdraw']
    except Exception as exc:
        await send_to_logs(exc)
        traceback.print_exc()
        return None, None, None, None


async def check_username_on_change(variables):
    """
        Check username on change in the bot
    """
    _is_username_in_db = col_users.find_one(
        {"username": variables.username}) is not None \
        if variables.username is not None \
        else True
    if not _is_username_in_db:
        col_users.update_one(
            {
                "_id": variables.user_id
            },
            {
                "$set":
                    {
                        "username": variables.username
                    }
            }
        )

    _is_first_name_in_db = col_users.find_one(
        {"first_name": variables.first_name}) is not None if variables.first_name is not None else True
    if not _is_first_name_in_db:
        col_users.update_one(
            {
                "_id": variables.user_id
            },
            {
                "$set":
                    {
                        "first_name": variables.first_name
                    }
            }
        )


async def incorrect_parameters_image(variables):
    try:
        im = Image.open("images/incorrect_parameters_template.png")

        d = ImageDraw.Draw(im)
        location_text = (230, 62)

        d.text(location_text, "Incorrect parameters", font=bold,
               fill='#000000')

        image_name = 'incorrect_parameters.png'
        im = im.convert("RGB")
        im.save(image_name)
        await variables.message.author.send(dictionary['incorrect_parameters'], file=discord.File(image_name))
    except Exception as exc:
        await send_to_logs(exc)
        traceback.print_exc()


async def tip_in_the_chat(variables, amount, comment="", _type=None):
    """
        Send a tip to user in the chat
    """
    try:
        try:
            amount = float(amount)
            if amount < 0.00000001:
                raise Exception
        except Exception as exc:
            await incorrect_parameters_image(variables)
            await send_to_logs(exc)
            traceback.print_exc()
            return

        tip_to = await variables.message.channel.fetch_message(variables.message.reference.message_id)

        await send_tip(variables,
                       tip_to.author.id,
                       amount,
                       _type,
                       comment
                       )

    except Exception as exc:
        await send_to_logs(exc)
        traceback.print_exc()


async def insufficient_balance_image(variables):
    try:
        im = Image.open("images/insufficient_balance_template.png")

        d = ImageDraw.Draw(im)
        location_text = (230, 62)

        d.text(location_text, "Insufficient Balance", font=bold, fill='#000000')

        image_name = 'insufficient_balance.png'
        im = im.convert("RGB")
        im.save(image_name)
        try:
            await variables.message.author.send(
                dictionary['incorrect_balance'] % "{0:.8f}".format(float(variables.balance_in_firo)),
                file=discord.File(image_name))
        except Exception as exc:
            await send_to_logs(exc)
    except Exception as exc:
        await send_to_logs(exc)
        traceback.print_exc()


async def send_tip(variables, user_id, amount, _type, comment):
    """
        Send tip to user with params
        user_id - user identifier
        address - user address
        amount - amount of a tip
    """
    try:
        if variables.user_id == user_id:
            await send_message(
                variables.message.author,
                "**You can't send tips to yourself!**"
            )
            return

        _user_receiver = col_users.find_one({"_id": user_id})

        if _user_receiver is None or _user_receiver['IsVerified'] is False:
            await send_message(variables.message.author,
                               dictionary['username_error'])
            return

        if _type == 'anonymous':
            sender_name = str(_type).title()
        else:
            sender_name = variables.first_name

        if variables.balance_in_firo >= amount > 0:
            try:

                await create_send_tips_image(
                    variables.user_id,
                    "{0:.8f}".format(float(amount)),
                    _user_receiver['first_name'],
                    comment
                )

                await create_receive_tips_image(
                    _user_receiver['_id'],
                    "{0:.8f}".format(float(amount)),
                    sender_name,
                    comment
                )

                col_users.update_one(
                    {
                        "_id": variables.user_id
                    },
                    {
                        "$set":
                            {
                                "Balance": float(
                                    "{0:.8f}".format(float(float(variables.balance_in_firo) - float(amount))))
                            }
                    }
                )
                col_users.update_one(
                    {
                        "_id": _user_receiver['_id']
                    },
                    {
                        "$set":
                            {
                                "Balance": float(
                                    "{0:.8f}".format(float(float(_user_receiver['Balance']) + float(amount))))
                            }
                    }
                )

                if _type == 'anonymous':
                    col_tip_logs.insert(
                        {
                            "type": "atip",
                            "from_user_id": user_id,
                            "to_user_id": _user_receiver['_id'],
                            "amount": amount
                        }
                    )

                else:
                    col_tip_logs.insert(
                        {
                            "type": "tip",
                            "from_user_id": user_id,
                            "to_user_id": _user_receiver['_id'],
                            "amount": amount
                        }
                    )

            except Exception as exc:
                await send_to_logs(exc)
                traceback.print_exc()

        else:
            await insufficient_balance_image(variables)
    except Exception as exc:
        await send_to_logs(exc)
        traceback.print_exc()


async def tip_user(variables, username, amount, comment, _type=None):
    """
        Tip user with params:
        username
        amount
    """
    try:
        try:
            amount = float(amount)
            if amount < 0.00000001:
                raise Exception
        except Exception as exc:
            await incorrect_parameters_image(variables)
            await send_to_logs(exc)
            traceback.print_exc()
            return

        username = username.replace('@', '')

        _user = col_users.find_one({"username": username})
        _is_username_exists = _user is not None

        if not _is_username_exists:
            await send_message(variables.message.author,
                               dictionary['username_error'])
            return

        await send_tip(variables, _user['_id'], amount, _type, comment)

    except Exception as exc:
        await send_to_logs(exc)
        traceback.print_exc()


async def red_envelope_created(variables, first_name):
    im = Image.open("images/red_envelope_created.png")

    d = ImageDraw.Draw(im)
    location_who = (230, 35)
    location_note = (256, 70)

    d.text(location_who, "%s CREATED" % first_name, font=bold, fill='#000000')
    d.text(location_note, "A RED ENVELOPE", font=bold,
           fill='#f72c56')
    image_name = 'created.png'
    im.save(image_name)
    try:
        message = await variables.message.channel.send('Catch Firo✋Please react to the message!', file=discord.File(image_name))
        return message.id
    except Exception as exc:
        await send_to_logs(exc)
        return 0


async def red_envelope_ended(target):
    im = Image.open("images/red_envelope_ended.png")

    d = ImageDraw.Draw(im)
    location_who = (256, 41)
    location_note = (306, 75)

    d.text(location_who, "RED ENVELOPE", font=bold, fill='#000000')
    d.text(location_note, "ENDED", font=bold, fill='#f72c56')
    image_name = 'ended.png'
    im.save(image_name)
    try:
        await target.send(file=discord.File(image_name))
    except Exception as exc:
        await send_to_logs(exc)


async def create_red_envelope(variables, amount):
    try:
        amount = float(amount)

        if amount < 0.001:
            await incorrect_parameters_image(variables)
            return

        if variables.balance_in_firo >= amount:
            envelope_id = str(uuid.uuid4())[:8]

            col_users.update_one(
                {
                    "_id": variables.user_id
                },
                {
                    "$set":
                        {
                            "Balance": float("{0:.8f}".format(float(variables.balance_in_firo) - amount))
                        }
                }
            )

            msg_id = await red_envelope_created(variables, variables.first_name[:8])

            col_envelopes.insert_one(
                {
                    "_id": envelope_id,
                    "amount": amount,
                    "remains": amount,
                    "group_id": variables.group_id,
                    "group_username": variables.group_username,
                    "group_type": "text",
                    "creator_id": variables.user_id,
                    "msg_id": msg_id,
                    "takers": [],
                    "created_at": int(datetime.datetime.now().timestamp())
                }
            )
        else:
            await insufficient_balance_image(variables)

    except Exception as exc:
        await incorrect_parameters_image(variables)
        await send_to_logs(exc)


async def delete_tg_message(user_id, message_id):
    try:
        found = await user_id.fetch_message(message_id)
        await found.delete()
    except Exception:
        pass


async def red_envelope_caught(target, amount):
    try:
        im = Image.open("images/red_envelope_caught.png")

        d = ImageDraw.Draw(im)
        location_transfer = (236, 35)
        location_amount = (256, 65)
        location_address = (205, 95)

        d.text(location_transfer, "You caught", font=bold, fill='#000000')
        d.text(location_amount, "%s Firo" % amount, font=bold, fill='#f72c56')
        d.text(location_address, "FROM A RED ENVELOPE", font=regular, fill='#000000')
        image_name = 'caught.png'
        im.save(image_name)
        try:
            await target.send(file=discord.File(image_name))
        except Exception as exc:
            await send_to_logs(exc)
    except Exception as exc:
        await send_to_logs(exc)
        traceback.print_exc()


async def catch_envelope(variables):
    try:
        envelope = col_envelopes.find_one({"msg_id": variables.message.id})
        _is_envelope_exist = envelope is not None
        _is_ended = envelope['remains'] == 0
        _is_user_caught = str(variables.user_id) in str(envelope['takers'])
        target = await bot.fetch_user(variables.user_id)

        if variables.balance_in_firo is None:
            await send_message(target, "You need to set up a firo tipbot account first to catch an envelope. Try !start")
            return

        if _is_user_caught:
            await send_message(target, "❗️You have already caught Firo from this envelope❗️")
            return

        if _is_ended:
            await send_message(variables.message.channel, "❗RED ENVELOPE ENDED❗️")
            await red_envelope_ended(variables.message.channel)
            await delete_tg_message(variables.message.channel, variables.message.id)
            return

        if _is_envelope_exist:
            minimal_amount = 0.001
            if envelope['remains'] <= minimal_amount:
                catch_amount = envelope['remains']
            else:
                if len(envelope['takers']) < 5:
                    catch_amount = float(
                        "{0:.8f}".format(float(random.uniform(minimal_amount, envelope['remains'] / 2))))
                else:
                    catch_amount = float(
                        "{0:.8f}".format(float(random.uniform(minimal_amount, envelope['remains']))))

            new_remains = float("{0:.8f}".format(envelope['remains'] - catch_amount))
            if new_remains < 0:
                new_remains = 0
                catch_amount = envelope['remains']

            col_envelopes.update_one(
                {
                    "msg_id": variables.message.id,
                },
                {
                    "$push": {
                        "takers": [variables.user_id, catch_amount]
                    },
                    "$set": {
                        "remains": new_remains
                    }
                }
            )
            col_users.update_one(
                {
                    "_id": variables.user_id
                },
                {
                    "$set":
                        {
                            "Balance": float("{0:.8f}".format(float(variables.balance_in_firo) + catch_amount))
                        }
                }
            )
            try:
                if envelope['group_username'] != "None":
                    msg_text = '*%s caught %s Firo from a RED ENVELOPE*' % (
                        variables.username,
                        "{0:.8f}".format(catch_amount),
                    )
                else:
                    msg_text = '*%scaught %s Firo from a RED ENVELOPE*' % (
                        variables.username,
                        "{0:.8f}".format(catch_amount),
                    )

                await send_message(
                    variables.message.channel,
                    text=msg_text
                )

                _is_ended = new_remains == 0
                if _is_ended:
                    await send_message(variables.message.channel, "❗RED ENVELOPE ENDED❗️")
                    await red_envelope_ended(variables.message.channel)
                    await delete_tg_message(variables.message.channel, variables.message.id)
            except Exception:
                traceback.print_exc()

            await send_message(target, "✅YOU CAUGHT %s Firo from ENVELOPE✅️" % catch_amount)
            await red_envelope_caught(target, "{0:.8f}".format(catch_amount))

    except Exception as exc:
        await send_to_logs(exc)


async def withdraw_image(user_id, amount, address, msg=None):
    try:
        im = Image.open("images/withdraw_template.png")

        d = ImageDraw.Draw(im)
        location_transfer = (256, 21)
        location_amount = (276, 45)
        location_address = (256, 65)

        d.text(location_transfer, "Transaction transfer", font=regular,
               fill='#000000')
        d.text(location_amount, "%s Firo" % amount, font=bold, fill='#000001')
        d.text(location_address, "to %s..." % address[:8], font=bold,
               fill='#000000')
        image_name = 'withdraw.png'
        im.save(image_name)
        await user_id.send(msg, file=discord.File(image_name))
    except Exception as exc:
        await send_to_logs(exc)
        traceback.print_exc()


async def withdraw_coins(variables, address, amount):
    """
        Withdraw coins to address with params:
        address
        amount
    """
    try:

        try:
            amount = float(amount)
        except Exception as exc:
            await send_message(variables.message.author,
                               dictionary['incorrect_amount'])
            await send_to_logs(exc)
            traceback.print_exc()
            return

        _is_address_valid = wallet_api.validate_address(address)['result']['isvalid']
        if not _is_address_valid:
            await send_message(
                variables.message.author,
                "**You specified incorrect address**"
            )
            return

        if float(variables.balance_in_firo) >= float("{0:.8f}".format(amount)) and float(
                variables.balance_in_firo) >= AV_FEE:

            _user = col_users.find_one({"_id": variables.user_id})

            new_balance = float("{0:.8f}".format(float(variables.balance_in_firo - amount)))
            new_locked = float("{0:.8f}".format(float(variables.locked_in_firo + amount - AV_FEE)))
            response = wallet_api.joinsplit(
                address,
                float(amount - AV_FEE),  # fee
            )
            print(response, "withdraw")
            if response.get('error'):
                await send_message(
                    variables.message.author, "Not enough inputs. Try to repeat a bit later!"
                )
                await send_to_logs(f"Unavailable Withdraw\n{str(response)}")
                return

            col_senders.insert_one(
                {"txId": response['result'], "status": "pending", "user_id": variables.user_id}
            )
            col_users.update_one(
                {
                    "_id": variables.user_id
                },
                {
                    "$set":
                        {
                            "Balance": new_balance,
                            "Locked": new_locked,
                        }
                }
            )
            await withdraw_image(variables.message.author,
                                 "{0:.8f}".format(float(amount)),
                                 address,
                                 msg=f"Your txId {response['result']}")

        else:
            await insufficient_balance_image(variables)

    except Exception as exc:
        await send_to_logs(exc)
        traceback.print_exc()


async def create_qr_code(variables):
    try:
        url = pyqrcode.create(variables.firo_address)
        url.png('qrcode.png', scale=6, module_color="#000000",
                background="#d8e4ee")
        time.sleep(0.5)
        await variables.message.author.send(file=discord.File('qrcode.png'))
    except Exception as exc:
        await send_to_logs(exc)


async def create_wallet_image(variables, public_address):
    try:
        im = Image.open("images/create_wallet_template.png")

        d = ImageDraw.Draw(im)
        location_transfer = (258, 32)

        d.text(location_transfer, "Wallet created", font=bold,
               fill='#000000')
        image_name = 'create_wallet.png'
        im.save(image_name)
        await variables.message.author.send(dictionary['welcome'] % public_address, file=discord.File(image_name))
    except Exception as exc:
        await send_to_logs(exc)
        traceback.print_exc()


async def auth_user(variables):
    try:
        if variables.firo_address is None:
            public_address = wallet_api.create_user_wallet()
            if not variables.is_verified:
                await send_message(
                    variables.message.author,
                    WELCOME_MESSAGE
                )

                col_users.update_one(
                    {
                        "_id": variables.user_id
                    },
                    {
                        "$set":
                            {
                                "IsVerified": True,
                                "Address": public_address,
                                "Balance": 0,
                                "Locked": 0,
                                "IsWithdraw": False
                            }
                    }, upsert=True
                )
                await create_wallet_image(variables, public_address)

            else:
                col_users.update_one(
                    {
                        "_id": variables.user_id
                    },
                    {
                        "$set":
                            {
                                "_id": variables.user_id,
                                "first_name": variables.first_name,
                                "username": variables.username,
                                "IsVerified": True,
                                "JoinDate": datetime.datetime.now(),
                                "Address": public_address,
                                "Balance": 0,
                                "Locked": 0,
                                "IsWithdraw": False,
                            }
                    }, upsert=True
                )

                await send_message(
                    variables.message.author,
                    WELCOME_MESSAGE
                )
                await create_wallet_image(variables, public_address)

        else:
            col_users.update_one(
                {
                    "_id": variables.user_id
                },
                {
                    "$set":
                        {
                            "IsVerified": True,
                        }
                }, upsert=True
            )
            await send_message(
                variables.message.author,
                WELCOME_MESSAGE
            )
    except Exception as exc:
        await send_to_logs(exc)
        traceback.print_exc()


async def withdraw_failed_image(user_id):
    try:
        im = Image.open("images/withdraw_failed_template.png")

        d = ImageDraw.Draw(im)
        location_text = (230, 52)

        d.text(location_text, "Withdraw failed", font=bold, fill='#000000')

        image_name = 'withdraw_failed.png'
        im.save(image_name)
        await user_id.send(dictionary['withdrawal_failed'], file=discord.File(image_name))
    except Exception as exc:
        await send_to_logs(exc)
        traceback.print_exc()


async def action_processing(cmd, args, variables):
    """
        Check each user actions
    """

    if variables.username in admins:
        if cmd.startswith("!botbalance"):
            balance = await get_wallet_balance()
            await send_to_logs("Current Balance in Bot: **" + str(balance / 1e8) + "**")
        if cmd.startswith("!help"):
            await send_to_logs("For admins:\nType !botbalance to see the total balance that the bot is holding")

    if cmd.startswith("!deposit") or cmd.startswith("!withdraw") or cmd.startswith("!balance") or \
            cmd.startswith("!envelope") or cmd.startswith("!tip") or cmd.startswith("!atip"):
        if not variables.is_user_in_db:
            await send_message(variables.message.channel,
                               f'{variables.first_name}, start the bot to receive tips!')
            return

    # ***** Tip bot section begin *****
    if cmd.startswith("!tip") or cmd.startswith("!atip"):
        try:
            if args is not None and len(args) >= 1:
                if cmd.startswith("!atip"):
                    _type = "anonymous"
                else:
                    _type = None

                if variables.message.reference is not None:
                    comment = " ".join(args[1:]) if len(args) > 1 else ""
                    args = args[0:1]
                    await tip_in_the_chat(variables, *args, _type=_type, comment=comment)
                else:
                    comment = " ".join(args[2:]) if len(args) > 2 else ""
                    args = args[0:2]
                    await tip_user(variables, *args, _type=_type, comment=comment, )
            else:
                await incorrect_parameters_image(variables)
                await send_message(variables.message.author,
                                   dictionary['tip_help']
                                   )
        except Exception as exc:
            await send_to_logs(exc)
            await incorrect_parameters_image(variables)
            await send_message(variables.message.author,
                               dictionary['tip_help']
                               )

    elif cmd.startswith("!envelope"):
        try:
            await variables.message.delete()
        except Exception:
            pass

        if variables.is_dm:
            await send_message(variables.message.author,
                               "**You can use this cmd only in the group**"
                               )
            return

        try:
            if args is not None and len(args) == 1:
                await create_red_envelope(variables, *args)
            else:
                await incorrect_parameters_image(variables)
        except Exception as exc:
            await send_to_logs(exc)
            await incorrect_parameters_image(variables)

    elif cmd.startswith("!balance"):
        await send_message(variables.message.author,
                           dictionary['balance'] % "{0:.8f}".format(float(variables.balance_in_firo))
                           )

    elif cmd.startswith("!withdraw"):
        try:
            if args is not None and len(args) == 2:
                await withdraw_coins(variables, *args)
            else:
                await incorrect_parameters_image(variables)
        except Exception as exc:
            await send_to_logs(exc)
            traceback.print_exc()

    elif cmd.startswith("!deposit"):
        await send_message(variables.message.author,
                           dictionary['deposit'] % variables.firo_address
                           )
        await create_qr_code(variables)

    elif cmd.startswith("!help"):
        await send_message(variables.message.author,
                           dictionary['help']
                           )

    # ***** Tip bot section end *****
    # ***** Verification section begin *****
    elif cmd.startswith("!start"):
        await auth_user(variables)


async def processing_messages(new_message_, variables):
    try:
        time.sleep(0.5)
        variables.message = new_message_
        variables.is_video = False
        variables.message_text = str(new_message_.content)
        variables.first_name = new_message_.author.name
        variables.username = str(new_message_.author.name)
        variables.user_id = int(new_message_.author.id)

        variables.firo_address, variables.balance_in_firo, variables.locked_in_firo, variables.is_withdraw = await get_user_data(
            variables.user_id)
        variables.balance_in_growth = variables.balance_in_firo * SATS_IN_BTC if variables.balance_in_firo is not None else 0

        try:
            variables.is_verified = col_users.find_one({"_id": variables.user_id})['IsVerified']
            variables.is_user_in_db = variables.is_verified
        except Exception as exc:
            await send_to_logs(exc)
            variables.is_verified = True
            variables.is_user_in_db = False

        print(variables.username)
        print(variables.user_id)
        print(variables.first_name)
        print(variables.message_text, '\n')
        variables.group_id = new_message_.channel.id
        if new_message_.guild is not None:
            variables.group_username = new_message_.channel.name
            variables.is_dm = False
            global last_channel
            last_channel = new_message_.channel.id
        else:
            variables.group_username = "None"
            variables.is_dm = True

        split = variables.message_text.split(' ')
        if len(split) > 1:
            args = split[1:]
        else:
            args = None

        # Check if user changed his username
        await check_username_on_change(variables)
        await action_processing(str(split[0]).lower(), args, variables)
    except Exception as exc:
        await send_to_logs(exc)
        traceback.print_exc()


@bot.event
async def on_raw_reaction_add(payload):
    channel = await bot.fetch_channel(payload.channel_id)
    message = await channel.fetch_message(payload.message_id)
    user = await bot.fetch_user(payload.user_id)
    variables = ImportantVariables()
    variables.message = message
    variables.user_id = user.id
    variables.first_name = user.name
    variables.username = user.name
    variables.firo_address, variables.balance_in_firo, variables.locked_in_firo, variables.is_withdraw = await get_user_data(
        variables.user_id)

    envelope = col_envelopes.find_one({"msg_id": variables.message.id})
    if envelope is not None:
        await catch_envelope(variables)


@bot.event
async def on_ready():
    print('We have logged in as {0.user}'.format(bot))
    loop_update_balance.start()
    await send_to_logs("logged on!")


@bot.event
async def on_message(message):
    if message.author == bot.user:
        return
    if not message.attachments:
        # The message is just text.
        variables = ImportantVariables()
        await processing_messages(message, variables)


bot.run(bot_token)
