import json

with open('state.json', 'r', encoding='utf-8') as f:
    st = json.load(f)

trades = st.get('trades', [])
# filter trades from 2026-11-14 16:04 onwards
v5_trades = [t for t in trades if t.get('time', '') >= '2026-11-14 16:04' and t.get('profit') is not None]

print("v5 Trades count:", len(v5_trades))
wins = [t for t in v5_trades if t.get('profit', 0) > 0]
losses = [t for t in v5_trades if t.get('profit', 0) < 0]

win_sum = sum(t.get('profit', 0) for t in wins)
loss_sum = sum(t.get('profit', 0) for t in losses)

print(f"Wins: {len(wins)} (+${win_sum:.2f})")
print(f"Losses: {len(losses)} (-${abs(loss_sum):.2f})")
if v5_trades:
    win_rate = len(wins) / len(v5_trades) * 100
    avg_win = win_sum / len(wins) if wins else 0
    avg_loss = abs(loss_sum) / len(losses) if losses else 0
    print(f"Win Rate: {win_rate:.1f}%")
    print(f"Avg Win: ${avg_win:.2f}")
    print(f"Avg Loss: ${avg_loss:.2f}")
    print(f"Total Session PnL: ${win_sum + loss_sum:.2f}")

# Look at trade types: BUY vs SELL
buys = [t for t in v5_trades if t.get('type') == 'BUY']
sells = [t for t in v5_trades if t.get('type') == 'SELL']
print(f"BUY trades: {len(buys)}, SELL trades: {len(sells)}")

# Look at reasons
reasons = {}
for t in v5_trades:
    r = t.get('reason', 'UNKNOWN')
    reasons[r] = reasons.get(r, 0) + 1
print("Reasons:", reasons)
