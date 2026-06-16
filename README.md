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

```bash
pip install -r requirements.txt
```

2. Run the application

```bash
python main.py
```

<img width="1448" height="853" alt="{B3393C47-90FA-4769-BB4F-470217DE2DEB}" src="https://github.com/user-attachments/assets/fc11beda-4e46-4a14-a4b6-79dc1cbee308" />
<img width="1552" height="862" alt="{ED2C0657-7225-469D-95B5-937A868AA347}" src="https://github.com/user-attachments/assets/8ddab1de-4bb1-42e9-a4aa-e951e3705d20" />

