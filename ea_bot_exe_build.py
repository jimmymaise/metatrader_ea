from bot import bot_runner
import multiprocessing

if __name__ == "__main__":
    multiprocessing.freeze_support()
    print('EA Python bot 1.0\n')
    input("Please enter any key to start\n");

    while True:
        try:
            print('Starting bot....\n')
            bot_runner()
        except Exception as e:
            print(f"[Error] Get exception {e}.\n");
            print("Please capture this error and send it to adminstrators for analyzing issue\n");
            input("Enter any key to restart program\n");

        