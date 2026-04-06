# ReAct Agent: Trích xuất dữ liệu lãi suất gửi tiết kiệm ngân hàng và tính lợi nhuận. 
_Đây là một bài tập về nhà_
## How to Run the Demo

Follow these steps to set up the environment and run the ReAct Agent demo:

**Step 1: Configure the API Key** Open the `main.py` file and modify the `api_key` parameter in the `OpenAIProvider` initialization with your actual OpenAI API Key.

**Step 2: Install `uv` (Fast Python Package Manager)** Run the appropriate command for your operating system to install `uv`:
* **Windows:**
    ```powershell
    powershell -ExecutionPolicy ByPass -c "irm [https://astral.sh/uv/install.ps1](https://astral.sh/uv/install.ps1) | iex"
    ```
* **Linux/macOS:**
    ```bash
    curl -LsSf [https://astral.sh/uv/install.sh](https://astral.sh/uv/install.sh) | sh
    ```

**Step 3: Initialize the project** ```bash
uv init
