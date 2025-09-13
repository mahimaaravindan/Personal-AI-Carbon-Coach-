from flask import Flask, render_template, request, redirect, url_for
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from io import BytesIO
import base64
import os
import matplotlib.dates as mdates

app = Flask(__name__)

# Path to dataset
DATA_PATH = 'data/carbon_data.csv'
def plot_to_base64(fig):
    buf = BytesIO()
    fig.savefig(buf, format='png', bbox_inches='tight')
    buf.seek(0)
    img_base64 = base64.b64encode(buf.getvalue()).decode()
    plt.close(fig)
    return img_base64

def load_csv_safe(path):
    try:
        df = pd.read_csv(path, encoding='utf-8-sig')
        return df
    except Exception as e:
        raise Exception(f"CSV could not be loaded: {e}")

# Home page
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/input', methods=['GET', 'POST'])
def input_page():
    if request.method == 'POST':
        daily_travel = float(request.form['daily_travel'])
        transport_mode = request.form['transport_mode']
        energy_usage = float(request.form['energy_usage'])
        energy_source = request.form['energy_source']
        diet_type = request.form['diet_type']
        habits = request.form.getlist('habit')
        return redirect(url_for('analysis',
                                daily_travel=daily_travel,
                                transport_mode=transport_mode,
                                energy_usage=energy_usage,
                                energy_source=energy_source,
                                diet_type=diet_type,
                                habits=",".join(habits)))
    return render_template('input.html')


@app.route('/analysis')
def analysis():
    daily_travel = float(request.args.get('daily_travel', 0))
    transport_mode = request.args.get('transport_mode', 'car_petrol')
    energy_usage = float(request.args.get('energy_usage', 0))
    energy_source = request.args.get('energy_source', 'grid')
    diet_type = request.args.get('diet_type', 'omnivore')
    habits = request.args.get('habits', '').split(',')

    transport_factors = {
        'car_petrol': 0.21,
        'car_diesel': 0.25,
        'car_electric': 0.05,
        'bus': 0.1,
        'train': 0.05,
        'bike': 0.0,
        'walk': 0.0
    }

    energy_factors = {
        'grid': 0.5,
        'solar': 0.0,
        'hybrid': 0.2
    }

    diet_factors = {
        'omnivore': 2.5,
        'vegetarian': 1.5,
        'vegan': 1.0,
        'pescatarian': 1.8
    }

    lifestyle_reduction = 0
    if 'recycle' in habits: lifestyle_reduction += 0.1
    if 'reusable_bags' in habits: lifestyle_reduction += 0.05
    if 'avoid_plastic' in habits: lifestyle_reduction += 0.1
    if 'compost' in habits: lifestyle_reduction += 0.05

    carbon_emission = (daily_travel * transport_factors.get(transport_mode, 0.2) +
                       energy_usage * energy_factors.get(energy_source, 0.5) +
                       diet_factors.get(diet_type, 2.0))
    carbon_emission *= (1 - lifestyle_reduction)
    return render_template('analysis.html', carbon=round(carbon_emission, 2))

# --- RESULT ROUTE (Fixed explode & indentation) ---
@app.route('/result')
def result():
    carbon = float(request.args.get('carbon', 0))
    daily_travel = float(request.args.get('daily_travel', 0))
    energy_usage = float(request.args.get('energy_usage', 0))
    diet_type = request.args.get('diet_type', 'omnivore')

    try:
        df = pd.read_csv(DATA_PATH)
    except Exception as e:
        return f"Error loading CSV: {e}"

    df['date'] = pd.to_datetime(df['date'])

    # --- DAILY PIE CHART ---
    labels = ['Travel', 'Energy', 'Diet']
    sizes = [
        daily_travel * 0.21,
        energy_usage * 0.5,
        {'omnivore': 2.5, 'vegetarian': 1.5, 'vegan': 1.0}.get(diet_type, 2.0)
    ]
    fig1, ax1 = plt.subplots()
    colors = ['#FF9999', '#66B3FF', '#99FF99']
    explode = (0.05, 0.05, 0)  # <<< Fixed explode
    ax1.pie(
        sizes,
        labels=labels,
        autopct='%1.1f%%',
        startangle=140,
        colors=colors,
        shadow=True,
        explode=explode,
        pctdistance=0.7,
        labeldistance=1.1
    )
    ax1.axis('equal')
    daily_img = plot_to_base64(fig1)

    # --- WEEKLY LINE GRAPH ---
    fig2, ax2 = plt.subplots(figsize=(8,4))
    weekly_dates = df['date'].head(7)
    weekly_values = df['daily_carbon'].head(7)
    ax2.plot(weekly_dates, weekly_values, marker='o', linewidth=2)
    ax2.set_title("Weekly Carbon Emission Trend")
    ax2.set_xlabel("Date")
    ax2.set_ylabel("kg CO2")
    ax2.xaxis.set_major_locator(mdates.DayLocator(interval=1))
    ax2.xaxis.set_major_formatter(mdates.DateFormatter('%b %d'))
    plt.xticks(rotation=45)
    ax2.grid(True, linestyle='--', alpha=0.5)
    fig2.tight_layout()
    weekly_img = plot_to_base64(fig2)

    # --- MONTHLY BAR GRAPH ---
    fig3, ax3 = plt.subplots(figsize=(10,5))
    monthly_dates = df['date'].head(30)
    monthly_values = df['daily_carbon'].head(30)
    ax3.bar(monthly_dates, monthly_values, color='skyblue')
    ax3.set_title("Monthly Carbon Emission")
    ax3.set_xlabel("Date")
    ax3.set_ylabel("kg CO2")
    ax3.xaxis.set_major_locator(mdates.DayLocator(interval=3))
    ax3.xaxis.set_major_formatter(mdates.DateFormatter('%b %d'))
    plt.xticks(rotation=45)
    ax3.grid(True, linestyle='--', alpha=0.5)
    fig3.tight_layout()
    monthly_img = plot_to_base64(fig3)

    # --- YEARLY LINE GRAPH ---
    df_yearly = df.set_index('date').resample('M')['yearly_carbon'].mean()
    fig4, ax4 = plt.subplots(figsize=(12,6))
    ax4.plot(df_yearly.index, df_yearly.values, color='green', marker='o', linewidth=2)
    ax4.set_title("Yearly Carbon Emission Trend")
    ax4.set_xlabel("Month")
    ax4.set_ylabel("kg CO2")
    ax4.xaxis.set_major_locator(mdates.MonthLocator(interval=1))
    ax4.xaxis.set_major_formatter(mdates.DateFormatter('%b'))
    plt.xticks(rotation=45)
    ax4.grid(True, linestyle='--', alpha=0.5)
    fig4.tight_layout()
    yearly_img = plot_to_base64(fig4)

    graphs = {
        'daily': daily_img,
        'weekly': weekly_img,
        'monthly': monthly_img,
        'yearly': yearly_img
    }

    if carbon <= 5:
        insight = "✅ Good job! Your current habits are relatively sustainable."
    elif carbon <= 10:
        insight = "⚠️ Moderate carbon footprint. Some improvements are recommended."
    else:
        insight = "❌ High carbon footprint! Consider reducing travel, energy use, or diet impact."

    return render_template('result.html', graphs=graphs, carbon=carbon, insight=insight)


if __name__ == '__main__':
    app.run(ssl_context='adhoc', debug=True)
