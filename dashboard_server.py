from flask import Flask, render_template_string
import json
import os

app = Flask(__name__)

TEMPLATE = """
<!doctype html>
<html>
<head>
  <title>Crypto Predictor Dashboard</title>
  <style>
    body { font-family: Arial, sans-serif; background: #111; color: #eee; }
    .container { max-width: 1100px; margin: 40px auto; }
    h1 { text-align: center; }
    .card { background: #1b1b1b; padding: 20px; margin-bottom: 20px; border-radius: 8px; }
    table { width: 100%; border-collapse: collapse; margin-top: 10px; }
    th, td { padding: 8px; text-align: left; border-bottom: 1px solid #333; }
    .profit { color: #4caf50; }
    .loss { color: #f44336; }
    canvas { background: #000; border-radius: 8px; }
  </style>
  <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
  <script>
    // Auto-refresh every 15 minutes (900000 ms)
    setInterval(function() {
      window.location.reload();
    }, 900000);
  </script>
</head>
<body>
<div class="container">
  <h1>Crypto Predictor Dashboard</h1>

  <div class="card">
    <h2>Latest Cycle</h2>
    {% if summary %}
      <p><b>Timestamp:</b> {{ summary.timestamp }}</p>
      <p><b>Trading pot start:</b> {{ summary.trading_pot_start | round(2) }}</p>
      <p><b>Trading pot end:</b> {{ summary.trading_pot_end | round(2) }}</p>
      <p>
        <b>P&L:</b>
        <span class="{{ 'profit' if summary.profit_loss >= 0 else 'loss' }}">
          {{ summary.profit_loss | round(2) }}
        </span>
      </p>
      <p><b>Skimmed to vault:</b> {{ summary.skimmed | round(2) }}</p>
      <p><b>BTC regime:</b> {{ summary.btc_regime }}</p>
    {% else %}
      <p>No summary found yet. Run python runner.py once.</p>
    {% endif %}
  </div>

  <div class="card">
    <h2>Positions</h2>
    {% if summary %}
      <table>
        <tr>
          <th>Coin</th>
          <th>Signal</th>
          <th>Allocation</th>
        </tr>
        {% for coin, pos in summary.positions.items() %}
        <tr>
          <td>{{ coin }}</td>
          <td>{{ pos.signal }}</td>
          <td>{{ summary.allocations[coin] }}</td>
        </tr>
        {% endfor %}
      </table>
    {% else %}
      <p>No positions yet.</p>
    {% endif %}
  </div>

  <div class="card">
    <h2>Vaults</h2>
    {% if vault %}
      <p><b>Trading pot balance:</b> {{ vault.balance | round(2) }}</p>
      <p><b>Vault skim total:</b> {{ vault.vault_value | round(2) }}</p>
    {% else %}
      <p>No vault.json found.</p>
    {% endif %}
  </div>

  <div class="card">
    <h2>Equity Curve</h2>
    {% if history_labels %}
      <canvas id="equityChart" height="80"></canvas>
      <script>
        const eqCtx = document.getElementById('equityChart').getContext('2d');
        const equityChart = new Chart(eqCtx, {
          type: 'line',
          data: {
            labels: {{ history_labels | safe }},
            datasets: [{
              label: 'Trading Pot',
              data: {{ history_equity | safe }},
              borderColor: '#4caf50',
              backgroundColor: 'rgba(76, 175, 80, 0.1)',
              tension: 0.2
            }]
          },
          options: {
            plugins: { legend: { labels: { color: '#eee' } } },
            scales: {
              x: { ticks: { color: '#eee' } },
              y: { ticks: { color: '#eee' } }
            }
          }
        });
      </script>
    {% else %}
      <p>No history yet. Run a few cycles.</p>
    {% endif %}
  </div>

  <div class="card">
    <h2>Per-Coin P&L</h2>
    {% if coin_labels %}
      <canvas id="coinPnlChart" height="80"></canvas>
      <script>
        const coinCtx = document.getElementById('coinPnlChart').getContext('2d');
        const coinPnlChart = new Chart(coinCtx, {
          type: 'bar',
          data: {
            labels: {{ coin_labels | safe }},
            datasets: [{
              label: 'Total P&L',
              data: {{ coin_pnl | safe }},
              backgroundColor: ['#4caf50', '#2196f3', '#ff9800', '#9c27b0', '#f44336']
            }]
          },
          options: {
            plugins: { legend: { labels: { color: '#eee' } } },
            scales: {
              x: { ticks: { color: '#eee' } },
              y: { ticks: { color: '#eee' } }
            }
          }
        });
      </script>
    {% else %}
      <p>No per-coin P&L data yet.</p>
    {% endif %}
  </div>

</div>
</body>
</html>
"""

def load_summary():
    path = os.path.join("dashboards", "dashboard.json")
    if not os.path.exists(path):
        return None
    with open(path, "r") as f:
        return json.load(f)

def load_vault():
    path = "vault.json"
    if not os.path.exists(path):
        return None
    with open(path, "r") as f:
        return json.load(f)

def load_history():
    path = os.path.join("history", "portfolio_history.json")
    if not os.path.exists(path):
        return [], []
    with open(path, "r") as f:
        data = json.load(f)
    labels = [entry["timestamp"] for entry in data]
    equity = [entry["trading_pot"] for entry in data]
    return labels, equity

def load_coin_pnl():
    path = os.path.join("history", "coin_pnl.json")
    if not os.path.exists(path):
        return [], []
    with open(path, "r") as f:
        data = json.load(f)
    labels = list(data.keys())
    pnl = [data[c] for c in labels]
    return labels, pnl

@app.route("/")
def index():
    summary = load_summary()
    vault = load_vault()
    history_labels, history_equity = load_history()
    coin_labels, coin_pnl = load_coin_pnl()
    return render_template_string(
        TEMPLATE,
        summary=summary,
        vault=vault,
        history_labels=history_labels,
        history_equity=history_equity,
        coin_labels=coin_labels,
        coin_pnl=coin_pnl,
    )

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)

