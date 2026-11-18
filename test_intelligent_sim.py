import MetaTrader5 as mt5
import pandas as pd
import numpy as np

def run_test():
    if not mt5.initialize():
        print("MT5 init failed")
        return
    rates = mt5.copy_rates_from_pos('BTCUSDm', mt5.TIMEFRAME_M1, 0, 5000)
    rates_m5 = mt5.copy_rates_from_pos('BTCUSDm', mt5.TIMEFRAME_M5, 0, 1500)
    mt5.shutdown()

    df = pd.DataFrame(rates)
    df['dt'] = pd.to_datetime(df['time'], unit='s')
    df['m1_ema21'] = df['close'].ewm(span=21, adjust=False).mean()
    df['m1_ema55'] = df['close'].ewm(span=55, adjust=False).mean()

    delta = df['close'].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1/14, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/14, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, 1e-9)
    df['rsi'] = 100 - (100 / (1 + rs))

    ema12 = df['close'].ewm(span=12, adjust=False).mean()
    ema26 = df['close'].ewm(span=26, adjust=False).mean()
    macd = ema12 - ema26
    sig = macd.ewm(span=9, adjust=False).mean()
    df['macd_hist'] = macd - sig

    df5 = pd.DataFrame(rates_m5)
    df5['dt'] = pd.to_datetime(df5['time'], unit='s')
    df5['m5_ema20'] = df5['close'].ewm(span=20, adjust=False).mean()
    df5['m5_ema50'] = df5['close'].ewm(span=50, adjust=False).mean()
    df5['m5_trend'] = np.where(df5['m5_ema20'] > df5['m5_ema50'], 1, np.where(df5['m5_ema20'] < df5['m5_ema50'], -1, 0))

    df_merged = pd.merge_asof(df, df5[['dt', 'm5_trend']], on='dt', direction='backward')

    def simulate(name, require_m1_agree=True, require_price_filter=True, max_consec_loss_lock=2):
        trades = []
        consec_buy_loss = 0
        consec_sell_loss = 0
        lock_buy_until = 0
        lock_sell_until = 0
        
        sl_usd = 0.50
        tp_usd = 0.85
        sl_dist = 50.0
        tp_dist = 85.0
        
        in_pos = False
        pos_type = None
        entry_price = 0.0
        
        for i in range(60, len(df_merged) - 1):
            row = df_merged.iloc[i]
            prev = df_merged.iloc[i-1]
            prev2 = df_merged.iloc[i-2]
            
            if in_pos:
                high = row['high']
                low = row['low']
                if pos_type == 'BUY':
                    if low <= entry_price - sl_dist:
                        trades.append(('BUY', -sl_usd))
                        in_pos = False
                        consec_buy_loss += 1
                        if max_consec_loss_lock and consec_buy_loss >= max_consec_loss_lock:
                            lock_buy_until = i + 15
                    elif high >= entry_price + tp_dist:
                        trades.append(('BUY', tp_usd))
                        in_pos = False
                        consec_buy_loss = 0
                elif pos_type == 'SELL':
                    if high >= entry_price + sl_dist:
                        trades.append(('SELL', -sl_usd))
                        in_pos = False
                        consec_sell_loss += 1
                        if max_consec_loss_lock and consec_sell_loss >= max_consec_loss_lock:
                            lock_sell_until = i + 15
                    elif low <= entry_price - tp_dist:
                        trades.append(('SELL', tp_usd))
                        in_pos = False
                        consec_sell_loss = 0
                continue
                
            m1_trend = 1 if prev['m1_ema21'] > prev['m1_ema55'] else (-1 if prev['m1_ema21'] < prev['m1_ema55'] else 0)
            m5_trend = prev['m5_trend']
            
            # BUY signal
            buy_ok = True
            if require_m1_agree and m1_trend != 1: buy_ok = False
            if m5_trend != 1: buy_ok = False
            if require_price_filter and prev['close'] < prev['m1_ema21']: buy_ok = False
            rsi_turn_up = (prev2['rsi'] < 52 and prev['rsi'] > prev2['rsi'])
            if not rsi_turn_up: buy_ok = False
            if prev['macd_hist'] <= prev2['macd_hist']: buy_ok = False
            if prev['close'] <= prev['open']: buy_ok = False
            if i < lock_buy_until: buy_ok = False
            
            # SELL signal
            sell_ok = True
            if require_m1_agree and m1_trend != -1: sell_ok = False
            if m5_trend != -1: sell_ok = False
            if require_price_filter and prev['close'] > prev['m1_ema21']: sell_ok = False
            rsi_turn_dn = (prev2['rsi'] > 48 and prev['rsi'] < prev2['rsi'])
            if not rsi_turn_dn: sell_ok = False
            if prev['macd_hist'] >= prev2['macd_hist']: sell_ok = False
            if prev['close'] >= prev['open']: sell_ok = False
            if i < lock_sell_until: sell_ok = False
            
            if buy_ok:
                in_pos = True
                pos_type = 'BUY'
                entry_price = row['open']
            elif sell_ok:
                in_pos = True
                pos_type = 'SELL'
                entry_price = row['open']
                
        pnl = [p for _, p in trades]
        wins = [p for p in pnl if p > 0]
        wr = len(wins) / len(pnl) * 100 if pnl else 0
        net = sum(pnl)
        max_consec_losses = 0
        cur_loss = 0
        for _, p in trades:
            if p < 0:
                cur_loss += 1
                max_consec_losses = max(max_consec_losses, cur_loss)
            else:
                cur_loss = 0
        print(f"{name:45s} | Trades: {len(trades):4d} | WR: {wr:4.1f}% | Net: ${net:+6.2f} | Max Loss Streak: {max_consec_losses}")

    print("=" * 85)
    simulate("Old Logic (No M1, No Price filter, No Lock)", require_m1_agree=False, require_price_filter=False, max_consec_loss_lock=0)
    simulate("Intelligent (M1+M5 Agree, Price Filter, Lock=2)", require_m1_agree=True, require_price_filter=True, max_consec_loss_lock=2)
    simulate("Smart Scalper (M1+M5, Price, Lock=1)", require_m1_agree=True, require_price_filter=True, max_consec_loss_lock=1)
    print("=" * 85)

if __name__ == '__main__':
    run_test()
