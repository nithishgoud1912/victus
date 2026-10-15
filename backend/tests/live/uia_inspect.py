from pywinauto import Desktop


def main() -> None:
    # Inspection only. Do not guess a window and begin typing into it.
    for window in Desktop(backend="uia").windows():
        print(window.process_id(), window.handle, window.window_text())


if __name__ == "__main__":
    main()