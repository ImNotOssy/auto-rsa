# Nelson Dane
# Robinhood API

import os
import robin_stocks.robinhood as rh
import pyotp
from dotenv import load_dotenv

def robinhood_init():
    # Initialize .env file
    load_dotenv()
    # Import Robinhood account
    if not os.environ["ROBINHOOD_USERNAME"] or not os.environ["ROBINHOOD_PASSWORD"]:
        print("Error: Missing Robinhood credentials")
        return None
    RH_USERNAME = os.environ["ROBINHOOD_USERNAME"]
    RH_PASSWORD = os.environ["ROBINHOOD_PASSWORD"]
    if os.environ["ROBINHOOD_TOTP"]:
        RH_TOTP = os.environ["ROBINHOOD_TOTP"]
        totp = pyotp.TOTP(RH_TOTP).now()
    else:
        totp = None
    # Log in to Robinhood account
    print("Logging in to Robinhood...")
    try:
        if not totp:
            rh.login(RH_USERNAME, RH_PASSWORD)
        else:
            print("Using Robinhood TOTP")
            rh.login(RH_USERNAME, RH_PASSWORD, mfa_code=totp)
    except Exception as e:
        print(f"Error: Unable to log in to Robinhood: {e}")
        return None
    print("Logged in to Robinhood!")
    return rh

async def robinhood_holdings(rh, ctx=None):
    print()
    print("==============================")
    print("Robinhood Holdings")
    print("==============================")
    print()
    # Make sure init didn't return None
    if rh is None:
        print("Error: No Robinhood account")
        return None
    try:
        # Get account holdings
        positions = rh.get_open_stock_positions()
        for item in positions:
            sym = item['symbol'] = rh.get_symbol_by_url(item['instrument'])
            print(f"{sym}: {item['quantity']}")
            if ctx:
                await ctx.send(f"{sym}: {item['quantity']}")
    except Exception as e:
        print(f'Error getting account holdings on Robinhood: {e}')
        if ctx:
            await ctx.send(f'Error getting account holdings on Robinhood: {e}')

async def robinhood_transaction(rh, action, stock, amount, price, time, DRY=True, ctx=None):
    print()
    print("==============================")
    print("Robinhood")
    print("==============================")
    print()
    action = action.lower()
    stock = stock.upper()
    amount = int(amount)
    # Make sure init didn't return None
    if rh is None:
        print("Error: No Robinhood account")
        return None
    if not DRY:
        try:
            # Buy Market order
            if action == "buy":
                rh.order_buy_market(stock, amount)
                print(f"Bought {amount} of {stock} on Robinhood")
                if ctx:
                    await ctx.send(f"Bought {amount} of {stock} on Robinhood")
            # Sell Market order
            elif action == "sell":
                rh.order_sell_market(stock, amount)
                print(f"Sold {amount} of {stock} on Robinhood")
                if ctx:
                    await ctx.send(f"Sold {amount} of {stock} on Robinhood")
            else:
                print("Error: Invalid action")
                return None
        except Exception as e:
            print(f'Error submitting order on Robinhood: {e}')
            if ctx:
                await ctx.send(f'Error submitting order on Robinhood: {e}')
    else:
        print(f"Running in DRY mode. Trasaction would've been: {action} {amount} of {stock} on Robinhood")
        if ctx:
            await ctx.send(f"Running in DRY mode. Trasaction would've been: {action} {amount} of {stock} on Robinhood")