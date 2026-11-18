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
    df['ema21'] = df['close'].ewm(span=21, adjust=False).mean()
    df['ema50'] = df['close'].ewm(span=50, adjust=False).mean()
    df['ema200'] = df['close'].ewm(span=200, adjust=False).mean()

    # Bollinger Bands (20, 2)
    sma20 = df['close'].rolling(20).mean()
    std20 = df['close'].rolling(20).std()
    df['bb_upper'] = sma20 + 2.0 * std20
    df['bb_lower'] = sma20 - 2.0 * std20
    df['bb_mid'] = sma20

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

    def test_strat(name, gen_signals, sl=0.50, tp=0.85):
        sl_dist = sl * 100
        tp_dist = tp * 100
        
        trades = []
        in_pos = False
        pos_type = None
        entry_price = 0.0
        
        consec_losses = 0
        consec_dir_losses = {'BUY': 0, 'SELL': 0}
        lock_until = {'BUY': 0, 'SELL': 0}
        
        for i in range(200, len(df) - 1):
            row = df.iloc[i]
            
            if in_pos:
                if pos_type == 'BUY':
                    if row['low'] <= entry_price - sl_dist:
                        trades.append(('BUY', -sl))
                        in_pos = False
                        consec_dir_losses['BUY'] += 1
                        if consec_dir_losses['BUY'] >= 2:
                            lock_until['BUY'] = i + 15
                    elif row['high'] >= entry_price + tp_dist:
                        trades.append(('BUY', tp))
                        in_pos = False
                        consec_dir_losses['BUY'] = 0
                elif pos_type == 'SELL':
                    if row['high'] >= entry_price + sl_dist:
                        trades.append(('SELL', -sl))
                        in_pos = False
                        consec_dir_losses['SELL'] += 1
                        if consec_dir_losses['SELL'] >= 2:
                            lock_until['SELL'] = i + 15
                    elif row['low'] <= entry_price - tp_dist:
                        trades.append(('SELL', tp))
                        in_pos = False
                        consec_dir_losses['SELL'] = 0
                continue
                
            sig = gen_signals(df, i)
            if sig == 'BUY' and i >= lock_until['BUY']:
                in_pos = True
                pos_type = 'BUY'
                entry_price = row['open']
            elif sig == 'SELL' and i >= lock_until['SELL']:
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
    # Test A: Pure BB Reversion (Any market)
    def strat_a(data, i):
        p = data.iloc[i-1]
        if p['low'] <= p['bb_lower'] and p['close'] > p['open']:
            return 'BUY'
        if p['high'] >= p['bb_upper'] and p['close'] < p['open']:
            return 'SELL'
        return None
    test_strat("A. Pure BB Reversion (TP=0.85)", strat_a, sl=0.50, tp=0.85)
    test_strat("A2. Pure BB Reversion (TP=0.95)", strat_a, sl=0.50, tp=0.95)

    # Test B: BB Reversion WITH Trend Direction (Buy Lower BB in Uptrend, Sell Upper BB in Downtrend)
    def strat_b(data, i):
        p = data.iloc[i-1]
        # In Uptrend (EMA21 > EMA50): ONLY buy at Lower BB (Buying extreme pullback in trend)
        if p['ema21'] > p['ema50'] and p['low'] <= p['bb_lower'] and p['close'] > p['open']:
            return 'BUY'
        # In Downtrend (EMA21 < EMA50): ONLY sell at Upper BB (Selling extreme rally in downtrend)
        if p['ema21'] < p['ema50'] and p['high'] >= p['bb_upper'] and p['close'] < p['open']:
            return 'SELL'
        return None
    test_strat("B. BB Reversion WITH Trend (EMA21/50) (TP=0.85)", strat_b, sl=0.50, tp=0.85)
    test_strat("B2. BB Reversion WITH Trend (EMA21/50) (TP=0.95)", strat_b, sl=0.50, tp=0.95)
    test_strat("B3. BB Reversion WITH Trend (EMA21/50) (TP=1.10)", strat_b, sl=0.50, tp=1.10)

    # Test C: BB Reversion + RSI Confirmation (<35 / >65)
    def strat_c(data, i):
        p = data.iloc[i-1]
        p2 = data.iloc[i-2]
        if p['low'] <= p['bb_lower'] and p['rsi'] < 38 and p['close'] > p['open'] and p['rsi'] > p2['rsi']:
            return 'BUY'
        if p['high'] >= p['bb_upper'] and p['rsi'] > 62 and p['close'] < p['open'] and p['rsi'] < p2['rsi']:
            return 'SELL'
        return None
    test_strat("C. BB + RSI (38/62) Turn (TP=0.85)", strat_c, sl=0.50, tp=0.85)
    test_strat("C2. BB + RSI (38/62) Turn (TP=0.95)", strat_c, sl=0.50, tp=0.95)

    # Test D: The Ultimate Sniper (Trend + BB Touch + RSI Turn + Closed Reversal Candle)
    def strat_d(data, i):
        p = data.iloc[i-1]
        p2 = data.iloc[i-2]
        # Uptrend: EMA21 > EMA50 OR Close > EMA200
        is_uptrend = (p['ema21'] > p['ema50']) or (p['close'] > p['ema200'])
        is_downtrend = (p['ema21'] < p['ema50']) or (p['close'] < p['ema200'])
        
        if is_uptrend and p['low'] <= p['bb_lower'] and p['rsi'] < 42 and p['close'] > p['open']:
            return 'BUY'
        if is_downtrend and p['high'] >= p['bb_upper'] and p['rsi'] > 58 and p['close'] < p['open']:
            return 'SELL'
        return None
    test_strat("D. Ultimate Sniper (Trend + BB + RSI 42/58) (TP=0.85)", strat_d, sl=0.50, tp=0.85)
    test_strat("D2. Ultimate Sniper (Trend + BB + RSI 42/58) (TP=0.95)", strat_d, sl=0.50, tp=0.95)
    print("=" * 95)

if __name__ == '__main__':
    run()
