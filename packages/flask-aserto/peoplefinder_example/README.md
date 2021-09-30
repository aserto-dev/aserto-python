# PeopleFinder example Flask app
The PeopleFinder app is used to introduce you to Aserto authorization concepts in Aserto's official [Getting Started](https://docs.aserto.com/docs/getting-started/quickstart) guide.

## Running the app
You'll want to follow the steps in the guide, but instead of deploying the app, you'll be running it locally.

Clone the PeopleFinder demo source:
```sh
git clone https://github.com/aserto-demo/peoplefinder
```

To start running the demo, navigate to the `peoplefinder` directory run the following in your terminal:
(You'll need to have [Yarn](https://classic.yarnpkg.com/en/docs/install) installed)
```sh
yarn
yarn spa
```
This might open up a web page at "https://localhost:3000" in your browser. This is expected, but it won't work just yet.

Now in your local clone of the Flask PeopleFinder demo (where this README is located), you'll need to follow a couple more steps.

Follow the instructions in [`.env.example`](https://github.com/aserto-dev/aserto-python/blob/main/packages/flask-aserto/peoplefinder_example/.env.example) to create a local `.env` configuration file with your Aserto credentials.

Now start the Flask server:
(You'll need to have [Poetry](https://python-poetry.org/docs/#installation) installed)
```sh
poetry install
poetry run flask run
```
The server should be running on port 3001.

Now head back to your browser and open "https://localhost:3000". The [Exploring PeopleFinder](https://docs.aserto.com/docs/getting-started/exploring-peoplefinder) guide will help you find your way around and see Aserto's features in action.

## Exploring the source code
- [`app.py`](https://github.com/aserto-dev/aserto-python/blob/main/packages/flask-aserto/peoplefinder_example/app.py) - is where the app's routes are defined.
- [`aserto_options.py`](https://github.com/aserto-dev/aserto-python/blob/main/packages/flask-aserto/peoplefinder_example/aserto_options.py) - provides an example of how to load configuration into your environment and pass it to the Aserto middleware. It makes use of the [`aserto-idp`](https://github.com/aserto-dev/aserto-python/tree/main/packages/aserto-idp) package to connect Auth0 identities to the middleware.