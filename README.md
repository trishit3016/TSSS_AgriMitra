# 🌱 AgriChain: Farm-to-Market Intelligence Platform

**AgriChain** is an intelligent, farm-to-market recommendation engine designed specifically for Indian farmers. By acting as a "Trust Engine," it bridges the gap between complex agricultural data and actionable, plain-language advice to tell farmers exactly **when to harvest**, **where to sell**, and most importantly, **why** that is the best decision.

---

## ⚠️ The Problem

Despite advancements in agricultural techniques, India's farmers lose up to **40% of their produce post-harvest**. This massive loss is rarely due to poor farming practices; it is a logistics and information problem caused by:
- **Poor Timing:** Harvesting right before unseasonal rain or a heatwave.
- **Market Mismatch:** Selling at a local market flooded with supply, while a Mandi 50km away is paying a premium.
- **The "Trust Gap":** Existing agritech apps dump raw data onto farmers who lack data literacy. Farmers do not trust "black box" recommendations that lack reasoning.

---

## 💡 Our Approach (The Solution)

We are not just building a data dashboard; we are building an **Explainable AI (XAI) Trust Engine**.

### 1. The "Why" Over the "What"
Farmers will only take action if they trust the system. Instead of simply generating a command, AgriChain translates complex data overlaps into a natural language narrative.
> *Example: "Wait to harvest your wheat. Heavy rain is expected which increases crop damage risk, but Azadpur Mandi prices are rising and expected to be +₹200/quintal in 3 days."*

### 2. Intelligent Spoilage Risk Mitigation
Beyond the harvest, the system evaluates post-harvest transit. It calculates the biological clock of the specific crop against real-time temperature and transit distance, outputting ranked, cost-effective preservation actions (e.g., *"Elevate Grain Bags - Low Cost"* or *"Cover with Tarpaulin"*).

### 3. Reality-First UI/UX
Designed for a farmer holding a basic Android phone in a field with patchy 3G/4G internet. Heavy graphs, loading screens, and complex menus are completely eliminated in favor of **Action Cards** and **Progressive Disclosure**.

---

## 📱 App Interface & Features

*(Replace the image paths below with your actual repository image paths)*

### 1. Action-Oriented Dashboard
Instead of complex charts, farmers see an immediate, traffic-light status (e.g., "WAIT TO HARVEST") backed by simple, expandable "Why?" reasoning cards.
![Harvest Status Dashboard](./docs/screenshot-dashboard.png)

### 2. Live Market Intelligence
Compare current prices across nearby Mandis. See exactly how far away the market is and the current selling price per quintal.
![Mandi Price Comparison](./docs/screenshot-market.png)

### 3. Storage Risk & Preservation 
Real-time tracking of humidity and spoilage risks, accompanied by actionable, cost-ranked preservation tips that farmers can mark as complete.
![Storage Risk & Tips](./docs/screenshot-storage.png)

---

## 🛠️ Technical Architecture & Tech Stack

To ensure ultra-low latency on mobile networks while delivering complex AI reasoning, AgriChain utilizes a **Tool-Calling Agentic Architecture** rather than a slow, heavy multi-agent system.

* **Frontend:** Flutter
  * *Why:* Compiles to highly optimized native code for low-end Android devices and handles offline caching beautifully.
* **Backend:** Python (FastAPI)
  * *Why:* Fast, lightweight, and inherently designed to handle the asynchronous API calls needed for our AI and data fetching.
* **AI Orchestrator (The Brain):** Kimi K2.5 via NVIDIA NIM API
  * *Why:* Exceptionally strong at tool-calling and reasoning. Cloud-hosted via NVIDIA NIM ensures no heavy local models are needed.
* **Knowledge Graph (The Memory):** Neo4j (GraphRAG)
  * *Why:* Maps dynamic relationships between entities (e.g., `Crop` -> *is vulnerable to* -> `High Humidity` -> *present in* -> `Nagpur`).
* **Data Sources (The Fuel):**
  * **AIKosh:** For localized, official Indian agricultural datasets and Mandi prices.
  * **OpenWeatherMap API:** For hyper-local, real-time 5-day weather forecasting.

---

## ⚙️ How the System Works (Data Flow)

1. **Trigger:** The farmer opens the app. The app securely sends their location, crop type, and local storage conditions to the FastAPI backend.
2. **Orchestration:** The LangChain agent (powered by Kimi K2.5) receives the request and determines what information it needs.
3. **Tool Execution:** 
   * Queries **AIKosh** for current market prices in surrounding Mandis.
   * Queries **OpenWeatherMap** for the 5-day forecast.
   * Queries the **Neo4j Graph Database** to determine the exact spoilage risk for that specific crop under current weather conditions.
4. **Synthesis:** Kimi K2.5 evaluates the retrieved data, runs logical checks, and generates a plain-language recommendation.
5. **Delivery:** The Flutter app receives a clean JSON payload and renders it into the simple, reality-first UI using Action Cards and a Traffic Light system.

---

## 🚀 Getting Started

### Prerequisites
* Flutter SDK (v3.0+)
* Python 3.9+
* Neo4j Database Instance
* API Keys for NVIDIA NIM, AIKosh, and OpenWeatherMap

### Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/trishit3016/TSSS_AgriMitra.git
   cd TSSS_AgriMitra
   ```

2. **Backend Setup:**
   ```bash
   cd backend
   python -m venv venv
   source venv/bin/activate  # On Windows use `venv\Scripts\activate`
   pip install -r requirements.txt
   ```
   *Create a `.env` file in the backend directory and add your API keys.*

3. **Frontend Setup:**
   ```bash
   cd frontend
   flutter pub get
   ```

4. **Run the Application:**
   * **Start FastAPI Server:** `uvicorn main:app --reload`
   * **Start Flutter App:** `flutter run`

---

## 🤝 Contributing
Contributions, issues, and feature requests are welcome! Feel free to check the [issues page](https://github.com/trishit3016/TSSS_AgriMitra/issues).

## 📄 License
This project is licensed under the [MIT License](LICENSE).