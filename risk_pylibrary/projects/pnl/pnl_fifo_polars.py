#!/usr/bin/env python
# -*- coding: UTF-8 -*-


# Loading 
import pandas as pd
import polars as pl


def pnl_realised_polars(data):
    """
    Calculate FIFO PnL using polars, ensuring that each residual short trade 
    retains its specific price instead of averaging.

    Parameters:
        data (pd.DataFrame): Input data with columns:
            - 'symbol': Asset identifier.
            - 'time': Trade date.
            - 'side': Trade Direction.
            - 'price': Trade execution price.
            - 'quantity': Positive for buys, negative for sells.

    Returns:
        tuple: Three DataFrames containing:
            - PnL results per trade
            - Remaining FIFO queue
            - Position tracking
    """
    # Convert to Polars DataFrame and sort by symbol and date
    df = pl.from_pandas(data).sort(by=["symbol", "time"])

    # Mapping positive and negative signs for trade direction
    df = df.with_columns(pl.when(pl.col("side")=="B").then(pl.col("quantity")).otherwise(-1 * pl.col("quantity")).alias("quantity"))

    # Group by symbol and process each group
    results = []
    cache = []
    pos = []

    for group in df.group_by("symbol"):
        trades = group[1]
        trades = trades.with_columns(pl.col("price").fill_null(strategy="backward"))

        # Prepare FIFO queue for buy trades
        fifo_queue = []
        fifo_pnl = []
        fifo_pos = []
        short_queue = []  # Stores individual short trades separately

        for row in trades.iter_rows(named=True):
            trade_quantity = row["quantity"]
            trade_price = row["price"]
            realized_pnl = 0.0
            match_quantity = 0.0

            # Buy trade: Process FIFO queue and reduce short position
            if trade_quantity > 0:
                # If there are short positions, they should be covered first
                while trade_quantity > 0 and short_queue:
                    short_trade = short_queue[0]
                    match_quantity = min(trade_quantity, short_trade["quantity"])
                    realized_pnl += match_quantity * ((trade_price if short_trade["price"] is None else short_trade["price"]) - trade_price)

                    # Adjust quantities
                    short_trade["quantity"] -= match_quantity
                    trade_quantity -= match_quantity

                    # Remove the short trade if fully offset
                    if short_trade["quantity"] == 0:
                        short_queue.pop(0)

                fifo_pos.append(
                    {   "time": row["time"],
                        "symbol": row["symbol"],
                        "trade_price": trade_price,
                        "trade_quantity": trade_quantity,
                        "short_position": sum(t["quantity"] for t in short_queue),
                        "match_quantity": match_quantity,
                    }
                )

                # If any buy quantity remains after covering shorts, store in FIFO queue
                if trade_quantity > 0:
                    fifo_queue.append(
                        {
                        "time": row["time"],
                        "symbol": row["symbol"],
                        "quantity": trade_quantity,
                        "price": trade_price
                        })

            # Sell trade: Process FIFO queue or add to short queue
            elif trade_quantity < 0:
                sell_quantity = -trade_quantity

                # Match against FIFO queue first
                while sell_quantity > 0 and fifo_queue:
                    buy_trade = fifo_queue[0]
                    match_quantity = min(sell_quantity, buy_trade["quantity"])
                    realized_pnl += match_quantity * (trade_price - (trade_price if buy_trade["price"] is None else buy_trade["price"]))

                    # Adjust quantities
                    buy_trade["quantity"] -= match_quantity
                    sell_quantity -= match_quantity

                    # Remove the buy trade if fully used
                    if buy_trade["quantity"] == 0:
                        fifo_queue.pop(0)

                # If there is remaining unmatched sell quantity, store it **separately** in short queue
                if sell_quantity > 0:
                    short_queue.append(
                        {
                        "time": row["time"], 
                        "symbol": row["symbol"],
                        "quantity": sell_quantity,
                        "price": trade_price
                        })

                fifo_pos.append(
                    {"time": row["time"],
                     "symbol": row["symbol"],
                     "trade_price": trade_price,
                     "trade_quantity": trade_quantity,
                     "short_position": sum(t["quantity"] for t in short_queue),
                     "match_quantity": match_quantity,
                    }
                )

            # Store the realized PnL for this trade
            fifo_pnl.append(
                {"time": row["time"],
                 "symbol": row["symbol"],
                 "pnl": realized_pnl,
                 "matched_quantity": match_quantity,
                }
            )

        # At the end, add any remaining short trades to the FIFO queue
        # Multiply Short Queue Quantities by -1:
        if len(short_queue)>0:
            short_queue = [{**pos, 'quantity': -1 * pos['quantity']} for pos in short_queue]

        cache.extend(short_queue)
        results.extend(fifo_pnl)
        cache.extend(fifo_queue)
        pos.extend(fifo_pos)

    # Convert results back to a Pandas DataFrame
    out_pnl = pd.DataFrame(results)
    out_cache = pd.DataFrame(cache)
    out_pos = pd.DataFrame(pos)

    return out_pnl, out_cache, out_pos

