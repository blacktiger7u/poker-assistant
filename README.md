# ♠️ Poker Assistant
Advanced desktop app which helps in real time **Texas Hold'em**  poker game. This program combines advanced math, monte carlo simulaiton and capital management giving the most precise strategic recommendations.

---

## 🚀 MAIN FEATURES

* **GUI (PyQt6):** Intuitive Dark themed GUI which containt visual card animations, containing UI scaling, amount of simulations,table positions and player count
* **Monte Carlo engine:** Up to 100 000 simulations in (`QThread`), preventing GUI.
* **Outs and draw calculator:** Automatically count outs after Flop and Turn abd chances of getting them (Rule of 2/4).
* **Pot Odds & Bankroll Manager:** Dynamic equity counting (Breakeven Point) and risk management depending on your balance in order to reduce a risk of bankruptcy.
* **Decision Engine:** Generates suggested actuib, confidence of an algorithm and logical explanation (counting table position: UTG, MP, CO, BTN, SB, BB and player count).

---

## 🛠️ TECHNOLOGIES

Libraries used in a project:

* **Python 3.10+**
* **PyQt6** – GUI
* **treys** – Poker Hand analisys
* **numpy** & **pandas** 

---

## 📦 How to install

1. Open terminal and install required dependencies

pip install -r requirements.txt

2. Run the application

python main.py
