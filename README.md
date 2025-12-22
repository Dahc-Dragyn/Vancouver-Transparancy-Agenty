# ForgeControl: Vancouver Transparency Agent (VTA)

**ForgeControl** is a specialized API Orchestrator and Governance Plane designed to automate municipal transparency. It uses **Gemini 2.5 Flash Lite** to scout, analyze, and score government data, ensuring only high-value "signals" reach the end user.

---

## 🌟 Core Features

- **Automated Scouting:** Uses Playwright to navigate and scrape municipal meeting portals (iCompass, CivicClerk).
- **Intelligence Layer:** Leverages Gemini 2.5 Flash Lite for real-time impact analysis and scoring (1-10 scale).
- **Signal Firewall:** ForgeControl acts as a gateway, filtering out low-score noise (Scores 1-5) and escalating high-priority alerts (Scores 7+).
- **MCP Integration:** Implements the Model Context Protocol, allowing the agent to function as a tool for broader AI ecosystems.
- **Firebase Persistence:** Securely stores organizations, board settings, and analyzed signals.

---

## 🏗️ Architecture

ForgeControl follows a "Control Plane" architecture:
1. **The Scout:** Playwright-based scraper extracts raw text from portals.
2. **The Brain:** Gemini 2.5 analyzes text against industry-specific keywords.
3. **The Gateway:** ForgeControl validates the output, checks against score thresholds, and logs the action.
4. **The Memory:** Firestore records the finalized "Signal" for the dashboard.

---

## 🚀 Quick Start

### 1. Installation
```bash
# Clone the repo
git clone [https://github.com/Dahc-Dragyn/Vancouver-Transparancy-Agenty.git](https://github.com/Dahc-Dragyn/Vancouver-Transparancy-Agenty.git)
cd Vancouver-Transparancy-Agenty

# Install dependencies
pip install -r requirements.txt
playwright install chromium