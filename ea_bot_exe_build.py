if __name__ == "__main__":
    try:
        import multiprocessing
        from bot import bot_runner
        multiprocessing.freeze_support()
        print("🤖🤖🤖EA Python bot 1.2 💰💰💰")
        input("🙏Please enter any key to start\n")

        while True:

            print("🤖 Starting bot....🚀\n")
            bot_runner()
    except Exception as e:
        print(f"❌❌❌❌❌❌❌❌❌❌❌❌❌❌\n")
        print(f"😞❌[Error] Get exception {e}. 💀\n")
        print(
            "✍Please capture this error and send it to adminstrators for analyzing issue\n"
        )
        input("🙏Enter any key to restart program\n")
