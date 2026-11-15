import json
import MetaTrader5 as mt5

if mt5.initialize():
    acc = mt5.account_info()
    if acc:
        print("MT5 Connected!")
        print(f"Login: {acc.login}, Balance: {acc.balance}, Equity: {acc.equity}, Profit: {acc.profit}")
    else:
        print("Could not get account info")
else:
    print("MT5 initialize failed")

try:
    with open('state.json', 'r', encoding='utf-8') as f:
        st = json.load(f)
    print("Stats in state.json:", st.get('stats'))
    trades = st.get('trades', [])
    print("Total trades count in state.json:", len(trades))
    closed = [t for t in trades if t.get('profit') is not None]
    print("Total closed trades:", len(closed))
    wins = [t for t in closed if t.get('profit', 0) > 0]
    losses = [t for t in closed if t.get('profit', 0) < 0]
    zeros = [t for t in closed if t.get('profit', 0) == 0]
    total_win_amt = sum(t.get('profit', 0) for t in wins)
    total_loss_amt = sum(t.get('profit', 0) for t in losses)
    print(f"Wins count: {len(wins)} (Total: +${total_win_amt:.2f})")
    print(f"Losses count: {len(losses)} (Total: -${abs(total_loss_amt):.2f})")
    print(f"Zeros count: {len(zeros)}")
    print(f"Net PnL: ${total_win_amt + total_loss_amt:.2f}")

    print("\nLast 15 closed trades:")
    for t in closed[-15:]:
        print(f"{t.get('time')} | {t.get('type')} | Profit: ${t.get('profit')} | Reason: {t.get('reason')}")
except Exception as e:
    print("Error:", e)
