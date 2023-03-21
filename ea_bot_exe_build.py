from bot import bot_runner
import multiprocessing

if __name__ == "__main__":
    multiprocessing.freeze_support()
    bot_runner()