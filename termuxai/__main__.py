from termuxai.app import run


if __name__ == "__main__":
    try:
        run()
    except KeyboardInterrupt:
        print("\n\nTermuxAI closed.")