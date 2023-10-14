# MetaTrader EA Bot: Automated Trading Simplified

## Introduction

Welcome to MetaTrader EA Bot, your go-to automated trading bot for the MetaTrader 5 platform. Built to execute trades using the insights of master traders, this bot provides automated capabilities for initiating, updating, and filtering trades according to your predefined criteria.

## Table of Contents

- [Getting Started](#getting-started)
  - [Installation](#installation)
  - [Configuration](#configuration)
  - [How to Use](#how-to-use)
- [Building the Executable](#building-the-executable)
- [Code Anatomy](#code-anatomy)
- [Get Involved](#get-involved)
- [Legal](#legal)
  - [License](#license)

## Getting Started

### Installation

1. Open a terminal window and navigate to the root folder of the project.
2. To install necessary dependencies, type the command: 'poetry install'

### Configuration

Before you run the bot, it's essential to set up your MetaTrader 5 login credentials and specify which master traders you wish to follow.

1. Locate and open the 'terminal_login.json' file.
2. Fill in your MetaTrader 5 login details and specify your preferred master traders to follow.

Sample format for 'terminal_login.json':
```
{
  "username": "your_username",
  "password": "your_password",
  "master_traders": ["trader_1", "trader_2"]
}
```
### How to Use

1. Open a terminal window and navigate to the root folder of the project.
2. To run the bot, execute the Python code: 'from bot import bot_runner; bot_runner()'

## Building the Executable

1. Go to the directory containing the 'build.bat' script.
2. To build a standalone version of the bot, run the command: 'build.bat'

## Code Anatomy

- 'bot.py': Houses the core classes and methods
  - 'TradingFromSignal': Central class containing methods for bot operation, signal processing, and exception handling.
  - 'worker()': Initializes an instance of 'TradingFromSignal' and executes the bot.
  - 'validate_mt5_settings()': Validates MetaTrader 5 configurations.
  - 'bot_runner()': Manages the configuration, validates settings, and initiates the bot.

- 'build.bat': A script for compiling the bot into an executable
  - Captures the current build timestamp.
  - Compiles into a standalone executable.
  - Copies 'terminal_login.json' and 'version.py' to the output directory.

## Get Involved

For contribution guidelines, please see the 'CONTRIBUTING.md' file.

## Legal

### License

This software is under the MIT License. Refer to the 'LICENSE.md' file for full details.
