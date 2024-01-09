# Nelson Dane
# Webull API

import os
import traceback

from webull import webull
from dotenv import load_dotenv

from helperAPI import Brokerage, maskString, printAndDiscord, printHoldings, stockOrder


def place_order(wbo: Brokerage, obj: webull, orderObj: stockOrder, key: str, s: str):
    # obj.get_trade_token(wbo.get_logged_in_objects(key, "trading_pin"))
    obj._account_id = wbo.get_logged_in_objects(key, "account_id")
    order = obj.place_order(
        stock=s,
        action=orderObj.get_action().upper(),
        orderType=orderObj.get_price().upper(),
        quant=orderObj.get_amount(),
        enforce=orderObj.get_time().upper(),
        # outsideRegularTradingHour=False,
    )
    print(order)
    if not order["success"]:
        print(f"{order['msg']} Code {order['code']}")
    return order["success"]


# Initialize Webull
def webull_init(WEBULL_EXTERNAL=None):
    # Initialize .env file
    load_dotenv()
    # Import Webull account
    if not os.getenv("WEBULL") and WEBULL_EXTERNAL is None:
        print("Webull not found, skipping...")
        return None
    accounts = (
        os.environ["WEBULL"].strip().split(",")
        if WEBULL_EXTERNAL is None
        else WEBULL_EXTERNAL.strip().split(",")
    )
    for account in accounts:
        print("Logging in to Webull...")
        name = f"Webull {accounts.index(account) + 1}"
        account = account.split(":")
        if len(account) != 4:
            print(f"Invalid number of parameters for {name}, got {len(account)}, expected 4")
            return None
        try:
            wb = webull()
            wb._set_did(account[2])
            wb.login(account[0], account[1])
            wb.get_trade_token(account[3])
            if not wb.is_logged_in():
                raise Exception(f"Unable to log in to {name}. Check credentials.")
            # Initialize Webull account
            wb_obj = Brokerage("Webull")
            wb_obj.set_logged_in_object(name, wb, "wb")
            wb_obj.set_logged_in_object(name, account[3], "trading_pin")
            wb_obj.set_logged_in_object(name, wb._account_id, "account_id")
            ac = wb.get_account()
            print(maskString(ac["brokerAccountId"]))
            wb_obj.set_account_number(name, ac["brokerAccountId"])
            wb_obj.set_account_type(name, ac["brokerAccountId"], ac["accountType"])
            wb_obj.set_account_totals(name, ac["brokerAccountId"], ac["netLiquidation"])
        except Exception as e:
            print(traceback.format_exc())
            print(f"Error: Unable to log in to Webull: {e}")
            return None
        print("Logged in to Webull!")
    return wb_obj


def webull_holdings(wbo: Brokerage, loop=None):
    for key in wbo.get_account_numbers():
        for account in wbo.get_account_numbers(key):
            obj: webull = wbo.get_logged_in_objects(key, "wb")
            try:
                # Make sure we're logged in
                if not obj.is_logged_in():
                    printAndDiscord(f"{key} {account}: Not logged in", loop)
                    continue
                # Get account holdings
                obj._account_id = wbo.get_logged_in_objects(key, "account_id")
                positions = obj.get_positions()
                # List of holdings dictionaries
                if positions != []:
                    for item in positions:
                        sym = item["ticker"]["symbol"]
                        if sym == "":
                            sym = "Unknown"
                        qty = item["position"]
                        mv = round(float(item["marketValue"]) / float(qty), 2)
                        wbo.set_holdings(key, account, sym, qty, mv)
            except Exception as e:
                printAndDiscord(f"{key} {account}: Error getting holdings: {e}", loop)
                traceback.print_exc()
                continue
        printHoldings(wbo, loop=loop)


def webull_transaction(wbo: Brokerage, orderObj: stockOrder, loop=None):
    print()
    print("==============================")
    print("Webull")
    print("==============================")
    print()
    for s in orderObj.get_stocks():
        for key in wbo.get_account_numbers():
            printAndDiscord(
                f"{key}: {orderObj.get_action()}ing {orderObj.get_amount()} of {s}",
                loop,
            )
            for account in wbo.get_account_numbers(key):
                print_account = maskString(account)
                # Webull doesn't support fractional shares
                if not orderObj.get_amount().is_integer():
                    printAndDiscord(
                        f"Webull account {print_account} Error: Fractional share {orderObj.get_amount()} not supported",
                        loop=loop,
                    )
                    continue
                obj: webull = wbo.get_logged_in_objects(key, "wb")
                # Make sure we're logged in
                if not obj.is_logged_in():
                    printAndDiscord(f"{key} {account}: Not logged in", loop)
                    continue
                if not orderObj.get_dry():
                    try:
                        if orderObj.get_price() == "market":
                            orderObj.set_price("MKT")
                        # If stock price < $1 or $0.10 and buy, buy 100/1000 shares and sell 100/1000 - amount
                        askList = obj.get_quote(s)["askList"]
                        bidList = obj.get_quote(s)["bidList"]
                        if askList == [] and bidList == []:
                            printAndDiscord(f"{key} {account}: {s} not found", loop)
                            continue
                        askPrice = float(askList[0]["price"]) if askList != [] else 0
                        bidPrice = float(bidList[0]["price"]) if bidList != [] else 0
                        if (askPrice < 1 or bidPrice < 1) and orderObj.get_action() == "buy":
                            big_amount = 1000 if askPrice < 0.1 or bidPrice < 0.1 else 100
                            print(f"Buying {big_amount} then selling {big_amount - orderObj.get_amount()} of {s}")
                            # Under $1, buy 100 shares and sell 100 - amount
                            old_amount = orderObj.get_amount()
                            orderObj.set_amount(big_amount)
                            buy_success = place_order(wbo, obj, orderObj, key, s)
                            if not buy_success:
                                raise Exception(f"Error buying {big_amount} of {s}")
                            orderObj.set_amount(big_amount - old_amount)
                            orderObj.set_action("sell")
                            sell_success = place_order(wbo, obj, orderObj, key, s)
                            if not sell_success:
                                raise Exception(f"Error selling {big_amount - old_amount} of {s}")
                        else:
                            # Place normal order
                            print(f"Placing normal order for {s}")
                            order = place_order(wbo, obj, orderObj, key, s)
                            if order:
                                printAndDiscord(
                                    f"{key}: {orderObj.get_action()} {orderObj.get_amount()} of {s} in {print_account}: Success",
                                    loop,
                                )
                    except Exception as e:
                        printAndDiscord(
                            f"{key} {print_account}: Error placing order: {e}", loop
                        )
                        print(traceback.format_exc())
                        continue
                else:
                    printAndDiscord(
                        f"{key} Running in DRY mode. Transaction would've been: {orderObj.get_action()} {orderObj.get_amount()} of {s}",
                        loop,
                    )
