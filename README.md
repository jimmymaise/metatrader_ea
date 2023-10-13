# MetaTrader EA Bot

## Overview

The MetaTrader EA Bot is an automated trading bot designed to interact with the MetaTrader 5 trading platform. Utilizing signals from master traders, it automates trading actions such as creating new trades, updating existing trades, and ignoring signals based on pre-defined criteria.

## Table of Contents

- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [Building the Bot](#building-the-bot)
- [Code Overview](#code-overview)
- [Contributing](#contributing)
- [License](#license)
- [Contact](#contact)

## Installation

To install the necessary dependencies, follow the steps below:

1. Open your terminal and navigate to the project's root directory.
2. Run the following command:
   \`\`\`
   poetry install
   \`\`\`

## Configuration

Before running the bot, you must configure your MetaTrader 5 login credentials and specific bot settings.

1. Open the `terminal_login.json` file.
2. Enter your MetaTrader 5 login credentials and specify which master traders to follow.

Here's an example of what the `terminal_login.json` file should look like:
\`\`\`json
{
  "username": "your_username",
  "password": "your_password",
  "master_traders": ["trader_1", "trader_2"]
}
\`\`\`

## Usage

To run the MetaTrader EA Bot:

1. Open your terminal and navigate to the project's root directory.
2. Run the following Python code:
   \`\`\`python
   from bot import bot_runner
   bot_runner()
   \`\`\`

## Building the Bot

To build a standalone executable version of the bot:

1. Navigate to the directory containing the `build.bat` script.
2. Run the following command:
   \`\`\`
   build.bat
   \`\`\`

This script will package the bot as a standalone executable and copy necessary files to the distribution directory.

## Code Overview

- `bot.py`: Contains the core classes and functions
  - `TradingFromSignal`: Main class, includes methods for running the bot, processing signals, and handling exceptions.
  - `worker()`: Function that initializes an instance of `TradingFromSignal` and runs the bot.
  - `validate_mt5_settings()`: Function that validates MetaTrader 5 settings.
  - `bot_runner()`: Reads the configuration, validates settings, and starts the bot.

- `build.bat`: Script to build the bot into an executable file
  - Captures the current build time.
  - Compiles into a standalone executable.
  - Copies `terminal_login.json` and `version.py` files to the distribution directory.

## Contributing

For information on how to contribute, please refer to the [CONTRIBUTING.md](CONTRIBUTING.md) file.

## License

This project is licensed under the MIT License. See the [LICENSE.md](LICENSE.md) file for details.

