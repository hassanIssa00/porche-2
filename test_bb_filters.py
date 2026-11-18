import MetaTrader5 as mt5
import pandas as pd
import numpy as np

def run():
    if not mt5.initialize():
        return
    rates = mt5.copy_rates_from_pos('BTCUSDm', mt5.TIMEFRAME_M1, 0, 10000)
    mt5.shutdown()

    df = pd.DataFrame(rates)
    df['dt'] = pd.to_datetime(df['time'], unit='s')
    
    sma20 = df['close'].rolling(20).mean()
    std20 = df['close'].rolling(20).std()
    df['bb_upper'] = sma20 + 2.0 * std20
    df['bb_lower'] = sma20 - 2.0 * std20

    # ATR
    tr = np.maximum(df['high'] - df['low'], np.maximum((df['high'] - df['close'].shift(1)).abs(), (df['low'] - df['close'].shift(1)).abs()))
    df['atr'] = tr.rolling(14).mean()

    # EMA 50
    df['ema50'] = df['close'].ewm(span=50, adjust=False).mean()

    # Candle range filter: Don't enter if the reversal candle was huge (exhaustion/spike)
    df['candle_body'] = (df['close'] - df['open']).abs()

    def test(name, filter_func, lock_streak=2, lock_len=15):
        sl = 0.50
        tp = 0.85
        sl_dist = 50.0
        tp_dist = 85.0
        
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
                
            buy_sig = (prev['low'] <= df['bb_lower'].iloc[i-1]) and (prev['close'] > prev['open'])
            sell_sig = (prev['high'] >= df['bb_upper'].iloc[i-1]) and (prev['close'] < prev['open'])
            
            # Apply filter
            if filter_func:
                b_ok, s_ok = filter_func(df, i)
                if not b_ok: buy_sig = False
                if not s_ok: sell_sig = False
                
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
        print(f"{name:55s} | Trades: {len(trades):4d} | WR: {wr:4.1f}% | Net: ${net:+7.2f} | Max Loss: {max_streak}")

    print("=" * 95)
    test("Base BB Reversion (Lock=2, 15 candles)", None)
    
    # Filter 1: Candle body must be reasonable (< 2.5 * ATR - avoid news spikes)
    def f_news_spike(data, i):
        p = data.iloc[i-1]
        ok = p['candle_body'] <= 2.5 * p['atr']
        return ok, ok
    test("Filter 1: No News Spike Candles (Body <= 2.5x ATR)", f_news_spike)

    # Filter 2: Lock streak = 2, Lock length = 20 candles
    test("Filter 2: Lock streak = 2, Lock length = 20 candles", None, lock_streak=2, lock_len=20)

    # Filter 3: Lock streak = 1 (Zero Tolerance: 1 loss locks direction for 12 candles)
    test("Filter 3: Lock streak = 1 (1 loss locks direction for 12 candles)", None, lock_streak=1, lock_len=12)

    # Filter 4: Lock streak = 1, Lock length = 15 candles
    test("Filter 4: Lock streak = 1, Lock length = 15 candles", None, lock_streak=1, lock_len=15)
    print("=" * 95)

if __name__ == '__main__':
    run()
