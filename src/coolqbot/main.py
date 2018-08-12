import argparse
import logging

from coolqbot.logger import logger

def main_loop(debug=False):
    if debug:
        logger.setLevel(logging.DEBUG)
    logger.info("Initializing...")


def run():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--debug",
        action="store_true",
        default=False,
        help="Switch to DEBUG mode for better view of message."
    )
    args = parser.parse_args()
    main_loop(**vars(args))


if __name__ == "__main__":
    run()
