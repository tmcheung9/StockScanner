from flask import Flask, request, jsonify, render_template_string
import yfinance as yf
import pandas as pd
import numpy as np
import os

app = Flask(__name__)

def get_layman_explanation(ticker):
    try:
        stock = yf.Ticker(ticker)
        df = stock.history(period="1y")
        if df.empty: return {"error": "Ticker not found"}

        # --- MATH ENGINE ---
        # 1. Momentum (How fast it's moving)
        six_m_price = df.iloc[-126]['Close'] if len(df) > 126 else df.iloc[0]['Close']
        momentum = ((df.iloc[-1]['Close'] - six_m_price) / six_m_price) * 100
        
        # 2. Tightness (How hard it is coiling)
        df['HL_Range'] = (df['High'] - df['Low']) / df['Close']
        avg_volatility = df['HL_Range'].rolling(20).mean().iloc[-1]
        current_volatility = df['HL_Range'].rolling(5).std().iloc[-1]
        tightness = round(avg_volatility / (current_volatility * 10) if current_volatility > 0 else 1.0, 2)

        # 3. Smart Money Score (Institutional flow)
        opt_score = 1.0
        try:
            exp = stock.options[0]
            chain = stock.option_chain(exp)
            c_vol = chain.calls['volume'].sum()
            p_vol = chain.puts['volume'].sum()
            opt_score = round(min(c_vol / (p_vol if p_vol > 0 else 1), 3.0), 2)
        except: pass

        # --- LAYMAN RECOMMENDATION LOGIC ---
        recommendation = "NEUTRAL"
        summary = "The stock is in a normal trading mode. It doesn't have the unique 'DNA' of a winner right now."
        
        if tightness > 2.0 and opt_score > 1.8:
            recommendation = "STRATEGIC BUY"
            summary = "This stock is 'coiling' like a spring. Big banks are quietly buying shares while price stays tight. High breakout potential."
        elif momentum > 100 and tightness < 1.0:
            recommendation = "AVOID / TOO LATE"
            summary = "The stock has already exploded. Buying now is chasing a speeding train; wait for it to slow down and 'coil' again."
        elif opt_score < 1.0 and momentum > 0:
            recommendation = "WAITING"
            summary = "Technicals are okay, but 'Smart Money' isn't betting on it yet. Wait for institutional conviction."

        return {
            "ticker": ticker,
            "price": round(df.iloc[-1]['Close'], 2),
            "momentum": f"{round(momentum, 0)}%",
            "tightness": tightness,
            "opt_score": opt_score,
            "recommendation": recommendation,
            "summary": summary,
            "stop_loss": round(df['Low'].tail(10).min(), 2)
        }
    except:
        return {"error": "Analysis failed."}

@app.route("/api/analyze/<ticker>")
def api_node(ticker):
    return jsonify(get_layman_explanation(ticker.upper()))

@app.route("/")
def home():
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <title>SCEM-O Intelligence</title>
        <script src="https://cdn.tailwindcss.com"></script>
        <style>
            body { background: #020617; color: #f8fafc; font-family: sans-serif; }
            .glass { background: #0f172a; border: 1px solid #1e293b; transition: all 0.3s ease; }
            .highlight-buy { border: 2px solid #10b981; box-shadow: 0 0 25px rgba(16, 185, 129, 0.15); }
        </style>
    </head>
    <body class="p-6">
        <div class="max-w-2xl mx-auto py-10">
            <header class="mb-10 text-center">
                <h1 class="text-4xl font-black italic text-blue-500">SCEM-O <span class="text-white">INTEL</span></h1>
                <p class="text-slate-500 text-xs font-bold tracking-widest mt-2">INSTITUTIONAL LOGIC ENGINE</p>
            </header>

            <div class="glass p-6 rounded-3xl mb-10">
                <div class="flex gap-4">
                    <input id="ticker" type="text" placeholder="TICKER (e.g. VEEV)" class="flex-1 bg-black border border-slate-700 rounded-xl px-5 py-3 font-bold text-xl outline-none focus:ring-2 focus:ring-blue-500 uppercase">
                    <button onclick="checkStock()" class="bg-blue-600 hover:bg-blue-500 text-white px-6 rounded-xl font-black">SCAN</button>
                </div>
            </div>

            <div id="loader" class="hidden text-center"><div class="animate-spin h-8 w-8 border-4 border-blue-500 border-t-transparent rounded-full mx-auto"></div></div>
            <div id="result" class="hidden"></div>
        </div>

        <script>
            async function checkStock() {
                const t = document.getElementById('ticker').value;
                if(!t) return;
                document.getElementById('loader').classList.remove('hidden');
                document.getElementById('result').classList.add('hidden');

                const res = await fetch(`/api/analyze/${t}`);
                const data = await res.json();
                
                document.getElementById('loader').classList.add('hidden');
                const container = document.getElementById('result');
                container.classList.remove('hidden');

                const isBuy = data.recommendation === 'STRATEGIC BUY';
                container.innerHTML = `
                    <div class="glass p-8 rounded-[32px] ${isBuy ? 'highlight-buy' : ''}">
                        <div class="flex justify-between items-start mb-6">
                            <div>
                                <h2 class="text-5xl font-black">${data.ticker}</h2>
                                <p class="text-xl text-slate-400 font-mono">$${data.price}</p>
                            </div>
                            <span class="px-3 py-1 rounded-lg text-[10px] font-black uppercase ${isBuy ? 'bg-emerald-500 text-white' : 'bg-slate-800 text-slate-500'}">
                                ${data.recommendation}
                            </span>
                        </div>
                        <div class="bg-slate-950/50 p-4 rounded-2xl mb-6 border border-slate-800">
                            <p class="text-sm text-slate-300 italic">"${data.summary}"</p>
                        </div>
                        <div class="grid grid-cols-2 gap-4">
                            <div class="p-4 bg-slate-900 rounded-xl">
                                <p class="text-[9px] text-slate-500 font-bold uppercase">6M Momentum</p>
                                <p class="text-lg font-bold">${data.momentum}</p>
                            </div>
                            <div class="p-4 bg-slate-900 rounded-xl">
                                <p class="text-[9px] text-slate-500 font-bold uppercase">Risk Exit (Stop)</p>
                                <p class="text-lg font-bold text-red-400">$${data.stop_loss}</p>
                            </div>
                        </div>
                    </div>
                `;
            }
        </script>
    </body>
    </html>
    """

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)