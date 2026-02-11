from dotenv import load_dotenv

load_dotenv()  # must run before juntos.config is imported

from juntos import create_app


def main():
    app = create_app()
    app.run(host="localhost", debug=True)


if __name__ == "__main__":
    main()
