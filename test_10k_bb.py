import MetaTrader5 as mt5
import pandas as pd
import numpy as np

def run():
    if not mt5.initialize():
        print("MT5 failed")
        return
    rates = mt5.copy_rates_from_pos('BTCUSDm', mt5.TIMEFRAME_M1, 0, 10000)
    mt5.shutdown()

    df = pd.DataFrame(rates)
    df['dt'] = pd.to_datetime(df['time'], unit='s')
    
    # Bollinger Bands (20, 2)
    sma20 = df['close'].rolling(20).mean()
    std20 = df['close'].rolling(20).std()
    df['bb_upper'] = sma20 + 2.0 * std20
    df['bb_lower'] = sma20 - 2.0 * std20
    
    # RSI (14)
    delta = df['close'].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1/14, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/14, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, 1e-9)
    df['rsi'] = 100 - (100 / (1 + rs))

    print(f"Data: {len(df)} candles from {df['dt'].iloc[0]} to {df['dt'].iloc[-1]}")

    def test(name, tp, sl=0.50, lock_streak=2, lock_len=15, bb_std=2.0, use_rsi_filter=False):
        sl_dist = sl * 100
        tp_dist = tp * 100
        
        # Recalc BB if std != 2.0
        if bb_std != 2.0:
            b_up = sma20 + bb_std * std20
            b_low = sma20 - bb_std * std20
        else:
            b_up = df['bb_upper']
            b_low = df['bb_lower']
            
        trades = []
        in_pos = False
        pos_type = None
        entry_price = 0.0
        
        consec_buy_loss = 0
        consec_sell_loss = 0
        lock_buy_until = 0
        lock_sell_until = 0
        
        for i in range(50, len(df) - 1):
            row = df.iloc[i]
            prev = df.iloc[i-1]
            
            if in_pos:
                if pos_type == 'BUY':
                    if row['low'] <= entry_price - sl_dist:
                        trades.append(('BUY', -sl))
                        in_pos = False
                        consec_buy_loss += 1
                        if lock_streak and consec_buy_loss >= lock_streak:
                            lock_buy_until = i + lock_len
                    elif row['high'] >= entry_price + tp_dist:
                        trades.append(('BUY', tp))
                        in_pos = False
                        consec_buy_loss = 0
                elif pos_type == 'SELL':
                    if row['high'] >= entry_price + sl_dist:
                        trades.append(('SELL', -sl))
                        in_pos = False
                        consec_sell_loss += 1
                        if lock_streak and consec_sell_loss >= lock_streak:
                            lock_sell_until = i + lock_len
                    elif row['low'] <= entry_price - tp_dist:
                        trades.append(('SELL', tp))
                        in_pos = False
                        consec_sell_loss = 0
                continue
                
            # Signal on closed candle
            buy_sig = (prev['low'] <= b_low.iloc[i-1]) and (prev['close'] > prev['open'])
            sell_sig = (prev['high'] >= b_up.iloc[i-1]) and (prev['close'] < prev['open'])
            
            if use_rsi_filter:
                if prev['rsi'] > 45: buy_sig = False
                if prev['rsi'] < 55: sell_sig = False
                
            if buy_sig and i >= lock_buy_until:
                in_pos = True
                pos_type = 'BUY'
                entry_price = row['open']
            elif sell_sig and i >= lock_sell_until:
                in_pos = True
                pos_type = 'SELL'
                entry_price = row['open']
                
        pnl = [p for _, p in trades]
        wins = [p for p in pnl if p > 0]
        wr = len(wins) / len(pnl) * 100 if pnl else 0
        net = sum(pnl)
        max_streak = 0
        cur_streak = 0
        for _, p in trades:
            if p < 0:
                cur_streak += 1
                max_streak = max(max_streak, cur_streak)
            else:
                cur_streak = 0
        print(f"{name:55s} | Trades: {len(trades):4d} | WR: {wr:4.1f}% | Net: ${net:+7.2f} | Max Loss Streak: {max_streak}")

    print("=" * 95)
    test("BB (2.0) + SL 0.50, TP 0.80, Lock=2 (15 candles)", 0.80, sl=0.50, lock_streak=2, lock_len=15)
    test("BB (2.0) + SL 0.50, TP 0.85, Lock=2 (15 candles)", 0.85, sl=0.50, lock_streak=2, lock_len=15)
    test("BB (2.0) + SL 0.50, TP 0.90, Lock=2 (15 candles)", 0.90, sl=0.50, lock_streak=2, lock_len=15)
    test("BB (2.0) + SL 0.50, TP 0.95, Lock=2 (15 candles)", 0.95, sl=0.50, lock_streak=2, lock_len=15)
    test("BB (2.1) + SL 0.50, TP 0.85, Lock=2 (15 candles)", 0.85, sl=0.50, lock_streak=2, lock_len=15, bb_std=2.1)
    test("BB (2.2) + SL 0.50, TP 0.85, Lock=2 (15 candles)", 0.85, sl=0.50, lock_streak=2, lock_len=15, bb_std=2.2)
    test("BB (2.0) + RSI Filter + SL 0.50, TP 0.85, Lock=2", 0.85, sl=0.50, lock_streak=2, lock_len=15, use_rsi_filter=True)
    test("BB (2.0) NO LOCK (What happens without circuit breaker)", 0.85, sl=0.50, lock_streak=0)
    print("=" * 95)

if __name__ == '__main__':
    run()
