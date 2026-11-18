import MetaTrader5 as mt5
import pandas as pd
import numpy as np

def run():
    if not mt5.initialize():
        print("MT5 failed")
        return
    rates = mt5.copy_rates_from_pos('BTCUSDm', mt5.TIMEFRAME_M1, 0, 5000)
    mt5.shutdown()

    df = pd.DataFrame(rates)
    df['dt'] = pd.to_datetime(df['time'], unit='s')
    
    # EMAs
    df['ema9'] = df['close'].ewm(span=9, adjust=False).mean()
    df['ema21'] = df['close'].ewm(span=21, adjust=False).mean()
    df['ema50'] = df['close'].ewm(span=50, adjust=False).mean()
    df['ema200'] = df['close'].ewm(span=200, adjust=False).mean()

    # Bollinger Bands
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

    # ADX
    # Simple proxy: absolute distance from EMA50 normalized by ATR
    tr = np.maximum(df['high'] - df['low'], np.maximum((df['high'] - df['close'].shift(1)).abs(), (df['low'] - df['close'].shift(1)).abs()))
    atr = tr.rolling(14).mean()
    df['trend_strength'] = (df['close'] - df['ema50']).abs() / atr.replace(0, 1)

    def test_with_circuit_breaker(name, raw_signals, lock_len=20, max_consec=2, sl=0.50, tp=0.90):
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
        
        for i in range(200, len(df) - 1):
            row = df.iloc[i]
            
            if in_pos:
                if pos_type == 'BUY':
                    if row['low'] <= entry_price - sl_dist:
                        trades.append(('BUY', -sl))
                        in_pos = False
                        consec_buy_loss += 1
                        if max_consec and consec_buy_loss >= max_consec:
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
                        if max_consec and consec_sell_loss >= max_consec:
                            lock_sell_until = i + lock_len
                    elif row['low'] <= entry_price - tp_dist:
                        trades.append(('SELL', tp))
                        in_pos = False
                        consec_sell_loss = 0
                continue
                
            sig = raw_signals[i]
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

    # Generate raw signals for BB Reversion
    sig_bb = [None] * len(df)
    for i in range(1, len(df)):
        p = df.iloc[i-1]
        if p['low'] <= p['bb_lower'] and p['close'] > p['open']:
            sig_bb[i] = 'BUY'
        elif p['high'] >= p['bb_upper'] and p['close'] < p['open']:
            sig_bb[i] = 'SELL'

    # Generate raw signals for Trend-Pullback
    sig_tp = [None] * len(df)
    for i in range(2, len(df)):
        p = df.iloc[i-1]
        p2 = df.iloc[i-2]
        # Uptrend: Close > EMA50, RSI was < 50 and ticked up, green candle
        if p['close'] > p['ema50'] and p2['rsi'] < 50 and p['rsi'] > p2['rsi'] and p['close'] > p['open'] and p['macd_hist'] > p2['macd_hist']:
            sig_tp[i] = 'BUY'
        elif p['close'] < p['ema50'] and p2['rsi'] > 50 and p['rsi'] < p2['rsi'] and p['close'] < p['open'] and p['macd_hist'] < p2['macd_hist']:
            sig_tp[i] = 'SELL'

    # Generate raw signals for RSI Extremes (30/70)
    sig_rsi = [None] * len(df)
    for i in range(2, len(df)):
        p = df.iloc[i-1]
        p2 = df.iloc[i-2]
        if p2['rsi'] < 30 and p['rsi'] > p2['rsi'] and p['close'] > p['open']:
            sig_rsi[i] = 'BUY'
        elif p2['rsi'] > 70 and p['rsi'] < p2['rsi'] and p['close'] < p['open']:
            sig_rsi[i] = 'SELL'

    print("=" * 95)
    print("--- 1. BB REVERSION WITH & WITHOUT CIRCUIT BREAKER ---")
    test_with_circuit_breaker("BB Reversion (No Lock)", sig_bb, max_consec=0, sl=0.50, tp=0.85)
    test_with_circuit_breaker("BB Reversion (Lock=2, 15 candles)", sig_bb, lock_len=15, max_consec=2, sl=0.50, tp=0.85)
    test_with_circuit_breaker("BB Reversion (Lock=2, 25 candles)", sig_bb, lock_len=25, max_consec=2, sl=0.50, tp=0.85)

    print("--- 2. TREND-PULLBACK WITH & WITHOUT CIRCUIT BREAKER ---")
    test_with_circuit_breaker("Trend-Pullback (No Lock)", sig_tp, max_consec=0, sl=0.50, tp=0.90)
    test_with_circuit_breaker("Trend-Pullback (Lock=2, 15 candles)", sig_tp, lock_len=15, max_consec=2, sl=0.50, tp=0.90)
    test_with_circuit_breaker("Trend-Pullback (Lock=2, 25 candles)", sig_tp, lock_len=25, max_consec=2, sl=0.50, tp=0.90)

    print("--- 3. RSI EXTREMES (30/70) WITH & WITHOUT CIRCUIT BREAKER ---")
    test_with_circuit_breaker("RSI 30/70 (No Lock)", sig_rsi, max_consec=0, sl=0.50, tp=0.90)
    test_with_circuit_breaker("RSI 30/70 (Lock=2, 20 candles)", sig_rsi, lock_len=20, max_consec=2, sl=0.50, tp=0.90)

    # Combined Strategy: Trend-Pullback + BB Extreme Filter
    sig_hybrid = [None] * len(df)
    for i in range(2, len(df)):
        p = df.iloc[i-1]
        p2 = df.iloc[i-2]
        # In Uptrend: Buy if pullback to EMA21 or Lower BB
        if p['close'] > p['ema50'] and p['low'] <= p['ema21'] and p['close'] > p['open'] and p['rsi'] > p2['rsi']:
            sig_hybrid[i] = 'BUY'
        # In Downtrend: Sell if pullback to EMA21 or Upper BB
        elif p['close'] < p['ema50'] and p['high'] >= p['ema21'] and p['close'] < p['open'] and p['rsi'] < p2['rsi']:
            sig_hybrid[i] = 'SELL'
            
    print("--- 4. HYBRID EMA21 TOUCH IN EMA50 TREND ---")
    test_with_circuit_breaker("EMA21 Touch in EMA50 (No Lock)", sig_hybrid, max_consec=0, sl=0.50, tp=0.90)
    test_with_circuit_breaker("EMA21 Touch in EMA50 (Lock=2, 20 candles)", sig_hybrid, lock_len=20, max_consec=2, sl=0.50, tp=0.90)
    print("=" * 95)

if __name__ == '__main__':
    run()
