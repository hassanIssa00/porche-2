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
    
    # EMAs
    df['ema21'] = df['close'].ewm(span=21, adjust=False).mean()
    df['ema50'] = df['close'].ewm(span=50, adjust=False).mean()

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

    # MACD
    ema12 = df['close'].ewm(span=12, adjust=False).mean()
    ema26 = df['close'].ewm(span=26, adjust=False).mean()
    macd = ema12 - ema26
    sig = macd.ewm(span=9, adjust=False).mean()
    df['macd_hist'] = macd - sig

    # Simulation engine
    def simulate(name, sig_list, sl=0.50, tp=0.85, lock_streak=2, lock_len=15):
        sl_dist = sl * 100
        tp_dist = tp * 100
        
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
                
            sig = sig_list[i]
            if sig == 'BUY' and i >= lock_buy_until:
                in_pos = True
                pos_type = 'BUY'
                entry_price = row['open']
            elif sig == 'SELL' and i >= lock_sell_until:
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
        print(f"{name:50s} | Trades: {len(trades):4d} | WR: {wr:4.1f}% | Net: ${net:+7.2f} | Max Loss: {max_streak}")

    # 1. Bollinger Band Reversion Signals
    sig_bb = [None] * len(df)
    for i in range(1, len(df)):
        p = df.iloc[i-1]
        if p['low'] <= p['bb_lower'] and p['close'] > p['open']:
            sig_bb[i] = 'BUY'
        elif p['high'] >= p['bb_upper'] and p['close'] < p['open']:
            sig_bb[i] = 'SELL'

    # 2. Trend Pullback Signals
    sig_tp = [None] * len(df)
    for i in range(2, len(df)):
        p = df.iloc[i-1]
        p2 = df.iloc[i-2]
        if p['ema21'] > p['ema50'] and p2['rsi'] < 50 and p['rsi'] > p2['rsi'] and p['close'] > p['open'] and p['macd_hist'] > p2['macd_hist']:
            sig_tp[i] = 'BUY'
        elif p['ema21'] < p['ema50'] and p2['rsi'] > 50 and p['rsi'] < p2['rsi'] and p['close'] < p['open'] and p['macd_hist'] < p2['macd_hist']:
            sig_tp[i] = 'SELL'

    # 3. Combined / Dual Engine (BB Reversion + Trend Pullback)
    sig_comb = [None] * len(df)
    for i in range(len(df)):
        if sig_bb[i]:
            sig_comb[i] = sig_bb[i]
        elif sig_tp[i]:
            sig_comb[i] = sig_tp[i]

    print("=" * 90)
    simulate("1. Bollinger Band Reversion (SL 0.50, TP 0.85)", sig_bb, sl=0.50, tp=0.85)
    simulate("2. Trend Pullback (SL 0.50, TP 0.85)", sig_tp, sl=0.50, tp=0.85)
    simulate("3. Combined Dual-Engine (SL 0.50, TP 0.85)", sig_comb, sl=0.50, tp=0.85)
    simulate("4. Combined Dual-Engine (SL 0.50, TP 0.90)", sig_comb, sl=0.50, tp=0.90)
    print("=" * 90)

if __name__ == '__main__':
    run()
