from datetime import datetime

from flask import Flask

app = Flask(__name__)

GREETINGS = (
    'Хорошего понедельника',
    'Хорошего вторника',
    'Хорошей среды',
    'Хорошего четверга',
    'Хорошей пятницы',
    'Хорошей субботы',
    'Хорошего воскресенья'
)


@app.route('/hello-world/<name>')
def hello_world(name: str) -> str:
    weekday: int = datetime.today().weekday()
    greeting: str = GREETINGS[weekday]
    return f'Привет, {name}. {greeting}!'


if __name__ == '__main__':
    app.run(debug=True)



from unittest import TestCase
from freezegun import freeze_time
from module_03_ci_culture_beginning.homework.hw1.hello_word_with_day import app


class TestHelloWorldWithDay(TestCase):

    def setUp(self):
        app.config['TESTING'] = True
        app.config['DEBUG'] = False
        self.app = app.test_client()
        self.base_url = '/hello-world/'

    # @classmethod
    # def setUpClass(cls):
    #     app.config["TESTING"] = True
    #     app.config["DEBUG"] = False
    #     cls.app = app.test_client()
    #     cls.base_url = "/hello_world/"

    def test_can_get_correct_greetings(self):
        with freeze_time("2023-06-20"):
            greet_count = len(greeting := "Хорошего вторника")
            username = "username"
            response = self.app.get(self.base_url + username)
            response_text = response.data.decode()
            self.assertEqual(response_text[-greet_count-1:-1], greeting)

    def test_can_get_not_correct_username(self):
        with freeze_time("2023-06-20"):
            usrn_count = len(username := "username")
            response = self.app.get(self.base_url + "Хорошей среды")
            response_text = response.data.decode()
            self.assertNotEqual(response_text[8: 8 + usrn_count], username)
